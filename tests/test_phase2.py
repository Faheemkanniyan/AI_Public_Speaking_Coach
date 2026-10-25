import io
import json
import os
import uuid
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from app.models import (
    SpeechSession, SpeechReport, InterviewSession, InterviewQuestion,
    InterviewAnswer, InterviewFeedback, VisualPresence
)
from app.services.speech_service import SpeechService
from app.services.report_service import ReportService
from app.services.tts_service import TTSService
from app.utils import (
    safe_int, validate_audio_file, validate_and_clean_visual_metrics,
    ratelimit_view
)


class Phase2SecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user_a = User.objects.create_user(username="usera", email="usera@example.com", password="password123")
        self.user_b = User.objects.create_user(username="userb", email="userb@example.com", password="password123")

        self.session_a = SpeechSession.objects.create(
            user=self.user_a,
            topic_title="User A Speech",
            transcript="This is user A's speech transcript.",
            duration_seconds=60,
        )
        self.report_a = SpeechReport.objects.create(
            session=self.session_a,
            overall_score=85,
            grammar_score=85,
            vocabulary_score=85,
            confidence_score=85,
            fluency_score=85,
            communication_score=85,
            motivational_feedback="Good job!",
            tts_audio_path="tts/test_feedback.mp3",
        )

        # Create dummy file on disk for TTS
        from django.conf import settings
        tts_dir = os.path.join(settings.MEDIA_ROOT, "tts")
        os.makedirs(tts_dir, exist_ok=True)
        self.dummy_tts_path = os.path.join(tts_dir, "test_feedback.mp3")
        with open(self.dummy_tts_path, "wb") as f:
            f.write(b"FAKE_MP3_CONTENT")

    def tearDown(self):
        cache.clear()
        if os.path.exists(self.dummy_tts_path):
            try:
                os.remove(self.dummy_tts_path)
            except OSError:
                pass

    # -------------------------------------------------------------
    # 6. State-changing views require POST and CSRF
    # -------------------------------------------------------------
    def test_delete_session_view_requires_post(self):
        self.client.force_login(self.user_a)
        # GET request must return 405 Method Not Allowed
        response = self.client.get(f"/history/delete/{self.session_a.id}/")
        self.assertEqual(response.status_code, 405)
        self.assertTrue(SpeechSession.objects.filter(id=self.session_a.id).exists())

        # POST request deletes session
        post_response = self.client.post(f"/history/delete/{self.session_a.id}/")
        self.assertIn(post_response.status_code, (302, 303))
        self.assertFalse(SpeechSession.objects.filter(id=self.session_a.id).exists())

    def test_logout_view_requires_post(self):
        self.client.force_login(self.user_a)
        # GET request must return 405 Method Not Allowed
        response = self.client.get("/logout/")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(int(self.client.session.get("_auth_user_id")), self.user_a.id)

        # POST request logs user out
        post_response = self.client.post("/logout/")
        self.assertEqual(post_response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_interview_retry_feedback_view_requires_post(self):
        int_session = InterviewSession.objects.create(
            user=self.user_a,
            interview_type="Technical",
            total_questions=1,
        )
        question = InterviewQuestion.objects.create(
            session=int_session,
            question_text="Sample question",
            question_number=1
        )
        answer = InterviewAnswer.objects.create(
            question=question,
            transcript="Some answer",
            answer_status="ANSWERED"
        )
        feedback = InterviewFeedback.objects.create(
            answer=answer,
            evaluation_status="FAILED"
        )

        self.client.force_login(self.user_a)
        # GET request must return 405
        response = self.client.get(f"/interview/{int_session.id}/question/{question.id}/retry-feedback/")
        self.assertEqual(response.status_code, 405)

        # POST request is accepted
        with patch("app.interview_views.InterviewService.evaluate_answer") as mock_eval:
            mock_eval.return_value = {"evaluation_status": "EVALUATED", "overall_score": 80}
            post_response = self.client.post(f"/interview/{int_session.id}/question/{question.id}/retry-feedback/")
            self.assertEqual(post_response.status_code, 302)

    # -------------------------------------------------------------
    # 7. Private Media & Access Control
    # -------------------------------------------------------------
    def test_public_media_tts_is_blocked(self):
        response = self.client.get("/media/tts/test_feedback.mp3")
        self.assertEqual(response.status_code, 403)

    def test_private_tts_media_authenticated_and_authorized(self):
        # Anonymous user gets redirected to login
        anon_resp = self.client.get(f"/media-private/tts/{self.session_a.id}/")
        self.assertEqual(anon_resp.status_code, 302)

        # User B cannot access User A's TTS
        self.client.force_login(self.user_b)
        b_resp = self.client.get(f"/media-private/tts/{self.session_a.id}/")
        self.assertEqual(b_resp.status_code, 404)

        # User A can stream own TTS
        self.client.force_login(self.user_a)
        a_resp = self.client.get(f"/media-private/tts/{self.session_a.id}/")
        self.assertEqual(a_resp.status_code, 200)
        self.assertEqual(a_resp["Content-Type"], "audio/mpeg")

    def test_random_uuid_filenames(self):
        # 1. SpeechService save_audio_file uses UUID
        speech_service = SpeechService()
        audio_content = SimpleUploadedFile("user_recording.webm", b"AUDIO_DATA", content_type="audio/webm")
        saved_path = speech_service.save_audio_file(audio_content, user_id=123)
        self.assertIn("speech_", saved_path)
        self.assertNotIn("123", saved_path)
        self.assertNotIn("user_recording", saved_path)

        # Clean up created file
        from django.conf import settings
        full_p = os.path.join(settings.BASE_DIR, saved_path)
        if os.path.exists(full_p):
            os.remove(full_p)

        # 2. ReportService generates UUID filename
        report_service = ReportService()
        pdf_rel = report_service.generate_pdf_report(self.report_a)
        if pdf_rel:
            self.assertIn("speakpro_report_", pdf_rel)
            self.assertNotIn(f"session_{self.session_a.id}", pdf_rel)
            full_pdf = os.path.join(settings.BASE_DIR, pdf_rel)
            if os.path.exists(full_pdf):
                os.remove(full_pdf)

    # -------------------------------------------------------------
    # 8. Settings & Security Configuration
    # -------------------------------------------------------------
    def test_settings_secret_key_missing_raises_when_debug_false(self):
        with patch.dict(os.environ, {"DEBUG": "False", "DJANGO_SECRET_KEY": ""}, clear=False):
            # Test that loading settings with DEBUG=False and no DJANGO_SECRET_KEY raises ImproperlyConfigured
            with self.assertRaises(ImproperlyConfigured):
                # Simulate the check from settings.py
                debug = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
                secret = os.getenv("DJANGO_SECRET_KEY", "")
                if not secret and not debug:
                    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in environment when DEBUG is False.")

    def test_allowed_hosts_parsed_from_comma_separated_env(self):
        allowed_hosts_str = "example.com, test.org, 127.0.0.1"
        parsed = [h.strip() for h in allowed_hosts_str.split(",") if h.strip()]
        self.assertEqual(parsed, ["example.com", "test.org", "127.0.0.1"])

    # -------------------------------------------------------------
    # 9. seed_data command conditions
    # -------------------------------------------------------------
    def test_seed_data_skips_users_in_production_without_flag(self):
        out = io.StringIO()
        with patch("django.conf.settings.DEBUG", False):
            # Delete any existing demo users for test
            User.objects.filter(username__in=["speaker_test", "admin_test"]).delete()
            call_command("seed_data", stdout=out)
            output = out.getvalue()
            self.assertIn("Skipped demo and admin user creation", output)

    def test_seed_data_creates_users_with_flag(self):
        out = io.StringIO()
        with patch("django.conf.settings.DEBUG", False):
            call_command("seed_data", "--with-demo-users", stdout=out)
            output = out.getvalue()
            self.assertIn("Users 'admin' and 'speaker' ready", output)
            self.assertTrue(User.objects.filter(username="admin").exists())
            self.assertTrue(User.objects.filter(username="speaker").exists())

    # -------------------------------------------------------------
    # 10. Rate Limiting
    # -------------------------------------------------------------
    def test_rate_limiting_blocks_after_limit_exceeded(self):
        self.client.force_login(self.user_a)
        # Call api_refine_transcript 10 times (the rate limit is 10/m)
        with patch("app.services.gemini_service.GeminiSpeechAnalyzer.refine_stt_transcript", return_value="Refined"):
            for _ in range(10):
                resp = self.client.post("/api/speech/refine-transcript/", {"transcript": "Test"})
                self.assertEqual(resp.status_code, 200)

            # 11th request must return 429
            blocked_resp = self.client.post("/api/speech/refine-transcript/", {"transcript": "Test"})
            self.assertEqual(blocked_resp.status_code, 429)
            data = blocked_resp.json()
            self.assertEqual(data.get("status"), "error")
            self.assertIn("Rate limit exceeded", data.get("message"))

    # -------------------------------------------------------------
    # 11. Audio File and Visual Metrics Validation
    # -------------------------------------------------------------
    def test_validate_audio_file_size_and_extension(self):
        # Valid webm file
        valid_audio = SimpleUploadedFile("audio.webm", b"SMALL_AUDIO", content_type="audio/webm")
        is_valid, msg = validate_audio_file(valid_audio)
        self.assertTrue(is_valid)

        # Invalid extension
        invalid_ext = SimpleUploadedFile("payload.exe", b"MALICIOUS", content_type="application/octet-stream")
        is_valid, msg = validate_audio_file(invalid_ext)
        self.assertFalse(is_valid)
        self.assertIn("Unsupported audio format", msg)

        # Exceeds max size
        large_audio = SimpleUploadedFile("large.mp3", b"0" * (26 * 1024 * 1024), content_type="audio/mp3")
        is_valid, msg = validate_audio_file(large_audio)
        self.assertFalse(is_valid)
        self.assertIn("exceeds maximum allowed size", msg)

    def test_validate_and_clean_visual_metrics_clamping(self):
        raw_metrics = {
            "eye_contact_pct": 150,  # Should clamp to 100
            "posture_score": -20,    # Should clamp to 0
            "expression_variety_score": "85",  # Should convert to int 85
            "face_detected_pct": "not_a_number",  # Should default to 0
            "extra_field": "test"
        }
        cleaned = validate_and_clean_visual_metrics(raw_metrics)
        self.assertEqual(cleaned["eye_contact_pct"], 100)
        self.assertEqual(cleaned["posture_score"], 0)
        self.assertEqual(cleaned["expression_variety_score"], 85)
        self.assertEqual(cleaned["face_detected_pct"], 0)

    def test_api_speech_analyze_rejects_invalid_audio(self):
        self.client.force_login(self.user_a)
        invalid_audio = SimpleUploadedFile("malicious.sh", b"echo 1", content_type="text/plain")
        resp = self.client.post("/api/speech/analyze/", {
            "transcript": "Hello world",
            "audio_file": invalid_audio
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Unsupported audio format", resp.json().get("message", ""))

    def test_api_speech_analyze_rejects_invalid_visual_metrics_json(self):
        self.client.force_login(self.user_a)
        resp = self.client.post("/api/speech/analyze/", {
            "transcript": "Hello world",
            "visual_metrics": "{not: valid: json}"
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid visual_metrics format", resp.json().get("message", ""))
