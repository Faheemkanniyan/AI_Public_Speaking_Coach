import os
import json
import tempfile
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.base import ContentFile
from django.urls import reverse
from django.conf import settings

from app.models import SpeechSession, SpeechReport, InterviewSession, InterviewQuestion, InterviewAnswer
from app.services.gemini_service import GeminiSpeechAnalyzer, call_gemini_with_retry
from app.services.interview_service import InterviewService


class Phase4TranscriptionAndFilesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="phase4_user", password="Password123!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_analyze_rejects_empty_transcript_when_no_audio(self):
        resp = self.client.post(reverse("api_speech_analyze"), {
            "transcript": "",
            "duration_seconds": 60
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("empty", data["message"].lower())

    @patch("app.services.assemblyai_service.AssemblyAIService.is_enabled", return_value=True)
    @patch("app.services.assemblyai_service.AssemblyAIService.transcribe_audio")
    @patch("app.services.gemini_service.GeminiSpeechAnalyzer._fallback_nlp_analysis")
    def test_analyze_transcribes_audio_when_transcript_is_empty(self, mock_fallback, mock_transcribe, mock_is_enabled):
        mock_transcribe.return_value = {
            "status": "completed",
            "text": "This is audio transcribed on the server via AssemblyAI."
        }
        mock_fallback.return_value = {
            "overall_score": 85,
            "grammar_score": 85,
            "strengths": ["Clear audio"],
            "weaknesses": [],
            "mistakes": [],
            "improvement_suggestions": [],
            "motivational_feedback": "Good job!",
            "practice_exercises": []
        }

        audio_content = b"\x1a\x45\xdf\xa3" + b"\x00" * 100
        audio_file = SimpleUploadedFile("test.webm", audio_content, content_type="audio/webm")

        resp = self.client.post(reverse("api_speech_analyze"), {
            "transcript": "",
            "audio_file": audio_file,
            "duration_seconds": 60
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

        session = SpeechSession.objects.get(id=data["session_id"])
        self.assertEqual(session.transcript, "This is audio transcribed on the server via AssemblyAI.")
        self.assertTrue(bool(session.audio_file))

    def test_post_delete_signal_removes_audio_file(self):
        session = SpeechSession.objects.create(
            user=self.user,
            transcript="Testing deletion",
            duration_seconds=30
        )
        session.audio_file.save("test_delete.webm", ContentFile(b"dummy audio content"), save=True)
        file_path = session.audio_file.path
        self.assertTrue(os.path.isfile(file_path))

        # Delete session
        session.delete()
        self.assertFalse(os.path.isfile(file_path))

    def test_post_delete_signal_removes_report_pdf_and_tts(self):
        session = SpeechSession.objects.create(
            user=self.user,
            transcript="Testing report files deletion",
            duration_seconds=30
        )
        # Create temp dummy PDF and TTS files
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f_pdf:
            f_pdf.write(b"%PDF-1.4 dummy pdf")
            pdf_path = f_pdf.name

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f_tts:
            f_tts.write(b"dummy mp3")
            tts_path = f_tts.name

        report = SpeechReport.objects.create(
            session=session,
            overall_score=80,
            pdf_report=pdf_path,
            tts_audio_path=tts_path
        )
        self.assertTrue(os.path.isfile(pdf_path))
        self.assertTrue(os.path.isfile(tts_path))

        report.delete()
        self.assertFalse(os.path.isfile(pdf_path))
        self.assertFalse(os.path.isfile(tts_path))


class Phase4CeleryAndAsyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="celery_user", password="Password123!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_api_speech_status_returns_processing_then_completed(self):
        session = SpeechSession.objects.create(
            user=self.user,
            transcript="Async speech session test",
            duration_seconds=45
        )
        # 1. When report does not exist yet
        resp = self.client.get(reverse("api_speech_status", args=[session.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "processing")

        # 2. Result view renders is_processing=True
        res_page = self.client.get(reverse("result", args=[session.id]))
        self.assertEqual(res_page.status_code, 200)
        self.assertContains(res_page, "AI Speech Analysis in Progress")

        # 3. Create report -> status becomes completed
        report = SpeechReport.objects.create(session=session, overall_score=88)
        resp2 = self.client.get(reverse("api_speech_status", args=[session.id]))
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertEqual(data2["status"], "completed")
        self.assertEqual(data2["overall_score"], 88)

        # 4. Result view renders full report
        res_page2 = self.client.get(reverse("result", args=[session.id]))
        self.assertEqual(res_page2.status_code, 200)
        self.assertContains(res_page2, "AI EVALUATION COMPLETE")


class Phase4GeminiConfigAndAICoachRemovalTests(TestCase):
    def test_gemini_model_configuration_used_by_services(self):
        analyzer = GeminiSpeechAnalyzer()
        self.assertEqual(analyzer.model_name, getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"))

        interview_svc = InterviewService()
        if interview_svc.model_name:
            self.assertEqual(interview_svc.model_name, getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"))

    def test_call_gemini_with_retry_succeeds_after_transient_failure(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"overall_score": 90}'

        # Fail once with 429 then succeed
        mock_client.models.generate_content.side_effect = [
            Exception("429 Resource exhausted: rate limit exceeded"),
            mock_response
        ]

        res = call_gemini_with_retry(mock_client, "gemini-test", "prompt test", max_retries=2, base_delay=0.01)
        self.assertEqual(res, mock_response)
        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    def test_ai_coach_feature_completely_removed(self):
        client = Client()
        user = User.objects.create_user(username="coach_checker", password="Password123!")
        client.force_login(user)

        # /api/coach/chat/ should 404
        resp = client.post("/api/coach/chat/", {"message": "hello"})
        self.assertEqual(resp.status_code, 404)

        # /ai-coach/ should 404
        resp_page = client.get("/ai-coach/")
        self.assertEqual(resp_page.status_code, 404)
