"""
Django management command to seed SpeakPro AI with default users,
speaking topics, sample speech sessions, AI reports, achievement badges, and analytics data.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.models import (
    UserProfile, Topic, SpeechSession, SpeechReport,
    Achievement, Statistic, Setting
)
from app.services.report_service import ReportService
import datetime
import json
from django.utils import timezone



class Command(BaseCommand):
    help = "Seeds SpeakPro AI with default topics, sample user, demo speeches, reports, and badges."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting SpeakPro AI database seeding..."))

        # 1. Create Default Users (Admin & Demo Speaker)
        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@speakpro.ai",
                "is_staff": True,
                "is_superuser": True
            }
        )
        admin_user.set_password("admin12345")
        admin_user.save()

        speaker_user, _ = User.objects.get_or_create(
            username="speaker",
            defaults={
                "email": "speaker@speakpro.ai",
                "first_name": "Alex",
                "last_name": "Orator"
            }
        )
        speaker_user.set_password("speakpro2026")
        speaker_user.save()

        # Ensure profiles exist
        profile, _ = UserProfile.objects.get_or_create(user=speaker_user)
        profile.professional_role = "Senior Product Lead & Public Speaker"
        profile.bio = "Passionate about executive storytelling, keynotes, and vocal clarity."
        profile.practice_streak = 5
        profile.total_practice_time = 42
        profile.average_score = 83.4
        profile.highest_score = 92.0
        profile.save()

        self.stdout.write(self.style.SUCCESS("[OK] Users 'admin' and 'speaker' ready."))

        # 2. Seed Speaking Topics (15 Diverse Prompts)
        topics_data = [
            ("Describe your greatest personal or professional achievement.", "general", "Intermediate"),
            ("What is the most important lesson you learned from a failure?", "general", "Intermediate"),
            ("How do you maintain work-life balance in a fast-paced environment?", "general", "Beginner"),
            ("What are the 3 key traits of an exceptional executive leader?", "leadership", "Advanced"),
            ("How should leaders communicate during times of organizational crisis?", "leadership", "Advanced"),
            ("Describe a time you motivated a cross-functional team to meet a deadline.", "leadership", "Intermediate"),
            ("How is Artificial Intelligence transforming the future of education?", "technology", "Intermediate"),
            ("What are the ethical responsibilities of software engineers building autonomous AI?", "technology", "Advanced"),
            ("Explain cloud computing and microservices to a non-technical stakeholder.", "technology", "Intermediate"),
            ("What can local communities do to promote sustainable clean energy adoption?", "social", "Beginner"),
            ("How does social media impact modern civil discourse and mental health?", "social", "Intermediate"),
            ("Why should businesses prioritize environmental sustainability in their supply chains?", "social", "Advanced"),
            ("Tell me about yourself and why you are the best candidate for this role.", "interview", "Beginner"),
            ("Describe a difficult conflict you had with a co-worker and how you resolved it.", "interview", "Intermediate"),
            ("Where do you see your career path evolving over the next five years?", "interview", "Beginner"),
        ]

        for title, category, diff in topics_data:
            Topic.objects.get_or_create(
                title=title,
                defaults={"category": category, "difficulty": diff}
            )

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {len(topics_data)} speaking topics."))

        # 3. Seed Achievement Badges for 'speaker' user
        badges_data = [
            ("First Speech", "Completed your very first AI speech evaluation.", "bi-mic-fill"),
            ("3-Day Streak", "Practiced speaking for 3 consecutive days.", "bi-fire"),
            ("7-Day Streak", "Practiced speaking for a full week without missing a day.", "bi-lightning-charge-fill"),
            ("Grammar Master", "Achieved a grammar score of 90+ on an evaluated speech.", "bi-check2-all"),
            ("Fluent Orator", "Delivered a speech with zero detected filler words.", "bi-soundwave"),
            ("Executive Speaker", "Earned an Overall Speaking Score of 85 or higher.", "bi-award-fill"),
        ]

        for title, desc, icon in badges_data:
            Achievement.objects.get_or_create(
                user=speaker_user,
                title=title,
                defaults={"description": desc, "badge_icon": icon}
            )
            Achievement.objects.get_or_create(
                user=admin_user,
                title=title,
                defaults={"description": desc, "badge_icon": icon}
            )

        self.stdout.write(self.style.SUCCESS("[OK] Seeded achievement badges."))
        
        # 4. Create Sample Speech Sessions & Reports for 'speaker' user
        if SpeechReport.objects.filter(session__user=speaker_user).count() == 0:
            SpeechSession.objects.filter(user=speaker_user).delete()
            sample_speeches = [
                {
                    "topic_title": "What are the 3 key traits of an exceptional executive leader?",
                    "transcript": "Great leadership is founded on three essential pillars: empathy, vision, and accountability. First, empathetic leaders actively listen to their team members and understand their challenges. Second, having a clear strategic vision aligns the entire organization toward shared goals. Third, accountability means owning both successes and setbacks. In my experience, when leaders communicate these priorities clearly, employee engagement soars.",
                    "duration": 65,
                    "overall": 88,
                    "grammar": 92,
                    "vocab": 86,
                    "conf": 90,
                    "fluency": 85,
                    "comm": 87,
                    "summary": "Outstanding executive communication! Your speech had clear three-part structure, professional vocabulary, and excellent vocal confidence. Minimal filler words detected.",
                    "strengths": ["Clear three-part structure with signpost transitions.", "Strong executive vocabulary (accountability, strategic vision).", "Assertive delivery and confident tone."],
                    "improvements": ["Try pausing for 2 seconds after presenting each pillar to emphasize importance."],
                    "corrections": []
                },
                {
                    "topic_title": "How is Artificial Intelligence transforming the future of education?",
                    "transcript": "Artificial intelligence is fundamentally reshaping how we learn and teach. Basically, AI tutors can adapt to every individual student's learning pace, offering personalized feedback in real-time. Um, I think this technology will democratize quality education globally. However, we must ensure ethical privacy protections for students.",
                    "duration": 52,
                    "overall": 79,
                    "grammar": 82,
                    "vocab": 80,
                    "conf": 76,
                    "fluency": 78,
                    "comm": 79,
                    "summary": "Solid argument on educational transformation. Good lexical choices, but watch out for filler words like 'Um' and casual qualifiers like 'Basically'.",
                    "strengths": ["Well-articulated thesis on personalized learning.", "Good balance of optimism and ethical caution."],
                    "improvements": ["Eliminate filler words ('Um') and casual fillers ('Basically').", "Project more vocal energy in the conclusion."],
                    "corrections": [
                        {"original": "Basically, AI tutors can adapt", "corrected": "AI tutors can adapt", "explanation": "Remove 'Basically' for a cleaner executive statement."}
                    ]
                },
                {
                    "topic_title": "Tell me about yourself and why you are the best candidate for this role.",
                    "transcript": "Over the past seven years, I have led product development and communication teams in high-growth technology sectors. My passion lies in bridging the gap between engineering complexity and user-centric design. Recently, I led a cross-functional initiative that increased retention by 28 percent. I am eager to bring this same dedication to your leadership team.",
                    "duration": 58,
                    "overall": 92,
                    "grammar": 95,
                    "vocab": 91,
                    "conf": 94,
                    "fluency": 90,
                    "comm": 90,
                    "summary": "Exceptional interview pitch! Concise, data-driven, and highly confident. Your narrative trajectory showed measurable impact without hesitation.",
                    "strengths": ["Quantifiable impact cited (28 percent retention increase).", "Clear professional narrative and vocal authority.", "Zero grammatical or filler word issues."],
                    "improvements": ["None—this was an exemplary response."],
                    "corrections": []
                }
            ]

            report_service = ReportService()
            for idx, item in enumerate(sample_speeches):
                session = SpeechSession.objects.create(
                    user=speaker_user,
                    topic_title=item["topic_title"],
                    transcript=item["transcript"],
                    duration_seconds=item["duration"]
                )
                session.created_at = timezone.now() - datetime.timedelta(days=(2 - idx))
                session.save()

                report = SpeechReport.objects.create(
                    session=session,
                    overall_score=item["overall"],
                    grammar_score=item["grammar"],
                    vocabulary_score=item["vocab"],
                    confidence_score=item["conf"],
                    fluency_score=item["fluency"],
                    communication_score=item["comm"],
                    motivational_feedback=item["summary"],
                    strengths_json=json.dumps(item["strengths"]),
                    weaknesses_json=json.dumps(item["improvements"]),
                    mistakes_json=json.dumps(item["corrections"])
                )

                # Generate sample PDF report
                try:
                    pdf_rel_path = report_service.generate_pdf_report(report)
                    report.pdf_report_path = pdf_rel_path
                    report.save()
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Note: PDF generation skipped for demo sample {idx}: {e}"))

            self.stdout.write(self.style.SUCCESS("[OK] Seeded demo speech practice sessions and AI reports."))

        # 5. Populate User Statistics
        stats, _ = Statistic.objects.get_or_create(user=speaker_user)
        stats.total_speeches = 3
        stats.total_practice_minutes = 3
        stats.average_grammar_score = 89.6
        stats.average_vocabulary_score = 85.6
        stats.average_confidence_score = 86.6
        stats.average_fluency_score = 84.3
        stats.average_communication_score = 85.3
        stats.weekly_improvement = 6.4
        stats.monthly_improvement = 12.8
        stats.save()

        # 6. Ensure Settings Model
        Setting.objects.get_or_create(user=speaker_user)
        Setting.objects.get_or_create(user=admin_user)

        self.stdout.write(self.style.SUCCESS("==============================================="))
        self.stdout.write(self.style.SUCCESS("  SPEAKPRO AI SEED DATA COMPLETE!             "))
        self.stdout.write(self.style.SUCCESS("  Demo Account -> username: speaker / speakpro2026 "))
        self.stdout.write(self.style.SUCCESS("  Admin Account-> username: admin   / admin12345   "))
        self.stdout.write(self.style.SUCCESS("==============================================="))
