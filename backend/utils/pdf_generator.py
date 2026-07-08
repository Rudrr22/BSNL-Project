# pdf_generator.py — Branded PDF report generation
# Uses ReportLab (already in requirements.txt)

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie
from io import BytesIO
from datetime import datetime


def generate_analysis_pdf(analysis, anomalies) -> BytesIO:
    """
    Generate a professional PDF report for an analysis session.
    
    Args:
        analysis: SQLAlchemy Analysis object
        anomalies: list of Anomaly objects
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=30*mm, bottomMargin=20*mm,
        leftMargin=20*mm, rightMargin=20*mm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        'BrandTitle', parent=styles['Title'],
        fontSize=26, textColor=colors.HexColor('#0891b2'),
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        'BrandSubtitle', parent=styles['Normal'],
        fontSize=11, textColor=colors.HexColor('#64748b'),
        spaceAfter=16
    ))
    styles.add(ParagraphStyle(
        'SectionHead', parent=styles['Heading2'],
        fontSize=15, textColor=colors.HexColor('#0e7490'),
        spaceBefore=18, spaceAfter=8,
        borderColor=colors.HexColor('#0e7490'),
        borderWidth=0, borderPadding=0
    ))
    styles.add(ParagraphStyle(
        'BodyText2', parent=styles['Normal'],
        fontSize=10, leading=14, textColor=colors.HexColor('#334155'),
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        'Small', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#94a3b8')
    ))

    elements = []

    from reportlab.graphics.shapes import Drawing, Circle, String, Polygon

    logo = Drawing(400, 50)
    # Grey circle background for arrows
    logo.add(Circle(25, 25, 22, fillColor=colors.HexColor('#C4C4C4'), strokeColor=None))
    # Red Arrow (Approximation)
    logo.add(Polygon([5, 40, 20, 20, 25, 25, 10, 45, 15, 50], fillColor=colors.HexColor('#E31837'), strokeColor=None))
    # Blue Arrow (Approximation)
    logo.add(Polygon([45, 10, 30, 30, 25, 25, 40, 5, 35, 0], fillColor=colors.HexColor('#005B9F'), strokeColor=None))
    
    # Text
    logo.add(String(60, 22, "BSNL", fontName="Helvetica-Bold", fontSize=28, fillColor=colors.HexColor('#005B9F')))
    logo.add(String(62, 8, "Connecting India", fontName="Helvetica-Oblique", fontSize=12, fillColor=colors.HexColor('#E31837')))
    
    elements.append(logo)
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(
        f"BSNL Network Analysis Report &bull; Generated {datetime.now().strftime('%d %B %Y, %H:%M IST')}",
        styles['BrandSubtitle']
    ))
    elements.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor('#0891b2'), spaceAfter=14
    ))

    # ─── SESSION INFO ──────────────────────────────────
    elements.append(Paragraph("SESSION OVERVIEW", styles['SectionHead']))

    session_data = [
        ['Analysis ID', str(analysis.id)],
        ['Filename', analysis.filename or 'Live analysis'],
        ['Source', analysis.source or 'upload'],
        ['Status', analysis.status],
        ['Created', analysis.created_at.strftime('%Y-%m-%d %H:%M:%S') if analysis.created_at else 'N/A'],
    ]
    session_table = Table(session_data, colWidths=[120, 380])
    session_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748b')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1e293b')),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    elements.append(session_table)
    elements.append(Spacer(1, 10))

    # ─── SEVERITY STATISTICS ───────────────────────────
    elements.append(Paragraph("SEVERITY BREAKDOWN", styles['SectionHead']))

    severity_data = [
        ['Severity', 'Count', 'Percentage'],
        ['CRITICAL', str(analysis.critical_count),
         f"{(analysis.critical_count / max(analysis.total_logs, 1) * 100):.1f}%"],
        ['WARNING', str(analysis.warning_count),
         f"{(analysis.warning_count / max(analysis.total_logs, 1) * 100):.1f}%"],
        ['INFO', str(analysis.info_count),
         f"{(analysis.info_count / max(analysis.total_logs, 1) * 100):.1f}%"],
        ['TOTAL', str(analysis.total_logs), '100%'],
    ]

    sev_table = Table(severity_data, colWidths=[160, 160, 180])
    sev_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0e7490')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
        ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor('#dc2626')),
        ('TEXTCOLOR', (0, 2), (0, 2), colors.HexColor('#d97706')),
        ('TEXTCOLOR', (0, 3), (0, 3), colors.HexColor('#16a34a')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#0e7490')),
    ]))
    elements.append(sev_table)
    elements.append(Spacer(1, 6))

    # ─── PIE CHART ─────────────────────────────────────
    if analysis.total_logs > 0:
        drawing = Drawing(300, 160)
        pie = Pie()
        pie.x = 80
        pie.y = 10
        pie.width = 130
        pie.height = 130
        pie.data = [
            max(analysis.critical_count, 0),
            max(analysis.warning_count, 0),
            max(analysis.info_count, 0)
        ]
        pie.labels = ['Critical', 'Warning', 'Info']
        pie.slices[0].fillColor = colors.HexColor('#ef4444')
        pie.slices[1].fillColor = colors.HexColor('#f59e0b')
        pie.slices[2].fillColor = colors.HexColor('#22c55e')
        pie.slices.strokeWidth = 0.5
        pie.slices.strokeColor = colors.white
        drawing.add(pie)
        elements.append(drawing)
        elements.append(Spacer(1, 8))

    # ─── AI SUMMARY ────────────────────────────────────
    if analysis.summary:
        elements.append(Paragraph("EXECUTIVE SUMMARY", styles['SectionHead']))
        elements.append(Paragraph(analysis.summary, styles['BodyText2']))

    # ─── ANOMALIES TABLE ───────────────────────────────
    if anomalies:
        elements.append(Paragraph(
            f"DETECTED ANOMALIES ({len(anomalies)})", styles['SectionHead']
        ))

        anomaly_header = ['#', 'Severity', 'Component', 'Event', 'Description']
        anomaly_rows = [anomaly_header]

        for i, a in enumerate(anomalies[:20], 1):
            desc = (a.description or '')[:80]
            if len(a.description or '') > 80:
                desc += '...'
            anomaly_rows.append([
                str(i),
                a.severity or '',
                a.component or '',
                a.event_type or '',
                desc
            ])

        a_table = Table(anomaly_rows, colWidths=[25, 70, 90, 100, 215])
        a_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0e7490')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -2), 0.4, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        elements.append(a_table)

    # ─── RECOMMENDATIONS ───────────────────────────────
    if analysis.recommendations:
        elements.append(Paragraph("RECOMMENDATIONS", styles['SectionHead']))
        for line in analysis.recommendations.split('\n'):
            if line.strip():
                elements.append(Paragraph(f"• {line.strip()}", styles['BodyText2']))

    # ─── FOOTER ────────────────────────────────────────
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#cbd5e1'), spaceAfter=8
    ))
    elements.append(Paragraph(
        "This report was auto-generated by Teleguard — "
        "BSNL Intelligent Network Monitoring System. "
        "Powered by LangGraph multi-agent pipeline + RAG.",
        styles['Small']
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
