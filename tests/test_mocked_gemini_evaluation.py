import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from app.models import SpeechSession, SpeechReport, InterviewSession, InterviewQuestion, InterviewAnswer
from app.services.gemini_service import (
    GeminiSpeechAnalyzer,
    GeminiEvaluationError,
    _to_score,
    is_verbatim_substring
)
from app.services.interview_service import InterviewService


class MockedGeminiEvaluationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mock_user", password="password123")
        self.analyzer = GeminiSpeechAnalyzer()
        self.analyzer.api_key = "fake_key_for_mock"
        self.analyzer.client = MagicMock()

    def test_hallucinated_quotes_and_mistakes_are_dropped(self):
        """Quotes and mistake originals not in the candidate transcript are dropped."""
        transcript = (
            "Good morning everyone. Today I will discuss sustainable green energy and its transformative impact "
            "on communities around the globe through reliable solar and wind infrastructure."
        )
        raw_model_response = {
            "topic_relevance": 90,
            "topic_relevance_reason": "Discusses green energy directly.",
            "scores": {
                "grammar": {
                    "score": 85,
                    "evidence": [
                        {"quote": "I will discuss sustainable green energy", "reason": "Accurate future tense construct"},
                        {"quote": "We was walking through the solar field", "reason": "Hallucinated: speaker never said this"}
                    ]
                },
                "vocabulary": {"score": 85, "evidence": [{"quote": "transformative impact", "reason": "Advanced lexical variety"}]},
                "fluency": {"score": 80, "evidence": [{"quote": "Good morning everyone", "reason": "Polite fluent greeting"}]},
                "clarity": {"score": 85, "evidence": [{"quote": "green energy and its transformative impact", "reason": "Clear articulation"}]},
                "confidence_delivery": {"score": 80, "evidence": []},
                "content_relevance": {"score": 90, "evidence": []}
            },
            "mistakes": [
                {"original": "green energy", "correction": "renewable energy", "type": "word_choice", "reason": "Stylistic preference"},
                {"original": "I ain't got no money", "correction": "I do not have money", "type": "grammar", "reason": "Hallucinated mistake"}
            ],
            "strengths": [
                {"strength": "Clear purpose stated", "evidence_quote": "Today I will discuss sustainable green energy"},
                {"strength": "Good storytelling about childhood", "evidence_quote": "When I was seven years old in Ohio"}  # Hallucinated
            ],
            "weaknesses": [
                {"weakness": "Could use stronger conclusion", "evidence_quote": "transformative impact on communities"}
            ],
            "suggestions": ["Add a quantitative metric to substantiate impact."]
        }

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(raw_model_response)

        with patch("app.services.gemini_service.call_gemini_with_retry", return_value=mock_resp):
            result = self.analyzer.analyze_speech(transcript, "Renewable Energy", duration_seconds=60)

        # 1. Hallucinated grammar evidence quote dropped
        grammar_ev = result["raw_model_json"]["scores"]["grammar"]["evidence"]
        self.assertEqual(len(grammar_ev), 1)
        self.assertEqual(grammar_ev[0]["quote"], "I will discuss sustainable green energy")

        # 2. Hallucinated mistake dropped
        mistakes = result["mistakes"]
        self.assertEqual(len(mistakes), 1)
        self.assertEqual(mistakes[0]["original"], "green energy")

        # 3. Hallucinated strength dropped
        strengths = result["strengths"]
        self.assertEqual(len(strengths), 1)
        self.assertIn("sustainable green energy", str(strengths[0]))

    def test_null_string_and_float_scores_are_safely_coerced(self):
        """Scores returned as None, string with suffix, or floats are safely coerced to int 0-100."""
        self.assertEqual(_to_score(None, default=60), 60)
        self.assertEqual(_to_score("85/100"), 85)
        self.assertEqual(_to_score("92%"), 92)
        self.assertEqual(_to_score(78.6), 79)
        self.assertEqual(_to_score("invalid_str", default=50), 50)
        self.assertEqual(_to_score(150), 100)
        self.assertEqual(_to_score(-20), 0)

    def test_gemini_api_errors_raise_gemini_evaluation_error_with_correct_codes(self):
        """Gemini 429, 404, 401, timeouts produce distinct GeminiEvaluationError codes without fake scores."""
        transcript = "This is a valid practice speech about artificial intelligence and public speaking." * 3

        # 1. Rate limit (429)
        with patch("app.services.gemini_service.call_gemini_with_retry", side_effect=Exception("429 Resource exhausted: quota exceeded")):
            with self.assertRaises(GeminiEvaluationError) as ctx:
                self.analyzer.analyze_speech(transcript, "AI", 60)
            self.assertEqual(ctx.exception.code, "rate_limit")
            self.assertIn("quota/rate limit exceeded", ctx.exception.message)

        # 2. Model not found (404)
        with patch("app.services.gemini_service.call_gemini_with_retry", side_effect=Exception("404 Model gemini-fake not found")):
            with self.assertRaises(GeminiEvaluationError) as ctx:
                self.analyzer.analyze_speech(transcript, "AI", 60)
            self.assertEqual(ctx.exception.code, "model_not_found")
            self.assertIn("not found", ctx.exception.message)

        # 3. Auth error (401/403)
        with patch("app.services.gemini_service.call_gemini_with_retry", side_effect=Exception("403 API key not valid")):
            with self.assertRaises(GeminiEvaluationError) as ctx:
                self.analyzer.analyze_speech(transcript, "AI", 60)
            self.assertEqual(ctx.exception.code, "auth_error")
            self.assertIn("invalid or not allowed", ctx.exception.message)

        # 4. Timeout / Unavailable (503)
        with patch("app.services.gemini_service.call_gemini_with_retry", side_effect=Exception("503 Service Unavailable")):
            with self.assertRaises(GeminiEvaluationError) as ctx:
                self.analyzer.analyze_speech(transcript, "AI", 60)
            self.assertEqual(ctx.exception.code, "unavailable")
            self.assertIn("unavailable", ctx.exception.message)

    def test_short_speech_under_25_words_returns_not_enough_speech_with_zero_scores(self):
        """Speech with fewer than 25 words returns zero scores and 'Not enough speech to evaluate'."""
        short_transcript = "Hello, this is just a very short test."
        result = self.analyzer.analyze_speech(short_transcript, "General", 10)

        self.assertEqual(result["overall_score"], 0)
        self.assertEqual(result["grammar_score"], 0)
        self.assertEqual(result["vocabulary_score"], 0)
        self.assertEqual(result["fluency_score"], 0)
        self.assertEqual(result["rating_label"], "Not Enough Speech")
        self.assertIn("Not enough speech to evaluate", result["motivational_feedback"])

    def test_overall_score_calculated_in_code_from_documented_weights(self):
        """Overall score = 25% Fluency + 20% Grammar + 15% Vocab + 15% Clarity + 15% Relevance + 10% Confidence."""
        transcript = "In today's presentation I am demonstrating our verified scoring formula using strict code-side arithmetic." * 3
        raw_response = {
            "topic_relevance": 80,
            "topic_relevance_reason": "On topic",
            "scores": {
                "grammar": {"score": 90, "evidence": []},          # 90 * 0.20 = 18.0
                "vocabulary": {"score": 80, "evidence": []},       # 80 * 0.15 = 12.0
                "fluency": {"score": 70, "evidence": []},          # 70 * 0.25 = 17.5
                "clarity": {"score": 80, "evidence": []},          # 80 * 0.15 = 12.0
                "confidence_delivery": {"score": 60, "evidence": []}, # 60 * 0.10 = 6.0
                "content_relevance": {"score": 80, "evidence": []} # 80 * 0.15 = 12.0
            },
            "mistakes": [],
            "strengths": [],
            "weaknesses": [],
            "suggestions": []
        }
        # Expected: 18.0 + 12.0 + 17.5 + 12.0 + 6.0 + 12.0 = 77.5 -> 78
        mock_resp = MagicMock()
        mock_resp.text = json.dumps(raw_response)

        with patch("app.services.gemini_service.call_gemini_with_retry", return_value=mock_resp):
            result = self.analyzer.analyze_speech(transcript, "Formula Test", 60)

        self.assertEqual(result["overall_score"], 78)

    def test_speech_recognition_errors_do_not_penalize_grammar(self):
        """Likely speech recognition errors are flagged separately and do not penalize grammar."""
        transcript = "Good morning ladies and gentlemen, today I will share insights about our journey." * 2
        raw_response = {
            "topic_relevance": 85,
            "topic_relevance_reason": "On topic",
            "scores": {
                "grammar": {"score": 92, "evidence": []},
                "vocabulary": {"score": 85, "evidence": []},
                "fluency": {"score": 85, "evidence": []},
                "clarity": {"score": 85, "evidence": []},
                "confidence_delivery": {"score": 80, "evidence": []},
                "content_relevance": {"score": 85, "evidence": []}
            },
            "mistakes": [
                {
                    "original": "Good morning",
                    "correction": "Good morning",
                    "type": "likely_speech_recognition_error",
                    "reason": "Audio distortion caused recognition glitch, not a grammar mistake"
                }
            ],
            "strengths": [],
            "weaknesses": [],
            "suggestions": []
        }
        mock_resp = MagicMock()
        mock_resp.text = json.dumps(raw_response)

        with patch("app.services.gemini_service.call_gemini_with_retry", return_value=mock_resp):
            result = self.analyzer.analyze_speech(transcript, "Morning Speech", 30)

        self.assertEqual(result["grammar_score"], 92)
        self.assertEqual(result["mistakes"][0]["type"], "likely_speech_recognition_error")

    def test_interview_unanswered_or_empty_gets_zero_and_no_hallucinations(self):
        """Interview question with empty answer transcript gets 0 score without calling LLM."""
        interview_svc = InterviewService()
        interview_svc.api_key = "test_key"
        interview_svc.client = MagicMock()

        session = InterviewSession.objects.create(
            user=self.user,
            interview_type="Technical",
            domain="Software",
            technology="Django",
            difficulty="Senior"
        )
        q = InterviewQuestion.objects.create(session=session, question_text="Describe Django database routers.")
        ans = InterviewAnswer.objects.create(question=q, transcript="", answer_status="NOT_ANSWERED")

        eval_data = interview_svc.evaluate_answer(ans, "English")
        self.assertEqual(eval_data["overall_score"], 0)
        self.assertEqual(eval_data["classification"], "Not Answered")
        self.assertEqual(eval_data["technical_correctness"], 0)
        self.assertIn("No answer was provided", eval_data["feedback"])
