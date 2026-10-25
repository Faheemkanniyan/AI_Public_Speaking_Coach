import io
import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.management import call_command
from app.utils import safe_int
from app.services.gemini_service import (
    GeminiSpeechAnalyzer,
    GeminiEvaluationError,
    map_gemini_exception,
    call_gemini_with_retry,
    compute_objective_speech_metrics,
    _to_score
)
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


class GeminiScoreAndErrorMappingTests(TestCase):
    def test_to_score_utility(self):
        self.assertEqual(_to_score(None), 0)
        self.assertEqual(_to_score(85), 85)
        self.assertEqual(_to_score(150), 100)
        self.assertEqual(_to_score(-20), 0)
        self.assertEqual(_to_score("85/100"), 85)
        self.assertEqual(_to_score("Overall: 92%"), 92)
        self.assertEqual(_to_score("no score"), 0)

    def test_error_mapping_exact_codes_and_messages(self):
        # 1. No key
        err_no_key = GeminiEvaluationError(code="no_key", message="GEMINI_API_KEY is not set")
        self.assertEqual(err_no_key.code, "no_key")
        self.assertEqual(err_no_key.message, "GEMINI_API_KEY is not set")

        # 2. 400/401/403 -> auth_error
        e401 = Exception("401 UNAUTHENTICATED: API_KEY_INVALID")
        mapped_401 = map_gemini_exception(e401)
        self.assertEqual(mapped_401.code, "auth_error")
        self.assertEqual(mapped_401.message, "Gemini API key is invalid or not allowed")

        # 3. 404 -> model_not_found
        e404 = Exception("404 NOT_FOUND: models/nonexistent is not found")
        mapped_404 = map_gemini_exception(e404, model_name="nonexistent")
        self.assertEqual(mapped_404.code, "model_not_found")
        self.assertEqual(mapped_404.message, "Model 'nonexistent' not found, check GEMINI_MODEL")

        # 4. 429 -> rate_limit
        e429 = Exception("429 RESOURCE_EXHAUSTED: quota exceeded for quota metric")
        mapped_429 = map_gemini_exception(e429)
        self.assertEqual(mapped_429.code, "rate_limit")
        self.assertEqual(mapped_429.message, "Gemini quota/rate limit exceeded, try later")

        # 5. 5xx/timeout -> unavailable
        e503 = Exception("503 UNAVAILABLE: backend outage timed out")
        mapped_503 = map_gemini_exception(e503)
        self.assertEqual(mapped_503.code, "unavailable")
        self.assertEqual(mapped_503.message, "Gemini is unavailable")

        # 6. invalid_response
        err_invalid = GeminiEvaluationError(code="invalid_response", message="Gemini returned an unusable response")
        self.assertEqual(err_invalid.code, "invalid_response")
        self.assertEqual(err_invalid.message, "Gemini returned an unusable response")

    def test_analyze_speech_raises_error_without_fallback_when_gemini_fails(self):
        analyzer = GeminiSpeechAnalyzer()
        analyzer.client = MagicMock()
        analyzer.api_key = "test_key"
        analyzer.client.models.generate_content.side_effect = Exception("429 Resource exhausted: rate limit exceeded")

        speech = (
            "Good morning distinguished colleagues. Today I am speaking about executive communication, "
            "team leadership, strategic collaboration, and how we can elevate public speaking performance "
            "across global engineering teams through consistent daily practice."
        )
        with self.assertRaises(GeminiEvaluationError) as ctx:
            analyzer.analyze_speech(speech, topic_title="Leadership")

        self.assertEqual(ctx.exception.code, "rate_limit")
        self.assertIn("quota/rate limit exceeded", ctx.exception.message)

    def test_analyze_speech_raises_no_key_when_key_missing(self):
        analyzer = GeminiSpeechAnalyzer()
        analyzer.api_key = ""
        analyzer.client = None

        speech = "This is a substantial test speech delivered by the speaker on the topic of communication leadership and team development."
        with self.assertRaises(GeminiEvaluationError) as ctx:
            analyzer.analyze_speech(speech, topic_title="Leadership")

        self.assertEqual(ctx.exception.code, "no_key")
        self.assertEqual(ctx.exception.message, "GEMINI_API_KEY is not set")

    def test_call_gemini_with_retry_only_retries_transient_errors(self):
        client = MagicMock()
        # 400/401/403: must NOT retry
        client.models.generate_content.side_effect = Exception("401 Unauthorized API key")
        with self.assertRaises(Exception):
            call_gemini_with_retry(client, "gemini-3-flash-preview", "test", max_retries=2, base_delay=0.01)
        self.assertEqual(client.models.generate_content.call_count, 1)

        # 429: retries max 2 times (total 3 attempts)
        client.reset_mock()
        client.models.generate_content.side_effect = Exception("429 rate limit exceeded")
        with self.assertRaises(Exception):
            call_gemini_with_retry(client, "gemini-3-flash-preview", "test", max_retries=2, base_delay=0.01)
        self.assertEqual(client.models.generate_content.call_count, 3)


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

    def test_speech_service_evaluation_failure_sets_status_and_no_report(self):
        from app.services.speech_service import SpeechService
        session = SpeechSession.objects.create(
            user=self.user,
            topic_title="Leadership",
            transcript="This is a practice speech about leadership and decision making under pressure with enough words.",
            duration_seconds=60
        )

        with patch("app.services.gemini_service.GeminiSpeechAnalyzer.analyze_speech") as mock_analyze:
            mock_analyze.side_effect = GeminiEvaluationError(code="rate_limit", message="Gemini quota/rate limit exceeded, try later")
            service = SpeechService()
            sess, rep = service.analyze_existing_session(session.id)

        session.refresh_from_db()
        self.assertEqual(session.status, "evaluation_failed")
        self.assertEqual(session.error_code, "rate_limit")
        self.assertIn("quota/rate limit exceeded", session.error_message)
        self.assertIsNone(rep)
        self.assertFalse(SpeechReport.objects.filter(session=session).exists())
        # Measurable facts must be preserved
        self.assertGreater(session.word_count, 0)
        self.assertGreater(session.wpm, 0)

    def test_api_speech_analyze_returns_503_on_evaluation_failed(self):
        url = reverse("api_speech_analyze")
        with patch("app.services.gemini_service.GeminiSpeechAnalyzer.analyze_speech") as mock_analyze:
            mock_analyze.side_effect = GeminiEvaluationError(code="unavailable", message="Gemini is unavailable")
            resp = self.client.post(url, {
                "transcript": "This is a full transcript that is delivered by the speaker during speech practice session.",
                "duration_seconds": 60
            })

        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["code"], "unavailable")
        self.assertEqual(data["message"], "Gemini is unavailable")

    def test_check_gemini_management_command_pass(self):
        out = io.StringIO()
        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_model = MagicMock()
            mock_model.name = "models/gemini-3.5-flash"
            mock_client.models.list.return_value = [mock_model]
            mock_resp = MagicMock()
            mock_resp.text = "pong"
            mock_client.models.generate_content.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            call_command("check_gemini", stdout=out)
            output = out.getvalue()
            self.assertIn("PASS: Gemini API is healthy", output)

    def test_check_gemini_management_command_fail_no_key(self):
        out = io.StringIO()
        with patch("django.conf.settings.GEMINI_API_KEY", ""):
            with self.assertRaises(SystemExit) as cm:
                call_command("check_gemini", stdout=out)
            self.assertEqual(cm.exception.code, 1)
            self.assertIn("FAIL: GEMINI_API_KEY is not set", out.getvalue())

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
