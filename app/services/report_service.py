"""
PDF Report Generation Service for SpeakPro AI.
Generates beautifully formatted PDF speech evaluation reports inside
D:\\AI_Public_Speaking_Coach\\reports\\ using ReportLab.
"""

import os
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

        filename = f"speakpro_report_session_{report.session.id}.pdf"
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

        elements = []

        # Title & Header
        elements.append(Paragraph("SpeakPro AI — Speech Evaluation Report", title_style))
        elements.append(
            Paragraph(
                f"<b>Speaker:</b> {report.session.user.username} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Topic:</b> {report.session.topic_title} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Date:</b> {report.created_at.strftime('%Y-%m-%d %H:%M')}",
                subtitle_style,
            )
        )
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#00ff88"), spaceAfter=15))

        # Score Summary Table
        score_data = [
            ["Dimension", "Score (0-100)", "Rating"],
            ["Overall Score", f"{report.overall_score}/100", self._rating_text(report.overall_score)],
            ["Grammar", f"{report.grammar_score}/100", self._rating_text(report.grammar_score)],
            ["Confidence", f"{report.confidence_score}/100", self._rating_text(report.confidence_score)],
            ["Vocabulary", f"{report.vocabulary_score}/100", self._rating_text(report.vocabulary_score)],
            ["Communication", f"{report.communication_score}/100", self._rating_text(report.communication_score)],
            ["Fluency", f"{report.fluency_score}/100", self._rating_text(report.fluency_score)],
        ]
        score_table = Table(score_data, colWidths=[180, 150, 180])
        score_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B0F19")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#00ff88")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ])
        )
        elements.append(score_table)
        elements.append(Spacer(1, 15))

        # Motivational Feedback
        elements.append(Paragraph("Coaching Feedback & Summary", heading2))
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

        # Grammar & Vocabulary Corrections
        mistakes = report.get_mistakes()
        if mistakes:
            elements.append(Paragraph("Highlighted Speech Corrections", heading2))
            corr_data = [["Original Speech Phrase", "Recommended Correction", "Coaching Rationale"]]
            for m in mistakes[:5]:
                corr_data.append([
                    Paragraph(str(m.get("original", "")), normal_style),
                    Paragraph(str(m.get("correction", "")), normal_style),
                    Paragraph(str(m.get("reason", "")), normal_style),
                ])
            corr_table = Table(corr_data, colWidths=[160, 160, 190])
            corr_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ])
            )
            elements.append(corr_table)
            elements.append(Spacer(1, 15))

        # Practice Exercises
        exercises = report.get_exercises()
        if exercises:
            elements.append(Paragraph("Recommended Practice Drills", heading2))
            for ex in exercises:
                elements.append(Paragraph(f"✓ {ex}", normal_style))
            elements.append(Spacer(1, 15))

        # Footer line
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=10))
        elements.append(
            Paragraph("SpeakPro AI — Generated by AI Public Speaking Coach", ParagraphStyle("F", fontSize=8, textColor=colors.gray))
        )

        doc.build(elements)
        return f"reports/{filename}"

    def _rating_text(self, score: int) -> str:
        if score >= 90:
            return "Executive Orator (Excellent)"
        elif score >= 80:
            return "Advanced Speaker (Very Good)"
        elif score >= 70:
            return "Proficient Speaker (Good)"
        else:
            return "Developing Orator (Needs Practice)"
