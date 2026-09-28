"""
Analytics Service for SpeakPro AI.
Computes chart data payloads (Radar, Line, Bar, Pie) for Chart.js dashboard & analytics pages.
"""

from django.db.models import Avg, Count
from app.models import SpeechSession, SpeechReport, Score, Topic, Statistic


class AnalyticsService:
    """
    Computes performance statistics and Chart.js datasets for users.
    """

    def get_user_charts_data(self, user) -> dict:
        """
        Returns JSON-serializable dictionary with data for:
        - radar_chart: 5 skill dimensions (Grammar, Vocabulary, Confidence, Fluency, Communication)
        - line_chart: Overall score over time (recent sessions)
        - bar_chart: Score breakdown across categories
        - pie_chart: Speech topics distribution
        """
        reports = SpeechReport.objects.filter(session__user=user).order_by("created_at")

        # 1. Radar Chart (Average skill breakdown)
        avg_grammar = round(reports.aggregate(avg=Avg("grammar_score"))["avg"] or 75, 1)
        avg_vocab = round(reports.aggregate(avg=Avg("vocabulary_score"))["avg"] or 76, 1)
        avg_conf = round(reports.aggregate(avg=Avg("confidence_score"))["avg"] or 74, 1)
        avg_fluency = round(reports.aggregate(avg=Avg("fluency_score"))["avg"] or 72, 1)
        avg_comm = round(reports.aggregate(avg=Avg("communication_score"))["avg"] or 75, 1)

        radar_chart = {
            "labels": ["Grammar", "Vocabulary", "Confidence", "Fluency", "Communication"],
            "datasets": [
                {
                    "label": "Your Skill Proficiency",
                    "data": [avg_grammar, avg_vocab, avg_conf, avg_fluency, avg_comm],
                    "backgroundColor": "rgba(0, 255, 136, 0.2)",
                    "borderColor": "#00ff88",
                    "pointBackgroundColor": "#00d2ff",
                    "pointBorderColor": "#fff",
                    "borderWidth": 2,
                }
            ],
        }

        # 2. Line Chart (Score progression over last 10 sessions)
        recent_reports = reports.order_by("-created_at")[:10]
        recent_reports = list(reversed(recent_reports))
        line_labels = [f"Session {r.session.id}" for r in recent_reports]
        line_scores = [r.overall_score for r in recent_reports]
        if not line_labels:
            line_labels = ["Demo 1", "Demo 2", "Demo 3"]
            line_scores = [72, 78, 85]

        line_chart = {
            "labels": line_labels,
            "datasets": [
                {
                    "label": "Overall Speaking Score",
                    "data": line_scores,
                    "borderColor": "#00d2ff",
                    "backgroundColor": "rgba(0, 210, 255, 0.15)",
                    "tension": 0.4,
                    "fill": True,
                    "pointRadius": 5,
                    "pointHoverRadius": 7,
                }
            ],
        }

        # Add Visual Presence line datasets if data exists
        eye_contact_data = []
        posture_data = []
        has_visuals = False
        
        for r in recent_reports:
            vp = getattr(r.session, 'visual_presence', None)
            if vp:
                has_visuals = True
                eye_contact_data.append(vp.eye_contact_pct)
                posture_data.append(vp.posture_score)
            else:
                eye_contact_data.append(None)
                posture_data.append(None)
                
        if has_visuals:
            line_chart["datasets"].append({
                "label": "Eye Contact %",
                "data": eye_contact_data,
                "borderColor": "#4a90e2",
                "backgroundColor": "transparent",
                "borderDash": [5, 5],
                "tension": 0.4,
                "pointRadius": 4,
                "spanGaps": True,
            })
            line_chart["datasets"].append({
                "label": "Posture Score",
                "data": posture_data,
                "borderColor": "#9b59b6",
                "backgroundColor": "transparent",
                "borderDash": [5, 5],
                "tension": 0.4,
                "pointRadius": 4,
                "spanGaps": True,
            })

        # 3. Bar Chart (Category Comparison)
        bar_chart = {
            "labels": ["Grammar", "Vocabulary", "Confidence", "Fluency", "Communication", "Overall"],
            "datasets": [
                {
                    "label": "Average Category Scores",
                    "data": [
                        avg_grammar,
                        avg_vocab,
                        avg_conf,
                        avg_fluency,
                        avg_comm,
                        round(reports.aggregate(avg=Avg("overall_score"))["avg"] or 76, 1),
                    ],
                    "backgroundColor": [
                        "rgba(0, 255, 136, 0.8)",
                        "rgba(0, 210, 255, 0.8)",
                        "rgba(255, 193, 7, 0.8)",
                        "rgba(233, 30, 99, 0.8)",
                        "rgba(156, 39, 176, 0.8)",
                        "rgba(33, 150, 243, 0.8)",
                    ],
                    "borderRadius": 6,
                }
            ],
        }

        # 4. Pie Chart (Topic Category Breakdown)
        sessions = SpeechSession.objects.filter(user=user)
        topic_counts = sessions.values("topic__category").annotate(count=Count("id"))
        pie_labels = []
        pie_data = []
        cat_map = dict(Topic.CATEGORY_CHOICES)
        for row in topic_counts:
            cat_key = row["topic__category"] or "general"
            pie_labels.append(cat_map.get(cat_key, "General Practice"))
            pie_data.append(row["count"])

        if not pie_labels:
            pie_labels = ["General & Personal", "Leadership & Career", "AI & Technology"]
            pie_data = [4, 3, 3]

        pie_chart = {
            "labels": pie_labels,
            "datasets": [
                {
                    "data": pie_data,
                    "backgroundColor": [
                        "#00ff88",
                        "#00d2ff",
                        "#ff007f",
                        "#ffc107",
                        "#9c27b0",
                    ],
                    "hoverOffset": 6,
                }
            ],
        }

        return {
            "radar_chart": radar_chart,
            "line_chart": line_chart,
            "bar_chart": bar_chart,
            "pie_chart": pie_chart,
        }
