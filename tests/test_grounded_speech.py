import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from app.services.gemini_service import (
    GeminiSpeechAnalyzer,
    GeminiEvaluationError,
    compute_objective_speech_metrics,
    is_verbatim_substring,
    _to_score
)
from app.models import SpeechSession, SpeechReport, User


class GroundedSpeechEvaluationTests(TestCase):
    def setUp(self):
        self.analyzer = GeminiSpeechAnalyzer()
        self.analyzer.api_key = "test_key"
        self.analyzer.client = MagicMock()

    def test_objective_metrics_calculation_in_python(self):
        transcript = "Good morning everyone. Um, today I would like to, uh, discuss our project results and basically share the outcome."
        metrics = compute_objective_speech_metrics(transcript, duration_seconds=30)
        self.assertEqual(metrics["duration_seconds"], 30)
        self.assertGreater(metrics["word_count"], 10)
        self.assertEqual(metrics["wpm"], int((metrics["word_count"] / 30) * 60))
        # Um, uh, basically, like are in filler list
        self.assertGreaterEqual(metrics["filler_count"], 3)
        self.assertIn("um", metrics["filler_breakdown"])
        self.assertIn("uh", metrics["filler_breakdown"])

    def test_short_speech_under_25_words_returns_not_enough_speech(self):
        short_speech = "Hello everyone. Thank you for coming today. I am happy to be here."
        # Word count is 13 (< 25 words)
        res = self.analyzer.analyze_speech(short_speech, topic_title="General Practice", duration_seconds=60)
        self.assertTrue(res["is_insufficient_speech"])
        self.assertEqual(res["overall_score"], 0)
        self.assertEqual(res["grammar_score"], 0)
        self.assertIn("Not enough speech to evaluate", res["motivational_feedback"])
        # Ensure Gemini client was never called for < 25 words
        self.analyzer.client.models.generate_content.assert_not_called()

    def test_hallucinated_mistakes_and_quotes_are_dropped(self):
        speech = (
            "Ladies and gentlemen, today we examine the future of artificial intelligence in public speaking. "
            "Clear communication is essential for effective leadership, yet many professionals struggle with delivery. "
            "Through daily structured practice, everyone can build confidence and articulate their ideas with clarity."
        )

        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "topic_relevance_score": 92,
            "topic_relevance_explanation": "Directly addresses public speaking and artificial intelligence.",
            "grammar_score": 85,
            "grammar_evidence": {
                "quotes": ["Clear communication is essential", "This quote was hallucinated by LLM"],
                "reason": "Strong compound sentence structure throughout."
            },
            "vocabulary_score": 88,
            "vocabulary_evidence": {
                "quotes": ["articulate their ideas with clarity"],
                "reason": "Strong academic vocabulary."
            },
            "fluency_score": 80,
            "fluency_evidence": {
                "quotes": ["yet many professionals struggle"],
                "reason": "Natural spoken cadence."
            },
            "clarity_score": 86,
            "clarity_evidence": {
                "quotes": ["Through daily structured practice"],
                "reason": "Coherent sentence progression."
            },
            "confidence_delivery_score": 84,
            "confidence_delivery_evidence": {
                "quotes": ["Ladies and gentlemen"],
                "reason": "Authoritative opening."
            },
            "content_relevance_score": 90,
            "content_relevance_evidence": {
                "quotes": ["future of artificial intelligence"],
                "reason": "Directly tied to the topic."
            },
            "mistakes": [
                {
                    "original": "articulate their ideas",
                    "correction": "articulate their thoughts",
                    "type": "word_choice",
                    "reason": "Slightly more natural."
                },
                {
                    "original": "TOTAL HALLUCINATION NEVER SPOKEN",
                    "correction": "Correction for phantom mistake",
                    "type": "grammar",
                    "reason": "Fabricated by rogue model"
                }
            ],
            "strengths": [
                'Effective opening: "Ladies and gentlemen"',
                'Ungrounded strength without quote at all'
            ],
            "weaknesses": [
                'Room for expansion: "many professionals struggle with delivery"'
            ],
            "suggestions": [
                "Incorporate interactive audience questions during key points."
            ],
            "motivational_feedback": "A compelling, grounded speech delivered with clarity.",
            "practice_exercises": ["Pacing exercise: pause 2s between sentences."]
        })

        self.analyzer.client.models.generate_content.return_value = mock_response

        res = self.analyzer.analyze_speech(speech, topic_title="AI and Speaking")

        # 1. Hallucinated mistake must be dropped
        originals = [m["original"] for m in res["mistakes"]]
        self.assertIn("articulate their ideas", originals)
        self.assertNotIn("TOTAL HALLUCINATION NEVER SPOKEN", originals)

        # 2. Hallucinated evidence quote must be dropped
        grammar_quotes = res["score_evidence"]["grammar"]["quotes"]
        self.assertIn("Clear communication is essential", grammar_quotes)
        self.assertNotIn("This quote was hallucinated by LLM", grammar_quotes)

        # 3. Overall score must be calculated in code:
        # Grammar 85 (0.20=17) + Vocab 88 (0.15=13.2) + Fluency 80 (0.25=20) + Clarity 86 (0.15=12.9) + Conf 84 (0.10=8.4) + Content 90 (0.15=13.5)
        # Expected = 17 + 13.2 + 20 + 12.9 + 8.4 + 13.5 = 85.0 -> 85
        self.assertEqual(res["overall_score"], 85)

        # 4. Provenance must be stored
        self.assertEqual(res["engine"], "gemini")
        self.assertEqual(res["model_name"], "gemini-3.5-flash")
        self.assertEqual(res["prompt_version"], "v2.0-grounded")

    def test_speech_recognition_errors_are_not_counted_in_grammar(self):
        speech = (
            "I have been working as a software engineer for five years. "
            "Our team builds distributed cloud systems and we prioritize reliable data storage "
            "and efficient algorithm design for modern enterprises."
        )

        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "topic_relevance_score": 90,
            "topic_relevance_explanation": "Relevant to software engineering.",
            "grammar_score": 70,
            "grammar_evidence": {"quotes": ["I have been working"], "reason": "Grammar check."},
            "vocabulary_score": 85,
            "vocabulary_evidence": {"quotes": ["distributed cloud systems"], "reason": "Technical vocabulary."},
            "fluency_score": 80,
            "fluency_evidence": {"quotes": ["for five years"], "reason": "Good flow."},
            "clarity_score": 85,
            "clarity_evidence": {"quotes": ["prioritize reliable data storage"], "reason": "Clear."},
            "confidence_delivery_score": 80,
            "confidence_delivery_evidence": {"quotes": ["efficient algorithm design"], "reason": "Solid delivery."},
            "content_relevance_score": 90,
            "content_relevance_evidence": {"quotes": ["modern enterprises"], "reason": "Enterprise context."},
            "mistakes": [
                {
                    "original": "software engineer",
                    "correction": "software engineer",
                    "type": "likely_speech_recognition_error",
                    "reason": "Acoustic slip in browser STT."
                }
            ],
            "strengths": ['Clear technical background: "working as a software engineer"'],
            "weaknesses": ['Could give more specific metrics: "efficient algorithm design"'],
            "suggestions": ["Include architecture diagrams or concrete project metrics."],
            "motivational_feedback": "Strong professional presentation.",
            "practice_exercises": []
        })

        self.analyzer.client.models.generate_content.return_value = mock_response

        res = self.analyzer.analyze_speech(speech, topic_title="Software Engineering")

        # Grammar should be protected/compensated for STT error
        self.assertGreater(res["grammar_score"], 70)
        # Marked in speech_recognition_errors
        self.assertEqual(len(res["speech_recognition_errors"]), 1)
        self.assertEqual(res["speech_recognition_errors"][0]["type"], "likely_speech_recognition_error")

    def test_verbatim_substring_checker(self):
        transcript = "The quick brown fox jumps over the lazy dog."
        self.assertTrue(is_verbatim_substring("quick brown fox", transcript))
        self.assertTrue(is_verbatim_substring("Quick Brown Fox", transcript))
        self.assertTrue(is_verbatim_substring("jumps over the lazy dog.", transcript))
        self.assertFalse(is_verbatim_substring("the fast red fox", transcript))
        self.assertFalse(is_verbatim_substring("", transcript))
        self.assertFalse(is_verbatim_substring("fox", ""))
