"""
REST API endpoints for asynchronous JavaScript interactions in SpeakPro AI.
Handles live random topic selection, speech audio/transcript upload & analysis,
AI Coach chat queries, and Chart.js dataset fetching.
"""

import json
import random
import os
from django.conf import settings
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .models import Topic, SpeechSession, SpeechReport
from .services.speech_service import SpeechService
from .services.ai_coach_service import AICoachService
from .services.analytics_service import AnalyticsService
from .utils import safe_int


@require_GET
@login_required
def api_random_topic(request):
    """
    Returns a random speaking topic, optionally filtered by category.
    """
    category = request.GET.get("category", "")
    difficulty = request.GET.get("difficulty", "")
    topics = Topic.objects.all()
    
    if category and category != "all":
        topics = topics.filter(category=category)
        
    if difficulty:
        topics = topics.filter(difficulty__iexact=difficulty)

    if not topics.exists():
        topics = Topic.objects.all()

    if topics.exists():
        topic = random.choice(list(topics))
        data = {
            "id": topic.id,
            "title": topic.title,
            "category": topic.get_category_display(),
            "difficulty": topic.difficulty,
        }
    else:
        data = {
            "id": None,
            "title": "Describe your greatest personal or professional achievement.",
            "category": "General & Personal",
            "difficulty": "Intermediate",
        }

    return JsonResponse({"status": "success", "topic": data})


@require_POST
@login_required
def api_refine_transcript(request):
    """
    POST endpoint to refine raw speech-to-text transcript from microphone.
    Corrects phonetic mishearings (e.g. 'song dear engineer' -> 'software engineer')
    while preserving authentic speech and disfluencies.
    """
    try:
        raw_transcript = request.POST.get("transcript", "").strip()
        topic = request.POST.get("topic_title", "General Practice")
        
        if not raw_transcript:
            return JsonResponse({"status": "error", "message": "Transcript is empty."}, status=400)
            
        from .services.gemini_service import GeminiSpeechAnalyzer
        analyzer = GeminiSpeechAnalyzer()
        refined = analyzer.refine_stt_transcript(raw_transcript, topic)
        
        return JsonResponse({
            "status": "success",
            "refined_transcript": refined,
            "original_transcript": raw_transcript
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_POST
@login_required
def api_speech_analyze(request):
    """
    POST endpoint to evaluate a speech session.
    Accepts form data or JSON containing transcript, topic_id, topic_title, duration_seconds,
    and optional audio_file blob.
    """
    try:
        transcript = request.POST.get("transcript", "").strip()
        topic_id = request.POST.get("topic_id", None)
        topic_title = request.POST.get("topic_title", "General Practice")
        raw_duration = request.POST.get("duration_seconds")
        if raw_duration is not None and str(raw_duration).strip():
            duration_seconds = safe_int(raw_duration, default=None, min=1, max=3600, clamp=True)
            if duration_seconds is None:
                return JsonResponse({
                    "status": "error",
                    "message": "Invalid duration_seconds. Must be a valid integer between 1 and 3600."
                }, status=400)
        else:
            duration_seconds = 60
        language = request.POST.get("language", "en-US")
        audio_file = request.FILES.get("audio_file", None)

        if not transcript:
            return JsonResponse({
                "status": "error",
                "message": "Speech transcript cannot be empty. Please speak or record before analyzing."
            }, status=400)

        visual_metrics = request.POST.get("visual_metrics", None)

        speech_service = SpeechService()
        
        # Synchronously create the session and save the audio file
        session = speech_service.create_session(
            user=request.user,
            topic_id=topic_id,
            topic_title=topic_title,
            transcript_text=transcript,
            audio_file=audio_file,
            duration_seconds=duration_seconds,
            language=language,
            visual_metrics_raw=visual_metrics
        )
        
        # Perform speech analysis and generate report
        session, report = speech_service.analyze_existing_session(session.id)

        return JsonResponse({
            "status": "success",
            "session_id": session.id,
            "overall_score": report.overall_score if report else 0,
            "redirect_url": f"/result/{session.id}/"
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Error analyzing speech: {str(e)}"
        }, status=500)


@require_POST
@login_required
def api_coach_chat(request):
    """
    POST endpoint for interactive AI Coach conversational Q&A.
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
        user_message = body.get("message", "").strip()
    except Exception:
        user_message = request.POST.get("message", "").strip()

    if not user_message:
        return JsonResponse({"status": "error", "message": "Message cannot be empty."}, status=400)

    coach_service = AICoachService()
    response_text = coach_service.get_coach_response(user_message, user=request.user)

    return JsonResponse({
        "status": "success",
        "bot_response": response_text
    })


@require_GET
@login_required
def api_analytics_data(request):
    """
    GET endpoint returning full Chart.js dataset JSON for the authenticated user.
    """
    service = AnalyticsService()
    data = service.get_user_charts_data(request.user)
    return JsonResponse({"status": "success", "charts": data})

@require_POST
@login_required
def api_generate_tts(request, session_id):
    """
    POST endpoint to generate TTS feedback for a session.
    """
    try:
        openai_key = getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        if not openai_key:
            return JsonResponse({"status": "error", "message": "TTS is not configured"}, status=503)

        from .services.tts_service import TTSService
        
        session = get_object_or_404(SpeechSession, id=session_id, user=request.user)
        report = session.report
        
        if report.tts_audio_path:
            return JsonResponse({"status": "success", "audio_url": report.tts_audio_path})
            
        # Construct summary feedback text for TTS
        tts_text = f"Here is your feedback. Overall Score: {report.overall_score} out of 100. "
        
        wpm = report.speaking_pace_wpm
        if wpm < 110:
            tts_text += "Your pace was a bit slow, try to speak a little faster next time. "
        elif wpm > 150:
            tts_text += "Your pace was a bit fast, try to slow down and articulate clearly. "
        else:
            tts_text += "Your pace was perfect. "
            
        tts_text += report.summary_feedback
        
        tts_service = TTSService()
        audio_url = tts_service.generate_feedback_audio(tts_text, session_id)
        
        if audio_url:
            report.tts_audio_path = audio_url
            report.save()
            return JsonResponse({"status": "success", "audio_url": audio_url})
        else:
            return JsonResponse({"status": "error", "message": "Failed to generate TTS audio."}, status=500)
            
    except Http404:
        return JsonResponse({"status": "error", "message": "Session not found."}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
