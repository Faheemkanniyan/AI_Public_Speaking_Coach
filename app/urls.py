"""
URL routing for SpeakPro AI web application.
"""

from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views, api_views, interview_views

urlpatterns = [
    # Core pages
    path('', views.landing_view, name='landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('practice/', views.practice_view, name='practice'),
    path('result/<int:session_id>/', views.result_view, name='result'),
    path('speech/<int:session_id>/retry-evaluation/', views.retry_speech_evaluation_view, name='retry_speech_evaluation'),
    path('history/', views.history_view, name='history'),
    path('history/delete/<int:session_id>/', views.delete_session_view, name='delete_session'),
    path('report/download/<int:session_id>/', views.download_report_pdf, name='download_report_pdf'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings_page'),
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('progress/daily/', views.progress_daily_view, name='progress_daily'),
    path('progress/weekly/', views.progress_weekly_view, name='progress_weekly'),
    path('progress/monthly/', views.progress_monthly_view, name='progress_monthly'),
    path('weaknesses/', views.weaknesses_view, name='weaknesses'),
    path('goals/', views.goals_view, name='goals'),

    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', auth_views.PasswordResetView.as_view(
        template_name='auth/forgot_password.html',
        email_template_name='auth/password_reset_email.html',
        subject_template_name='auth/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
    ), name='forgot_password'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='auth/forgot_password.html',
        email_template_name='auth/password_reset_email.html',
        subject_template_name='auth/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
    ), name='password_reset'),
    path('forgot-password/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='auth/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='auth/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='auth/password_reset_complete.html',
    ), name='password_reset_complete'),

    # Interview Preparation
    path('interview/', interview_views.interview_setup_view, name='interview_setup'),
    path('interview/<int:session_id>/question/<int:question_id>/', interview_views.interview_question_view, name='interview_question'),
    path('interview/<int:session_id>/question/<int:question_id>/feedback/', interview_views.interview_feedback_view, name='interview_feedback'),
    path('interview/<int:session_id>/question/<int:question_id>/retry-feedback/', interview_views.interview_retry_feedback_view, name='interview_retry_feedback'),
    path('interview/<int:session_id>/report/', interview_views.interview_report_view, name='interview_report'),
    path('interview/history/', interview_views.interview_history_view, name='interview_history'),
    path('interview/performance/', interview_views.interview_performance_view, name='interview_performance'),

    # REST API endpoints
    path('api/topics/random/', api_views.api_random_topic, name='api_random_topic'),
    path('api/speech/refine-transcript/', api_views.api_refine_transcript, name='api_refine_transcript'),
    path('api/speech/analyze/', api_views.api_speech_analyze, name='api_speech_analyze'),
    path('api/speech/status/<int:session_id>/', api_views.api_speech_status, name='api_speech_status'),
    path('api/speech/generate-tts/<int:session_id>/', api_views.api_generate_tts, name='api_generate_tts'),
    path('api/analytics/data/', api_views.api_analytics_data, name='api_analytics_data'),

    # Private Authenticated Media
    path('media-private/tts/<int:session_id>/', views.private_tts_media_view, name='private_tts_media'),
    path('media-private/speech/<int:session_id>/', views.private_speech_audio_view, name='private_speech_audio'),
    path('media-private/interview/<int:answer_id>/', views.private_interview_audio_view, name='private_interview_audio'),
    path('media-private/pdf/<int:session_id>/', views.private_pdf_report_view, name='private_pdf_report'),
]
