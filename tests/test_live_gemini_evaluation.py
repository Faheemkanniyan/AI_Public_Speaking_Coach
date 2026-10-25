import os
import pytest
from django.test import TestCase
from app.services.gemini_service import GeminiSpeechAnalyzer, is_verbatim_substring

HAS_GEMINI_KEY = bool(os.getenv("GEMINI_API_KEY", "").strip())


@pytest.mark.live
@pytest.mark.skipif(not HAS_GEMINI_KEY, reason="Live integration tests require GEMINI_API_KEY")
class LiveGeminiSpeechEvaluationTests(TestCase):
    """
    Live evaluation tests against Google Gemini API with 6 diverse benchmark transcripts.
    Exercises genuine structured output, quote verification, and score ordering.
    """

    def setUp(self):
        self.analyzer = GeminiSpeechAnalyzer()

    def test_six_benchmark_transcripts_grounding_and_score_ordering(self):
        # 1. Strong executive speech
        strong_transcript = (
            "Good morning distinguished board members. Today I am honored to present our multi-year strategic roadmap "
            "for sustainable technology innovation. Over the past twelve months, our engineering division has accelerated "
            "product delivery cycles while systematically mitigating operational vulnerabilities. By prioritizing disciplined "
            "capital allocation and stakeholder alignment, we are exceptionally well-positioned to expand market leadership."
        )
        strong_res = self.analyzer.analyze_speech(strong_transcript, topic="Corporate Strategy", duration_seconds=60)

        # 2. Average conversational speech
        avg_transcript = (
            "Hello everyone, I want to share a few thoughts on our daily office workflow. Sometimes our communication "
            "could be clearer when we update team members about tasks. If we send regular updates every morning, "
            "it will help our projects run more smoothly and everyone will understand the schedule better."
        )
        avg_res = self.analyzer.analyze_speech(avg_transcript, topic="Office Workflow", duration_seconds=45)

        # 3. Grammar-heavy speech
        grammar_transcript = (
            "Yesterday me and him was going to the store and we doesn't seen nobody there. We was thinking that the shop "
            "are closed, but then two person comes out and tells us that we is late for the appointment."
        )
        grammar_res = self.analyzer.analyze_speech(grammar_transcript, topic="Daily Errands", duration_seconds=30)

        # 4. Filler-heavy speech
        filler_transcript = (
            "Um, so, basically, like, I want to talk about, you know, our project. Like, actually, um, we started last week, "
            "and, uh, you know, it was, like, pretty challenging, but, um, basically, we kind of finished it, right?"
        )
        filler_res = self.analyzer.analyze_speech(filler_transcript, topic="Project Summary", duration_seconds=30)

        # 5. Off-topic speech (Topic: Quantum Computing, Speech: Pizza Recipe)
        off_topic_transcript = (
            "Today I am excited to share my secret recipe for traditional Neapolitan Margherita pizza. You must use "
            "high-protein double zero flour, San Marzano crushed tomatoes, fresh buffalo mozzarella, and aromatic basil leaves. "
            "Bake it in a wood-fired oven at nine hundred degrees for exactly ninety seconds."
        )
        off_topic_res = self.analyzer.analyze_speech(
            off_topic_transcript,
            topic="Quantum Computing and Quantum Supremacy Algorithms",
            duration_seconds=45
        )

        # 6. Very short speech (< 25 words)
        short_transcript = "Good morning. Thank you all for coming today."
        short_res = self.analyzer.analyze_speech(short_transcript, topic="Welcome Speech", duration_seconds=10)

        # --- ASSERTIONS ---

        # A. Ordering: Strong > Average > Weak
        self.assertGreater(strong_res["overall_score"], avg_res["overall_score"], "Strong speech must score higher than average speech")
        self.assertGreater(avg_res["overall_score"], grammar_res["overall_score"], "Average speech must score higher than grammar-heavy speech")

        # B. Off-topic: Relevance must be low
        self.assertLessEqual(off_topic_res["content_relevance_score"], 45, "Off-topic pizza speech must receive low content relevance score for Quantum Computing")

        # C. Short speech: Returns 0 scores and 'Not enough speech to evaluate'
        self.assertEqual(short_res["overall_score"], 0)
        self.assertEqual(short_res["rating_label"], "Not Enough Speech")

        # D. Grounding: EVERY quoted mistake must be an exact verbatim substring in the candidate's transcript!
        for name, res, txt in [
            ("strong", strong_res, strong_transcript),
            ("average", avg_res, avg_transcript),
            ("grammar", grammar_res, grammar_transcript),
            ("filler", filler_res, filler_transcript),
            ("off_topic", off_topic_res, off_topic_transcript),
        ]:
            for mistake in res.get("mistakes", []):
                original = mistake.get("original", "").strip()
                self.assertTrue(
                    is_verbatim_substring(original, txt),
                    f"Mistake quote '{original}' in {name} speech is not a verbatim substring of candidate speech!"
                )
