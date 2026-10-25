import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from app.models import (
    SpeechSession, SpeechReport, Topic, InterviewSession,
    InterviewQuestion, InterviewAnswer, InterviewFeedback, CoachingPreference
)
from app.forms import CustomUserCreationForm


class ComprehensiveGetPagesAndAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="valid_user", email="valid@example.com", password="StrongPassword123!")
        self.client = Client()

    def test_anonymous_redirects_for_protected_get_pages(self):
        protected_urls = [
            reverse("dashboard"),
            reverse("practice"),
            reverse("history"),
            reverse("analytics"),
            reverse("profile"),
            reverse("settings_page"),
            reverse("onboarding"),
            reverse("progress_daily"),
            reverse("progress_weekly"),
            reverse("progress_monthly"),
            reverse("weaknesses"),
            reverse("goals"),
            reverse("interview_setup"),
            reverse("interview_history"),
            reverse("interview_performance"),
        ]
        for url in protected_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f"Expected redirect for anonymous GET to {url}")
            self.assertIn("login", resp.url)

    def test_authenticated_200_for_protected_get_pages(self):
        self.client.force_login(self.user)
        # Ensure coaching pref onboarding completed so dashboard doesn't redirect to onboarding
        CoachingPreference.objects.filter(user=self.user).update(onboarding_completed=True)

        protected_urls = [
            reverse("dashboard"),
            reverse("practice"),
            reverse("history"),
            reverse("analytics"),
            reverse("profile"),
            reverse("settings_page"),
            reverse("onboarding"),
            reverse("progress_daily"),
            reverse("progress_weekly"),
            reverse("progress_monthly"),
            reverse("weaknesses"),
            reverse("goals"),
            reverse("interview_setup"),
            reverse("interview_history"),
            reverse("interview_performance"),
        ]
        for url in protected_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"Expected 200 for authenticated GET to {url}")

    def test_landing_anonymous_200_authenticated_redirect(self):
        anon_resp = self.client.get(reverse("landing"))
        self.assertEqual(anon_resp.status_code, 200)

        self.client.force_login(self.user)
        auth_resp = self.client.get(reverse("landing"))
        self.assertEqual(auth_resp.status_code, 302)
        self.assertIn("dashboard", auth_resp.url)

    def test_signup_rejects_weak_or_short_password(self):
        form = CustomUserCreationForm(data={
            "username": "shortuser",
            "email": "short@example.com",
            "password1": "123",
            "password2": "123"
        })
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)


class ComprehensiveInterviewFlowTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="candidate_a", password="Password123!")
        self.user_b = User.objects.create_user(username="candidate_b", password="Password123!")
        self.client_a = Client()
        self.client_a.force_login(self.user_a)
        self.client_b = Client()
        self.client_b.force_login(self.user_b)

    def test_interview_setup_with_invalid_numbers_renders_error(self):
        resp = self.client_a.post(reverse("interview_setup"), {
            "interview_type": "Technical",
            "domain": "Web",
            "technology": "Python",
            "difficulty": "Easy",
            "num_questions": 999  # max is 15
        })
        self.assertEqual(resp.status_code, 400)
        self.assertContains(resp, "between 1 and 15", status_code=400)

    def test_interview_full_flow_including_not_answered_and_failed_retry(self):
        # 1. Create interview session and question
        session = InterviewSession.objects.create(
            user=self.user_a,
            interview_type="Technical",
            domain="Backend",
            technology="Django",
            difficulty="Medium",
            total_questions=1,
            completed_questions=0
        )
        question = InterviewQuestion.objects.create(
            session=session,
            question_number=1,
            question_text="Explain Django middleware.",
            ideal_answer="Middleware is a framework of hooks into Django request/response processing."
        )

        # 2. Submit question with EMPTY transcript -> NOT_ANSWERED
        q_url = reverse("interview_question", args=[session.id, question.id])
        post_resp = self.client_a.post(q_url, {
            "transcript": "",
            "duration": "10"
        })
        self.assertEqual(post_resp.status_code, 302)
        answer = InterviewAnswer.objects.get(question=question)
        self.assertEqual(answer.answer_status, "NOT_ANSWERED")

        # 3. View feedback page for NOT_ANSWERED answer (auto-handled without 500)
        fb_url = reverse("interview_feedback", args=[session.id, question.id])
        fb_resp = self.client_a.get(fb_url)
        self.assertEqual(fb_resp.status_code, 200)
        self.assertContains(fb_resp, "Not Answered")

        # 4. Failed evaluation retry flow
        feedback = InterviewFeedback.objects.get(answer=answer)
        feedback.evaluation_status = "FAILED"
        feedback.save()

        # Retry feedback via POST only
        retry_url = reverse("interview_retry_feedback", args=[session.id, question.id])
        get_retry = self.client_a.get(retry_url)
        self.assertEqual(get_retry.status_code, 405)  # require_POST

        post_retry = self.client_a.post(retry_url)
        self.assertEqual(post_retry.status_code, 302)

        # 5. Access control: User B cannot see User A's interview
        b_fb_resp = self.client_b.get(fb_url)
        self.assertEqual(b_fb_resp.status_code, 404)


class ComprehensiveReportAndHistoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="report_user", password="Password123!")
        self.client = Client()
        self.client.force_login(self.user)

        self.topic1 = Topic.objects.create(title="Leadership Skills", category="leadership")
        self.topic2 = Topic.objects.create(title="Cloud Computing", category="technology")

        self.s1 = SpeechSession.objects.create(user=self.user, topic=self.topic1, topic_title="Leadership Skills", transcript="leadership and teamwork")
        self.r1 = SpeechReport.objects.create(session=self.s1, overall_score=85)

        self.s2 = SpeechSession.objects.create(user=self.user, topic=self.topic2, topic_title="Cloud Computing", transcript="cloud servers and microservices")
        self.r2 = SpeechReport.objects.create(session=self.s2, overall_score=78)

    def test_history_search_by_query(self):
        resp = self.client.get(reverse("history") + "?q=leadership")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Leadership Skills")
        self.assertNotContains(resp, "Cloud Computing")

    def test_history_filter_by_category(self):
        resp = self.client.get(reverse("history") + "?category=technology")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Cloud Computing")
        self.assertNotContains(resp, "Leadership Skills")

    def test_download_report_pdf(self):
        # User downloads their own PDF
        resp = self.client.get(reverse("download_report_pdf", args=[self.s1.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertIn("filename=", resp["Content-Disposition"])
