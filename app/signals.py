import os
import logging
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings
from pathlib import Path
from .models import SpeechSession, SpeechReport, InterviewAnswer

logger = logging.getLogger(__name__)


def _safe_remove(file_obj_or_path):
    if not file_obj_or_path:
        return
    try:
        path = None
        if hasattr(file_obj_or_path, "path"):
            try:
                path = file_obj_or_path.path
            except Exception:
                path = None

        if not path:
            raw_str = str(file_obj_or_path).strip()
            if raw_str:
                p = Path(raw_str)
                if p.is_absolute() and p.exists():
                    path = str(p)
                else:
                    cand1 = Path(settings.MEDIA_ROOT) / raw_str.lstrip("/").replace("media/", "")
                    cand2 = Path(settings.BASE_DIR) / raw_str.lstrip("/")
                    if cand1.exists():
                        path = str(cand1)
                    elif cand2.exists():
                        path = str(cand2)

        if path and os.path.isfile(path):
            os.remove(path)
            logger.info(f"Deleted file {path}")
    except Exception as e:
        logger.warning(f"Could not delete file {file_obj_or_path}: {e}")


@receiver(post_delete, sender=SpeechSession)
def delete_speech_session_files(sender, instance, **kwargs):
    """
    Deletes the session audio file and associated report files when a SpeechSession is deleted.
    """
    if instance.audio_file:
        _safe_remove(instance.audio_file)

    report = getattr(instance, "report", None)
    if report:
        if report.pdf_report:
            _safe_remove(report.pdf_report)
        if report.tts_audio_path:
            _safe_remove(report.tts_audio_path)


@receiver(post_delete, sender=SpeechReport)
def delete_speech_report_files(sender, instance, **kwargs):
    """
    Deletes PDF and TTS audio files when a SpeechReport is deleted.
    """
    if instance.pdf_report:
        _safe_remove(instance.pdf_report)
    if instance.tts_audio_path:
        _safe_remove(instance.tts_audio_path)


@receiver(post_delete, sender=InterviewAnswer)
def delete_interview_answer_files(sender, instance, **kwargs):
    """
    Deletes audio file when an InterviewAnswer is deleted.
    """
    if instance.audio_file:
        _safe_remove(instance.audio_file)
