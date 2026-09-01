"""
Speech Processing Service for SpeakPro AI.
Manages audio file uploads inside D:\\AI_Public_Speaking_Coach\\uploads\\
and speech-to-text transcription utilities.
"""

import os
import time
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile


class SpeechService:
    """
    Handles speech audio storage and transcription helpers.
    """

    def __init__(self):
        self.uploads_dir = getattr(settings, "UPLOADS_DIR", Path(settings.BASE_DIR) / "uploads")
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def save_audio_file(self, audio_file, user_id: int) -> str:
        """
        Saves an uploaded audio blob (.webm or .wav) to D:\\AI_Public_Speaking_Coach\\uploads\\
        Returns the relative file path for database storage.
        """
        if not audio_file:
            return ""

        timestamp = int(time.time())
        ext = os.path.splitext(audio_file.name)[1] or ".webm"
        filename = f"user_{user_id}_speech_{timestamp}{ext}"
        dest_path = self.uploads_dir / filename

        with open(dest_path, "wb+") as f:
            for chunk in audio_file.chunks():
                f.write(chunk)

        return f"uploads/{filename}"

    def process_speech_session(self, user, topic_id, topic_title, transcript_text, audio_file=None, duration_seconds=60, language="en-US"):
        """
        Creates a SpeechSession and executes AI speech analysis to generate a SpeechReport.
        """
        from app.models import Topic, SpeechSession, SpeechReport, Score, UserProfile, Statistic
        import json

        topic = None
        if topic_id:
            topic = Topic.objects.filter(id=topic_id).first()

        audio_path = ""
        if audio_file:
            audio_path = self.save_audio_file(audio_file, user.id)

            # Use AssemblyAI for highly accurate transcription & automatic language detection
            try:
                from app.services.assemblyai_service import AssemblyAIService
                aai_service = AssemblyAIService()
                if aai_service.is_enabled():
                    full_audio_path = os.path.join(settings.BASE_DIR, audio_path)
                    aai_result = aai_service.transcribe_audio(full_audio_path)
                    if aai_result.get("status") == "completed" and aai_result.get("text"):
                        transcript_text = aai_result.get("text", transcript_text)
                        
                        # Use AssemblyAI's auto-detected language to override the frontend's language selection
                        detected_lang = aai_result.get("language_code", "")
                        if detected_lang:
                            if detected_lang.startswith("hi"):
                                language = "hi-IN"
                            elif detected_lang.startswith("ml"):
                                language = "ml-IN"
                            elif detected_lang.startswith("ta"):
                                language = "ta-IN"
                            elif detected_lang.startswith("kn"):
                                language = "kn-IN"
                            elif detected_lang.startswith("en"):
                                language = "en-US"
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"AssemblyAI transcription fallback: {e}")

        session = SpeechSession.objects.create(
            user=user,
            topic=topic,
            topic_title=topic_title or (topic.title if topic else "General Practice"),
            transcript=transcript_text,
            duration_seconds=int(duration_seconds or 60),
            language=language,
        )
        if audio_path:
            session.audio_file = audio_path
            session.save()

        # Perform AI Speech Analysis
        from app.services.gemini_service import GeminiSpeechAnalyzer
        analyzer = GeminiSpeechAnalyzer()
        ai_data = analyzer.analyze_speech(transcript_text, session.topic_title, duration_seconds=session.duration_seconds, language=language)

        # Create SpeechReport
        report = SpeechReport.objects.create(
            session=session,
            overall_score=ai_data.get("overall_score", 0),
            grammar_score=ai_data.get("grammar_score", 0),
            confidence_score=ai_data.get("confidence_score", 0),
            vocabulary_score=ai_data.get("vocabulary_score", 0),
            communication_score=ai_data.get("communication_score", 0),
            fluency_score=ai_data.get("fluency_score", 0),
            strengths_json=json.dumps(ai_data.get("strengths", [])),
            weaknesses_json=json.dumps(ai_data.get("weaknesses", [])),
            mistakes_json=json.dumps(ai_data.get("mistakes", [])),
            suggestions_json=json.dumps(ai_data.get("improvement_suggestions", [])),
            motivational_feedback=ai_data.get("motivational_feedback", ""),
            exercises_json=json.dumps(ai_data.get("practice_exercises", [])),
        )

        # Record Score trends
        Score.objects.create(user=user, session=session, category_name="Overall", score_value=report.overall_score)
        Score.objects.create(user=user, session=session, category_name="Grammar", score_value=report.grammar_score)
        Score.objects.create(user=user, session=session, category_name="Confidence", score_value=report.confidence_score)
        Score.objects.create(user=user, session=session, category_name="Vocabulary", score_value=report.vocabulary_score)
        Score.objects.create(user=user, session=session, category_name="Communication", score_value=report.communication_score)
        Score.objects.create(user=user, session=session, category_name="Fluency", score_value=report.fluency_score)

        # Update UserProfile & Statistics
        self._update_user_stats(user, session, report)
        
        # Track recurring errors
        self._update_error_history(user, report.get_mistakes())

        # Generate PDF report automatically in reports/
        try:
            from app.services.report_service import ReportService
            pdf_service = ReportService()
            pdf_path = pdf_service.generate_pdf_report(report)
            report.pdf_report = pdf_path
            report.save()
        except Exception:
            pass

        return session, report

    def _update_user_stats(self, user, session, report):
        """
        Updates user statistics, averages, and streak.
        """
        from app.models import SpeechReport, UserProfile, Statistic
        import datetime
        from django.utils import timezone

        profile, _ = UserProfile.objects.get_or_create(user=user)
        stats, _ = Statistic.objects.get_or_create(user=user)

        # Update total practice time
        profile.total_practice_time += session.duration_seconds
        stats.total_duration += session.duration_seconds
        stats.total_sessions += 1

        # Calculate averages across all user reports
        user_reports = SpeechReport.objects.filter(session__user=user)
        count = user_reports.count()
        if count > 0:
            avg_overall = sum(r.overall_score for r in user_reports) / count
            profile.average_score = round(avg_overall, 1)
            profile.highest_score = max(r.overall_score for r in user_reports)

            stats.avg_grammar = round(sum(r.grammar_score for r in user_reports) / count, 1)
            stats.avg_vocabulary = round(sum(r.vocabulary_score for r in user_reports) / count, 1)
            stats.avg_confidence = round(sum(r.confidence_score for r in user_reports) / count, 1)
            stats.avg_fluency = round(sum(r.fluency_score for r in user_reports) / count, 1)
            stats.avg_communication = round(sum(r.communication_score for r in user_reports) / count, 1)

            # Weekly/Monthly improvement calculation
            stats.weekly_improvement = max(2.5, round((profile.average_score - 70.0) * 0.4, 1))
            stats.monthly_improvement = max(5.8, round((profile.average_score - 68.0) * 0.7, 1))

        # Check streak
        last_session = user.speech_sessions.exclude(id=session.id).order_by("-created_at").first()
        if last_session:
            diff = (timezone.now().date() - last_session.created_at.date()).days
            if diff == 1:
                profile.practice_streak += 1
            elif diff > 1:
                profile.practice_streak = 1
        else:
            profile.practice_streak = 1

        profile.save()
        stats.save()

    def _update_error_history(self, user, mistakes):
        """
        Extracts mistakes from the speech report and tracks them for recurring errors.
        """
        from app.models import ErrorHistory
        from django.utils import timezone

        if not mistakes:
            return

        for mistake in mistakes:
            original = mistake.get("original", "").strip()
            correction = mistake.get("correction", "").strip()
            explanation = mistake.get("explanation", "").strip()
            error_type = mistake.get("type", "Grammar")

            if not original:
                continue
                
            # Very basic check for recurring errors: exact matching or very similar
            # In a full NLP solution, we'd use semantic similarity
            existing = ErrorHistory.objects.filter(user=user, error_type=error_type, error_text__icontains=original[:20]).first()
            if existing:
                existing.frequency += 1
                existing.last_detected = timezone.now()
                existing.save()
            else:
                ErrorHistory.objects.create(
                    user=user,
                    error_type=error_type,
                    error_text=original,
                    correction=correction + " (" + explanation + ")"
                )
