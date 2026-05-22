from __future__ import annotations

import os
from datetime import datetime

from django.http import HttpResponse
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PDF_PALETTE = {
    "navy": colors.HexColor("#29435A"),
    "slate": colors.HexColor("#4F677A"),
    "mint": colors.HexColor("#6F9C95"),
    "sand": colors.HexColor("#F3EFE8"),
    "ice": colors.HexColor("#F4F7F8"),
    "ink": colors.HexColor("#1F2A33"),
    "muted": colors.HexColor("#667480"),
    "line": colors.HexColor("#D7E1DD"),
    "accent1": colors.HexColor("#D8B36A"),
    "accent2": colors.HexColor("#9B8BB3"),
    "accent3": colors.HexColor("#D97A6C"),
    "accent4": colors.HexColor("#7CA6C2"),
}

CHART_COLORS = [
    PDF_PALETTE["navy"],
    PDF_PALETTE["mint"],
    PDF_PALETTE["accent1"],
    PDF_PALETTE["accent2"],
    PDF_PALETTE["accent3"],
    PDF_PALETTE["accent4"],
]


def _resolve_logo_path() -> str | None:
    candidates = ["logo.png", "logo.jpg"]
    for filename in candidates:
        logo_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "static", "images", filename)
        )
        if os.path.exists(logo_path):
            return logo_path
    return None


def _paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph("" if value is None else str(value), style)


def _base_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PdfTitle",
            parent=styles["Title"],
            textColor=PDF_PALETTE["navy"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            alignment=1,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "PdfSubtitle",
            parent=styles["Heading3"],
            textColor=PDF_PALETTE["navy"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            spaceBefore=6,
            spaceAfter=8,
        ),
        "meta": ParagraphStyle(
            "PdfMeta",
            parent=styles["Normal"],
            textColor=PDF_PALETTE["muted"],
            fontSize=9,
            leading=12,
        ),
        "body": ParagraphStyle(
            "PdfBody",
            parent=styles["Normal"],
            textColor=PDF_PALETTE["ink"],
            fontSize=8.5,
            leading=10.8,
        ),
        "small": ParagraphStyle(
            "PdfSmall",
            parent=styles["Normal"],
            textColor=PDF_PALETTE["muted"],
            fontSize=8,
            leading=10,
        ),
        "header": ParagraphStyle(
            "PdfHeader",
            parent=styles["Normal"],
            textColor=colors.white,
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,
        ),
        "card_label": ParagraphStyle(
            "PdfCardLabel",
            parent=styles["Normal"],
            textColor=PDF_PALETTE["muted"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=1,
        ),
        "card_value": ParagraphStyle(
            "PdfCardValue",
            parent=styles["Normal"],
            textColor=PDF_PALETTE["navy"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            alignment=1,
        ),
    }


def _build_stats_cards(stats: list[tuple[str, str]], available_width: float, styles: dict) -> Table:
    cards_per_row = 3 if len(stats) >= 3 else max(1, len(stats))
    card_width = (available_width - (12 * (cards_per_row - 1))) / cards_per_row
    rows = []
    current = []
    for label, value in stats:
        card = Table(
            [
                [_paragraph(label, styles["card_label"])],
                [_paragraph(value, styles["card_value"])],
            ],
            colWidths=[card_width],
        )
        card.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.8, PDF_PALETTE["line"]),
                    ("INNERGRID", (0, 0), (-1, -1), 0, colors.white),
                    ("TOPPADDING", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                    ("TOPPADDING", (0, 1), (-1, 1), 2),
                    ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
                    ("BACKGROUND", (0, 0), (-1, 0), PDF_PALETTE["ice"]),
                ]
            )
        )
        current.append(card)
        if len(current) == cards_per_row:
            rows.append(current)
            current = []
    if current:
        while len(current) < cards_per_row:
            current.append("")
        rows.append(current)
    grid = Table(rows, colWidths=[card_width] * cards_per_row, hAlign="LEFT", spaceBefore=4)
    grid.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return grid


def _build_bar_chart(labels: list[str], values: list[float], title: str) -> Drawing:
    drawing = Drawing(470, 230)
    chart = VerticalBarChart()
    chart.x = 38
    chart.y = 35
    chart.height = 135
    chart.width = 380
    chart.data = [values]
    max_value = max(values) if values else 0
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(max_value * 1.15, 1)
    chart.valueAxis.valueStep = max(1, int(chart.valueAxis.valueMax / 5))
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 8
    chart.valueAxis.labels.fillColor = PDF_PALETTE["muted"]
    chart.valueAxis.visibleGrid = 1
    chart.valueAxis.gridStrokeColor = colors.HexColor("#E7ECEF")
    chart.valueAxis.strokeColor = colors.HexColor("#D9E1E6")
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.boxAnchor = "ne"
    chart.categoryAxis.labels.angle = 20 if len(labels) > 4 else 0
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.fillColor = PDF_PALETTE["muted"]
    chart.categoryAxis.strokeColor = colors.HexColor("#D9E1E6")
    chart.barWidth = 22
    chart.groupSpacing = 12
    chart.barSpacing = 5
    chart.bars[0].fillColor = PDF_PALETTE["mint"]
    chart.bars[0].strokeColor = PDF_PALETTE["navy"]
    chart.bars[0].strokeWidth = 0.5
    drawing.add(chart)
    drawing.add(String(235, 204, title, fontName="Helvetica-Bold", fontSize=11, fillColor=PDF_PALETTE["navy"], textAnchor="middle"))
    return drawing


def _build_pie_chart(labels: list[str], values: list[float], title: str) -> Drawing:
    drawing = Drawing(470, 235)
    pie = Pie()
    pie.x = 60
    pie.y = 30
    pie.width = 150
    pie.height = 150
    pie.data = values
    pie.labels = [f"{label} ({value})" for label, value in zip(labels, values)]
    pie.sideLabels = True
    pie.simpleLabels = False
    pie.slices.strokeWidth = 0.4
    pie.slices.strokeColor = colors.white
    pie.slices.popout = 1
    for idx, _ in enumerate(values):
        pie.slices[idx].fillColor = CHART_COLORS[idx % len(CHART_COLORS)]
    drawing.add(pie)
    drawing.add(String(235, 205, title, fontName="Helvetica-Bold", fontSize=11, fillColor=PDF_PALETTE["navy"], textAnchor="middle"))
    return drawing


def _normalize_charts(chart_data: dict | list[dict] | None) -> list[dict]:
    if not chart_data:
        return []
    if isinstance(chart_data, dict):
        return [chart_data]
    return [chart for chart in chart_data if isinstance(chart, dict)]


def _build_data_table(headers: list[str], rows: list[list[str]], available_width: float, styles: dict) -> Table:
    data = [[_paragraph(h, styles["header"]) for h in headers]]
    for row in rows:
        data.append([_paragraph(cell, styles["body"]) for cell in row])

    col_width = max(56, available_width / max(len(headers), 1))
    col_widths = [col_width for _ in headers]
    table = Table(data, hAlign="LEFT", repeatRows=1, colWidths=col_widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PDF_PALETTE["navy"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.45, PDF_PALETTE["line"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PDF_PALETTE["ice"]]),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _draw_footer(canvas, doc_obj):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#DDE5E8"))
    canvas.line(doc_obj.leftMargin, 28, doc_obj.pagesize[0] - doc_obj.rightMargin, 28)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(PDF_PALETTE["muted"])
    canvas.drawString(doc_obj.leftMargin, 16, "JobXpress · Reporte administrativo")
    canvas.drawRightString(doc_obj.pagesize[0] - doc_obj.rightMargin, 16, f"Pagina {canvas.getPageNumber()}")
    canvas.restoreState()


def build_simple_report(title: str, headers: list[str], rows: list[list[str]], filename: str) -> HttpResponse:
    return build_report_with_stats(
        title=title,
        headers=headers,
        rows=rows,
        filename=filename,
        stats=[("Total de registros", str(len(rows)))],
    )


def build_report_with_stats(
    title: str,
    headers: list[str],
    rows: list[list[str]],
    filename: str,
    stats: list[tuple[str, str]] | None = None,
    chart_data: dict | list[dict] | None = None,
) -> HttpResponse:
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename={filename}"

    use_landscape = len(headers) >= 7
    pagesize = landscape(A4) if use_landscape else A4
    doc = SimpleDocTemplate(
        response,
        pagesize=pagesize,
        leftMargin=34,
        rightMargin=34,
        topMargin=34,
        bottomMargin=34,
    )

    styles = _base_styles()
    story: list = []
    available_width = pagesize[0] - doc.leftMargin - doc.rightMargin

    logo_path = _resolve_logo_path()
    if logo_path:
        story.append(Image(logo_path, width=112, height=112))
        story.append(Spacer(1, 8))

    story.append(_paragraph(title, styles["title"]))
    story.append(_paragraph(f"Fecha de generacion: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["meta"]))
    story.append(_paragraph(f"Total de registros listados: {len(rows)}", styles["meta"]))
    story.append(Spacer(1, 10))

    banner = Table(
        [[_paragraph("Resumen ejecutivo", styles["subtitle"])]],
        colWidths=[available_width],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PDF_PALETTE["sand"]),
                ("BOX", (0, 0), (-1, -1), 0.6, PDF_PALETTE["line"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(banner)
    story.append(Spacer(1, 8))

    if stats:
        story.append(_build_stats_cards(stats, available_width, styles))
        story.append(Spacer(1, 6))

    for chart in _normalize_charts(chart_data):
        labels = chart.get("labels") or []
        values = chart.get("values") or []
        chart_title = chart.get("title") or "Grafica"
        chart_type = (chart.get("type") or "bar").lower()
        if not labels or not values or len(labels) != len(values):
            continue
        if all((v or 0) == 0 for v in values):
            continue

        story.append(_paragraph(chart_title, styles["subtitle"]))
        drawing = _build_pie_chart(labels, values, chart_title) if chart_type == "pie" else _build_bar_chart(labels, values, chart_title)
        story.append(drawing)
        story.append(Spacer(1, 12))

    story.append(_paragraph("Detalle de registros", styles["subtitle"]))
    story.append(_build_data_table(headers, rows, available_width, styles))

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return response
