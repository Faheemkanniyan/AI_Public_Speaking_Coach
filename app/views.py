"""
Views for SpeakPro AI web application.
Handles rendering of Landing, Auth, Dashboard, Practice, Results,
History, Analytics, Profile, AI Coach, Settings, and PDF exports.
"""

import os
import json
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import HttpResponse, Http404, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.conf import settings
from django.utils import timezone
import datetime

from .models import (
    UserProfile,
    Topic,
    SpeechSession,
    SpeechReport,
    Score,
    Achievement,
    Statistic,
    History,
    Setting,
    CoachingPreference,
    PracticePlan,
    ErrorHistory,
)
from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    UserProfileForm,
    SettingForm,
)
from .services.analytics_service import AnalyticsService


def landing_view(request):
    """
    Renders the premium Landing Page.
    If already logged in, show Dashboard link prominently.
    """
    features = [
        {
            "icon": "bi-cpu-fill",
            "title": "AI Speech Analysis",
            "desc": "Real-time evaluation of 10 speaking dimensions powered by advanced AI models.",
        },
        {
            "icon": "bi-spellcheck",
            "title": "Grammar & Vocabulary",
            "desc": "Instant detection of grammar slips, filler words, and suggestions for stronger vocabulary.",
        },
        {
            "icon": "bi-activity",
            "title": "Confidence & Fluency Score",
            "desc": "Quantitative tracking of vocal confidence, speech rhythm, and pacing.",
        },
        {
            "icon": "bi-file-earmark-pdf-fill",
            "title": "Professional Speech Reports",
            "desc": "Download beautifully branded PDF reports with highlighted speech corrections and drills.",
        },
        {
            "icon": "bi-graph-up-arrow",
            "title": "Long-Term Analytics",
            "desc": "Radar, line, bar, and pie charts to track weekly and monthly speech improvements.",
        },
        {
            "icon": "bi-chat-dots-fill",
            "title": "Interactive AI Coach",
            "desc": "Ask conversational questions anytime about interview prep, filler words, and vocal clarity.",
        },
    ]
    return render(request, "landing.html", {"features": features})


def signup_view(request):
    """
    User registration view.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to SpeakPro AI, {user.username}! Your speaking journey begins now.")
            return redirect("dashboard")
    else:
        form = CustomUserCreationForm()

    return render(request, "auth/signup.html", {"form": form})


def login_view(request):
    """
    User login view.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = CustomAuthenticationForm()

    return render(request, "auth/login.html", {"form": form})


def logout_view(request):
    """
    Log out user.
    """
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("landing")


def forgot_password_view(request):
    """
    Forgot password recovery page.
    """
    if request.method == "POST":
        email = request.POST.get("email", "")
        messages.success(request, f"If an account exists for {email}, a password reset link has been sent!")
        return redirect("login")
    return render(request, "auth/forgot_password.html")


@login_required
def dashboard_view(request):
    """
    User Dashboard displaying streak, average score, highest score, weekly/monthly progress,
    recent practice sessions, and Chart.js graphs.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    stats, _ = Statistic.objects.get_or_create(user=request.user)
    coaching_pref, _ = CoachingPreference.objects.get_or_create(user=request.user)
    
    recent_sessions = SpeechSession.objects.filter(user=request.user).order_by("-created_at")[:5]
    
    # Onboarding check: if user has completed at least 1 session but hasn't done onboarding
    if recent_sessions.count() >= 1 and not coaching_pref.onboarding_completed:
        return redirect('onboarding')

    analytics_service = AnalyticsService()
    charts_data = analytics_service.get_user_charts_data(request.user)

    # Get today's practice plan
    today_name = datetime.datetime.now().strftime("%A")
    todays_plan = PracticePlan.objects.filter(user=request.user, day=today_name, completed=False).first()

    # --- Milestone calculations ---
    daily_duration_seconds = 0
    unique_days_count = 0
    try:
        today = timezone.now().date()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        
        daily_sessions = SpeechSession.objects.filter(user=request.user, created_at__date=today)
        daily_duration_seconds = daily_sessions.aggregate(Sum('duration_seconds'))['duration_seconds__sum'] or 0
        
        weekly_sessions = SpeechSession.objects.filter(user=request.user, created_at__date__gte=start_of_week)
        unique_days = set(session.created_at.date() for session in weekly_sessions)
        unique_days_count = len(unique_days)
    except Exception as e:
        print(f"Error checking milestones: {e}")

    daily_goal_sec = coaching_pref.daily_practice_minutes * 60
    daily_progress_percent = min(100, int((daily_duration_seconds / daily_goal_sec) * 100)) if daily_goal_sec > 0 else 0
    daily_goal_met = daily_duration_seconds >= daily_goal_sec and daily_goal_sec > 0
    daily_remaining_mins = max(0, int((daily_goal_sec - daily_duration_seconds) / 60))

    weekly_goal_days = coaching_pref.practice_days_per_week
    weekly_progress_percent = min(100, int((unique_days_count / weekly_goal_days) * 100)) if weekly_goal_days > 0 else 0
    weekly_goal_met = unique_days_count >= weekly_goal_days and weekly_goal_days > 0
    weekly_remaining_days = max(0, weekly_goal_days - unique_days_count)

    # Calculate Tomorrow's Focus based on today's sessions
    tomorrow_focus = None
    try:
        today_sessions = SpeechSession.objects.filter(user=request.user, created_at__date=today).order_by("-created_at")
        if today_sessions.exists():
            latest_session = today_sessions.first()
            if hasattr(latest_session, 'report') and latest_session.report:
                suggestions = latest_session.report.get_suggestions()
                if suggestions:
                    tomorrow_focus = suggestions[0]
                else:
                    mistakes = latest_session.report.get_mistakes()
                    if mistakes:
                        tomorrow_focus = f"Focus on accuracy: {mistakes[0].get('reason', 'Refine sentence structures.')}"
    except Exception as e:
        print(f"Error getting tomorrow focus: {e}")

    context = {
        "profile": profile,
        "stats": stats,
        "coaching_pref": coaching_pref,
        "todays_plan": todays_plan,
        "recent_sessions": recent_sessions,
        "charts_data_json": json.dumps(charts_data),
        
        "daily_goal_met": daily_goal_met,
        "daily_remaining_mins": daily_remaining_mins,
        "daily_progress_percent": daily_progress_percent,
        "daily_duration_mins": int(daily_duration_seconds / 60),
        
        "weekly_goal_met": weekly_goal_met,
        "weekly_remaining_days": weekly_remaining_days,
        "weekly_progress_percent": weekly_progress_percent,
        "unique_days_count": unique_days_count,
        
        "tomorrow_focus": tomorrow_focus,
    }
    return render(request, "dashboard.html", context)


@login_required
def practice_view(request):
    """
    Speech Practice studio with random topics, mic visualizer, timer, and STT.
    """
    topics = Topic.objects.all().order_by("category", "title")
    default_topic = topics.first()
    
    languages = [
        {"code": "en-US", "name": "English"},
        {"code": "ml-IN", "name": "Malayalam"},
        {"code": "hi-IN", "name": "Hindi"},
        {"code": "ta-IN", "name": "Tamil"},
        {"code": "kn-IN", "name": "Kannada"},
    ]
    coaching_pref, _ = CoachingPreference.objects.get_or_create(user=request.user)

    context = {
        "topics": topics,
        "default_topic": default_topic,
        "languages": languages,
        "coaching_pref": coaching_pref,
    }
    return render(request, "practice.html", context)


@login_required
def result_view(request, session_id):
    """
    Speech evaluation Result page.
    Shows circular score, skill bars, highlighted corrections, AI report, and download CTA.
    """
    session = get_object_or_404(SpeechSession, id=session_id, user=request.user)
    report = getattr(session, "report", None)
    if not report:
        messages.warning(request, "Analysis report is being generated or not available.")
        return redirect("history")

    context = {
        "session": session,
        "report": report,
        "strengths": report.get_strengths(),
        "weaknesses": report.get_weaknesses(),
        "mistakes": report.get_mistakes(),
        "suggestions": report.get_suggestions(),
        "exercises": report.get_exercises(),
    }
    return render(request, "result.html", context)


@login_required
def history_view(request):
    """
    Speech practice session history with search, category filtering, and pagination.
    """
    query = request.GET.get("q", "")
    category_filter = request.GET.get("category", "")

    sessions_list = SpeechSession.objects.filter(user=request.user).order_by("-created_at")

    if query:
        sessions_list = sessions_list.filter(
            Q(topic_title__icontains=query) | Q(transcript__icontains=query)
        )
    if category_filter:
        sessions_list = sessions_list.filter(topic__category=category_filter)

    paginator = Paginator(sessions_list, 10)  # 10 sessions per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    categories = Topic.CATEGORY_CHOICES

    context = {
        "sessions": page_obj,
        "page_obj": page_obj,
        "query": query,
        "category_filter": category_filter,
        "categories": categories,
    }
    return render(request, "history.html", context)


@login_required
def delete_session_view(request, session_id):
    """
    Deletes a speech practice session and its report.
    """
    session = get_object_or_404(SpeechSession, id=session_id, user=request.user)
    session.delete()
    messages.success(request, "Practice session deleted successfully.")
    return redirect("history")


@login_required
def download_report_pdf(request, session_id):
    """
    Downloads the generated PDF report from D:\\AI_Public_Speaking_Coach\\reports\\
    """
    session = get_object_or_404(SpeechSession, id=session_id, user=request.user)
    report = getattr(session, "report", None)
    if not report:
        raise Http404("Report not found.")

    pdf_rel_path = report.pdf_report
    if not pdf_rel_path:
        # Re-generate if missing
        from .services.report_service import ReportService
        srv = ReportService()
        pdf_rel_path = srv.generate_pdf_report(report)
        report.pdf_report = pdf_rel_path
        report.save()

    pdf_full_path = Path(settings.BASE_DIR) / pdf_rel_path
    if not pdf_full_path.exists():
        raise Http404("PDF file not found on disk.")

    with open(pdf_full_path, "rb") as f:
        response = HttpResponse(f.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="SpeakPro_Report_Session_{session.id}.pdf"'
        return response


@login_required
def analytics_view(request):
    """
    Comprehensive Analytics Page with interactive Radar, Line, Bar, and Pie charts.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    stats, _ = Statistic.objects.get_or_create(user=request.user)
    analytics_service = AnalyticsService()
    charts_data = analytics_service.get_user_charts_data(request.user)

    context = {
        "profile": profile,
        "stats": stats,
        "charts_data_json": json.dumps(charts_data),
    }
    return render(request, "analytics.html", context)


@login_required
def profile_view(request):
    """
    User profile view displaying bio, avatar, practice statistics, and achievements.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    stats, _ = Statistic.objects.get_or_create(user=request.user)
    achievements = Achievement.objects.filter(user=request.user).order_by("-date_earned")

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            request.user.first_name = form.cleaned_data.get("first_name", "")
            request.user.last_name = form.cleaned_data.get("last_name", "")
            request.user.email = form.cleaned_data.get("email", request.user.email)
            request.user.save()
            form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect("profile")
    else:
        form = UserProfileForm(instance=profile, user=request.user)

    context = {
        "profile": profile,
        "stats": stats,
        "achievements": achievements,
        "form": form,
    }
    return render(request, "profile.html", context)


@login_required
def ai_coach_view(request):
    """
    Interactive AI Coach chat assistant page.
    """
    return render(request, "ai_coach.html")


@login_required
def settings_view(request):
    """
    Settings page for theme toggle, audio inputs, and notifications.
    """
    user_setting, _ = Setting.objects.get_or_create(user=request.user)

    if request.method == "POST":
        if "delete_account" in request.POST:
            user = request.user
            logout(request)
            user.delete()
            messages.info(request, "Your account has been deleted.")
            return redirect("landing")

        form = SettingForm(request.POST, instance=user_setting)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated successfully!")
            return redirect("settings_page")
    else:
        form = SettingForm(instance=user_setting)

    context = {
        "form": form,
        "user_setting": user_setting,
    }
    return render(request, "settings_page.html", context)


@login_required
def onboarding_view(request):
    """
    Onboarding questionnaire to capture practice preferences and goals.
    """
    coaching_pref, _ = CoachingPreference.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        coaching_pref.daily_practice_minutes = int(request.POST.get("daily_time", 15))
        coaching_pref.practice_days_per_week = int(request.POST.get("practice_days", 3))
        coaching_pref.main_goal = request.POST.get("main_goal", "Improve general speaking")
        coaching_pref.current_level = request.POST.get("current_level", "Intermediate")
        coaching_pref.preferred_language = request.POST.get("language", "English")
        coaching_pref.onboarding_completed = True
        coaching_pref.save()
        
        # Generate personalized practice plan
        from .services.ai_coach_service import AICoachService
        coach = AICoachService()
        coach.generate_practice_plan(request.user)
        
        messages.success(request, "Your personalized practice plan is ready!")
        return redirect("dashboard")
        
    return render(request, "onboarding.html", {"pref": coaching_pref})


@login_required
def progress_daily_view(request):
    """
    Daily progress view showing recent sessions and score trends.
    """
    sessions = SpeechSession.objects.filter(user=request.user).order_by("-created_at")[:10]
    return render(request, "progress_daily.html", {"sessions": sessions})


@login_required
def progress_weekly_view(request):
    """
    Weekly progress view comparing past weeks.
    """
    stats, _ = Statistic.objects.get_or_create(user=request.user)
    return render(request, "progress_weekly.html", {"stats": stats})


@login_required
def progress_monthly_view(request):
    """
    Monthly progress overview.
    """
    stats, _ = Statistic.objects.get_or_create(user=request.user)
    return render(request, "progress_monthly.html", {"stats": stats})


@login_required
def weaknesses_view(request):
    """
    Displays the user's recurring errors and weaknesses.
    """
    errors = ErrorHistory.objects.filter(user=request.user).order_by("-frequency")
    return render(request, "weaknesses.html", {"errors": errors})


@login_required
def goals_view(request):
    """
    Displays the user's current coaching preferences and goals.
    """
    coaching_pref, _ = CoachingPreference.objects.get_or_create(user=request.user)
    return render(request, "goals.html", {"pref": coaching_pref})
