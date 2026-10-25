import json
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.contrib.auth.models import User
from app.models import InterviewSession, InterviewQuestion, InterviewAnswer, InterviewFeedback
from app.services.interview_service import InterviewService
from app.services.gemini_service import GeminiEvaluationError


class GroundedInterviewEvaluationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cand1", password="password123")
        self.service = InterviewService()
        self.service.api_key = "test_key"
        self.service.client = MagicMock()

    def test_question_generation_generates_structured_questions_without_gemini(self):
        """Generates realistic structured questions without calling Gemini API."""
        session = self.service.create_session(
            user=self.user,
            interview_type="Technical",
            domain="Software Engineering",
            technology="Python",
            difficulty="Intermediate",
            num_questions=3,
            language="English"
        )
        self.assertEqual(session.status, "IN_PROGRESS")
        self.assertEqual(session.questions.count(), 3)
        q1 = session.questions.first()
        self.assertTrue(len(q1.question_text) > 10)
        expected_pts = json.loads(q1.expected_points_json)
        self.assertGreaterEqual(len(expected_pts), 2)
        self.assertTrue(len(q1.ideal_answer) > 10)

    def test_unanswered_or_empty_answer_scores_zero_without_llm_call(self):
        """Empty transcript gets 0 score and Not Answered classification without calling Gemini."""
        session = InterviewSession.objects.create(
            user=self.user,
            interview_type="Technical",
            domain="Software Engineering",
            technology="Django",
            difficulty="Intermediate",
            status="IN_PROGRESS"
        )
        q = InterviewQuestion.objects.create(
            session=session,
            question_text="Explain Django ORM select_related vs prefetch_related.",
            expected_points_json=json.dumps(["SQL JOIN", "separate queries", "ForeignKey/OneToOne", "ManyToMany"])
        )
        ans = InterviewAnswer.objects.create(
            question=q,
            transcript="",
            answer_status="NOT_ANSWERED"
        )

        with patch.object(self.service.client.models, "generate_content") as mock_gen:
            eval_data = self.service.evaluate_answer(ans, "English")
            mock_gen.assert_not_called()

        self.assertEqual(eval_data["overall_score"], 0)
        self.assertEqual(eval_data["classification"], "Not Answered")
        self.assertEqual(eval_data["relevance"], 0)
        self.assertEqual(eval_data["technical_correctness"], 0)
        self.assertIn("SQL JOIN", eval_data["missing_points"])

    def test_idk_answer_receives_low_score_and_honest_feedback(self):
        """An 'I don't know' response receives low score and never hallucinates praise."""
        session = InterviewSession.objects.create(
            user=self.user,
            interview_type="Technical",
            domain="Software Engineering",
            technology="Django",
            difficulty="Intermediate",
            status="IN_PROGRESS"
        )
        q = InterviewQuestion.objects.create(
            session=session,
            question_text="What is the difference between select_related and prefetch_related?",
            expected_points_json=json.dumps(["select_related does SQL join", "prefetch_related executes separate queries"])
        )
        ans = InterviewAnswer.objects.create(
            question=q,
            transcript="I do not know the answer to this question, sorry.",
            answer_status="ANSWERED"
        )

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = json.dumps({
            "relevance_score": 10,
            "relevance_evidence": {"quotes": ["I do not know"], "reason": "Candidate admitted not knowing"},
            "technical_correctness_score": 0,
            "technical_correctness_evidence": {"quotes": [], "reason": "No technical explanation given"},
            "completeness_score": 0,
            "completeness_evidence": {"quotes": [], "reason": "Omitted all key concepts"},
            "structure_score": 10,
            "structure_evidence": {"quotes": ["sorry"], "reason": "Polite but unstructured"},
            "communication_score": 25,
            "communication_evidence": {"quotes": ["sorry"], "reason": "Honest admission"},
            "classification": "Incorrect",
            "feedback": "Candidate honestly acknowledged not knowing. A complete answer would explain SQL joins vs in-memory caching.",
            "model_answer": "select_related performs an SQL JOIN, while prefetch_related queries separately.",
            "missing_points": ["SQL JOIN", "Separate queries"],
            "incorrect_statements": [],
            "correct_points": [],
            "suggestions": ["Review Django query optimization and ForeignKey prefetching."]
        })

        with patch("app.services.interview_service.call_gemini_with_retry", return_value=mock_gemini_response):
            eval_data = self.service.evaluate_answer(ans, "English")

        self.assertLessEqual(eval_data["overall_score"], 20)
        self.assertEqual(eval_data["classification"], "Incorrect")
        self.assertEqual(eval_data["technical_correctness"], 0)
        self.assertIn("SQL JOIN", eval_data["missing_points"])

    def test_in_code_technical_score_weighting(self):
        """Technical score formula: 35% tech, 25% comp, 20% rel, 10% comm, 10% struct."""
        transcript = "Django select_related uses SQL JOIN while prefetch_related does in-memory filtering."
        data = {
            "relevance_score": 90,
            "technical_correctness_score": 80,
            "completeness_score": 70,
            "structure_score": 60,
            "communication_score": 50,
            "incorrect_statements": []
        }
        # Expected: 80*0.35 + 70*0.25 + 90*0.20 + 50*0.10 + 60*0.10
        # = 28 + 17.5 + 18 + 5 + 6 = 74.5 -> 75
        result = self.service._finalize_interview_evaluation(data, transcript, "Technical")
        self.assertEqual(result["overall_score"], 75)

    def test_in_code_hr_score_weighting(self):
        """HR / Behavioral score formula: 25% each."""
        transcript = "I handled conflict by listening actively to the stakeholder."
        data = {
            "relevance_score": 80,
            "technical_correctness_score": 0,  # ignored in HR
            "completeness_score": 80,
            "structure_score": 60,
            "communication_score": 60,
            "incorrect_statements": []
        }
        # Expected: 80*0.25 + 80*0.25 + 60*0.25 + 60*0.25 = 20 + 20 + 15 + 15 = 70
        result = self.service._finalize_interview_evaluation(data, transcript, "HR")
        self.assertEqual(result["overall_score"], 70)

    def test_hallucinated_incorrect_statements_are_dropped(self):
        """Incorrect statement quotes not present in the candidate's transcript are dropped."""
        transcript = "Python uses a GIL to synchronize threads."
        data = {
            "relevance_score": 80,
            "technical_correctness_score": 85,
            "completeness_score": 80,
            "structure_score": 75,
            "communication_score": 80,
            "incorrect_statements": [
                {"quote": "Python uses a GIL", "why_wrong": "Accurate, but flagged by error"},
                {"quote": "Java uses a GIL too", "why_wrong": "Hallucinated: candidate never said this"}
            ]
        }
        result = self.service._finalize_interview_evaluation(data, transcript, "Technical")
        self.assertEqual(len(result["incorrect_statements"]), 1)
        self.assertEqual(result["incorrect_statements"][0]["quote"], "Python uses a GIL")
