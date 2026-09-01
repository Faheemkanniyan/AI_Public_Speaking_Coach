"""
URL routing for SpeakPro AI web application.
"""

from django.urls import path
from . import views, api_views

urlpatterns = [
    # Core pages
    path('', views.landing_view, name='landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('practice/', views.practice_view, name='practice'),
    path('result/<int:session_id>/', views.result_view, name='result'),
    path('history/', views.history_view, name='history'),
    path('history/delete/<int:session_id>/', views.delete_session_view, name='delete_session'),
    path('report/download/<int:session_id>/', views.download_report_pdf, name='download_report_pdf'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('profile/', views.profile_view, name='profile'),
    path('ai-coach/', views.ai_coach_view, name='ai_coach'),
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
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),

    # REST API endpoints
    path('api/topics/random/', api_views.api_random_topic, name='api_random_topic'),
    path('api/speech/analyze/', api_views.api_speech_analyze, name='api_speech_analyze'),
    path('api/coach/chat/', api_views.api_coach_chat, name='api_coach_chat'),
    path('api/analytics/data/', api_views.api_analytics_data, name='api_analytics_data'),
]
