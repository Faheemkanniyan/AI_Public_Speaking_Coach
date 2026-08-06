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
from django.db.models import Q
from django.conf import settings

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

    recent_sessions = SpeechSession.objects.filter(user=request.user).order_by("-created_at")[:5]
    analytics_service = AnalyticsService()
    charts_data = analytics_service.get_user_charts_data(request.user)

    context = {
        "profile": profile,
        "stats": stats,
        "recent_sessions": recent_sessions,
        "charts_data_json": json.dumps(charts_data),
    }
    return render(request, "dashboard.html", context)


@login_required
def practice_view(request):
    """
    Speech Practice studio with random topics, mic visualizer, timer, and STT.
    """
    topics = Topic.objects.all().order_by("category", "title")
    default_topic = topics.first()
    context = {
        "topics": topics,
        "default_topic": default_topic,
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
