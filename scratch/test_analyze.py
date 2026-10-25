import os
import sys
import django
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from app.services.gemini_service import GeminiSpeechAnalyzer

a = GeminiSpeechAnalyzer()
print("Initialized model:", a.model_name, flush=True)

transcript = "the greatest personal achievement I choose my teachers PG in MCX match good"
topic = "achievement"
metrics = {'eye_contact_pct': 84, 'posture_score': 92, 'expression_variety_score': 68, 'face_detected_pct': 100}

print("Calling _analyze_with_gemini...", flush=True)
try:
    res = a._analyze_with_gemini(transcript, topic, 60, "en-US", metrics)
    print("Done! Overall:", res.get("overall_score"), "Presence:", res.get("presence_score"), flush=True)
    print("Body language:", res.get("body_language_feedback"), flush=True)
except Exception as e:
    import traceback
    traceback.print_exc()
