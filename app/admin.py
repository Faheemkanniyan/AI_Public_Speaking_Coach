"""
Django admin configuration for SpeakPro AI models.
"""
from django.contrib import admin
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


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "practice_streak", "average_score", "highest_score", "total_practice_time")
    search_fields = ("user__username", "user__email", "bio")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "difficulty", "is_custom", "created_at")
    list_filter = ("category", "difficulty", "is_custom")
    search_fields = ("title",)


@admin.register(SpeechSession)
class SpeechSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "topic_title", "duration_seconds", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "topic_title", "transcript")


@admin.register(SpeechReport)
class SpeechReportAdmin(admin.ModelAdmin):
    list_display = ("session", "overall_score", "grammar_score", "confidence_score", "fluency_score", "created_at")
    list_filter = ("overall_score",)
    search_fields = ("session__user__username", "motivational_feedback")


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("user", "session", "category_name", "score_value", "created_at")
    list_filter = ("category_name",)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "badge_icon", "date_earned")
    search_fields = ("title", "user__username")


@admin.register(Statistic)
class StatisticAdmin(admin.ModelAdmin):
    list_display = ("user", "total_sessions", "total_duration", "weekly_improvement", "monthly_improvement")


@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "action_type", "timestamp")
    list_filter = ("action_type",)


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("user", "dark_mode", "notifications_enabled", "language")
