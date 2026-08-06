"""
REST API endpoints for asynchronous JavaScript interactions in SpeakPro AI.
Handles live random topic selection, speech audio/transcript upload & analysis,
AI Coach chat queries, and Chart.js dataset fetching.
"""

import json
import random
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .models import Topic, SpeechSession, SpeechReport
from .services.speech_service import SpeechService
from .services.ai_coach_service import AICoachService
from .services.analytics_service import AnalyticsService


@require_GET
@login_required
def api_random_topic(request):
    """
    Returns a random speaking topic, optionally filtered by category.
    """
    category = request.GET.get("category", "")
    topics = Topic.objects.all()
    if category and category != "all":
        topics = topics.filter(category=category)

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
        duration_seconds = int(request.POST.get("duration_seconds", 60))
        language = request.POST.get("language", "en-US")
        audio_file = request.FILES.get("audio_file", None)

        if not transcript:
            return JsonResponse({
                "status": "error",
                "message": "Speech transcript cannot be empty. Please speak or record before analyzing."
            }, status=400)

        speech_service = SpeechService()
        session, report = speech_service.process_speech_session(
            user=request.user,
            topic_id=topic_id,
            topic_title=topic_title,
            transcript_text=transcript,
            audio_file=audio_file,
            duration_seconds=duration_seconds,
            language=language,
        )

        return JsonResponse({
            "status": "success",
            "session_id": session.id,
            "overall_score": report.overall_score,
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
