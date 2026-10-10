from celery import shared_task
from django.contrib.auth.models import User
from .services.speech_service import SpeechService

@shared_task
def analyze_speech_task(session_id):
    """
    Background task to analyze the speech and generate the report.
    """
    speech_service = SpeechService()
    session, report = speech_service.analyze_existing_session(session_id)
    return f"Analysis complete for session {session.id}"
