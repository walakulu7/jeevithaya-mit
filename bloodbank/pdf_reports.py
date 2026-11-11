"""
Jeevithaya Blood Bank Management System - Formal PDF Report Generator
Builds paginated, branded clinical and operational PDF documents using ReportLab.
"""

from datetime import datetime
from io import BytesIO
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .services import (
    AnalyticsContext,
    DisposalReportStrategy,
    DonationReportStrategy,
    ExecutiveOverviewStrategy,
    InventoryReportStrategy,
    RequestReportStrategy,
    VerificationReportStrategy,
)

REPORT_TITLES = {
    "all": "Complete Executive Audit Report Pack",
    "overview": "Executive Overview Report",
    "inventory": "Inventory & Cold-Chain Expiry Report",
    "requests": "Hospital Requests & Fulfillment Report",
    "donations": "Donors & Collection Intake Report",
    "verification": "Serological Verification & QC Audit Report",
    "disposal": "Bio-Waste Disposal & Wastage Compliance Report",
}

BRAND_CRIMSON = colors.HexColor("#D90429")
BRAND_NAVY = colors.HexColor("#0F172A")
SLATE_HEADER = colors.HexColor("#1E293B")
SLATE_TEXT = colors.HexColor("#334155")
SLATE_MUTED = colors.HexColor("#64748B")
SURFACE_ALT = colors.HexColor("#F8FAFC")
BORDER_SUBTLE = colors.HexColor("#CBD5E1")
SUCCESS_GREEN = colors.HexColor("#15803D")
SUCCESS_BG = colors.HexColor("#DCFCE7")
WARN_AMBER = colors.HexColor("#B45309")
WARN_BG = colors.HexColor("#FEF3C7")
DANGER_RED = colors.HexColor("#B91C1C")
DANGER_BG = colors.HexColor("#FEE2E2")


class NumberedReportCanvas(canvas.Canvas):
    """Two-pass ReportLab canvas rendering branded headers, footers, and Page X of Y."""

    def __init__(self, *args, report_title="", report_id="", **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self._report_title = report_title
        self._report_id = report_id

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_chrome(total_pages)
            super().showPage()
        super().save()

    def _draw_chrome(self, total_pages):
        width, height = A4
        margin_x = 15 * mm

        self.saveState()

        # Top crimson bar
        self.setFillColor(BRAND_CRIMSON)
        self.rect(0, height - 4 * mm, width, 4 * mm, fill=1, stroke=0)

        # Emblem (Crimson rounded badge with white droplet + pulse line)
        badge_x = margin_x
        badge_y = height - 21 * mm
        badge_size = 11 * mm
        self.setFillColor(BRAND_CRIMSON)
        self.roundRect(badge_x, badge_y, badge_size, badge_size, 2.4 * mm, fill=1, stroke=0)

        self.setFillColor(colors.white)
        cx = badge_x + badge_size / 2
        cy = badge_y + badge_size / 2 - 0.5 * mm
        path = self.beginPath()
        path.moveTo(cx, cy + 3.4 * mm)
        path.curveTo(cx + 2.6 * mm, cy + 0.6 * mm, cx + 2.6 * mm, cy - 2.3 * mm, cx, cy - 2.7 * mm)
        path.curveTo(cx - 2.6 * mm, cy - 2.3 * mm, cx - 2.6 * mm, cy + 0.6 * mm, cx, cy + 3.4 * mm)
        self.drawPath(path, fill=1, stroke=0)

        self.setStrokeColor(BRAND_CRIMSON)
        self.setLineWidth(1.0)
        pulse = self.beginPath()
        pulse.moveTo(cx - 2.0 * mm, cy - 0.3 * mm)
        pulse.lineTo(cx - 0.8 * mm, cy - 0.3 * mm)
        pulse.lineTo(cx - 0.2 * mm, cy + 1.1 * mm)
        pulse.lineTo(cx + 0.5 * mm, cy - 1.3 * mm)
        pulse.lineTo(cx + 1.0 * mm, cy - 0.3 * mm)
        pulse.lineTo(cx + 2.0 * mm, cy - 0.3 * mm)
        self.drawPath(pulse, fill=0, stroke=1)

        # Left Brand Text
        text_x = badge_x + badge_size + 3.5 * mm
        self.setFillColor(BRAND_NAVY)
        self.setFont("Helvetica-Bold", 12)
        self.drawString(text_x, height - 13.5 * mm, "JEEVITHAYA BLOOD & PLASMA BANK")
        self.setFillColor(SLATE_MUTED)
        self.setFont("Helvetica", 8)
        self.drawString(text_x, height - 18 * mm, "Centralized Blood Bank Operations & Regulatory Audit System")

        # Right Report Title & Reference
        right_x = width - margin_x
        self.setFillColor(BRAND_CRIMSON)
        self.setFont("Helvetica-Bold", 9.5)
        self.drawRightString(right_x, height - 13.5 * mm, self._report_title)
        self.setFillColor(SLATE_MUTED)
        self.setFont("Helvetica", 7.5)
        self.drawRightString(right_x, height - 18 * mm, f"Ref: {self._report_id}  |  OFFICIAL REPORT")

        # Header divider line
        self.setStrokeColor(BORDER_SUBTLE)
        self.setLineWidth(0.8)
        self.line(margin_x, height - 24 * mm, right_x, height - 24 * mm)

        # Footer divider line & Page X of Y
        footer_y = 11 * mm
        self.line(margin_x, footer_y + 4 * mm, right_x, footer_y + 4 * mm)
        self.setFillColor(SLATE_MUTED)
        self.setFont("Helvetica", 7.5)
        self.drawString(
            margin_x,
            footer_y,
            "Confidential Clinical & Operational Record — Generated directly from Jeevithaya Database",
        )
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(SLATE_TEXT)
        self.drawRightString(right_x, footer_y, f"Page {self._pageNumber} of {total_pages}")

        self.restoreState()


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "section": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=BRAND_NAVY,
            spaceBefore=10,
            spaceAfter=5,
        ),
        "sub": ParagraphStyle(
            "SubText",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=SLATE_MUTED,
            spaceAfter=6,
        ),
        "cell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=SLATE_TEXT,
        ),
        "cell_bold": ParagraphStyle(
            "TableCellBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10.5,
            textColor=BRAND_NAVY,
        ),
        "header_cell": ParagraphStyle(
            "HeaderCell",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.white,
        ),
        "kpi_label": ParagraphStyle(
            "KpiLabel",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=SLATE_MUTED,
        ),
        "kpi_val": ParagraphStyle(
            "KpiVal",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=BRAND_NAVY,
        ),
        "kpi_sub": ParagraphStyle(
            "KpiSub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=SLATE_MUTED,
        ),
    }


def _status_style_colors(value):
    clean = str(value or "").strip().lower()
    if clean in {"fulfilled", "passed", "available", "eligible", "healthy (> 30d)", "sufficient"}:
        return SUCCESS_GREEN, SUCCESS_BG
    if clean in {
        "rejected",
        "failed",
        "expired",
        "critical (<= 7d)",
        "critical",
        "not eligible",
        "contaminated",
        "shortage",
        "failed verification",
    }:
        return DANGER_RED, DANGER_BG
    if clean in {"pending", "approved", "reserved", "urgent", "warning (8-30d)", "damaged"}:
        return WARN_AMBER, WARN_BG
    return None, None


def _kpi_strip(items, styles, doc_width):
    """Build a crisp 4-column scorecard table."""
    col_w = doc_width / max(1, len(items))
    cells = []
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, -1), SURFACE_ALT),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_SUBTLE),
        ("INNERGRID", (0, 0), (-1, -1), 0.75, BORDER_SUBTLE),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for idx, (label, val, sub, tone) in enumerate(items):
        val_color = BRAND_NAVY
        if tone == "danger":
            val_color = DANGER_RED
        elif tone == "success":
            val_color = SUCCESS_GREEN
        val_style = ParagraphStyle(
            f"KpiVal_{idx}",
            parent=styles["kpi_val"],
            textColor=val_color,
        )
        cells.append([
            Paragraph(label.upper(), styles["kpi_label"]),
            Spacer(1, 2),
            Paragraph(str(val), val_style),
            Paragraph(sub, styles["kpi_sub"]),
        ])
    table = Table([cells], colWidths=[col_w] * len(items))
    table.setStyle(TableStyle(style_cmds))
    return table


def _styled_table(headers, rows, col_widths, styles, status_cols=None, empty_msg="No records found for selected filters."):
    """Create a multi-page repeating-header audit table with wrapped paragraphs and zebra shading."""
    status_cols = set(status_cols or [])
    header_row = [Paragraph(str(h).upper(), styles["header_cell"]) for h in headers]

    if not rows:
        data = [
            header_row,
            [Paragraph(empty_msg, styles["sub"])] + [""] * (len(headers) - 1),
        ]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SLATE_HEADER),
            ("SPAN", (0, 1), (-1, 1)),
            ("ALIGN", (0, 1), (-1, 1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.6, BORDER_SUBTLE),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return t

    data = [header_row]
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), SLATE_HEADER),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER_SUBTLE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]

    for r_idx, row in enumerate(rows, start=1):
        if r_idx % 2 == 0:
            cmds.append(("BACKGROUND", (0, r_idx), (-1, r_idx), SURFACE_ALT))
        formatted_row = []
        for c_idx, val in enumerate(row):
            text = "-" if val in (None, "") else str(val)
            if c_idx in status_cols:
                fg, bg = _status_style_colors(text)
                if fg and bg:
                    st = ParagraphStyle(f"St_{r_idx}_{c_idx}", parent=styles["cell_bold"], textColor=fg)
                    formatted_row.append(Paragraph(text, st))
                    cmds.append(("BACKGROUND", (c_idx, r_idx), (c_idx, r_idx), bg))
                    continue
            formatted_row.append(Paragraph(text, styles["cell_bold"] if c_idx == 0 else styles["cell"]))
        data.append(formatted_row)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(cmds))
    return t


def _bar_chart(title, categories, series_values, series_names, series_colors, doc_width):
    """Build a crisp native ReportLab vector bar chart."""
    drawing = Drawing(doc_width, 155)
    drawing.add(Rect(0, 0, doc_width, 155, fillColor=SURFACE_ALT, strokeColor=BORDER_SUBTLE, strokeWidth=0.6))
    drawing.add(String(12, 138, title, fontName="Helvetica-Bold", fontSize=9, fillColor=BRAND_NAVY))

    # Legend
    lx = doc_width - 14
    for idx in range(len(series_names) - 1, -1, -1):
        label = series_names[idx]
        col = series_colors[idx]
        label_w = len(label) * 4.7 + 16
        lx -= label_w
        drawing.add(Rect(lx, 137, 8, 8, fillColor=col, strokeColor=None))
        drawing.add(String(lx + 11, 138, label, fontName="Helvetica", fontSize=7.5, fillColor=SLATE_TEXT))

    chart = VerticalBarChart()
    chart.x = 38
    chart.y = 24
    chart.width = doc_width - 54
    chart.height = 100
    chart.data = series_values
    chart.categoryAxis.categoryNames = categories
    chart.categoryAxis.labels.fontName = "Helvetica-Bold"
    chart.categoryAxis.labels.fontSize = 7.5
    chart.categoryAxis.labels.fillColor = SLATE_TEXT
    chart.valueAxis.valueMin = 0
    max_val = max([v for series in series_values for v in series] or [1])
    chart.valueAxis.valueMax = max(2, int(max_val * 1.2) + 1)
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = SLATE_MUTED
    chart.valueAxis.gridStrokeColor = colors.HexColor("#E2E8F0")
    chart.valueAxis.visibleGrid = True
    chart.barSpacing = 2
    chart.groupSpacing = 10

    for idx, col in enumerate(series_colors):
        chart.bars[idx].fillColor = col
        chart.bars[idx].strokeColor = None

    drawing.add(chart)
    return drawing


def _sign_off_block(prepared_by, styles, doc_width):
    """Formal approval & sign-off footer block."""
    half = doc_width / 2
    rows = [
        [
            Paragraph("PREPARED & VERIFIED BY", styles["kpi_label"]),
            Paragraph("REVIEWED & AUTHORIZED BY", styles["kpi_label"]),
        ],
        [
            Paragraph(f"<b>{prepared_by}</b><br/>Signature: ________________________<br/>Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["cell"]),
            Paragraph("<b>Medical / Lab Director</b><br/>Signature: ________________________<br/>Date / Stamp: _____________________", styles["cell"]),
        ],
    ]
    t = Table(rows, colWidths=[half, half])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SURFACE_ALT),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_SUBTLE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, BORDER_SUBTLE),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ]))
    return t


def _metadata_banner(filters, report_type, prepared_by, generated_at, styles, doc_width):
    days = filters.get("days") or "all"
    if filters.get("start_date") or filters.get("end_date"):
        period_str = f"{filters.get('start_date') or '...'} to {filters.get('end_date') or '...'}"
    elif str(days) == "all":
        period_str = "All Time"
    else:
        period_str = f"Last {days} Days"

    bg = filters.get("blood_group") or "All Blood Groups"
    if str(bg).lower() == "all":
        bg = "All Blood Groups"
    tp = filters.get("item_type") or "All Components"
    if str(tp).lower() == "all":
        tp = "All Components"

    col_w = doc_width / 3
    rows = [
        [
            Paragraph(f"<b>Report Scope:</b> {REPORT_TITLES.get(report_type, 'Audit Report')}", styles["cell"]),
            Paragraph(f"<b>Period:</b> {period_str}", styles["cell"]),
            Paragraph(f"<b>Blood / Type:</b> {bg} / {tp}", styles["cell"]),
        ],
        [
            Paragraph(f"<b>Prepared By:</b> {prepared_by}", styles["cell"]),
            Paragraph(f"<b>Generated At:</b> {generated_at}", styles["cell"]),
            Paragraph("<b>System:</b> Jeevithaya Clinical Repository", styles["cell"]),
        ],
    ]
    t = Table(rows, colWidths=[col_w] * 3)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SURFACE_ALT),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_SUBTLE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def _append_overview(story, data, styles, w):
    s = data["summary"]
    story.append(Paragraph("1. Executive Blood Bank Overview", styles["section"]))
    story.append(_kpi_strip([
        ("Request Fulfillment", f"{s['fulfillmentRate']}%", f"{s['totalRequests']} total requests logged", "success"),
        ("Available Safe Stock", s["availableUnits"], f"{s['expiringSoonUnits']} units expiring <= 7 days", "neutral"),
        ("QC Clearance Yield", f"{s['verificationPassRate']}%", f"{s['totalVerifications']} verifications audited", "neutral"),
        ("Bio-Waste Wastage", f"{s['wastageRate']}%", f"{s['totalDisposals']} disposal records", "danger" if s["wastageRate"] > 10 else "neutral"),
    ], styles, w))
    story.append(Spacer(1, 8))

    shortages = data.get("criticalShortages", [])
    if shortages:
        msg = " | ".join(f"{x['bloodGroup']} (Avail {x['available']} / Demand {x['pendingDemand']})" for x in shortages)
        alert = Table([[Paragraph(f"<b>CRITICAL STOCK SHORTAGE ALERT:</b> {msg}", ParagraphStyle("Alert", parent=styles["cell_bold"], textColor=DANGER_RED))]], colWidths=[w])
        alert.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), DANGER_BG),
            ("BOX", (0, 0), (-1, -1), 0.8, DANGER_RED),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(alert)
        story.append(Spacer(1, 8))

    svd = data.get("supplyVsDemand", [])
    if svd:
        story.append(_bar_chart(
            "Available Safe Stock vs. Pending Hospital Demand by Blood Group",
            [x["bloodGroup"] for x in svd],
            [[x["available"] for x in svd], [x["pendingDemand"] for x in svd]],
            ["Available Units", "Pending Demand"],
            [SUCCESS_GREEN, BRAND_CRIMSON],
            w,
        ))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Recent Cross-Module Audit Timeline", styles["section"]))
    tl_rows = [[r["module"], r["id"], r["date"], r["bloodGroup"], r["summary"]] for r in data.get("timeline", [])[:15]]
    story.append(_styled_table(
        ["Module", "Record ID", "Date", "Blood Group", "Operational Summary"],
        tl_rows,
        [w * 0.14, w * 0.15, w * 0.14, w * 0.13, w * 0.44],
        styles,
    ))


def _append_inventory(story, data, styles, w):
    s = data["summary"]
    story.append(Paragraph("Inventory, Cold-Chain Stock & Expiry Aging Report", styles["section"]))
    story.append(_kpi_strip([
        ("Available Units", s["availableUnits"], "Ready for hospital issue", "success"),
        ("Reserved Units", s["reservedUnits"], "Allocated to open orders", "neutral"),
        ("Expiring <= 7 Days", s["expiringSoonUnits"], "Urgent FIFO dispatch needed", "danger" if s["expiringSoonUnits"] > 0 else "neutral"),
        ("Expired Stock", s["expiredUnits"], f"{s['expiredRecords']} batch records expired", "danger" if s["expiredUnits"] > 0 else "neutral"),
    ], styles, w))
    story.append(Spacer(1, 8))

    buckets = data.get("expiryBuckets", [])
    if buckets:
        story.append(_bar_chart(
            "Cold-Chain Shelf-Life Aging Distribution (Units)",
            [b["bucket"] for b in buckets],
            [[b["units"] for b in buckets]],
            ["Units by Shelf-Life Window"],
            [BRAND_NAVY],
            w,
        ))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Blood Group x Component Availability Matrix", styles["section"]))
    mat_rows = [
        [r["bloodGroup"], r["bloodUnits"], r["plasmaUnits"], r["totalAvailable"], r["reservedUnits"], r["expiredUnits"]]
        for r in data.get("componentMatrix", [])
    ]
    story.append(_styled_table(
        ["Blood Group", "Whole Blood", "Plasma", "Total Available", "Reserved", "Expired"],
        mat_rows,
        [w * 0.18, w * 0.16, w * 0.16, w * 0.18, w * 0.16, w * 0.16],
        styles,
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Batch-Level Cold-Chain Inventory Ledger", styles["section"]))
    led_rows = [
        [r["unitId"], r["batchNo"], r["bloodGroup"], r["type"], r["quantity"], r["expiryDate"], r["expiryBucket"], r["status"]]
        for r in data.get("ledger", [])
    ]
    story.append(_styled_table(
        ["Unit ID", "Batch No", "Blood", "Type", "Qty", "Expiry Date", "Shelf-Life Bucket", "Status"],
        led_rows,
        [w * 0.11, w * 0.14, w * 0.08, w * 0.09, w * 0.06, w * 0.14, w * 0.22, w * 0.16],
        styles,
        status_cols={6, 7},
    ))


def _append_requests(story, data, styles, w):
    s = data["summary"]
    story.append(Paragraph("Hospital Transfusion Requests & Fulfillment Report", styles["section"]))
    story.append(_kpi_strip([
        ("Total Requests", s["totalRequests"], f"{s['totalUnitsRequested']} units requested", "neutral"),
        ("Open Queue", s["pendingRequests"] + s["approvedRequests"], f"{s['pendingRequests']} Pending / {s['approvedRequests']} Approved", "neutral"),
        ("Fulfilled Orders", s["fulfilledRequests"], f"{s['fulfillmentRate']}% completion rate", "success"),
        ("Critical Urgency", s["criticalRequests"], "Priority medical demand", "danger" if s["criticalRequests"] > 0 else "neutral"),
    ], styles, w))
    story.append(Spacer(1, 8))

    sb = data.get("statusBreakdown", [])
    if sb:
        story.append(_bar_chart(
            "Hospital Requisitions by Workflow Status",
            [x["status"] for x in sb],
            [[x["count"] for x in sb], [x["units"] for x in sb]],
            ["Request Count", "Units Requested"],
            [SLATE_HEADER, BRAND_CRIMSON],
            w,
        ))
        story.append(Spacer(1, 8))

    hosp_rows = [[f"Hospital #{h['hospitalId']}", h["totalRequests"], h["fulfilled"], h["open"], h["totalUnits"]] for h in data.get("hospitalBreakdown", [])]
    story.append(Paragraph("Hospital Demand Summary", styles["section"]))
    story.append(_styled_table(
        ["Hospital", "Total Requests", "Fulfilled", "Open Queue", "Total Units"],
        hosp_rows,
        [w * 0.28, w * 0.18, w * 0.18, w * 0.18, w * 0.18],
        styles,
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Itemized Hospital Request Ledger", styles["section"]))
    req_rows = [
        [
            r["requestId"],
            r["patientName"],
            f"#{r['hospitalId']}",
            r["requestDate"],
            f"{r['bloodGroup']} ({r['type']})",
            r["quantity"],
            r["urgency"],
            r["status"],
            "Fulfilled" if r["status"] == "Fulfilled" else ("Sufficient" if r["stockSufficient"] else "Shortage"),
        ]
        for r in data.get("ledger", [])
    ]
    story.append(_styled_table(
        ["Req ID", "Patient", "Hosp", "Date", "Component", "Qty", "Urgency", "Status", "Stock Check"],
        req_rows,
        [w * 0.10, w * 0.16, w * 0.07, w * 0.12, w * 0.14, w * 0.06, w * 0.11, w * 0.12, w * 0.12],
        styles,
        status_cols={6, 7, 8},
    ))


def _append_donations(story, data, styles, w):
    s = data["summary"]
    story.append(Paragraph("Donor Registry & Collection Intake Report", styles["section"]))
    story.append(_kpi_strip([
        ("Registered Donors", s["totalDonors"], f"{s['eligibleDonors']} eligible ({s['eligibilityRate']}%)", "success"),
        ("Donation Sessions", s["totalDonations"], f"{s['totalUnitsCollected']} total units collected", "neutral"),
        ("Whole Blood Intake", s["bloodUnits"], "Units collected in period", "neutral"),
        ("Plasma Intake", s["plasmaUnits"], "Units collected in period", "neutral"),
    ], styles, w))
    story.append(Spacer(1, 8))

    dbg = data.get("donorByBloodGroup", [])
    if dbg:
        story.append(_bar_chart(
            "Registered Donor Eligibility by Blood Group",
            [x["bloodGroup"] for x in dbg],
            [[x["eligible"] for x in dbg], [x["notEligible"] for x in dbg]],
            ["Eligible Donors", "Not Eligible"],
            [SUCCESS_GREEN, WARN_AMBER],
            w,
        ))
        story.append(Spacer(1, 8))

    top_rows = [[f"{d['name']} ({d['donorId']})", d["bloodGroup"], d["donations"], d["units"], d["lastDate"]] for d in data.get("topDonors", [])]
    story.append(Paragraph("Top & Repeat Contributors", styles["section"]))
    story.append(_styled_table(
        ["Donor", "Blood Group", "Sessions", "Total Units", "Last Donation"],
        top_rows,
        [w * 0.36, w * 0.14, w * 0.14, w * 0.16, w * 0.20],
        styles,
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Collection Intake Ledger", styles["section"]))
    don_rows = [
        [d["donationId"], d["donorName"], d["date"], d["bloodGroup"], d["type"], d["quantity"], f"#{d['bloodBankId']}", d["status"]]
        for d in data.get("ledger", [])
    ]
    story.append(_styled_table(
        ["Donation ID", "Donor", "Date", "Blood", "Type", "Qty", "Bank", "Status"],
        don_rows,
        [w * 0.13, w * 0.22, w * 0.13, w * 0.09, w * 0.10, w * 0.07, w * 0.10, w * 0.16],
        styles,
        status_cols={7},
    ))


def _append_verification(story, data, styles, w):
    s = data["summary"]
    story.append(Paragraph("Serological Screening & Quality Control Audit Report", styles["section"]))
    story.append(_kpi_strip([
        ("Total Screened", s["totalVerified"], "Serological unit tests", "neutral"),
        ("Cleared (Passed)", s["passedCount"], "Approved for cold storage", "success"),
        ("Rejected (Failed)", s["failedCount"], "Quarantined for disposal", "danger" if s["failedCount"] > 0 else "neutral"),
        ("Clearance Yield", f"{s['passRate']}%", "Overall safety pass rate", "success"),
    ], styles, w))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Infectious Marker & Lab Officer Breakdown", styles["section"]))
    mk_rows = [[m["marker"], m["passed"], m["failed"]] for m in data.get("markerBreakdown", [])]
    story.append(_styled_table(
        ["Screening Marker", "Passed Units", "Failed / Reactive Units"],
        mk_rows,
        [w * 0.44, w * 0.28, w * 0.28],
        styles,
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Quality Verification Audit Ledger", styles["section"]))
    ver_rows = [
        [
            v["verificationId"],
            v["unitId"],
            v["date"],
            v["verifiedBy"],
            f"{v['hiv']} / {v['hepatitisB']} / {v['hepatitisC']} / {v['syphilis']}",
            v["overallResult"],
            v["notes"] or "-",
        ]
        for v in data.get("ledger", [])
    ]
    story.append(_styled_table(
        ["Verif ID", "Unit ID", "Date", "Verified By", "HIV / HBV / HCV / Syph", "Result", "Lab Notes"],
        ver_rows,
        [w * 0.11, w * 0.10, w * 0.11, w * 0.17, w * 0.21, w * 0.11, w * 0.19],
        styles,
        status_cols={5},
    ))


def _append_disposal(story, data, styles, w):
    s = data["summary"]
    story.append(Paragraph("Bio-Waste Disposal & Wastage Compliance Report", styles["section"]))
    story.append(_kpi_strip([
        ("Disposal Events", s["totalDisposals"], f"{s['totalUnitsDisposed']} units incinerated", "neutral"),
        ("Expired Units", s["expiredReasonCount"], "Shelf-life elapsed discards", "danger" if s["expiredReasonCount"] > 0 else "neutral"),
        ("Failed QC", s["failedVerificationCount"], "Serological rejection discards", "danger" if s["failedVerificationCount"] > 0 else "neutral"),
        ("Contaminated / Damaged", s["contaminatedCount"] + s["damagedCount"], "Cold-chain / handling loss", "neutral"),
    ], styles, w))
    story.append(Spacer(1, 8))

    rb = data.get("reasonBreakdown", [])
    if rb:
        story.append(_bar_chart(
            "Wastage Volume by Disposal Reason",
            [r["reason"] for r in rb],
            [[r["count"] for r in rb]],
            ["Disposal Events"],
            [DANGER_RED],
            w,
        ))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Bio-Waste Compliance Audit Ledger", styles["section"]))
    disp_rows = [
        [dp["disposalId"], dp["unitId"], f"{dp['bloodGroup']} ({dp['type']})", dp["quantity"], dp["disposalDate"], dp["reason"], dp["disposedBy"], dp["notes"] or "-"]
        for dp in data.get("ledger", [])
    ]
    story.append(_styled_table(
        ["Disp ID", "Unit ID", "Component", "Qty", "Date", "Reason", "Disposed By", "Compliance Notes"],
        disp_rows,
        [w * 0.10, w * 0.10, w * 0.12, w * 0.06, w * 0.11, w * 0.15, w * 0.15, w * 0.21],
        styles,
        status_cols={5},
    ))


SECTION_RENDERERS = {
    "overview": (ExecutiveOverviewStrategy, _append_overview),
    "inventory": (InventoryReportStrategy, _append_inventory),
    "requests": (RequestReportStrategy, _append_requests),
    "donations": (DonationReportStrategy, _append_donations),
    "donors": (DonationReportStrategy, _append_donations),
    "verification": (VerificationReportStrategy, _append_verification),
    "disposal": (DisposalReportStrategy, _append_disposal),
}


def generate_pdf_report(report_type="overview", filters=None, prepared_by="Authorized Administrator"):
    """Render a branded A4 PDF report bytes buffer for any single report or the full 6-part pack."""
    filters = filters or {}
    clean_type = (report_type or "overview").strip().lower()
    if clean_type not in REPORT_TITLES:
        clean_type = "overview"

    now = datetime.now()
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S")
    report_id = f"JV-{clean_type[:3].upper()}-{now.strftime('%Y%m%d-%H%M')}"
    title = REPORT_TITLES[clean_type]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=28 * mm,
        bottomMargin=19 * mm,
        title=f"Jeevithaya - {title}",
        author=prepared_by,
    )
    doc_width = A4[0] - 30 * mm
    styles = _build_styles()
    story = [
        _metadata_banner(filters, clean_type, prepared_by, generated_at, styles, doc_width),
        Spacer(1, 10),
    ]

    if clean_type == "all":
        order = ("overview", "inventory", "requests", "donations", "verification", "disposal")
        ctx = AnalyticsContext(ExecutiveOverviewStrategy())
        for idx, key in enumerate(order):
            strategy_cls, append_fn = SECTION_RENDERERS[key]
            ctx.set_strategy(strategy_cls())
            data = ctx.execute(filters=filters)
            if idx > 0:
                story.append(PageBreak())
            append_fn(story, data, styles, doc_width)
    else:
        strategy_cls, append_fn = SECTION_RENDERERS[clean_type]
        ctx = AnalyticsContext(strategy_cls())
        data = ctx.execute(filters=filters)
        append_fn(story, data, styles, doc_width)

    story.append(Spacer(1, 14))
    story.append(_sign_off_block(prepared_by, styles, doc_width))

    doc.build(
        story,
        canvasmaker=lambda *args, **kwargs: NumberedReportCanvas(
            *args, report_title=title, report_id=report_id, **kwargs
        ),
    )
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes, f"jeevithaya_{clean_type}_report_{now.strftime('%Y%m%d')}.pdf"

