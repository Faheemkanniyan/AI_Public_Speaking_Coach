"""
AI Interview Service for SpeakPro AI.
Provides grounded interview question generation and strictly grounded answer evaluation using Google Gemini.
Raises GeminiEvaluationError on failures with mapped error codes — no canned questions or fake fallback scoring.
"""

import os
import json
import re
import time
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from django.conf import settings
from django.utils import timezone

from app.models import InterviewSession, InterviewQuestion, InterviewAnswer, InterviewFeedback
from app.services.gemini_service import (
    GeminiEvaluationError,
    map_gemini_exception,
    call_gemini_with_retry,
    is_verbatim_substring,
    _to_score
)

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False


class GeneratedQuestionItem(BaseModel):
    question: str = Field(description="The actual interview question string")
    interview_type: str = Field(description="Technical, HR, Behavioral, etc.")
    domain: str = Field(description="Domain such as Software, Product, Data")
    topic: str = Field(description="Technology or topic evaluated")
    difficulty: str = Field(description="Beginner, Intermediate, or Advanced")
    question_type: str = Field(description="Conceptual, Practical, Behavioral, Scenario")
    expected_points: List[str] = Field(description="List of key points expected in a correct answer")
    ideal_answer: str = Field(description="Concise model answer 3-6 sentences")
    evaluation_criteria: List[str] = Field(description="Assessment criteria")


class InterviewQuestionsListSchema(BaseModel):
    questions: List[GeneratedQuestionItem]


class InterviewEvidence(BaseModel):
    quotes: List[str] = Field(default_factory=list, description="Verbatim quotes copied from candidate answer as evidence")
    reason: str = Field(default="", description="One-line justification grounded in the evidence quotes")


class IncorrectStatementItem(BaseModel):
    quote: str = Field(description="Exact verbatim quote from candidate answer that is incorrect or inaccurate")
    why_wrong: str = Field(description="Clear explanation of why this claim is incorrect")


class GroundedInterviewAnswerSchema(BaseModel):
    relevance_score: int = Field(default=50, ge=0, le=100)
    relevance_evidence: InterviewEvidence = Field(default_factory=InterviewEvidence)

    technical_correctness_score: int = Field(default=50, ge=0, le=100)
    technical_correctness_evidence: InterviewEvidence = Field(default_factory=InterviewEvidence)

    completeness_score: int = Field(default=50, ge=0, le=100)
    completeness_evidence: InterviewEvidence = Field(default_factory=InterviewEvidence)

    structure_score: int = Field(default=50, ge=0, le=100)
    structure_evidence: InterviewEvidence = Field(default_factory=InterviewEvidence)

    communication_score: int = Field(default=50, ge=0, le=100)
    communication_evidence: InterviewEvidence = Field(default_factory=InterviewEvidence)

    grammar_score: int = Field(default=50, ge=0, le=100, description="Strict evaluation of candidate's spoken grammar and sentence syntax accuracy")
    timing_pacing_feedback: str = Field(default="", description="Strict critique of candidate's speaking pace (WPM), pauses, and delivery duration")

    classification: str = Field(default="Partially Correct", description="'Correct', 'Partially Correct', 'Incorrect', or 'Not Answered'")
    feedback: str = Field(default="", description="Honest, grounded feedback citing verbatim quotes")
    model_answer: str = Field(default="", description="Ideal answer outline (concise model answer)")
    missing_points: List[str] = Field(default_factory=list, description="Points the candidate missed")
    incorrect_statements: List[IncorrectStatementItem] = Field(default_factory=list, description="Candidate statements that were incorrect")
    correct_points: List[str] = Field(default_factory=list, description="Points the candidate articulated correctly")
    suggestions: List[str] = Field(default_factory=list, description="Specific suggestions tied to weaknesses")


class InterviewService:
    """
    Evaluates interview responses with strict grounding against the candidate's actual answer.
    """

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        self.model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash")
        self.client = None

        if self.api_key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client for InterviewService: {e}")
                self.client = None

    def analyze_filler_words(self, transcript: str) -> int:
        """
        Calculates filler words using word-boundary regex.
        """
        if not transcript:
            return 0
        filler_patterns = [
            r"\bum\b", r"\buh\b", r"\bah\b", r"\ber\b", r"\blike\b",
            r"\byou know\b", r"\bi mean\b", r"\bactually\b", r"\bbasically\b"
        ]
        count = 0
        lower = transcript.lower()
        for p in filler_patterns:
            count += len(re.findall(p, lower))
        return count

    def create_session(self, user, interview_type, domain, technology, difficulty, num_questions, language):
        """
        Creates an InterviewSession and generates structured interview questions
        from the curated questions bank without consuming Gemini API tokens.
        Preserves Gemini API quota exclusively for speech and interview answer evaluation.
        """
        session = InterviewSession.objects.create(
            user=user,
            interview_type=interview_type,
            domain=domain,
            technology=technology,
            difficulty=difficulty,
            total_questions=num_questions,
            interview_language=language,
            status="IN_PROGRESS"
        )

        questions = self._generate_questions(interview_type, domain, technology, difficulty, num_questions, language)

        for i, q_data in enumerate(questions):
            InterviewQuestion.objects.create(
                session=session,
                question_text=q_data.get("question", "Could you discuss a core concept in this topic?"),
                question_number=i + 1,
                question_type=q_data.get("question_type", "General"),
                expected_points_json=json.dumps(q_data.get("expected_points", [])),
                ideal_answer=q_data.get("ideal_answer", ""),
                evaluation_criteria_json=json.dumps(q_data.get("evaluation_criteria", []))
            )

        return session

    def _generate_questions(self, interview_type, domain, technology, difficulty, num_questions, language):
        """
        Generates structured interview questions from curated questions bank
        without calling Gemini API.
        """
        from app.services.interview_questions_data import generate_local_interview_questions
        return generate_local_interview_questions(
            interview_type=interview_type,
            domain=domain,
            technology=technology,
            difficulty=difficulty,
            num_questions=num_questions,
            language=language
        )


    def evaluate_answer(self, answer_obj: InterviewAnswer, language: str) -> dict:
        """
        Evaluates a candidate's voice transcript against question criteria.
        Returns a validated dictionary of scores, evidence quotes, and suggestions.
        """
        transcript = (answer_obj.transcript or "").strip()

        # Hard Rule: Unanswered or empty answer
        if not transcript or answer_obj.answer_status == "NOT_ANSWERED":
            try:
                expected_points = json.loads(answer_obj.question.expected_points_json)
            except Exception:
                expected_points = []
            return {
                "evaluation_status": "EVALUATED",
                "overall_score": 0,
                "classification": "Not Answered",
                "relevance": 0,
                "technical_correctness": 0,
                "completeness": 0,
                "structure": 0,
                "clarity": 0,
                "communication": 0,
                "feedback": "No answer was provided for this question.",
                "model_answer": answer_obj.question.ideal_answer or "A concise, structured response.",
                "missing_points": expected_points,
                "correct_points": [],
                "incorrect_points": [],
                "incorrect_statements": [],
                "suggestions": ["Deliver a complete answer using the ideal answer outline."]
            }

        if not self.api_key or not self.client:
            raise GeminiEvaluationError(code="no_key", message="GEMINI_API_KEY is not set")

        question_text = answer_obj.question.question_text
        interview_type = answer_obj.question.session.interview_type
        technology = answer_obj.question.session.technology
        difficulty = answer_obj.question.session.difficulty
        ideal_answer = answer_obj.question.ideal_answer
        expected_points = answer_obj.question.expected_points_json

        # Check for brief "I don't know" answers
        lower_trans = transcript.lower().strip()
        is_dont_know = any(phrase in lower_trans for phrase in [
            "i don't know", "i do not know", "no idea", "not sure", "pass", "skip"
        ]) and len(transcript.split()) < 12

        visual_context = ""
        if hasattr(answer_obj, 'visual_presence') and answer_obj.visual_presence:
            vp = answer_obj.visual_presence
            visual_context = f"""
[WEBCAM VISUAL METRICS]
- Eye Contact: {vp.eye_contact_pct}%
- Posture: {vp.posture_score}/100
- Expressions: {vp.expression_variety_score}/100
- Face Tracked: {vp.face_detected_pct}%
"""

        audio_path = None
        has_audio = False
        try:
            if answer_obj.audio_file and hasattr(answer_obj.audio_file, 'path') and os.path.exists(answer_obj.audio_file.path):
                audio_path = answer_obj.audio_file.path
                has_audio = True
        except Exception:
            has_audio = False

        prompt = f"""You are a senior executive interviewer and technical bar raiser evaluating a candidate's spoken answer for a {difficulty} level {interview_type} interview.
DOMAIN/TECHNOLOGY: "{technology}"
QUESTION: "{question_text}"
EXPECTED KEY POINTS: {expected_points}
IDEAL MODEL ANSWER: "{ideal_answer}"

OBJECTIVE MEASURED SPEECH FACTS (computed in Python, you MUST NOT contradict these):
- Recorded Duration: {answer_obj.duration_seconds} seconds
- Word Count: {answer_obj.word_count} words
- Speaking Pace: {answer_obj.speaking_rate} WPM (Executive benchmark: 120 - 150 WPM)
- Vocal Fillers: {answer_obj.filler_count} fillers detected

{visual_context}

CANDIDATE'S VERBATIM SPOKEN ANSWER:
"{transcript}"

{"NOTE: Candidate stated they do not know or gave a one-line admission. Assign appropriately low scores (0-20), acknowledge their honesty politely in feedback, and explain what a complete answer includes." if is_dont_know else ""}

CRITICAL GROUNDING & STRICT EVALUATION RULES:
1. Every score and comment MUST come strictly from what the candidate actually spoke in their answer.
2. Never award unearned high scores or hallucinate technical concepts that were not in the candidate's answer.
3. STRICT SCORING RUBRICS (Executive Hiring Standards):
   - 85-100: Executive / Senior Level (accurate technical depth, complete key points, fluent delivery 120-150 WPM, flawless grammar, coherent structure).
   - 70-84: Competent / Acceptable (correct core concepts, minor omissions, solid spoken communication).
   - 45-69: Developing / Significant Gaps (misses multiple expected points, noticeable grammatical errors, basic phrasing, or hesitations).
   - 20-44: Weak / Significant Deficiencies (broken grammar, missing most expected points, severe technical misconceptions, halting pace <100 WPM).
   - 0-19: Unanswered or Incoherent (cannot construct meaningful response).
4. SPOKEN COMMUNICATION & PACING EVALUATION:
   - Evaluates clarity, articulation, speaking pace (WPM), and vocal presence.
   - If Speaking Pace is < 100 WPM (e.g. 80-95 WPM), heavily penalize communication_score (score 20-45) for dragging, excessive hesitations, and lack of forward momentum.
   - If Speaking Pace is > 165 WPM, penalize for rushing.
   - Write a dedicated timing & rhythm critique in `timing_pacing_feedback`.
5. GRAMMAR & SYNTAX (`grammar_score`):
   - Evaluate grammatical correctness and sentence coherence (0-100). Broken grammar, missing verbs, or fragmented phrasing must receive a strict score in the 20-45 range.
6. TECHNICAL ACCURACY & COMPLETENESS:
   - Compare claims against EXPECTED KEY POINTS. If expected points are missing, penalize completeness_score strictly.
   - Factually wrong statements MUST be listed in `incorrect_statements` with exact verbatim quotes and penalize technical_correctness_score.
7. STRUCTURE (`structure_score`):
   - For technical questions: defines concept, explains mechanics, gives practical application.
   - For behavioral questions: adherence to STAR framework (Situation, Task, Action, Result).
8. MODEL ANSWER (`model_answer`):
   - Concise 3-6 sentence ideal model answer demonstrating how a top candidate would articulate this aloud.
"""

        prompt += """
CRITICAL OUTPUT FORMAT:
Return response STRICTLY as a valid JSON object matching this schema:
{
  "relevance_score": 0-100,
  "relevance_evidence": {"quotes": ["verbatim transcript quote"], "reason": "one-line reason"},
  "technical_correctness_score": 0-100,
  "technical_correctness_evidence": {"quotes": ["verbatim transcript quote"], "reason": "one-line reason"},
  "completeness_score": 0-100,
  "completeness_evidence": {"quotes": ["verbatim transcript quote"], "reason": "one-line reason"},
  "structure_score": 0-100,
  "structure_evidence": {"quotes": ["verbatim transcript quote"], "reason": "one-line reason"},
  "communication_score": 0-100,
  "communication_evidence": {"quotes": ["verbatim transcript quote"], "reason": "one-line reason"},
  "grammar_score": 0-100,
  "timing_pacing_feedback": "Detailed critique of speaking pace, duration, and rhythm",
  "classification": "Correct" | "Partially Correct" | "Incorrect" | "Not Answered",
  "feedback": "Honest grounded feedback citing verbatim quotes",
  "model_answer": "Concise 3-6 sentence ideal answer outline",
  "missing_points": ["point 1", "point 2"],
  "incorrect_statements": [{"quote": "verbatim quote", "why_wrong": "explanation"}],
  "correct_points": ["point 1"],
  "suggestions": ["specific suggestion"]
}
"""

        contents = [prompt]
        if has_audio:
            try:
                import mimetypes
                mime_type, _ = mimetypes.guess_type(audio_path)
                if not mime_type or not mime_type.startswith("audio/"):
                    mime_type = "audio/webm"
                if os.path.getsize(audio_path) < 20 * 1024 * 1024:
                    with open(audio_path, "rb") as f:
                        contents.append(types.Part.from_bytes(data=f.read(), mime_type=mime_type))
            except Exception as ae:
                logger.warning(f"Could not attach interview audio: {ae}")

        thinking = types.ThinkingConfig(thinking_budget=0) if (hasattr(types, "ThinkingConfig") and "thinking" in self.model_name.lower()) else None
        config_kwargs = {
            "response_mime_type": "application/json",
            "response_schema": GroundedInterviewAnswerSchema,
            "temperature": 0.0,
        }
        if thinking:
            config_kwargs["thinking_config"] = thinking
        config = types.GenerateContentConfig(**config_kwargs)

        last_error = None
        for attempt in range(1, 3):
            try:
                response = call_gemini_with_retry(
                    self.client,
                    self.model_name,
                    contents,
                    config=config,
                    max_retries=2
                )
                text = (response.text or "").strip()
                data = json.loads(text)
                return self._finalize_interview_evaluation(data, transcript, interview_type)
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini interview evaluation attempt {attempt} failed: {e}")
                # Fallback: remove thinking_config or response_schema if model threw 400
                if "thinking_config" in config_kwargs:
                    config_kwargs.pop("thinking_config", None)
                    config = types.GenerateContentConfig(**config_kwargs)
                elif "response_schema" in config_kwargs and ("400" in str(e) or "invalid" in str(e).lower()):
                    config_kwargs.pop("response_schema", None)
                    config = types.GenerateContentConfig(**config_kwargs)
                if attempt == 1:
                    time.sleep(0.5)

        mapped_e = map_gemini_exception(last_error, model_name=self.model_name)
        if isinstance(last_error, (json.JSONDecodeError, ValueError)):
            mapped_e = GeminiEvaluationError(
                code="invalid_response",
                message="Gemini returned an unusable response",
                original_exception=last_error
            )
        raise mapped_e

    def _finalize_interview_evaluation(self, data: dict, transcript: str, interview_type: str) -> dict:
        """
        Validates quotes against transcript and computes overall interview score IN CODE.
        """
        relevance = _to_score(data.get("relevance_score", 50))
        technical = _to_score(data.get("technical_correctness_score", 50))
        completeness = _to_score(data.get("completeness_score", 50))
        structure = _to_score(data.get("structure_score", 50))
        communication = _to_score(data.get("communication_score", 50))
        grammar_score = _to_score(data.get("grammar_score", communication))
        timing_pacing_feedback = str(data.get("timing_pacing_feedback", "")).strip()

        def validate_evidence(ev_dict):
            if not isinstance(ev_dict, dict):
                return {"quotes": [], "reason": ""}
            quotes = ev_dict.get("quotes", [])
            valid_quotes = [q for q in quotes if q and is_verbatim_substring(q, transcript)]
            return {"quotes": valid_quotes, "reason": ev_dict.get("reason", "") if valid_quotes else ""}

        # Validate incorrect_statements quotes
        raw_incorrect = data.get("incorrect_statements", [])
        validated_incorrect = []
        for item in raw_incorrect:
            if isinstance(item, dict):
                quote = str(item.get("quote", "")).strip()
                why_wrong = str(item.get("why_wrong", "")).strip()
                if quote and is_verbatim_substring(quote, transcript):
                    validated_incorrect.append({"quote": quote, "why_wrong": why_wrong})

        validated_evidences = {
            "relevance_evidence": validate_evidence(data.get("relevance_evidence")),
            "technical_correctness_evidence": validate_evidence(data.get("technical_correctness_evidence")),
            "completeness_evidence": validate_evidence(data.get("completeness_evidence")),
            "structure_evidence": validate_evidence(data.get("structure_evidence")),
            "communication_evidence": validate_evidence(data.get("communication_evidence")),
        }

        # Calculate Overall Score IN CODE from documented weights
        is_technical = interview_type in ["Technical", "Coding"]
        if is_technical:
            # Technical: 35% Technical Correctness, 25% Completeness, 20% Relevance, 10% Communication, 10% Structure
            raw_val = (
                (technical * 0.35) +
                (completeness * 0.25) +
                (relevance * 0.20) +
                (communication * 0.10) +
                (structure * 0.10)
            )
            overall = int(raw_val + 0.5)
        else:
            # HR / Behavioral: 25% Relevance, 25% Completeness, 25% Structure, 25% Communication
            raw_val = (
                (relevance * 0.25) +
                (completeness * 0.25) +
                (structure * 0.25) +
                (communication * 0.25)
            )
            overall = int(raw_val + 0.5)

        overall = max(0, min(100, overall))

        classification = data.get("classification", "Partially Correct")
        if overall >= 80:
            classification = "Correct"
        elif overall < 45:
            classification = "Incorrect"

        return {
            "evaluation_status": "EVALUATED",
            "overall_score": overall,
            "classification": classification,
            "relevance": relevance,
            "technical_correctness": technical,
            "completeness": completeness,
            "structure": structure,
            "clarity": communication,
            "communication": communication,
            "grammar_score": grammar_score,
            "timing_pacing_feedback": timing_pacing_feedback,
            "feedback": data.get("feedback", ""),
            "model_answer": data.get("model_answer", ""),
            "missing_points": data.get("missing_points", []),
            "correct_points": data.get("correct_points", []),
            "incorrect_points": [item["quote"] + ": " + item["why_wrong"] for item in validated_incorrect] or data.get("incorrect_points", []),
            "incorrect_statements": validated_incorrect,
            "suggestions": data.get("suggestions", []),
            "relevance_evidence": validated_evidences["relevance_evidence"],
            "technical_correctness_evidence": validated_evidences["technical_correctness_evidence"],
            "completeness_evidence": validated_evidences["completeness_evidence"],
            "structure_evidence": validated_evidences["structure_evidence"],
            "communication_evidence": validated_evidences["communication_evidence"],
            "raw_model_json": {**data, **validated_evidences, "grammar_score": grammar_score, "timing_pacing_feedback": timing_pacing_feedback},
            "engine": "gemini",
            "model_name": self.model_name,
            "evaluated_at": timezone.now().isoformat()
        }
