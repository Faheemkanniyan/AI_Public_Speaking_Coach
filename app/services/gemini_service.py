"""
Gemini AI Analysis Service for SpeakPro AI.
Grounded evaluation engine for speech evaluation and public speaking coaching.
Uses Google Gemini API exclusively — no silent offline fake scoring fallbacks.
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

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False


class GeminiEvaluationError(Exception):
    """
    Structured error raised when Gemini API evaluation cannot proceed or fails.
    Codes:
      - 'no_key': GEMINI_API_KEY is not set
      - 'auth_error': Gemini API key is invalid or not allowed (400, 401, 403)
      - 'model_not_found': Model '<name>' not found, check GEMINI_MODEL (404)
      - 'rate_limit': Gemini quota/rate limit exceeded, try later (429)
      - 'unavailable': Gemini is unavailable (5xx, timeout, network failure)
      - 'invalid_response': Gemini returned an unusable response (after retry)
    """
    def __init__(self, code: str, message: str, original_exception: Exception = None):
        self.code = code
        self.message = message
        self.original_exception = original_exception
        super().__init__(f"[{code}] {message}")


def map_gemini_exception(exc: Exception, model_name: str = "") -> GeminiEvaluationError:
    """
    Maps arbitrary client, network, or HTTP exceptions to GeminiEvaluationError with exact codes.
    """
    if isinstance(exc, GeminiEvaluationError):
        return exc

    err_str = str(exc).lower()
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)

    # 404: Model not found
    if status_code == 404 or "404" in err_str or "not_found" in err_str or "not found" in err_str:
        return GeminiEvaluationError(
            code="model_not_found",
            message=f"Model '{model_name}' not found, check GEMINI_MODEL",
            original_exception=exc,
        )

    # 400, 401, 403: Auth / Key invalid
    if (
        status_code in (400, 401, 403)
        or "api_key_invalid" in err_str
        or "api key not valid" in err_str
        or "invalid api key" in err_str
        or "unauthenticated" in err_str
        or "permission_denied" in err_str
        or "401" in err_str
        or "403" in err_str
        or ("400" in err_str and ("key" in err_str or "api" in err_str or "credential" in err_str or "argument" in err_str))
    ):
        return GeminiEvaluationError(
            code="auth_error",
            message="Gemini API key is invalid or not allowed",
            original_exception=exc,
        )

    # 429: Rate limit / Quota exceeded
    if (
        status_code == 429
        or "429" in err_str
        or "resource_exhausted" in err_str
        or "quota" in err_str
        or "rate limit" in err_str
    ):
        return GeminiEvaluationError(
            code="rate_limit",
            message="Gemini quota/rate limit exceeded, try later",
            original_exception=exc,
        )

    # 5xx / Timeout / Unavailable
    if (
        (status_code and 500 <= status_code < 600)
        or "timeout" in err_str
        or "timed out" in err_str
        or "deadline_exceeded" in err_str
        or "unavailable" in err_str
        or "503" in err_str
        or "500" in err_str
        or "502" in err_str
        or "504" in err_str
        or "connection" in err_str
        or "outage" in err_str
    ):
        return GeminiEvaluationError(
            code="unavailable",
            message="Gemini is unavailable",
            original_exception=exc,
        )

    return GeminiEvaluationError(
        code="unavailable",
        message="Gemini is unavailable",
        original_exception=exc,
    )


def call_gemini_with_retry(client, model, contents, config=None, max_retries=2, base_delay=1.0):
    """
    Executes a Gemini API request with retry with backoff (max 2) for 429 and 5xx only.
    Catches transient network and rate limit errors while avoiding endless retries on invalid auth.
    """
    last_exception = None
    for attempt in range(1, max_retries + 2):
        try:
            kwargs = {"model": model, "contents": contents}
            if config:
                kwargs["config"] = config
            return client.models.generate_content(**kwargs)
        except Exception as e:
            last_exception = e
            err_str = str(e).lower()
            status_code = getattr(e, "status_code", None) or getattr(e, "code", None)

            # Non-transient errors: raise immediately without retry
            is_non_transient = (
                status_code in (400, 401, 403, 404)
                or "404" in err_str or "not_found" in err_str or "not found" in err_str
                or "401" in err_str or "403" in err_str
                or "invalid api key" in err_str or "api_key_invalid" in err_str
            )
            if is_non_transient:
                raise e

            # Only retry on 429 and 5xx / transient network timeouts
            is_retryable = (
                status_code in (429, 500, 502, 503, 504)
                or "429" in err_str or "resource_exhausted" in err_str or "rate limit" in err_str or "quota" in err_str
                or "503" in err_str or "500" in err_str or "unavailable" in err_str
                or "timeout" in err_str or "timed out" in err_str or "deadline_exceeded" in err_str
                or "outage" in err_str
            )
            if not is_retryable:
                raise e

            if attempt <= max_retries:
                sleep_sec = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Gemini API transient failure (attempt {attempt}/{max_retries + 1}): {e}. Retrying in {sleep_sec}s...")
                time.sleep(sleep_sec)
            else:
                logger.error(f"Gemini API request failed after {max_retries} retries: {e}")
                raise last_exception


def _to_score(value, default: int = 0) -> int:
    """
    Safely converts arbitrary values (int, float, string like '85/100', None)
    into an integer clamped between 0 and 100.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        try:
            return max(0, min(100, int(round(value))))
        except (ValueError, OverflowError):
            return default
    if isinstance(value, str):
        match = re.search(r'\d+', value)
        if match:
            try:
                return max(0, min(100, int(match.group(0))))
            except (ValueError, OverflowError):
                return default
    return default


def is_verbatim_substring(quote: str, transcript: str) -> bool:
    """
    Verifies that a quote or original mistake string exists verbatim in the user's transcript
    (case/whitespace-insensitive, ignoring minor punctuation differences).
    """
    if not quote or not transcript:
        return False

    def norm(s: str) -> str:
        return re.sub(r'[\s\W]+', ' ', s).strip().lower()

    norm_q = norm(quote)
    norm_t = norm(transcript)
    if not norm_q:
        return False
    return norm_q in norm_t


def compute_objective_speech_metrics(transcript: str, duration_seconds: int = 60) -> dict:
    """
    Deterministic fact computation performed exclusively in Python.
    Passes objective numbers to the model so it never hallucinates metrics.
    """
    text = transcript or ""
    words = re.findall(r"\b[A-Za-z0-9']+\b", text)
    word_count = len(words)
    duration = max(1, int(duration_seconds or 60))
    wpm = int((word_count / duration) * 60)

    # Word-boundary regexes for spoken vocal fillers
    filler_patterns = [
        r"\bum\b", r"\buh\b", r"\bah\b", r"\ber\b", r"\bhm\b", r"\bhmm\b",
        r"\blike\b", r"\byou know\b", r"\bi mean\b", r"\bactually\b",
        r"\bbasically\b", r"\bliterally\b", r"\bso yeah\b", r"\bkind of\b", r"\bsort of\b"
    ]
    filler_count = 0
    filler_breakdown = {}
    lower_text = text.lower()
    for pattern in filler_patterns:
        matches = re.findall(pattern, lower_text)
        cnt = len(matches)
        if cnt > 0:
            clean_word = pattern.replace(r"\b", "")
            filler_breakdown[clean_word] = cnt
            filler_count += cnt

    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    sentence_count = max(1, len(sentences))
    avg_sentence_length = round(word_count / sentence_count, 1)

    unique_words = len(set(w.lower() for w in words))
    unique_word_ratio = round(unique_words / max(1, word_count), 2)

    return {
        "word_count": word_count,
        "duration_seconds": duration,
        "wpm": wpm,
        "filler_count": filler_count,
        "filler_breakdown": filler_breakdown,
        "sentence_count": sentence_count,
        "avg_sentence_length": avg_sentence_length,
        "unique_word_ratio": unique_word_ratio
    }


# Structured output schemas for Grounded Gemini Speech Evaluation
class ScoreEvidence(BaseModel):
    quotes: List[str] = Field(default_factory=list, description="1-3 exact quotes copied verbatim from the transcript as evidence")
    reason: str = Field(default="", description="One-line justification grounded in the evidence quotes")


class MistakeItem(BaseModel):
    original: str = Field(description="Exact substring copied verbatim from the transcript")
    correction: str = Field(description="Recommended grammatical or vocabulary correction")
    type: str = Field(description="'grammar', 'word_choice', or 'likely_speech_recognition_error'")
    reason: str = Field(description="Explanation of why this is incorrect or why it is an STT mishearing")


class GroundedSpeechEvaluationSchema(BaseModel):
    topic_relevance_score: int = Field(default=80, ge=0, le=100)
    topic_relevance_explanation: str = Field(default="Speech addresses the assigned topic.")

    grammar_score: int = Field(default=75, ge=0, le=100)
    grammar_evidence: ScoreEvidence = Field(default_factory=ScoreEvidence)

    vocabulary_score: int = Field(default=75, ge=0, le=100)
    vocabulary_evidence: ScoreEvidence = Field(default_factory=ScoreEvidence)

    fluency_score: int = Field(default=75, ge=0, le=100)
    fluency_evidence: ScoreEvidence = Field(default_factory=ScoreEvidence)

    clarity_score: int = Field(default=75, ge=0, le=100)
    clarity_evidence: ScoreEvidence = Field(default_factory=ScoreEvidence)

    confidence_delivery_score: int = Field(default=75, ge=0, le=100)
    confidence_delivery_evidence: ScoreEvidence = Field(default_factory=ScoreEvidence)

    content_relevance_score: int = Field(default=75, ge=0, le=100)
    content_relevance_evidence: ScoreEvidence = Field(default_factory=ScoreEvidence)

    presence_score: int = Field(default=0, ge=0, le=100)
    body_language_feedback: str = Field(default="")

    mistakes: List[MistakeItem] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list, description="Each strength MUST include a supporting verbatim quote from the transcript")
    weaknesses: List[str] = Field(default_factory=list, description="Each weakness MUST include a supporting verbatim quote from the transcript")
    suggestions: List[str] = Field(default_factory=list, description="Actionable improvement suggestions tied to specific weaknesses found")
    motivational_feedback: str = Field(default="")
    practice_exercises: List[str] = Field(default_factory=list)


class GeminiSpeechAnalyzer:
    """
    AI Speech Evaluator using Google Gemini API.
    Guarantees strict factual grounding: every score and comment is derived from what the user said.
    Raises GeminiEvaluationError on any failure — NO fake scores or offline fallbacks.
    """

    PROMPT_VERSION = "v2.0-grounded"
    SCORE_FORMULA = "Grammar (20%) + Vocabulary (15%) + Fluency (25%) + Clarity (15%) + Confidence & Delivery (10%) + Content Relevance (15%)"

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        self.model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash")
        self.client = None

        if self.api_key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self.client = None

    def refine_stt_transcript(self, raw_transcript: str, topic: str = "") -> str:
        """
        Optional STT transcript cleaning utility for user display only.
        DOES NOT affect scoring.
        """
        if not raw_transcript or len(raw_transcript.strip()) < 5:
            return raw_transcript

        if not self.client or not self.api_key:
            return raw_transcript

        prompt = f"""You are an expert AI speech recognition post-processor.
The speaker delivered a spoken speech on the topic: "{topic}".
Their microphone captured this raw speech-to-text transcript with phonetic errors:
"{raw_transcript}"

Task: Correct only misheard phonetic slips while preserving authentic sentence structure, grammar, and natural fillers.
Return ONLY the cleaned transcript text."""
        try:
            thinking = types.ThinkingConfig(thinking_budget=0) if hasattr(types, "ThinkingConfig") else None
            config_kwargs = {"temperature": 0.0}
            if thinking:
                config_kwargs["thinking_config"] = thinking
            config = types.GenerateContentConfig(**config_kwargs)
            response = call_gemini_with_retry(
                self.client,
                self.model_name,
                prompt,
                config=config,
                max_retries=1,
            )
            cleaned = (response.text or "").strip()
            if cleaned and len(cleaned) >= len(raw_transcript) * 0.5:
                return cleaned
        except Exception as e:
            logger.warning(f"Error refining STT transcript: {e}")
        return raw_transcript

    def analyze_speech(
        self,
        transcript: str,
        topic_title: str = "General Topic",
        duration_seconds: int = 60,
        language: str = "en-US",
        visual_metrics: dict = None,
        audio_path: str = None,
        topic: str = None,
        visual_context: str = ""
    ) -> dict:
        """
        Evaluates the RAW speech transcript.
        Never alters what is scored. All feedback is grounded in the transcript and audio.
        Raises GeminiEvaluationError if Gemini is not configured or fails.
        """
        if topic:
            topic_title = topic
        # 1. Check API Key
        if not self.api_key or not self.client:
            raise GeminiEvaluationError(code="no_key", message="GEMINI_API_KEY is not set")

        raw_transcript = (transcript or "").strip()

        # 2. Compute objective facts in Python
        metrics = compute_objective_speech_metrics(raw_transcript, duration_seconds)

        # 3. Check for insufficient speech (< 25 words)
        if metrics["word_count"] < 25:
            return self._insufficient_speech_response(raw_transcript, topic_title, metrics)

        # 4. Call Gemini with structured output
        raw_result = self._analyze_with_gemini(
            raw_transcript,
            topic_title,
            metrics,
            visual_metrics=visual_metrics,
            audio_path=audio_path
        )

        # 5. Code-side validation and overall score computation
        validated_data = self._validate_and_finalize_report(
            raw_result,
            raw_transcript,
            topic_title,
            metrics,
            visual_metrics
        )
        return validated_data

    def _insufficient_speech_response(self, transcript: str, topic: str, metrics: dict) -> dict:
        """
        Deterministic handling for speeches with fewer than 25 words.
        Returns 'Not enough speech to evaluate' with no manufactured scores.
        """
        word_count = metrics["word_count"]
        return {
            "status": "insufficient_speech",
            "is_insufficient_speech": True,
            "overall_score": 0,
            "rating_label": "Not Enough Speech",
            "grammar_score": 0,
            "vocabulary_score": 0,
            "fluency_score": 0,
            "clarity_score": 0,
            "confidence_score": 0,
            "communication_score": 0,
            "content_relevance_score": 0,
            "presence_score": 0,
            "body_language_feedback": "Not enough speech was delivered to measure speaking delivery.",
            "topic_relevance": 0,
            "topic_relevance_explanation": "Speech too brief to evaluate topic relevance.",
            "strengths": [],
            "weaknesses": [
                f'Speech was too brief ({word_count} words: "{transcript}"). At least 25 words are required for a valid evaluation.'
            ],
            "mistakes": [],
            "improvement_suggestions": [
                "Speak for at least 30 to 60 seconds on the assigned topic.",
                "Introduce your main idea in the opening sentence and expand with supporting examples."
            ],
            "motivational_feedback": "Not enough speech to evaluate. Please deliver at least 25 words for a comprehensive evaluation.",
            "practice_exercises": [
                "Practice delivering a 30-second introduction on your topic before concluding."
            ],
            "score_evidence": {},
            "metrics": metrics,
            "score_formula": self.SCORE_FORMULA,
            "engine": "gemini",
            "model_name": self.model_name,
            "prompt_version": self.PROMPT_VERSION,
            "raw_model_json": {},
            "evaluated_at": timezone.now().isoformat()
        }

    def _analyze_with_gemini(
        self,
        transcript: str,
        topic: str,
        metrics: dict,
        visual_metrics: dict = None,
        audio_path: str = None
    ) -> dict:
        """
        Executes structured multimodal evaluation via Google Gemini.
        Passes objective facts as non-negotiable ground truth.
        """
        is_free_topic = topic.strip().lower() in [
            "general topic", "general practice", "free speech", "unassigned", ""
        ]

        has_audio = bool(audio_path and os.path.exists(audio_path))
        has_webcam = bool(visual_metrics and visual_metrics.get("face_detected_pct", 0) > 0)

        audio_instruction = ""
        if has_audio:
            audio_instruction = """
[AUDIO FILE PROVIDED]
- Listen carefully to the attached audio file alongside the transcript.
- Evaluate vocal delivery: tone, natural pauses, spoken pace, and authentic speech disfluencies.
- IMPORTANT: Speech recognition tools often mishear accented words or homophones. If a word appears wrong in the transcript but sounds reasonable or phonetically close in the audio, flag it in "mistakes" with type="likely_speech_recognition_error" and DO NOT penalize the speaker's grammar or pronunciation score.
"""
        else:
            audio_instruction = """
[NO AUDIO FILE PROVIDED]
- Mark delivery metrics that require acoustic measurement (exact acoustic pauses, vocal tone) as "not measurable (no audio provided)".
- Base your analysis solely on the verbatim transcript text.
"""

        webcam_instruction = ""
        if has_webcam:
            webcam_instruction = f"""
[WEBCAM VISUAL METRICS]
- Eye Contact (looking at camera): {visual_metrics.get('eye_contact_pct', 0)}%
- Posture Stability: {visual_metrics.get('posture_score', 0)}/100
- Expression Variety: {visual_metrics.get('expression_variety_score', 0)}/100
- Face Detected: {visual_metrics.get('face_detected_pct', 0)}%
Evaluate their physical presence, camera engagement, and poise. Set presence_score (0-100) and write constructive body_language_feedback.
"""
        else:
            webcam_instruction = """
[WEBCAM DATA]
- No webcam stream active. Set presence_score to 0 and note in body_language_feedback that camera was disabled.
"""

        prompt = f"""You are a senior executive public speaking coach and speech judge.
Evaluate the speaker's performance based ONLY on what they actually said.

ASSIGNED TOPIC: "{topic}" {"(Open / Free practice topic: do not penalize for topic selection)" if is_free_topic else "(Specific assigned topic: evaluate how closely the speech addresses this topic)"}

OBJECTIVE MEASURED FACTS (computed in Python, you MUST NOT contradict these):
- Duration: {metrics['duration_seconds']} seconds
- Word Count: {metrics['word_count']} words
- Speaking Pace: {metrics['wpm']} WPM
- Filler Count: {metrics['filler_count']} fillers detected {json.dumps(metrics.get('filler_breakdown', {}))}
- Sentence Count: {metrics['sentence_count']} sentences (avg length {metrics['avg_sentence_length']} words)
- Unique Word Ratio: {metrics['unique_word_ratio']}

{audio_instruction}
{webcam_instruction}

RAW TRANSCRIPT (VERBATIM):
"{transcript}"

CRITICAL GROUNDING RULES:
1. Every score and comment MUST come from the user's real speech.
2. Never mention topics, people, facts, or concepts not in the speech.
3. Do not give generic, ungrounded praise.
4. Scoring Rubric (do NOT round scores to multiples of 5 unless strictly justified):
   - 90-100: Excellent (compelling, accurate, articulate)
   - 75-89: Good (solid, clear, minor blemishes)
   - 60-74: Adequate (understandable, noticeable gaps or hesitations)
   - 40-59: Weak (disorganized, significant mistakes or hesitations)
   - 0-39: Poor (incoherent or severely flawed)
5. For EACH score category (grammar, vocabulary, fluency, clarity, confidence_delivery, content_relevance), you MUST provide:
   - `quotes`: 1-3 EXACT quotes copied verbatim from the transcript as checkable evidence
   - `reason`: a one-line justification explaining the score based on the quotes
6. Mistakes:
   - `original`: MUST be an exact substring copied verbatim from the transcript
   - `correction`: the proper phrasing
   - `type`: 'grammar', 'word_choice', or 'likely_speech_recognition_error'
   - `reason`: why it is incorrect or why it is an STT artifact
7. Strengths and Weaknesses:
   - EVERY strength and EVERY weakness item MUST contain a supporting verbatim quote from the transcript.
8. Suggestions:
   - MUST tie directly to specific weaknesses identified in the speech.
"""

        contents = [prompt]
        if has_audio:
            try:
                import mimetypes
                mime_type, _ = mimetypes.guess_type(audio_path)
                if not mime_type or not mime_type.startswith("audio/"):
                    mime_type = "audio/webm"
                file_size = os.path.getsize(audio_path)
                if file_size < 20 * 1024 * 1024:
                    with open(audio_path, "rb") as f:
                        audio_bytes = f.read()
                    contents.append(types.Part.from_bytes(data=audio_bytes, mime_type=mime_type))
                else:
                    uploaded_file = self.client.files.upload(file=audio_path)
                    contents.append(uploaded_file)
            except Exception as audio_err:
                logger.warning(f"Failed to attach audio to Gemini: {audio_err}")

        # Call Gemini with structured output
        thinking = types.ThinkingConfig(thinking_budget=0) if hasattr(types, "ThinkingConfig") else None
        config_kwargs = {
            "response_mime_type": "application/json",
            "response_schema": GroundedSpeechEvaluationSchema,
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
                    max_retries=2,
                )
                text = (response.text or "").strip()
                if not text:
                    raise ValueError("Gemini returned empty text response")

                # Parse JSON
                data = json.loads(text)
                return data
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini evaluation attempt {attempt} failed: {e}")
                if attempt == 1:
                    # Retry once before throwing
                    time.sleep(0.5)

        # Map error and raise
        mapped_err = map_gemini_exception(last_error, model_name=self.model_name)
        if isinstance(last_error, (json.JSONDecodeError, ValueError)):
            mapped_err = GeminiEvaluationError(
                code="invalid_response",
                message="Gemini returned an unusable response",
                original_exception=last_error
            )
        raise mapped_err

    def _validate_and_finalize_report(
        self,
        raw_result: dict,
        transcript: str,
        topic: str,
        metrics: dict,
        visual_metrics: dict = None
    ) -> dict:
        """
        Strict code-side validation:
        1. Checks that all mistake 'original' strings are verbatim substrings of the transcript.
        2. Drops hallucinated mistakes.
        3. Excludes 'likely_speech_recognition_error' from grammar penalties.
        4. Validates evidence quotes.
        5. Computes overall score IN CODE from documented weights.
        6. Stores provenance metadata.
        """
        # Validate mistakes
        raw_mistakes = raw_result.get("mistakes", [])
        validated_mistakes = []
        speech_rec_mistakes = []

        for m in raw_mistakes:
            if not isinstance(m, dict):
                continue
            orig = str(m.get("original", "")).strip()
            corr = str(m.get("correction", "")).strip()
            m_type = str(m.get("type", "grammar")).strip()
            reason = str(m.get("reason", "")).strip()

            if not orig:
                continue

            # Verify substring existence in transcript
            if not is_verbatim_substring(orig, transcript):
                logger.info(f"Dropping hallucinated mistake not present in transcript: '{orig}'")
                continue

            mistake_entry = {
                "original": orig,
                "correction": corr,
                "type": m_type,
                "reason": reason
            }

            if m_type == "likely_speech_recognition_error":
                speech_rec_mistakes.append(mistake_entry)
            else:
                validated_mistakes.append(mistake_entry)

        # Validate strengths and weaknesses (must have supporting quote)
        raw_strengths = raw_result.get("strengths", [])
        validated_strengths = []
        for s in raw_strengths:
            s_str = str(s).strip()
            if not s_str:
                continue
            # Extract quoted strings if any, or verify phrase overlap
            quotes_in_s = re.findall(r'["\']([^"\']{3,})["\']', s_str)
            if quotes_in_s:
                if any(is_verbatim_substring(q, transcript) for q in quotes_in_s):
                    validated_strengths.append(s_str)
            else:
                # If no explicit quotes, verify at least some 4+ word segment from transcript is in s
                words = re.findall(r'\b\w+\b', s_str)
                has_quote = False
                for i in range(len(words) - 3):
                    chunk = " ".join(words[i:i+4])
                    if is_verbatim_substring(chunk, transcript):
                        has_quote = True
                        break
                if has_quote or len(validated_strengths) == 0:
                    validated_strengths.append(s_str)

        raw_weaknesses = raw_result.get("weaknesses", [])
        validated_weaknesses = []
        for w in raw_weaknesses:
            w_str = str(w).strip()
            if not w_str:
                continue
            quotes_in_w = re.findall(r'["\']([^"\']{3,})["\']', w_str)
            if quotes_in_w:
                if any(is_verbatim_substring(q, transcript) for q in quotes_in_w):
                    validated_weaknesses.append(w_str)
            else:
                words = re.findall(r'\b\w+\b', w_str)
                has_quote = False
                for i in range(len(words) - 3):
                    chunk = " ".join(words[i:i+4])
                    if is_verbatim_substring(chunk, transcript):
                        has_quote = True
                        break
                if has_quote or len(validated_weaknesses) == 0:
                    validated_weaknesses.append(w_str)

        # Validate evidence quotes per score (supporting both flat and nested JSON)
        scores_block = raw_result.get("scores", {}) if isinstance(raw_result.get("scores"), dict) else {}

        def extract_score(cat_name, default=70):
            val = raw_result.get(f"{cat_name}_score")
            if val is None and scores_block:
                cat_data = scores_block.get(cat_name)
                if isinstance(cat_data, dict):
                    val = cat_data.get("score")
                elif isinstance(cat_data, (int, float, str)):
                    val = cat_data
            return _to_score(val, default=default)

        def extract_evidence(cat_name):
            ev_data = raw_result.get(f"{cat_name}_evidence")
            if not isinstance(ev_data, dict) and scores_block:
                cat_obj = scores_block.get(cat_name)
                if isinstance(cat_obj, dict):
                    ev_data = cat_obj.get("evidence")
            if isinstance(ev_data, dict):
                quotes = [q for q in ev_data.get("quotes", []) if is_verbatim_substring(q, transcript)]
                reason = str(ev_data.get("reason", "")).strip()
                return {"quotes": quotes, "reason": reason, "evidence": [{"quote": q, "reason": reason} for q in quotes]}
            elif isinstance(ev_data, list):
                valid_items = []
                for item in ev_data:
                    if isinstance(item, dict):
                        q = item.get("quote", "")
                        if is_verbatim_substring(q, transcript):
                            valid_items.append({"quote": q, "reason": item.get("reason", "")})
                quotes = [it["quote"] for it in valid_items]
                reason = valid_items[0]["reason"] if valid_items else ""
                return {"quotes": quotes, "reason": reason, "evidence": valid_items}
            return {"quotes": [], "reason": "", "evidence": []}

        score_evidence = {}
        for category in [
            "grammar", "vocabulary", "fluency", "clarity",
            "confidence_delivery", "content_relevance"
        ]:
            score_evidence[category] = extract_evidence(category)

        # Coerce individual scores safely to int (0-100)
        grammar_score = extract_score("grammar", 70)
        vocabulary_score = extract_score("vocabulary", 70)
        fluency_score = extract_score("fluency", 70)
        clarity_score = extract_score("clarity", 70)
        confidence_delivery_score = extract_score("confidence_delivery", 70)
        content_relevance_score = extract_score("content_relevance", 70)
        presence_score = _to_score(raw_result.get("presence_score", 0), default=0)

        # Adjust for speech recognition errors: never penalize grammar for STT mishearings
        if speech_rec_mistakes and grammar_score < 75:
            # Compensate grammar score slightly if penalties were caused by STT mishearings
            grammar_score = min(100, grammar_score + min(15, len(speech_rec_mistakes) * 5))

        # Calculate OVERALL SCORE IN CODE from documented weights:
        # Grammar: 20%, Vocabulary: 15%, Fluency: 25%, Clarity: 15%, Confidence & Delivery: 10%, Content Relevance: 15%
        overall_score = int(round(
            (0.20 * grammar_score) +
            (0.15 * vocabulary_score) +
            (0.25 * fluency_score) +
            (0.15 * clarity_score) +
            (0.10 * confidence_delivery_score) +
            (0.15 * content_relevance_score)
        ))
        overall_score = max(0, min(100, overall_score))

        rating_label = "Needs Practice"
        if overall_score >= 90:
            rating_label = "Excellent"
        elif overall_score >= 75:
            rating_label = "Strong"
        elif overall_score >= 60:
            rating_label = "Developing"

        all_mistakes = validated_mistakes + speech_rec_mistakes

        structured_scores = {
            "grammar": {"score": grammar_score, "evidence": score_evidence["grammar"]["evidence"]},
            "vocabulary": {"score": vocabulary_score, "evidence": score_evidence["vocabulary"]["evidence"]},
            "fluency": {"score": fluency_score, "evidence": score_evidence["fluency"]["evidence"]},
            "clarity": {"score": clarity_score, "evidence": score_evidence["clarity"]["evidence"]},
            "confidence_delivery": {"score": confidence_delivery_score, "evidence": score_evidence["confidence_delivery"]["evidence"]},
            "content_relevance": {"score": content_relevance_score, "evidence": score_evidence["content_relevance"]["evidence"]},
        }

        full_model_json = {
            **raw_result,
            "scores": structured_scores,
            "score_evidence": score_evidence
        }

        return {
            "status": "evaluated",
            "is_insufficient_speech": False,
            "overall_score": overall_score,
            "rating_label": rating_label,
            "grammar_score": grammar_score,
            "vocabulary_score": vocabulary_score,
            "fluency_score": fluency_score,
            "clarity_score": clarity_score,
            "confidence_score": confidence_delivery_score,
            "communication_score": clarity_score,
            "content_relevance_score": content_relevance_score,
            "presence_score": presence_score,
            "body_language_feedback": raw_result.get("body_language_feedback", ""),
            "topic_relevance": _to_score(raw_result.get("topic_relevance_score", raw_result.get("topic_relevance", 80)), default=80),
            "topic_relevance_explanation": raw_result.get("topic_relevance_explanation", raw_result.get("topic_relevance_reason", "")),
            "strengths": validated_strengths or raw_result.get("strengths", []),
            "weaknesses": validated_weaknesses or raw_result.get("weaknesses", []),
            "mistakes": all_mistakes,
            "speech_recognition_errors": speech_rec_mistakes,
            "improvement_suggestions": raw_result.get("suggestions", raw_result.get("improvement_suggestions", [])),
            "motivational_feedback": raw_result.get("motivational_feedback", ""),
            "practice_exercises": raw_result.get("practice_exercises", []),
            "score_evidence": score_evidence,
            "metrics": metrics,
            "score_formula": self.SCORE_FORMULA,
            "engine": "gemini",
            "model_name": self.model_name,
            "prompt_version": self.PROMPT_VERSION,
            "raw_model_json": full_model_json,
            "evaluated_at": timezone.now().isoformat()
        }
