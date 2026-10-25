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
from django.utils import timezone

from app.models import SpeechSession, SpeechReport, InterviewSession, InterviewQuestion, InterviewAnswer, InterviewFeedback
from app.services.gemini_service import GeminiSpeechAnalyzer, call_gemini_with_retry
from app.services.interview_service import InterviewService
from app.services.report_service import ReportService


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


class Phase4ReportAndUIFixesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ui_tester", password="Password123!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_score_gauge_svg_has_fill_none_and_no_black_circle(self):
        """SVG circle elements must have fill='none' and proper classes so they don't render black."""
        session = SpeechSession.objects.create(
            user=self.user,
            transcript="This is a strong practice speech evaluating modern public speaking skills.",
            duration_seconds=45,
            word_count=45,
            wpm=120
        )
        report = SpeechReport.objects.create(
            session=session,
            overall_score=85,
            fluency_score=80,
            grammar_score=90,
            vocabulary_score=85,
            clarity_score=85,
            content_relevance_score=85,
            confidence_score=80,
            engine="gemini",
            model_name="gemini-3-flash-preview"
        )
        resp = self.client.get(reverse("result", args=[session.id]))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")

        # Must have score-gauge-container, fill="none", and score-gauge-bar
        self.assertIn("score-gauge-container", content)
        self.assertIn('fill="none"', content)
        self.assertIn("score-gauge-bg", content)
        self.assertIn("score-gauge-bar", content)
        self.assertIn("85", content)

    def test_unified_rating_labels_across_speech_and_interview(self):
        """Unified rating labels: Excellent (90+), Strong (75-89), Developing (60-74), Needs Practice (<60)."""
        session = SpeechSession.objects.create(user=self.user, transcript="test speech with enough words to evaluate thoroughly and properly.", duration_seconds=60, word_count=30)
        rep = SpeechReport.objects.create(session=session, overall_score=92)
        self.assertEqual(rep.rating_label, "Excellent")

        rep.overall_score = 78
        self.assertEqual(rep.rating_label, "Strong")

        rep.overall_score = 65
        self.assertEqual(rep.rating_label, "Developing")

        rep.overall_score = 45
        self.assertEqual(rep.rating_label, "Needs Practice")

    def test_speech_evaluation_failure_shows_banner_and_measurable_facts_only(self):
        """When evaluation fails, result page shows error banner, retry button, and measurable facts."""
        session = SpeechSession.objects.create(
            user=self.user,
            topic_title="Leadership Communication",
            transcript="This is the raw recorded speech transcript for the failed session.",
            duration_seconds=30,
            word_count=12,
            wpm=120,
            filler_count=2,
            status="evaluation_failed",
            error_code="rate_limit",
            error_message="Gemini quota/rate limit exceeded, try later"
        )
        resp = self.client.get(reverse("result", args=[session.id]))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")

        self.assertIn("AI EVALUATION UNAVAILABLE", content)
        self.assertIn("rate_limit", content)
        self.assertIn("Gemini quota/rate limit exceeded, try later", content)
        self.assertIn("Retry Evaluation", content)
        self.assertIn("Measurable Facts", content)
        self.assertIn("30s", content)
        self.assertIn("12", content)

    def test_mistakes_table_displays_speech_recognition_error_badge(self):
        """Likely speech recognition errors are badged and noted as not penalized in grammar."""
        session = SpeechSession.objects.create(user=self.user, transcript="speech test", duration_seconds=30)
        mistakes = [
            {"original": "good evening", "correction": "good evening", "type": "likely_speech_recognition_error", "reason": "Acoustic distortion"},
            {"original": "we was going", "correction": "we were going", "type": "grammar", "reason": "Subject verb agreement"}
        ]
        report = SpeechReport.objects.create(
            session=session,
            overall_score=75,
            mistakes_json=json.dumps(mistakes)
        )
        resp = self.client.get(reverse("result", args=[session.id]))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")

        self.assertIn("Speech Rec. Error", content)
        self.assertIn("Not penalized in grammar", content)
        self.assertIn("Grammar", content)

    def test_report_service_pdf_uses_localized_timezone_and_provenance(self):
        """PDF generation uses timezone.localtime, includes model provenance, formula, and transcript."""
        session = SpeechSession.objects.create(
            user=self.user,
            topic_title="Timezone and Provenance Test",
            transcript="Public speaking requires confidence, structure, and clarity in all dimensions.",
            duration_seconds=30,
            word_count=10,
            wpm=120,
            filler_count=1
        )
        report = SpeechReport.objects.create(
            session=session,
            overall_score=80,
            fluency_score=85,
            grammar_score=80,
            vocabulary_score=75,
            clarity_score=80,
            content_relevance_score=80,
            confidence_score=75,
            engine="gemini",
            model_name="gemini-3-flash-preview",
            score_formula="Overall score = 25% Fluency + 20% Grammar + 15% Vocabulary + 15% Clarity + 15% Content Relevance + 10% Confidence/Delivery",
            raw_model_json={"scores": {"fluency": {"evidence": [{"quote": "confidence, structure", "reason": "Fluid pacing"}]}}}
        )
        svc = ReportService()
        pdf_path = svc.generate_pdf_report(report)
        self.assertTrue(bool(pdf_path))
        self.assertTrue(os.path.exists(os.path.join(settings.BASE_DIR, pdf_path)))

    def test_interview_feedback_page_shows_failure_banner(self):
        """Interview feedback page shows clear failure banner and retry button on evaluation failure."""
        session = InterviewSession.objects.create(user=self.user, interview_type="Technical", domain="Engineering", technology="Django", difficulty="Intermediate")
        q = InterviewQuestion.objects.create(session=session, question_text="What is select_related?")
        ans = InterviewAnswer.objects.create(question=q, transcript="select_related joins tables in SQL.", answer_status="ANSWERED")
        feedback = InterviewFeedback.objects.create(
            answer=ans,
            evaluation_status="FAILED",
            error_code="unavailable",
            error_message="Gemini is unavailable"
        )
        resp = self.client.get(reverse("interview_feedback", args=[session.id, q.id]))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")

        self.assertIn("AI Evaluation Unavailable", content)
        self.assertIn("unavailable", content)
        self.assertIn("Retry Evaluation", content)
