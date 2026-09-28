import os
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class TTSService:
    """
    Service to generate Text-To-Speech (TTS) audio feedback using OpenAI API.
    """
    
    OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.media_dir = os.path.join(settings.MEDIA_ROOT, "tts")
        os.makedirs(self.media_dir, exist_ok=True)

    def is_enabled(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def generate_feedback_audio(self, text: str, session_id: int) -> str:
        """
        Generates TTS for the given text and saves it as an mp3.
        Returns the relative media URL of the saved file, or empty string on failure.
        """
        if not self.is_enabled():
            logger.warning("OPENAI_API_KEY is not set. TTS is disabled.")
            return ""

        filename = f"feedback_session_{session_id}.mp3"
        filepath = os.path.join(self.media_dir, filename)
        
        # If already exists, return the cached version
        if os.path.exists(filepath):
            return f"{settings.MEDIA_URL}tts/{filename}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": "alloy",
            "response_format": "mp3"
        }

        try:
            response = requests.post(self.OPENAI_TTS_URL, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        f.write(chunk)
                return f"{settings.MEDIA_URL}tts/{filename}"
            else:
                logger.error(f"OpenAI TTS API Error: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            logger.exception("Exception occurred during TTS generation.")
            return ""
