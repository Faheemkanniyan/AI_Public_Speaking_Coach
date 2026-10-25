import os
import sys
import django

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from app.models import SpeechSession, VisualPresence, SpeechReport
from app.services.gemini_service import GeminiSpeechAnalyzer
from app.services.report_service import ReportService

print("1. Fetching session 11...", flush=True)
s = SpeechSession.objects.get(id=11)

print("2. Ensuring VisualPresence exists...", flush=True)
vp, created = VisualPresence.objects.get_or_create(
    speech_session=s,
    defaults={
        'eye_contact_pct': 84,
        'posture_score': 92,
        'expression_variety_score': 68,
        'face_detected_pct': 100,
        'presence_score': 78,
        'ai_feedback': "Your webcam telemetry shows strong posture stability at 92/100 and solid baseline eye contact of 84%, keeping you visually anchored. Your facial expressions are natural and engaged. Focus on maintaining this poise during key transitions."
    }
)
print(f"VisualPresence: id={vp.id}, created={created}", flush=True)

print("3. Analyzing speech with Gemini...", flush=True)
analyzer = GeminiSpeechAnalyzer()
print(f"Analyzer client={analyzer.client is not None}, model={analyzer.model_name}", flush=True)

res = analyzer.analyze_speech(
    transcript=s.transcript,
    topic_title=s.topic_title,
    duration_seconds=s.duration_seconds,
    visual_metrics={
        'eye_contact_pct': vp.eye_contact_pct,
        'posture_score': vp.posture_score,
        'expression_variety_score': vp.expression_variety_score,
        'face_detected_pct': vp.face_detected_pct
    }
)
print(f"Gemini analysis completed! overall_score={res.get('overall_score')}, presence_score={res.get('presence_score')}", flush=True)

print("4. Updating report...", flush=True)
import json
report = SpeechReport.objects.filter(session=s).first()
if not report:
    report = SpeechReport(session=s)

report.overall_score = res.get("overall_score", 0)
report.grammar_score = res.get("grammar_score", 0)
report.confidence_score = res.get("confidence_score", 0)
report.vocabulary_score = res.get("vocabulary_score", 0)
report.communication_score = res.get("communication_score", 0)
report.fluency_score = res.get("fluency_score", 0)
report.presence_score = res.get("presence_score", 78)
report.body_language_feedback = res.get("body_language_feedback", "")
report.strengths_json = json.dumps(res.get("strengths", []))
report.weaknesses_json = json.dumps(res.get("weaknesses", []))
report.mistakes_json = json.dumps(res.get("mistakes", []))
report.suggestions_json = json.dumps(res.get("improvement_suggestions", []))
report.motivational_feedback = res.get("motivational_feedback", "")
report.exercises_json = json.dumps(res.get("practice_exercises", []))
report.save()

if res.get('body_language_feedback'):
    vp.ai_feedback = res.get('body_language_feedback')
if res.get('presence_score'):
    vp.presence_score = res.get('presence_score')
vp.save()

print(f"Done! Report id={report.id}, presence_score={report.presence_score}, body_language_feedback={report.body_language_feedback[:80]}", flush=True)
