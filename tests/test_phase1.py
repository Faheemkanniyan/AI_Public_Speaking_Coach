import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from app.utils import safe_int
from app.services.gemini_service import GeminiSpeechAnalyzer, _to_score
from app.models import SpeechSession, SpeechReport, InterviewSession, InterviewQuestion, InterviewAnswer, InterviewFeedback


class SafeIntTests(TestCase):
    def test_safe_int_valid_conversion(self):
        self.assertEqual(safe_int("42"), 42)
        self.assertEqual(safe_int(42), 42)

    def test_safe_int_defaults_on_invalid(self):
        self.assertEqual(safe_int("invalid", default=10), 10)
        self.assertEqual(safe_int(None, default=5), 5)
        self.assertIsNone(safe_int("abc", default=None))

    def test_safe_int_clamping(self):
        self.assertEqual(safe_int("5000", default=60, min=1, max=3600, clamp=True), 3600)
        self.assertEqual(safe_int("-5", default=60, min=1, max=3600, clamp=True), 1)
        self.assertEqual(safe_int("120", default=60, min=1, max=3600, clamp=True), 120)

    def test_safe_int_range_validation_without_clamp(self):
        self.assertEqual(safe_int("10", default=None, min=1, max=7), None)
        self.assertEqual(safe_int("5", default=None, min=1, max=7), 5)


class GeminiScoreAndFallbackTests(TestCase):
    def test_to_score_utility(self):
        self.assertEqual(_to_score(None), 0)
        self.assertEqual(_to_score(85), 85)
        self.assertEqual(_to_score(150), 100)
        self.assertEqual(_to_score(-20), 0)
        self.assertEqual(_to_score("85/100"), 85)
        self.assertEqual(_to_score("Overall: 92%"), 92)
        self.assertEqual(_to_score("no score"), 0)

    def test_apply_strict_speech_evaluation_rules_handles_null_and_malformed(self):
        analyzer = GeminiSpeechAnalyzer()
        raw_data = {
            "overall_score": None,
            "grammar_score": "75/100",
            "confidence_score": 80,
            "strengths": "Single string instead of list",
            "weaknesses": None,
            "mistakes": "invalid mistakes list",
            "improvement_suggestions": ["Keep practicing"]
        }
        res = analyzer._apply_strict_speech_evaluation_rules(
            raw_data, "Here is a complete speech test transcript with more than fifteen words for testing.",
            "Test Topic", 60, "en-US"
        )
        self.assertEqual(res["overall_score"], 0)
        self.assertEqual(res["grammar_score"], 75)
        self.assertEqual(res["confidence_score"], 80)
        self.assertIsInstance(res["strengths"], list)
        self.assertIsInstance(res["weaknesses"], list)
        self.assertIsInstance(res["mistakes"], list)
        self.assertIsInstance(res["improvement_suggestions"], list)

    def test_gemini_refine_stt_failure_falls_back_gracefully(self):
        analyzer = GeminiSpeechAnalyzer()
        analyzer.client = MagicMock()
        analyzer.client.models.generate_content.side_effect = Exception("Gemini API error")
        # Should not raise exception; must return raw transcript
        result = analyzer.refine_stt_transcript("Hello this is test speech", topic="Testing")
        self.assertEqual(result, "Hello this is test speech")

    def test_analyze_speech_falls_back_on_gemini_exception(self):
        analyzer = GeminiSpeechAnalyzer()
        analyzer.client = MagicMock()
        analyzer.client.models.generate_content.side_effect = Exception("Gemini Outage")
        res = analyzer.analyze_speech("Hello world, this is a test speech to verify offline fallback works properly without crashing.")
        self.assertIn("overall_score", res)
        self.assertGreater(res["overall_score"], 0)


class Phase1ApiAndViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="phase1user", email="p1@example.com", password="PassWord123!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_api_speech_analyze_rejects_invalid_duration(self):
        url = reverse("api_speech_analyze")
        resp = self.client.post(url, {
            "transcript": "Valid transcript here",
            "duration_seconds": "invalid_duration"
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data["status"], "error")

    def test_api_generate_tts_missing_openai_key_returns_503(self):
        session = SpeechSession.objects.create(
            user=self.user,
            topic_title="TTS test",
            transcript="Testing speech transcript",
            duration_seconds=60
        )
        SpeechReport.objects.create(session=session, overall_score=80)

        url = reverse("api_generate_tts", kwargs={"session_id": session.id})
        with patch("app.api_views.settings.OPENAI_API_KEY", ""), patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            resp = self.client.post(url)
            self.assertEqual(resp.status_code, 503)
            self.assertIn("TTS is not configured", resp.json().get("message", ""))

    def test_api_generate_tts_missing_session_returns_404(self):
        url = reverse("api_generate_tts", kwargs={"session_id": 99999})
        with patch("app.api_views.settings.OPENAI_API_KEY", "test-key"), patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            resp = self.client.post(url)
            self.assertEqual(resp.status_code, 404)

    def test_onboarding_view_rejects_out_of_range_numbers(self):
        url = reverse("onboarding")
        resp = self.client.post(url, {
            "daily_time": "300", # Max is 240
            "practice_days": "10" # Max is 7
        })
        self.assertEqual(resp.status_code, 400)

    def test_interview_setup_view_rejects_invalid_num_questions(self):
        url = reverse("interview_setup")
        resp = self.client.post(url, {
            "interview_type": "technical",
            "domain": "software",
            "num_questions": "50" # Max is 15
        })
        self.assertEqual(resp.status_code, 400)

    def test_interview_feedback_view_handles_missing_feedback_gracefully(self):
        int_session = InterviewSession.objects.create(
            user=self.user,
            interview_type="technical",
            domain="backend",
            total_questions=1
        )
        question = InterviewQuestion.objects.create(
            session=int_session,
            question_number=1,
            question_text="What is Django?"
        )
        answer = InterviewAnswer.objects.create(
            question=question,
            transcript="Django is a python web framework",
            duration_seconds=30
        )
        # Ensure answer has NO feedback attached
        self.assertFalse(hasattr(answer, 'feedback'))

        url = reverse("interview_feedback", kwargs={"session_id": int_session.id, "question_id": question.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Django is a python web framework")
