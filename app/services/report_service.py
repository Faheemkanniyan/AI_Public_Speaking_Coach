"""
PDF Report Generation Service for SpeakPro AI.
Generates beautifully formatted PDF speech evaluation reports inside
D:\\AI_Public_Speaking_Coach\\reports\\ using ReportLab.
"""

import os
import uuid
import json
from pathlib import Path
from django.conf import settings

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class ReportService:
    """
    Generates downloadable PDF evaluation reports for speech practice sessions.
    """

    def __init__(self):
        self.reports_dir = getattr(settings, "REPORTS_DIR", Path(settings.BASE_DIR) / "reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_pdf_report(self, report) -> str:
        """
        Creates a PDF file in D:\\AI_Public_Speaking_Coach\\reports\\ and returns the relative path.
        """
        if not REPORTLAB_AVAILABLE:
            return ""

        filename = f"speakpro_report_{uuid.uuid4().hex}.pdf"
        dest_path = self.reports_dir / filename

        doc = SimpleDocTemplate(
            str(dest_path),
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0B0F19"),
            spaceAfter=12,
            fontName="Helvetica-Bold",
        )
        subtitle_style = ParagraphStyle(
            "ReportSub",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#475569"),
            spaceAfter=15,
        )
        heading2 = ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=15,
            spaceAfter=8,
            fontName="Helvetica-Bold",
        )
        normal_style = ParagraphStyle(
            "NormalText",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1E293B"),
        )

        from django.utils import timezone

        local_created = timezone.localtime(report.created_at)
        formatted_date = local_created.strftime("%B %d, %Y - %H:%M %Z")

        elements = []

        # Title & Header
        elements.append(Paragraph("SpeakPro AI — Speech Evaluation Report", title_style))
        elements.append(
            Paragraph(
                f"<b>Speaker:</b> {report.session.user.username} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Topic:</b> {report.session.topic_title}<br/>"
                f"<b>Date:</b> {formatted_date} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Evaluated by Gemini:</b> {report.model_name or 'gemini-3.5-flash'} (engine: {report.engine or 'gemini'})",
                subtitle_style,
            )
        )
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#00ff88"), spaceAfter=12))

        # Objective Measurable Facts Table
        facts_data = [
            ["Metric", "Value", "Standard"],
            ["Target Duration", f"{report.session.duration_seconds} seconds", "Goal Duration"],
            ["Time Consumed", f"{report.time_consumed_seconds}s ({report.time_utilization_percent}%)", "Session Length"],
            ["Word Count", f"{report.session.word_count or len((report.session.transcript or '').split())} words", ">= 25 words for AI evaluation"],
            ["Speaking Pace", f"{report.speaking_pace_wpm} WPM", "110 - 150 WPM Target"],
            ["Filler Count", f"{report.session.filler_count or 0}", "<= 3 recommended"],
        ]
        facts_table = Table(facts_data, colWidths=[160, 180, 170])
        facts_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        elements.append(facts_table)
        elements.append(Spacer(1, 12))

        # Score Summary Table
        score_data = [
            ["Competency Dimension", "Score", "Rating"],
            ["Overall Speaking Score", f"{report.overall_score}/100", self._rating_text(report.overall_score)],
            ["Fluency & Rhythm (25%)", f"{report.fluency_score}/100", self._rating_text(report.fluency_score)],
            ["Grammar & Syntax (20%)", f"{report.grammar_score}/100", self._rating_text(report.grammar_score)],
            ["Lexical Variety & Vocabulary (15%)", f"{report.vocabulary_score}/100", self._rating_text(report.vocabulary_score)],
            ["Clarity (15%)", f"{report.clarity_score}/100", self._rating_text(report.clarity_score)],
            ["Content & Topic Relevance (15%)", f"{report.content_relevance_score}/100", self._rating_text(report.content_relevance_score)],
            ["Vocal Confidence & Delivery (10%)", f"{report.confidence_score}/100", self._rating_text(report.confidence_score)],
        ]
        score_table = Table(score_data, colWidths=[200, 130, 180])
        score_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B0F19")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#00ff88")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ])
        )
        elements.append(score_table)
        elements.append(Spacer(1, 6))

        formula_style = ParagraphStyle(
            "Formula",
            parent=normal_style,
            fontSize=8,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=10
        )
        elements.append(
            Paragraph("<b>Score Formula:</b> Overall Score = 25% Fluency + 20% Grammar + 15% Vocabulary + 15% Clarity + 15% Content Relevance + 10% Confidence/Delivery. (Webcam visual presence is scored separately).", formula_style)
        )

        # Evidence Quotes under Competencies
        categories = [
            ("Fluency Evidence", report.fluency_evidence),
            ("Grammar Evidence", report.grammar_evidence),
            ("Vocabulary Evidence", report.vocabulary_evidence),
            ("Clarity Evidence", report.clarity_evidence),
            ("Content Relevance Evidence", report.content_relevance_evidence),
            ("Confidence Evidence", report.confidence_evidence),
        ]
        has_any_evidence = any(ev for _, ev in categories)
        if has_any_evidence:
            elements.append(Paragraph("Verbatim Evidence from Candidate Speech", heading2))
            for cat_title, ev_items in categories:
                if ev_items:
                    elements.append(Paragraph(f"<b>{cat_title}:</b>", normal_style))
                    for item in ev_items:
                        quote = item.get("quote", "")
                        reason = item.get("reason", "")
                        elements.append(Paragraph(f'• <i>"{quote}"</i> — {reason}', normal_style))
                    elements.append(Spacer(1, 4))
            elements.append(Spacer(1, 8))

        # Full Transcript
        if report.session.transcript:
            elements.append(Paragraph("Verbatim Transcript", heading2))
            elements.append(Paragraph(f'"{report.session.transcript}"', normal_style))
            elements.append(Spacer(1, 10))

        # Motivational Feedback
        elements.append(Paragraph("Executive Coaching Summary", heading2))
        elements.append(Paragraph(report.motivational_feedback, normal_style))
        elements.append(Spacer(1, 10))

        # Strengths & Weaknesses
        strengths = report.get_strengths()
        if strengths:
            elements.append(Paragraph("Key Strengths", heading2))
            for st in strengths:
                elements.append(Paragraph(f"• {st}", normal_style))
            elements.append(Spacer(1, 10))

        weaknesses = report.get_weaknesses()
        if weaknesses:
            elements.append(Paragraph("Areas for Improvement", heading2))
            for wk in weaknesses:
                elements.append(Paragraph(f"• {wk}", normal_style))
            elements.append(Spacer(1, 10))

        # Visual Presence Analytics
        if hasattr(report.session, 'visual_presence') and report.session.visual_presence:
            vp = report.session.visual_presence
            elements.append(Paragraph("Visual Presence Analytics (Webcam)", heading2))
            vp_data = [
                ["Metric", "Score", "Description"],
                ["Eye Contact", f"{vp.eye_contact_pct}%", "Maintaining eye contact with audience/camera."],
                ["Posture", f"{vp.posture_score}/100", "Steadiness and posture stability."],
                ["Expressions", f"{vp.expression_variety_score}/100", "Facial expression engagement."],
                ["Face Tracked", f"{vp.face_detected_pct}%", "Face visibility during recording."],
            ]
            vp_table = Table(vp_data, colWidths=[130, 80, 300])
            vp_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ])
            )
            elements.append(vp_table)
            elements.append(Spacer(1, 10))

        # Grammar & Speech Mistakes Table
        mistakes = report.get_mistakes()
        if mistakes:
            elements.append(Paragraph("Speech Mistakes & Corrections", heading2))
            corr_data = [["Original Quote", "Type", "Correction", "Coaching Rationale"]]
            for m in mistakes[:8]:
                m_type = m.get("type", "grammar")
                type_display = "Grammar"
                if m_type == "word_choice":
                    type_display = "Word Choice"
                elif m_type == "likely_speech_recognition_error":
                    type_display = "Speech Rec. Error (No penalty)"

                corr_data.append([
                    Paragraph(str(m.get("original", "")), normal_style),
                    Paragraph(type_display, normal_style),
                    Paragraph(str(m.get("correction", "")), normal_style),
                    Paragraph(str(m.get("reason", "")), normal_style),
                ])
            corr_table = Table(corr_data, colWidths=[120, 110, 130, 150])
            corr_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ])
            )
            elements.append(corr_table)
            elements.append(Spacer(1, 10))

        # Suggestions
        suggestions = report.get_suggestions()
        if suggestions:
            elements.append(Paragraph("Actionable Improvement Suggestions", heading2))
            for sg in suggestions:
                elements.append(Paragraph(f"• {sg}", normal_style))
            elements.append(Spacer(1, 10))

        # Footer line
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=10))
        elements.append(
            Paragraph("SpeakPro AI — Generated by AI Public Speaking Coach with Grounded Gemini Evaluation", ParagraphStyle("F", fontSize=8, textColor=colors.gray))
        )

        doc.build(elements)
        return f"reports/{filename}"

    def _rating_text(self, score: int) -> str:
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Strong"
        elif score >= 60:
            return "Developing"
        else:
            return "Needs Practice"
