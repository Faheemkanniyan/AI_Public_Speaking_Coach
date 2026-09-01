"""
Database models for SpeakPro AI.
Implements the 9 required database tables: Users (UserProfile), Topics, Speech Sessions,
Speech Reports, Scores, Achievements, Statistics, History, and Settings.
"""

import json
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    Extended user profile storing speaking stats, streak, bio, and profile photo.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True, default="Passionate about mastering public speaking and communication skills.")
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)
    practice_streak = models.IntegerField(default=1, help_text="Current daily speaking practice streak.")
    total_practice_time = models.IntegerField(default=0, help_text="Total practice duration in seconds.")
    average_score = models.FloatField(default=0.0, help_text="Overall average AI speaking score.")
    highest_score = models.FloatField(default=0.0, help_text="Highest overall AI speaking score.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class Topic(models.Model):
    """
    Random and preloaded speaking topics for practice sessions.
    """
    CATEGORY_CHOICES = [
        ("general", "General & Personal"),
        ("leadership", "Leadership & Career"),
        ("technology", "AI & Technology"),
        ("social", "Social & Climate"),
        ("interview", "Job Interview Preparation"),
    ]
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="general")
    difficulty = models.CharField(max_length=20, default="Intermediate")
    is_custom = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class SpeechSession(models.Model):
    """
    Records a user's speech practice session, audio file, and transcript.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="speech_sessions")
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions")
    topic_title = models.CharField(max_length=255, blank=True)
    audio_file = models.FileField(upload_to="speech_audio/", blank=True, null=True)
    transcript = models.TextField(help_text="Transcribed speech text.")
    duration_seconds = models.IntegerField(default=60)
    language = models.CharField(max_length=20, default="en-US")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session #{self.id} by {self.user.username} on {self.topic_title or 'Untitled'}"

    def save(self, *args, **kwargs):
        if self.topic and not self.topic_title:
            self.topic_title = self.topic.title
        super().save(*args, **kwargs)

    @property
    def language_display_name(self):
        mapping = {
            "en-US": "English",
            "hi-IN": "Hindi",
            "ml-IN": "Malayalam",
            "ta-IN": "Tamil",
            "kn-IN": "Kannada"
        }
        return mapping.get(self.language, self.language)

class SpeechReport(models.Model):
    """
    Detailed AI feedback report for a speech session.
    """
    session = models.OneToOneField(SpeechSession, on_delete=models.CASCADE, related_name="report")
    overall_score = models.IntegerField(default=0)
    grammar_score = models.IntegerField(default=0)
    confidence_score = models.IntegerField(default=0)
    vocabulary_score = models.IntegerField(default=0)
    communication_score = models.IntegerField(default=0)
    fluency_score = models.IntegerField(default=0)

    # JSON fields for structured lists
    strengths_json = models.TextField(default="[]", help_text="JSON list of strengths")
    weaknesses_json = models.TextField(default="[]", help_text="JSON list of weaknesses")
    mistakes_json = models.TextField(default="[]", help_text="JSON list of grammar/vocabulary mistakes with corrections")
    suggestions_json = models.TextField(default="[]", help_text="JSON list of actionable improvement suggestions")
    motivational_feedback = models.TextField(blank=True, default="Great effort! Keep practicing to elevate your speaking.")
    exercises_json = models.TextField(default="[]", help_text="JSON list of recommended practice exercises")

    pdf_report = models.CharField(max_length=500, blank=True, help_text="Relative or absolute path to generated PDF in reports/ dir")
    created_at = models.DateTimeField(auto_now_add=True)

    def get_strengths(self):
        try:
            return json.loads(self.strengths_json)
        except Exception:
            return []

    def get_weaknesses(self):
        try:
            return json.loads(self.weaknesses_json)
        except Exception:
            return []

    def get_mistakes(self):
        try:
            return json.loads(self.mistakes_json)
        except Exception:
            return []

    def get_suggestions(self):
        try:
            return json.loads(self.suggestions_json)
        except Exception:
            return []

    def get_exercises(self):
        try:
            return json.loads(self.exercises_json)
        except Exception:
            return []

    @property
    def summary_feedback(self):
        return self.motivational_feedback

    @property
    def strengths_list(self):
        return self.get_strengths()

    @property
    def improvements_list(self):
        return self.get_weaknesses()

    @property
    def corrections_list(self):
        return self.get_mistakes()

    @property
    def filler_analysis(self):
        from app.services.assemblyai_service import AssemblyAIService
        return AssemblyAIService.analyze_filler_words(self.session.transcript, mistakes=self.get_mistakes())

    @property
    def time_consumed_seconds(self):
        words = (self.session.transcript or "").split()
        if len(words) == 0:
            return 0.0
        elif len(words) <= 2:
            return 1.0
        else:
            return round(min(float(self.session.duration_seconds), max(2.0, len(words) / 2.2)), 1)

    @property
    def time_utilization_percent(self):
        dur = max(1, self.session.duration_seconds)
        return min(100, int((self.time_consumed_seconds / dur) * 100))

    @property
    def speaking_pace_wpm(self):
        words = (self.session.transcript or "").split()
        if len(words) == 0:
            return 0
        return int((len(words) / max(2.0, self.time_consumed_seconds)) * 60)

    def __str__(self):
        return f"Report for Session #{self.session.id} (Score: {self.overall_score})"


class Score(models.Model):
    """
    Historical record of individual category scores over time.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scores")
    session = models.ForeignKey(SpeechSession, on_delete=models.CASCADE, related_name="scores", null=True, blank=True)
    category_name = models.CharField(max_length=50, help_text="Grammar, Vocabulary, Confidence, Fluency, Communication, Overall")
    score_value = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.category_name}: {self.score_value}"


class Achievement(models.Model):
    """
    Gamified badges, certificates, and milestones earned by a user.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="achievements")
    title = models.CharField(max_length=100)
    description = models.TextField()
    badge_icon = models.CharField(max_length=50, default="fa-award", help_text="FontAwesome icon class")
    date_earned = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} earned by {self.user.username}"


class Statistic(models.Model):
    """
    Aggregated performance statistics for quick dashboard & chart rendering.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="statistics")
    total_sessions = models.IntegerField(default=0)
    total_duration = models.IntegerField(default=0)
    weekly_improvement = models.FloatField(default=0.0, help_text="Percentage improvement over last week")
    monthly_improvement = models.FloatField(default=0.0, help_text="Percentage improvement over last month")
    avg_grammar = models.FloatField(default=0.0)
    avg_vocabulary = models.FloatField(default=0.0)
    avg_confidence = models.FloatField(default=0.0)
    avg_fluency = models.FloatField(default=0.0)
    avg_communication = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Statistics for {self.user.username}"


class History(models.Model):
    """
    Activity audit log of user practice sessions and actions.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="history_logs")
    action_type = models.CharField(max_length=100, default="Speech Practice")
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.user.username}: {self.action_type}"

    class Meta:
        verbose_name_plural = "Histories"
        ordering = ["-timestamp"]


class Setting(models.Model):
    """
    User account and coaching preferences.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="settings")
    dark_mode = models.BooleanField(default=True)
    notifications_enabled = models.BooleanField(default=True)
    microphone_device = models.CharField(max_length=255, default="Default Microphone")
    language = models.CharField(max_length=50, default="English (US)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Settings for {self.user.username}"


class CoachingPreference(models.Model):
    """
    Stores onboarding preferences like daily practice time, days per week, goal, and language.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="coaching_preference")
    preferred_language = models.CharField(max_length=50, default="English")
    daily_practice_minutes = models.IntegerField(default=15)
    practice_days_per_week = models.IntegerField(default=3)
    main_goal = models.CharField(max_length=100, default="Improve general speaking")
    current_level = models.CharField(max_length=50, default="Intermediate")
    onboarding_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Coaching Preferences for {self.user.username}"


class PracticePlan(models.Model):
    """
    Personalized practice schedule generated for the user.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="practice_plans")
    week_number = models.IntegerField(default=1)
    day = models.CharField(max_length=20) # e.g., Monday, Tuesday
    activity = models.CharField(max_length=255)
    duration = models.IntegerField(help_text="Duration in minutes", default=10)
    focus_area = models.CharField(max_length=100)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Plan for {self.user.username} - {self.day} (Week {self.week_number})"


class ErrorHistory(models.Model):
    """
    Tracks recurring errors to adapt future practice plans.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="error_history")
    error_type = models.CharField(max_length=100) # e.g., Grammar, Fluency, Vocabulary
    error_text = models.TextField(help_text="The mistake the user made")
    correction = models.TextField(help_text="The corrected version")
    frequency = models.IntegerField(default=1)
    first_detected = models.DateTimeField(auto_now_add=True)
    last_detected = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.error_type} ({self.frequency}x)"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create Profile, Statistics, Setting, and CoachingPreference for new Users.
    """
    if created:
        UserProfile.objects.create(user=instance)
        Statistic.objects.create(user=instance)
        Setting.objects.create(user=instance)
        CoachingPreference.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
        instance.statistics.save()
        instance.settings.save()
        instance.coaching_preference.save()
    except Exception:
        pass
