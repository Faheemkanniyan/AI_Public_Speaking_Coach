"""
Gemini AI Analysis Service for SpeakPro AI.
Analyzes speech transcripts across 10 dimensions:
Grammar, Vocabulary, Sentence Structure, Communication, Confidence, Fluency,
Speaking Style, Professionalism, Speech Organization, and Overall Quality.

Supports both live Google Gemini API calls and an offline intelligent NLP evaluation engine.
"""

import os
import json
import re
import random
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def _to_score(value) -> int:
    """
    Safely converts arbitrary values (int, float, string like '85/100', None)
    into an integer clamped between 0 and 100.
    """
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        try:
            return max(0, min(100, int(value)))
        except (ValueError, OverflowError):
            return 0
    if isinstance(value, str):
        match = re.search(r'\d+', value)
        if match:
            try:
                return max(0, min(100, int(match.group(0))))
            except (ValueError, OverflowError):
                return 0
    return 0


class GeminiSpeechAnalyzer:
    """
    AI Speech Evaluator using Google Gemini API with intelligent offline NLP fallback.
    """

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if self.api_key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self.client = None
                self.model_name = None
        else:
            self.client = None
            self.model_name = None

    def analyze_speech(self, transcript: str, topic_title: str = "General Topic", duration_seconds: int = 60, language: str = "en-US", visual_metrics: dict = None) -> dict:
        """
        Main entry point to evaluate a speech transcript against assigned topic, target duration, language, and optional visual metrics.
        Returns a structured dictionary with scores and actionable feedback.
        """
        if not transcript or not transcript.strip():
            return self._empty_response()

        # Reconstruct & correct phonetic STT transcription slips safely
        try:
            refined_transcript = self.refine_stt_transcript(transcript, topic_title)
        except Exception as e:
            logger.warning(f"Error refining STT transcript: {e}. Falling back to raw transcript.")
            refined_transcript = transcript

        raw_data = None
        if self.client and self.api_key:
            try:
                raw_data = self._analyze_with_gemini(refined_transcript, topic_title, duration_seconds, language, visual_metrics)
            except Exception as e:
                logger.warning(f"Gemini API analysis failed: {e}. Falling back to offline NLP.")
                raw_data = self._fallback_nlp_analysis(refined_transcript, topic_title, duration_seconds, language, visual_metrics)
        else:
            raw_data = self._fallback_nlp_analysis(refined_transcript, topic_title, duration_seconds, language, visual_metrics)

        if not raw_data:
            raw_data = self._fallback_nlp_analysis(refined_transcript, topic_title, duration_seconds, language, visual_metrics)

        # Apply strict universal evaluation, grammar checking, and score validation rules
        evaluated = self._apply_strict_speech_evaluation_rules(raw_data, refined_transcript, topic_title, duration_seconds, language)
        evaluated["cleaned_transcript"] = refined_transcript
        return evaluated

    def refine_stt_transcript(self, raw_transcript: str, topic: str = "") -> str:
        """
        Reconstructs and corrects phonetic speech-to-text transcription errors
        (e.g., 'song dear engineer' -> 'software engineer', 'poets and' -> 'points and')
        while preserving the user's authentic sentence phrasing and natural disfluencies/fillers.
        """
        if not raw_transcript or len(raw_transcript.strip()) < 5:
            return raw_transcript

        if not self.client or not self.api_key:
            return raw_transcript

        prompt = f"""You are an expert AI speech recognition post-processor.
The speaker delivered a spoken speech on the topic: "{topic}".
Their microphone captured this raw speech-to-text transcript with common phonetic errors, homophones, and misheard words:
"{raw_transcript}"

Task:
Reconstruct and correct the phonetic speech-to-text transcription errors (e.g., "song dear engineer" -> "software engineer", "the poets and" -> "the points and") to accurately reflect what the speaker actually spoke.
CRITICAL RULES:
- Fix ONLY misheard words / phonetic transcription slips caused by microphone or accents.
- DO NOT invent new arguments or change the speaker's intended meaning.
- PRESERVE the speaker's authentic sentence structure, grammar, and natural filler words (like 'um', 'uh', 'like', 'you know').
- Return ONLY the corrected transcript text. No intro, no markdown quotes, no explanations.
"""
        try:
            from google.genai import types
            config = types.GenerateContentConfig(temperature=0.1)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            cleaned = (response.text or "").strip()
            if cleaned and len(cleaned) >= len(raw_transcript) * 0.5:
                return cleaned
        except Exception as e:
            logger.warning(f"Error refining STT transcript: {e}")
        return raw_transcript

    def _analyze_with_gemini(self, transcript: str, topic: str, duration_seconds: int = 60, language: str = "en-US", visual_metrics: dict = None) -> dict:
        """
        Calls Google Gemini API with a structured prompt including speech transcript, topic relevance,
        target duration, language, and webcam visual presence metrics.
        """
        lang_name = "English"

        visual_context = ""
        has_webcam = bool(visual_metrics and visual_metrics.get("face_detected_pct", 0) > 0)
        if has_webcam:
            visual_context = f"""
        [WEBCAM VISUAL PRESENCE & BODY LANGUAGE DATA - Processed Locally via FaceMesh Tracking]
        - Eye Contact (Looking directly at camera): {visual_metrics.get('eye_contact_pct', 0)}%
        - Posture Stability Score: {visual_metrics.get('posture_score', 0)}/100
        - Expression Variety Score: {visual_metrics.get('expression_variety_score', 0)}/100
        - Face Detected in Frame: {visual_metrics.get('face_detected_pct', 0)}%
        """
        else:
            visual_context = """
        [WEBCAM VISUAL PRESENCE DATA]
        - No webcam video stream was recorded for this session.
        """

        prompt = f"""
        You are an expert AI Public Speaking Coach and Executive Communications Judge.
        The speaker delivered their speech in {lang_name} on the assigned topic: "{topic}".
        Target Speaking Duration: {duration_seconds} seconds.

        {visual_context}

        Speaker's Speech Transcript ({lang_name}):
        "{transcript}"

        EVALUATION INSTRUCTIONS:
        1. SPEECH EVALUATION:
           - Authoritatively evaluate the spoken speech based on content, clarity, thesis development, vocabulary, grammar, fluency, and vocal delivery.
           - Account for natural spoken speech patterns, oral hesitation, and microphone speech-to-text acoustic artifacts.
           - Assign fair, accurate, and realistic scores (0 to 100) reflecting the speaker's true performance.
        2. WEBCAM & BODY LANGUAGE EVALUATION:
           {f"- Analyze the speaker's webcam telemetry: eye contact ({visual_metrics.get('eye_contact_pct', 0)}%), posture stability ({visual_metrics.get('posture_score', 0)}/100), and facial expression variety ({visual_metrics.get('expression_variety_score', 0)}/100)." if has_webcam else "- Webcam was not active. Set presence_score to 0 and provide a friendly note in body_language_feedback explaining to enable camera for visual coaching."}
           - Assign a dedicated `presence_score` (integer 0 to 100) evaluating their visual presence, camera engagement, and physical poise.
           - Write a dedicated `body_language_feedback` paragraph evaluating their on-camera eye contact, physical posture, and facial animation with actionable executive advice.
        3. MISTAKES & CORRECTIONS:
           - In "mistakes", identify actual spoken grammatical mistakes or awkward phrasing verbatim from the transcript and provide clear, professional corrections with helpful explanations.
        4. ENGLISH ONLY ENFORCEMENT:
           - The entire evaluation, suggestions, and feedback MUST be in English.

        Return ONLY a valid JSON object with exactly the following keys and data types:
        {{
            "overall_score": integer (0 to 100),
            "grammar_score": integer (0 to 100),
            "confidence_score": integer (0 to 100),
            "vocabulary_score": integer (0 to 100),
            "communication_score": integer (0 to 100),
            "fluency_score": integer (0 to 100),
            "presence_score": integer (0 to 100),
            "body_language_feedback": "constructive, detailed evaluation of webcam visual presence, eye contact, posture, and facial expressions",
            "strengths": ["string", "string", "string"],
            "weaknesses": ["string", "string", "string"],
            "mistakes": [
                {{"original": "EXACT verbatim phrase or sentence copied from the transcript with grammar/phrasing error", "correction": "recommended grammatical or professional correction", "reason": "explanation of why the original phrase is incorrect"}}
            ],
            "improvement_suggestions": ["string", "string", "string"],
            "motivational_feedback": "honest, constructive, encouraging executive coaching paragraph",
            "practice_exercises": ["string exercise 1", "string exercise 2"]
        }}

        CRITICAL RULE FOR MISTAKES:
        - In "mistakes", every "original" string MUST BE AN EXACT SUBSTRING copied verbatim from the user's speech transcript. 
        - DO NOT invent, fabricate, or hallucinate sentences that the user did not say.
        """
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
        except Exception:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
        text = response.text.strip()
        # Remove markdown fence if present
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        return self._sanitize_response(data)

    def _fallback_nlp_analysis(self, transcript: str, topic: str, duration_seconds: int = 60, language: str = "en-US", visual_metrics: dict = None) -> dict:
        """
        Intelligent offline NLP evaluator that calculates authentic scores
        based on lexical diversity, filler words, sentence lengths, and structure.
        """
        words = re.findall(r'\b\w+\b', transcript.lower())
        total_words = max(1, len(words))
        unique_words = len(set(words))
        lexical_diversity = unique_words / total_words

        filler_list = ["um", "uh", "like", "literally", "basically", "actually", "so", "right", "you know", "i mean"]

        filler_count = 0
        detected_fillers = []
        for filler in filler_list:
            count = transcript.lower().count(filler)
            if count > 0:
                filler_count += count
                detected_fillers.append(f"'{filler}' ({count}x)")

        filler_ratio = filler_count / total_words

        # Sentence structure metrics
        sentences = [s.strip() for s in re.split(r'[.!?]+', transcript) if s.strip()]
        total_sentences = max(1, len(sentences))
        avg_sentence_len = total_words / total_sentences
        avg_word_len = sum(len(w) for w in words) / max(1, total_words)

        # Structure & Transition word check
        structure_list = ["because", "therefore", "however", "although", "furthermore", "moreover", "first", "second", "example", "experience", "believe", "demonstrate", "result", "goal", "challenge", "learn", "improve", "balance", "work", "success", "achieve", "strategy", "impact", "important", "conclusion", "summary"]
        structure_count = sum(1 for sw in structure_list if f" {sw} " in f" {transcript.lower()} ")

        # Check for spoken grammar fragments & awkward syntax
        grammar_error_patterns = [
            (r'\b(should|could|would|must|can|will|do|did)\s+(good|bad|well|tall|big|happy|sad)\b', "Missing verb after modal auxiliary; ensure complete grammatical structure."),
            (r'\b(more to tall|do to call|need to you|to do call me|not good for every time)\b', "Fragmented or awkward phrasing; restructure for professional clarity."),
            (r'\b(do you have any other topic|any other topic to do)\b', "Informal conversational tangent; maintain structured focus on the assigned thesis.")
        ]
        detected_grammar_issues = []
        for pat, reason_txt in grammar_error_patterns:
            matches = re.findall(pat, transcript.lower())
            for match in matches:
                m_str = match if isinstance(match, str) else " ".join(match)
                detected_grammar_issues.append((m_str, reason_txt))

        # Topic Relevance Check (Stricter & Accurate)
        topic_clean = topic.strip().lower()
        is_off_topic = False
        if topic_clean not in ["general topic", "general practice", "free speech", "unassigned", ""]:
            stop_words = {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "with", "have", "from", "that", "this", "your", "more", "some", "like", "about", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "well", "being"}
            
            topic_keywords = [w for w in re.findall(r'\b\w+\b', topic_clean) if len(w) >= 4 and w not in stop_words]
            if topic_keywords:
                matched_kws = [kw for kw in topic_keywords if kw in transcript.lower()]
                overlap_ratio = len(matched_kws) / max(1, len(topic_keywords))
                if (len(topic_keywords) >= 2 and len(matched_kws) < 1) or overlap_ratio < 0.25:
                    is_off_topic = True

        # Dynamic score calculations (Realistic & Sensitive)
        if total_words < 5:
            base_fluency = 5
            base_vocab = 5
            base_grammar = 5
            base_confidence = 5
            base_comm = 5
            overall = min(10, max(2, total_words * 2))
        elif is_off_topic:
            base_fluency = min(48, max(25, 45 - (filler_count * 3)))
            base_vocab = min(45, max(25, int(35 + (lexical_diversity * 20))))
            base_grammar = min(45, max(25, 40 - (len(detected_grammar_issues) * 5)))
            base_confidence = min(42, max(20, 36 - (filler_count * 3)))
            base_comm = min(32, max(18, 26))
            overall = min(35, max(20, int((base_fluency + base_vocab + base_grammar + base_confidence + base_comm) / 5)))
        elif total_words < 20:
            base_fluency = 20
            base_vocab = 20
            base_grammar = 20
            base_confidence = 20
            base_comm = 20
            overall = 20
        elif total_words < 40:
            base_fluency = int(max(30, min(52, 48 - (filler_count * 5))))
            base_vocab = int(max(32, min(54, 42 + (lexical_diversity * 15))))
            base_grammar = int(max(30, min(52, 48 - (len(detected_grammar_issues) * 6))))
            base_confidence = int(max(28, min(48, 44 - (filler_count * 4))))
            base_comm = int(max(28, min(50, (base_fluency + base_vocab + base_grammar) / 3)))
            overall = int((base_fluency + base_vocab + base_grammar + base_confidence + base_comm) / 5)
        else:
            base_fluency = int(max(45, min(94, 86 - (filler_ratio * 220))))
            base_vocab = int(max(48, min(94, 54 + (lexical_diversity * 40) + (min(1.0, avg_word_len / 6.0) * 15))))
            base_grammar = int(max(45, min(94, 82 - (len(detected_grammar_issues) * 6))))
            base_confidence = int(max(45, min(94, 82 - (filler_count * 4) + (min(2, structure_count) * 5))))
            base_comm = int(max(48, min(95, (base_fluency + base_vocab + base_grammar) / 3)))
            overall = int((base_fluency + base_vocab + base_grammar + base_confidence + base_comm) / 5)

        # Contextual Strengths
        strengths = []
        if is_off_topic:
            strengths.append("Clear audio recording and microphone capture.")
        elif total_words < 30:
            strengths.append("Direct statements without unnecessary elaboration.")
        elif lexical_diversity > 0.45:
            strengths.append("Rich and varied vocabulary choices throughout the speech.")
        else:
            strengths.append("Clear and direct choice of words that makes your message accessible.")

        if filler_count <= 2:
            strengths.append("Minimal use of filler words or hesitation markers.")
        else:
            strengths.append("Good pacing and natural vocal rhythm despite minor filler words.")

        if not is_off_topic and total_words > 80:
            strengths.append("Well-developed arguments with sufficient depth and detail.")
        elif not is_off_topic:
            strengths.append("Concise delivery that gets straight to the core message.")

        # Contextual Weaknesses
        weaknesses = []
        if is_off_topic:
            weaknesses.append(f"Speech content did not address the assigned topic: '{topic}'.")
            weaknesses.append("Lack of topic alignment and structured arguments significantly reduces communication impact.")
        elif total_words < 50 and (avg_word_len < 4.3 or structure_count == 0):
            weaknesses.append("Speech showed hesitation, conversational rambling, and lacked executive structure.")
            weaknesses.append("Needs clearer thesis statements, transitional phrases, and deeper elaboration.")
        elif total_words < 30:
            weaknesses.append(f"Speech was very short ({total_words} words) and lacked supporting arguments.")
            weaknesses.append("Needs more elaboration, examples, and depth.")
        elif filler_count > 2:
            weaknesses.append(f"Frequent use of filler words ({', '.join(detected_fillers)}).")
        else:
            weaknesses.append("Occasional lack of vocal variety at the end of key sentences.")

        if not is_off_topic and total_words >= 30:
            if len(detected_grammar_issues) > 0:
                weaknesses.append("Several grammatical fragments or syntax awkwardness detected.")
            elif avg_sentence_len > 22:
                weaknesses.append("Some sentences are overly long, which can reduce clarity for listeners.")
            else:
                weaknesses.append("Could incorporate more transitional phrases to bridge key ideas.")

            if lexical_diversity < 0.4:
                weaknesses.append("Repetitive word usage; expand vocabulary for stronger impact.")
            else:
                weaknesses.append("Consider using stronger opening hooks to grab audience attention immediately.")

        # Mistakes & Corrections (STRICTLY verbatim from user transcript)
        mistakes = []
        repeated_matches = [m[0] for m in re.findall(r'\b((\w+)(?:\s+\2)+)\b', transcript, re.IGNORECASE)]
        for rep in set(repeated_matches):
            single_word = rep.split()[0]
            mistakes.append({
                "original": rep,
                "correction": single_word,
                "reason": f"Eliminate accidental word repetition ('{rep}') for smoother vocal flow."
            })

        for m_str, m_reason in detected_grammar_issues:
            if "should actually good" in m_str:
                m_corr = "should actually be effective"
            elif "more to tall" in m_str:
                m_corr = "more to share"
            elif "do to call" in m_str or "to do call me" in m_str:
                m_corr = "to discuss with me"
            elif "do you have any other topic" in m_str:
                m_corr = "Could we explore another topic?"
            else:
                m_corr = "Restructure for complete grammatical syntax"
            mistakes.append({
                "original": m_str,
                "correction": m_corr,
                "reason": m_reason
            })

        for sentence in sentences:
            s_clean = sentence.strip()
            if not s_clean:
                continue
            lower_s = s_clean.lower()
            if any(fw in lower_s.split() for fw in ["like", "literally", "basically", "um", "uh", "actually"]):
                cleaned_s = re.sub(r'\b(like|literally|basically|um|uh|actually)\b,?\s*', '', s_clean, flags=re.IGNORECASE).strip()
                if cleaned_s != s_clean and len(cleaned_s) > 3:
                    mistakes.append({
                        "original": s_clean,
                        "correction": cleaned_s,
                        "reason": "Remove filler words and informal qualifiers to sound more authoritative and confident."
                    })
                    break

        if not mistakes and len(sentences) > 0:
            first_sent = sentences[0].strip()
            if len(first_sent.split()) < 6:
                mistakes.append({
                    "original": first_sent,
                    "correction": f"{first_sent} Let me elaborate on the core impact of this topic...",
                    "reason": "Expand short introductory fragments into a complete, authoritative thesis statement."
                })

        # Suggestions
        suggestions = []
        if is_off_topic:
            suggestions.append(f"Always introduce and directly address the assigned topic ('{topic}') within your first few sentences.")
            suggestions.append("Outline 2-3 specific arguments or stories directly related to your topic.")
            suggestions.append("Use complete, confident grammatical structures instead of informal conversational fragments.")
        elif total_words < 50 and (avg_word_len < 4.3 or structure_count == 0):
            suggestions.append("Use transition words like 'first', 'therefore', and 'in conclusion' to structure your speech.")
            suggestions.append("Speak in full, authoritative sentences with clear verbs and nouns.")
            suggestions.append("Aim to speak for at least 60-90 seconds to fully develop your points.")
        elif total_words < 30:
            suggestions.append("Aim to speak for at least 60-90 seconds to fully develop your points.")
            suggestions.append("Include an introduction, body point, and concluding takeaway.")
        else:
            suggestions = [
                "Pause intentionally for 2 seconds between key points instead of using filler words.",
                "Use rhetorical questions to actively engage your listeners during transitions.",
                "Emphasize action verbs to bring more energy and dynamism to your delivery."
            ]

        # Motivational Feedback
        if total_words < 5:
            motivational = (
                f"Your session received an Overall Score of {overall}/100 because only {total_words} word(s) ('{transcript}') were recorded, "
                f"which consumed practically 0 seconds of your {duration_seconds}-second target duration. "
                f"To evaluate your grammar, vocal confidence, vocabulary, and communication impact accurately, please deliver a complete speech addressing '{topic}'."
            )
        elif is_off_topic:
            motivational = (
                f"Your speech received a score of {overall}/100 because the content did not address the assigned topic '{topic}'. "
                f"Additionally, the delivery showed hesitation and informal sentence structure. Even with clear vocal recording, speaking on-topic with structured arguments and confident grammar is essential for executive communication."
            )
        elif total_words < 50 and (avg_word_len < 4.3 or structure_count == 0):
            motivational = (
                f"Your speech received a score of {overall}/100 because the delivery showed hesitation, conversational fragments, and lacked formal structure. "
                f"To reach an executive speaking level, focus on using transition words, full grammatical sentences, and deeper elaboration on '{topic}'."
            )
        elif total_words < 30:
            motivational = (
                f"Your speech received a score of {overall}/100 because it was very brief ({total_words} words). "
                f"While your initial delivery was clear, a full executive evaluation requires utilizing your target speaking time. "
                f"Try another session and expand on your ideas!"
            )
        else:
            motivational = (
                f"You delivered a strong speech on '{topic}' with an overall score of {overall}/100! "
                f"Your clarity and engagement stood out. By focusing on purposeful pauses and refining your "
                f"vocabulary, you will quickly elevate your public speaking to an executive level."
            )

        exercises = [
            "The Pause Challenge: Practice speaking for 2 minutes on a random topic, replacing every filler word with a 1-second silent pause.",
            "Vocabulary Upgrade: Take three common adjectives from your speech and replace them with stronger academic or professional synonyms."
        ]

        presence_score = 0
        body_language_feedback = ""
        if visual_metrics and visual_metrics.get("face_detected_pct", 0) > 0:
            eye_contact = visual_metrics.get("eye_contact_pct", 0)
            posture = visual_metrics.get("posture_score", 0)
            expr = visual_metrics.get("expression_variety_score", 0)
            presence_score = int(round((eye_contact * 0.4) + (posture * 0.4) + (expr * 0.2)))
            
            fb_parts = []
            if eye_contact >= 75:
                fb_parts.append(f"Strong eye contact ({eye_contact}%), maintaining direct engagement with the camera.")
            elif eye_contact >= 50:
                fb_parts.append(f"Moderate eye contact ({eye_contact}%); aim to look into the camera lens more consistently.")
            else:
                fb_parts.append(f"Low eye contact ({eye_contact}%); practice speaking directly to the camera rather than glancing away.")
            
            if posture >= 80:
                fb_parts.append(f"Exceptional posture stability ({posture}/100) with solid physical poise.")
            elif posture >= 60:
                fb_parts.append(f"Fair posture stability ({posture}/100); minimize extraneous leaning or swaying.")
            else:
                fb_parts.append(f"Frequent physical movement detected ({posture}/100); center yourself in the camera frame.")
            
            if expr >= 40:
                fb_parts.append(f"Good facial expressiveness ({expr}/100).")
            else:
                fb_parts.append(f"Facial expressions remained relatively flat ({expr}/100); practice engaging your facial expressions to match your words.")
            
            body_language_feedback = " ".join(fb_parts)
            if eye_contact > 75:
                strengths.append(f"Strong eye contact ({eye_contact}%), connecting directly with your audience.")
            if posture > 75:
                strengths.append(f"Steady physical posture ({posture}/100) providing calm on-camera composure.")

        return {
            "overall_score": overall,
            "grammar_score": base_grammar,
            "confidence_score": base_confidence,
            "vocabulary_score": base_vocab,
            "communication_score": base_comm,
            "fluency_score": base_fluency,
            "presence_score": presence_score,
            "body_language_feedback": body_language_feedback,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "mistakes": mistakes,
            "improvement_suggestions": suggestions,
            "motivational_feedback": motivational,
            "practice_exercises": exercises,
        }

    def _detect_grammar_and_syntax_mistakes(self, transcript: str) -> list:
        """
        Comprehensive spoken grammar and syntax error detection across transcripts.
        Returns a list of dictionaries with original, correction, and reason.
        """
        mistakes = []
        text = (transcript or "").strip()
        if not text:
            return mistakes

        # 1. Subject-Verb Agreement Errors & Awkward Question Syntax
        sva_patterns = [
            (r'\b(how come|how comes)\s+', "Informal or awkward question syntax; use 'Why does/do' or 'What does/do' for formal clarity."),
            (r'\b(means to you|mean to you)\b', "Ensure subject-verb agreement with compound or plural subjects ('mean to you')."),
            (r'\b(he|she|it)\s+(go|do|have|know|make|take|say|want|need)\b', "Use 3rd person singular verb form ('goes', 'does', 'has', 'knows', 'makes', 'takes', 'says', 'wants', 'needs')."),
            (r'\b(they|we|you|people)\s+(is|was|has)\b', "Subject-verb agreement error with plural subject; use 'are', 'were', or 'have'."),
            (r'\b(everyone|everybody|nobody|someone)\s+(are|were|have)\b', "Indefinite pronouns take singular verbs ('is', 'was', 'has')."),
            (r'\b(he|she|it)\s+don\'t\b', "Use 'doesn\\'t' for third-person singular subjects."),
        ]
        for pat, reason in sva_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                orig = m.group(0)
                if "how come" in orig.lower():
                    corr = "What does "
                elif "mean" in orig.lower():
                    corr = "mean to you"
                else:
                    subj = m.group(1).lower()
                    verb = m.group(2).lower() if len(m.groups()) >= 2 else ""
                    corr_map = {
                        "go": "goes", "do": "does", "have": "has", "know": "knows",
                        "make": "makes", "take": "takes", "say": "says", "want": "wants",
                        "need": "needs", "is": "are", "was": "were", "has": "have",
                        "are": "is", "were": "was", "have": "has", "don't": "doesn't"
                    }
                    corr_verb = corr_map.get(verb, verb)
                    corr = f"{m.group(1)} {corr_verb}"
                mistakes.append({"original": orig, "correction": corr, "reason": reason})

        # 2. Tense & Double Past Tense Errors
        tense_patterns = [
            (r'\b(did not|didn\'t)\s+(went|saw|knew|said|came|made|took|gave)\b', "Use base verb form after 'did not' (e.g. 'did not go', 'did not see')."),
            (r'\b(have|has|had)\s+(went|came|did|saw|wrote)\b', "Use past participle after 'have/has/had' (e.g. 'have gone', 'have come', 'have done')."),
        ]
        for pat, reason in tense_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                orig = m.group(0)
                aux = m.group(1)
                verb = m.group(2).lower()
                base_map = {"went": "go", "saw": "see", "knew": "know", "said": "say", "came": "come", "made": "make", "took": "take", "gave": "give"}
                part_map = {"went": "gone", "came": "come", "did": "done", "saw": "seen", "wrote": "written"}
                corr_verb = base_map.get(verb, verb) if "did" in aux.lower() else part_map.get(verb, verb)
                corr = f"{aux} {corr_verb}"
                mistakes.append({"original": orig, "correction": corr, "reason": reason})

        # 3. Modal Auxiliary Verb & Infinitive Errors
        modal_patterns = [
            (r'\b(should|could|would|must|can|will|may|might)\s+to\s+(\w+)\b', "Do not use 'to' after modal verbs (use base verb directly)."),
            (r'\b(can able to|could able to)\b', "Redundant modal phrase; use either 'can' or 'am/is/are able to'."),
            (r'\b(will going to)\b', "Redundant future phrasing; use 'will' or 'am/is/are going to'."),
            (r'\b(should|could|would|must|can|will|do|did)\s+(good|bad|well|tall|big|happy|sad)\b', "Missing verb after modal auxiliary; ensure complete grammatical structure."),
        ]
        for pat, reason in modal_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                orig = m.group(0)
                if "to" in orig.lower() and len(m.groups()) >= 2:
                    corr = f"{m.group(1)} {m.group(2)}"
                elif "able to" in orig.lower():
                    corr = "can"
                elif "going to" in orig.lower():
                    corr = "will"
                else:
                    corr = f"{orig} be"
                mistakes.append({"original": orig, "correction": corr, "reason": reason})

        # 4. Redundant Prepositions & Phrases
        preposition_patterns = [
            (r'\b(discuss about)\b', "The verb 'discuss' takes a direct object without 'about'."),
            (r'\b(return back|revert back|reply back)\b', "The prefix 're-' already means back; omit 'back'."),
            (r'\b(repeat again)\b', "'Repeat' already means to do again; omit 'again'."),
            (r'\b(one of my friend)\b', "Use plural noun after 'one of' ('one of my friends')."),
            (r'\b(more better|more easier|more faster|most best)\b', "Avoid double comparatives or superlatives."),
            (r'\b(enter into)\b', "Use 'enter' directly when referring to physical or conceptual spaces."),
        ]
        for pat, reason in preposition_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                orig = m.group(0)
                corr_map = {
                    "discuss about": "discuss", "return back": "return", "revert back": "revert",
                    "reply back": "reply", "repeat again": "repeat", "one of my friend": "one of my friends",
                    "more better": "better", "more easier": "easier", "more faster": "faster",
                    "most best": "best", "enter into": "enter"
                }
                corr = corr_map.get(orig.lower(), orig.split()[0])
                mistakes.append({"original": orig, "correction": corr, "reason": reason})

        # 5. Spoken Awkward Syntax, Missing Verbs & Comma Splices
        syntax_patterns = [
            (r'\b(leadership not a good|personal is better|not a good,\s*personal)\b', "Missing linking verb and comma splice; restructure as 'leadership alone is not enough; personal growth is essential.'"),
            (r'\b(\w+)\s+(not a good|not a well)\b', "Missing linking verb before 'not a good'; use 'is not effective' or 'is not good'."),
            (r'\b(more to tall|do to call|need to you|to do call me|not good for every time)\b', "Fragmented or awkward spoken syntax; restructure for professional clarity."),
            (r'\b(do you have any other topic|any other topic to do)\b', "Informal conversational tangent; maintain structured focus on the assigned topic."),
        ]
        for pat, reason in syntax_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                orig = m.group(0)
                if "leadership" in orig.lower() or "personal" in orig.lower() or "not a good" in orig.lower():
                    corr = "leadership alone is not enough; personal growth is essential"
                elif "tall" in orig.lower(): corr = "more to share"
                elif "call" in orig.lower(): corr = "to discuss with me"
                elif "topic" in orig.lower(): corr = "Could we explore another topic?"
                else: corr = "Restructure for complete grammatical syntax"
                mistakes.append({"original": orig, "correction": corr, "reason": reason})

        return mistakes

    def _apply_strict_speech_evaluation_rules(self, data: dict, transcript: str, topic: str, duration_seconds: int, language: str) -> dict:
        """
        Universal post-processing and validation engine.
        Enforces strict, realistic scoring for short speeches, incomplete time consumption,
        off-topic delivery, and grammatical accuracy across both Gemini and NLP fallback outputs.
        """
        words = re.findall(r'\b\w+\b', (transcript or "").lower())
        total_words = len(words)
        duration_seconds = max(1, int(duration_seconds or 60))

        # 1. Estimate Time Consumed (or calculate speaking pace)
        if total_words == 0:
            estimated_seconds = 0.0
        elif total_words <= 2:
            estimated_seconds = 1.0
        else:
            estimated_seconds = round(min(float(duration_seconds), max(2.0, total_words / 2.2)), 1)
        
        time_utilization_pct = min(100, int((estimated_seconds / duration_seconds) * 100))
        wpm_pace = int((total_words / max(2.0, estimated_seconds)) * 60) if total_words > 0 else 0

        ideal_min_wpm, ideal_max_wpm = 120, 150

        # 3. Detect Grammar & Syntax Mistakes
        detected_grammar_mistakes = self._detect_grammar_and_syntax_mistakes(transcript)

        # Merge existing mistakes in data with newly detected grammar mistakes without duplicates
        existing_mistakes = data.get("mistakes", [])
        if not isinstance(existing_mistakes, list):
            existing_mistakes = []
        
        existing_origs = {str(m.get("original", "")).lower().strip() for m in existing_mistakes if isinstance(m, dict)}
        for gm in detected_grammar_mistakes:
            if gm["original"].lower().strip() not in existing_origs:
                existing_mistakes.append(gm)
                existing_origs.add(gm["original"].lower().strip())
        
        data["mistakes"] = existing_mistakes
        grammar_error_count = len(existing_mistakes)

        # 3. Check Topic Relevance
        topic_clean = (topic or "").strip().lower()
        is_off_topic = False
        if topic_clean not in ["general topic", "general practice", "free speech", "unassigned", ""]:
            stop_words = {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "with", "have", "from", "that", "this", "your", "more", "some", "like", "about", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "well", "being"}
            topic_keywords = [w for w in re.findall(r'\b\w+\b', topic_clean) if len(w) >= 4 and w not in stop_words]
            if topic_keywords:
                matched_kws = [kw for kw in topic_keywords if kw in (transcript or "").lower()]
                overlap_ratio = len(matched_kws) / max(1, len(topic_keywords))
                if (len(topic_keywords) >= 2 and len(matched_kws) < 1) or overlap_ratio < 0.25:
                    is_off_topic = True

        # Proportional Scoring Tiers based on Length & Structure
        if total_words < 5:
            # Saying only "hello", "hi", "test"
            score_val = max(5, min(15, total_words * 3))
            for col in ["overall_score", "grammar_score", "vocabulary_score", "confidence_score", "fluency_score", "communication_score"]:
                data[col] = score_val
            data["strengths"] = ["Microphone recording was captured successfully."]
            data["weaknesses"] = [
                f"Speech was only {total_words} word(s) ('{transcript}'). Please speak in complete sentences to evaluate your communication skills.",
                f"Did not address the assigned topic: '{topic}'."
            ]
            if not existing_mistakes:
                data["mistakes"] = [{
                    "original": transcript,
                    "correction": f"Good morning everyone, today I want to discuss '{topic}'...",
                    "reason": "Expand single-word greetings into a complete speech addressing your assigned topic."
                }]
            data["improvement_suggestions"] = [
                "Aim for at least 30 to 60 seconds of speaking to develop a full thought.",
                "Introduce a clear thesis statement within your opening sentence.",
                "Provide supporting examples and a closing summary."
            ]
            data["motivational_feedback"] = (
                f"Your session received an Overall Score of {score_val}/100 because only {total_words} word(s) were recorded. "
                f"Please deliver a complete speech addressing '{topic}' to get full feedback on your grammar, vocabulary, and delivery."
            )
        # Validate list types for strengths, weaknesses, and suggestions
        for list_key in ["strengths", "weaknesses", "improvement_suggestions"]:
            raw_list = data.get(list_key, [])
            if not isinstance(raw_list, list):
                raw_list = [str(raw_list)] if raw_list else []
            data[list_key] = [str(item) for item in raw_list if item is not None and str(item).strip()]

        # Validate mistakes as a list of dicts with original, correction, reason
        raw_mistakes = data.get("mistakes", [])
        if not isinstance(raw_mistakes, list):
            raw_mistakes = []
        valid_mistakes = []
        for m in raw_mistakes:
            if isinstance(m, dict):
                orig = str(m.get("original", "")).strip()
                corr = str(m.get("correction", "")).strip()
                reason = str(m.get("reason", m.get("explanation", ""))).strip()
                if orig or corr:
                    valid_mistakes.append({
                        "original": orig,
                        "correction": corr,
                        "reason": reason
                    })
        data["mistakes"] = valid_mistakes

        # Ensure all scores are strictly bounded 0-100 and integers via safe _to_score
        for k in ["overall_score", "grammar_score", "vocabulary_score", "confidence_score", "fluency_score", "communication_score", "presence_score"]:
            data[k] = _to_score(data.get(k, 0))

        # Ensure strings and feedback fields are valid
        if not data.get("body_language_feedback") or not isinstance(data.get("body_language_feedback"), str):
            data["body_language_feedback"] = str(data.get("body_language_feedback") or "")

        return data

    def _sanitize_response(self, data: dict) -> dict:
        """
        Ensures all required keys exist and values are valid types.
        """
        if not isinstance(data, dict):
            data = self._empty_response()
        default_resp = self._empty_response()
        for key in default_resp:
            if key not in data or data[key] is None:
                data[key] = default_resp[key]
        return data

    def _empty_response(self) -> dict:
        return {
            "overall_score": 0,
            "grammar_score": 0,
            "confidence_score": 0,
            "vocabulary_score": 0,
            "communication_score": 0,
            "fluency_score": 0,
            "presence_score": 0,
            "body_language_feedback": "",
            "strengths": ["Microphone active and recording ready"],
            "weaknesses": ["No speech transcript was detected in this practice session"],
            "mistakes": [],
            "improvement_suggestions": [
                "Ensure your microphone is enabled and speak clearly into the microphone.",
                "Speak for at least 45 to 60 seconds on the assigned topic."
            ],
            "motivational_feedback": "No speech transcript was recorded. Please check your microphone permissions and try speaking clearly into the microphone!",
            "practice_exercises": [
                "Microphone Check: Practice a 10-second introduction to ensure your speech is transcribed accurately."
            ],
        }

