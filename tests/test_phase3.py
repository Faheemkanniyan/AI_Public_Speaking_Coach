import json
import re
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.urls import reverse
from django.utils import timezone

from app.forms import CustomUserCreationForm
from app.models import SpeechSession, SpeechReport, Statistic, ErrorHistory, UserProfile
from app.services.speech_service import SpeechService
from app.services.analytics_service import AnalyticsService
from app.services.gemini_service import GeminiSpeechAnalyzer


class Phase3AuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="JohnDoe",
            email="John.Doe@Example.com",
            password="SecurePassword123!"
        )

    def test_login_with_username_case_sensitive_or_insensitive(self):
        user_auth = authenticate(username="JohnDoe", password="SecurePassword123!")
        self.assertIsNotNone(user_auth)
        self.assertEqual(user_auth.pk, self.user.pk)

        user_auth_lower = authenticate(username="johndoe", password="SecurePassword123!")
        self.assertIsNotNone(user_auth_lower)
        self.assertEqual(user_auth_lower.pk, self.user.pk)

    def test_login_with_email_case_insensitive(self):
        user_auth = authenticate(username="john.doe@example.com", password="SecurePassword123!")
        self.assertIsNotNone(user_auth)
        self.assertEqual(user_auth.pk, self.user.pk)

        user_auth_upper = authenticate(username="JOHN.DOE@EXAMPLE.COM", password="SecurePassword123!")
        self.assertIsNotNone(user_auth_upper)
        self.assertEqual(user_auth_upper.pk, self.user.pk)

    def test_signup_enforces_case_insensitive_unique_email(self):
        form_data = {
            "username": "newuser",
            "email": "JOHN.DOE@EXAMPLE.COM",
            "password": "ValidPassword123!",
            "password_confirm": "ValidPassword123!"
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertTrue(any("already exists" in err.lower() or "already registered" in err.lower() for err in form.errors["email"]))

    def test_password_reset_flow_available(self):
        client = Client()
        resp = client.get(reverse("password_reset"))
        self.assertEqual(resp.status_code, 200)

        post_resp = client.post(reverse("password_reset"), {"email": "john.doe@example.com"})
        self.assertEqual(post_resp.status_code, 302)
        self.assertIn("done", post_resp.url)


class Phase3DataCorrectnessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="speaker",
            email="speaker@example.com",
            password="Password123!"
        )

    def test_error_history_handles_reason_and_explanation_without_empty_parens(self):
        service = SpeechService()
        mistakes = [
            {"original": "We was going", "correction": "We were going", "reason": "Subject-verb agreement error"},
            {"original": "She don't know", "correction": "She doesn't know", "explanation": "Third person singular"},
            {"original": "I seen it", "correction": "I saw it"}  # no reason or explanation
        ]
        service._update_error_history(self.user, mistakes)

        weaknesses = ErrorHistory.objects.filter(user=self.user)
        self.assertEqual(weaknesses.count(), 3)

        w1 = weaknesses.get(error_text__icontains="We was going")
        self.assertIn("(Subject-verb agreement error)", w1.correction)

        w2 = weaknesses.get(error_text__icontains="She don't know")
        self.assertIn("(Third person singular)", w2.correction)

        w3 = weaknesses.get(error_text__icontains="I seen it")
        self.assertNotIn("()", w3.correction)
        self.assertEqual(w3.correction.strip(), "I saw it")

    def test_error_history_normalized_text_matching(self):
        service = SpeechService()
        # First save with extra punctuation/spaces
        service._update_error_history(self.user, [
            {"original": "We was going!", "correction": "We were going", "reason": "Grammar"}
        ])
        self.assertEqual(ErrorHistory.objects.filter(user=self.user).count(), 1)
        w = ErrorHistory.objects.get(user=self.user)
        self.assertEqual(w.frequency, 1)

        # Second save with different casing and trailing punctuation
        service._update_error_history(self.user, [
            {"original": "  we was going...  ", "correction": "We were going", "reason": "Grammar"}
        ])
        self.assertEqual(ErrorHistory.objects.filter(user=self.user).count(), 1)
        w.refresh_from_db()
        self.assertEqual(w.frequency, 2)

    def test_statistic_real_improvement_calculation(self):
        service = SpeechService()
        now = timezone.now()

        # Session 1: 10 days ago (previous period), score 70
        s1 = SpeechSession.objects.create(user=self.user, transcript="speech 1", duration_seconds=60)
        SpeechSession.objects.filter(pk=s1.pk).update(created_at=now - timedelta(days=10))
        rep1 = SpeechReport.objects.create(session=s1, overall_score=70)
        SpeechReport.objects.filter(pk=rep1.pk).update(created_at=now - timedelta(days=10))

        # Session 2: 2 days ago (recent period), score 80
        s2 = SpeechSession.objects.create(user=self.user, transcript="speech 2", duration_seconds=60)
        SpeechSession.objects.filter(pk=s2.pk).update(created_at=now - timedelta(days=2))
        rep2 = SpeechReport.objects.create(session=s2, overall_score=80)
        SpeechReport.objects.filter(pk=rep2.pk).update(created_at=now - timedelta(days=2))

        service._update_user_stats(self.user, s2, rep2)
        stats = Statistic.objects.get(user=self.user)

        # Weekly improvement: 80 - 70 = 10.0
        self.assertIsNotNone(stats.weekly_improvement)
        self.assertAlmostEqual(stats.weekly_improvement, 10.0, places=1)
        self.assertEqual(stats.weekly_improvement_display, "+10.0%")

    def test_statistic_not_enough_data_when_no_previous_period(self):
        service = SpeechService()
        s = SpeechSession.objects.create(user=self.user, transcript="speech test", duration_seconds=60)
        rep = SpeechReport.objects.create(session=s, overall_score=85)
        service._update_user_stats(self.user, s, rep)

        stats = Statistic.objects.get(user=self.user)
        self.assertIsNone(stats.weekly_improvement)
        self.assertEqual(stats.weekly_improvement_display, "Not enough data")
        self.assertIsNone(stats.monthly_improvement)
        self.assertEqual(stats.monthly_improvement_display, "Not enough data")

    def test_analytics_service_empty_state_for_new_user(self):
        analytics = AnalyticsService().get_user_charts_data(self.user)
        self.assertFalse(analytics["has_data"])
        self.assertEqual(analytics["line_chart"]["labels"], [])
        self.assertEqual(analytics["line_chart"]["datasets"][0]["data"], [])
        self.assertEqual(analytics["radar_chart"]["datasets"][0]["data"], [0, 0, 0, 0, 0])
        self.assertEqual(analytics["pie_chart"]["labels"], [])

    def test_streak_logic_handles_same_day_sessions(self):
        service = SpeechService()
        now = timezone.now()

        # Session 1 on day 1
        s1 = SpeechSession.objects.create(user=self.user, transcript="first session", duration_seconds=60)
        SpeechSession.objects.filter(pk=s1.pk).update(created_at=now)
        rep1 = SpeechReport.objects.create(session=s1, overall_score=75)
        SpeechReport.objects.filter(pk=rep1.pk).update(created_at=now)
        service._update_user_stats(self.user, s1, rep1)

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.practice_streak, 1)

        # Session 2 on same day
        s2 = SpeechSession.objects.create(user=self.user, transcript="second session same day", duration_seconds=60)
        SpeechSession.objects.filter(pk=s2.pk).update(created_at=now)
        rep2 = SpeechReport.objects.create(session=s2, overall_score=80)
        SpeechReport.objects.filter(pk=rep2.pk).update(created_at=now)
        service._update_user_stats(self.user, s2, rep2)

        profile.refresh_from_db()
        # Streak should still be 1, NOT incremented to 2 and NOT reset to 1
        self.assertEqual(profile.practice_streak, 1)


class Phase3SpeakingTimeAndNLPTests(TestCase):
    def test_speech_report_uses_real_duration_for_wpm_and_time_consumed(self):
        user = User.objects.create_user(username="test_speaker", password="pwd")
        # 120 words spoken in 60 seconds -> 120 WPM
        words_120 = "word " * 120
        session = SpeechSession.objects.create(
            user=user,
            transcript=words_120.strip(),
            duration_seconds=60
        )
        report = SpeechReport.objects.create(session=session, overall_score=80)

        self.assertEqual(report.time_consumed_seconds, 60.0)
        self.assertEqual(report.speaking_pace_wpm, 120)
        self.assertEqual(report.time_utilization_percent, 100)

    def test_speech_report_estimates_duration_only_when_missing(self):
        user = User.objects.create_user(username="test_speaker2", password="pwd")
        words_22 = "word " * 22
        session = SpeechSession.objects.create(
            user=user,
            transcript=words_22.strip(),
            duration_seconds=0
        )
        report = SpeechReport.objects.create(session=session, overall_score=80)

        # Estimated at 22 / 2.2 = 10.0 seconds
        self.assertEqual(report.time_consumed_seconds, 10.0)
        # WPM: (22 / 10.0) * 60 = 132
        self.assertEqual(report.speaking_pace_wpm, 132)

    def test_fallback_nlp_filler_counting_uses_word_boundaries(self):
        evaluator = GeminiSpeechAnalyzer()
        # Words "also", "number", "person" contain "so" and "um" as substrings but should NOT be counted as fillers
        transcript = "I also visited a large number of places and every person was kind."
        result = evaluator._fallback_nlp_analysis(transcript, topic="Travel")

        # Weaknesses/mistakes should not flag 'so' or 'um'
        detected_fillers_text = " ".join(result.get("weaknesses", []))
        self.assertNotIn("'so'", detected_fillers_text)
        self.assertNotIn("'um'", detected_fillers_text)

        # Now test with actual filler words
        transcript_with_fillers = "Um, so I like think that, uh, basically this is good."
        result_with_fillers = evaluator._fallback_nlp_analysis(transcript_with_fillers, topic="Opinion")
        weaknesses_str = " ".join(result_with_fillers.get("weaknesses", []))
        self.assertTrue("filler words" in weaknesses_str.lower() or any("'" in w for w in result_with_fillers.get("weaknesses", [])))

    def test_no_hardcoded_personal_test_phrases_in_nlp_or_rules(self):
        evaluator = GeminiSpeechAnalyzer()
        # An innocent speech shouldn't trigger random personal phrases
        res = evaluator._fallback_nlp_analysis("We need to share more with each other.", topic="Teamwork")
        mistake_origs = [m["original"] for m in res.get("mistakes", [])]
        self.assertNotIn("more to tall", mistake_origs)
        self.assertNotIn("leadership not a good", mistake_origs)
        self.assertNotIn("do to call", mistake_origs)
