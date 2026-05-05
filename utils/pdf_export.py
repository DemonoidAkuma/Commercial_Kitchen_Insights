from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from io import BytesIO
import os

# =============================
# STYLES
# =============================

styles = getSampleStyleSheet()

TITLE = styles["Heading1"]
SUBTITLE = styles["Heading2"]
BODY = styles["BodyText"]

TITLE.fontSize = 20
SUBTITLE.fontSize = 13
BODY.fontSize = 9

# =============================
# KPI CARD BUILDER
# =============================

def kpi_card(title, value, subtitle=None, good=None):
    color = colors.whitesmoke

    if good is True:
        color = colors.HexColor("#E8F5E9")  # green
    elif good is False:
        color = colors.HexColor("#FDECEA")  # red

    data = [[
        Paragraph(f"<b>{title}</b>", BODY),
        Paragraph(f"<b>{value}</b>", BODY)
    ]]

    if subtitle:
        data.append([
            Paragraph(f"<font size=8 color='grey'>{subtitle}</font>", BODY),
            ""
        ])

    table = Table(data, colWidths=[60*mm, 40*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("BOX", (0, 0), (-1, -1), 1, colors.lightgrey),
        ("INNERPADDING", (0, 0), (-1, -1), 6),
    ]))

    return table


# =============================
# TABLE STYLING
# =============================

def styled_table(data):
    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    return table


# =============================
# COMMENTARY FORMAT
# =============================

def format_commentary(text):
    elements = []

    for line in text.split("."):
        line = line.strip()
        if line:
            elements.append(Paragraph(f"• {line}", BODY))
            elements.append(Spacer(1, 4))

    return elements


# =============================
# MAIN EXPORT
# =============================

def export_branded_report(report_data, reference_pdf_paths=None):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=25,
        leftMargin=25,
        topMargin=30,
        bottomMargin=20
    )

    elements = []

    # =============================
    # HEADER WITH LOGO
    # =============================

    logo_path = f"assets/venues/{report_data['venue_name'].replace(' ', '_')}.png"

    header_data = []

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=40*mm, height=20*mm)
        header_data.append([logo, Paragraph(f"<b>{report_data['venue_name']}</b><br/>{report_data['period_label']}", TITLE)])
    else:
        header_data.append([Paragraph(f"<b>{report_data['venue_name']}</b><br/>{report_data['period_label']}", TITLE)])

    header_table = Table(header_data)
    elements.append(header_table)

    elements.append(Spacer(1, 15))

    # =============================
    # KPI SECTION
    # =============================

    elements.append(Paragraph("Key Metrics", SUBTITLE))
    elements.append(Spacer(1, 10))

    kpis = [
        kpi_card("Revenue", report_data["revenue"]),
        kpi_card("Purchases", report_data["purchases"]),
        kpi_card("Budget", report_data["revenue_target"]),
        kpi_card("Variance", report_data["revenue_var"]),

        kpi_card("Food Cost %", report_data["food_cost"], f"Target {report_data['food_target']}"),
        kpi_card("Waste %", report_data["waste_pct"], f"Target {report_data['waste_target']}"),
        kpi_card("Closing Stock", report_data["stock"]),
        kpi_card("Waste $", report_data["waste_total"]),
    ]

    # Arrange in grid
    kpi_grid = []
    row = []

    for i, kpi in enumerate(kpis, start=1):
        row.append(kpi)
        if i % 2 == 0:
            kpi_grid.append(row)
            row = []

    elements.append(Table(kpi_grid, hAlign="LEFT"))
    elements.append(Spacer(1, 20))

    # =============================
    # COMMENTARY
    # =============================

    elements.append(Paragraph("Executive Commentary", SUBTITLE))
    elements.append(Spacer(1, 8))
    elements.extend(format_commentary(report_data["commentary"]))
    elements.append(Spacer(1, 16))

    # =============================
    # WASTE TABLE
    # =============================

    elements.append(Paragraph("Top Wasted Items", SUBTITLE))
    elements.append(Spacer(1, 8))

    waste_data = [["Item", "Reason", "Qty", "Total ($)"]]

    for row in report_data["waste_table"]:
        if len(row) >= 4:
            waste_data.append(row)

    elements.append(styled_table(waste_data))
    elements.append(Spacer(1, 20))

    # =============================
    # ITEM PERFORMANCE
    # =============================

    elements.append(Paragraph("Item Performance", SUBTITLE))
    elements.append(Spacer(1, 8))

    elements.append(styled_table(report_data["item_performance"]))

    # =============================
    # FOOTER
    # =============================

    elements.append(Spacer(1, 25))
    elements.append(Paragraph(
        "Generated by Commercial Kitchen Insights",
        styles["Italic"]
    ))

    # =============================
    # BUILD
    # =============================

    doc.build(elements)

    buffer.seek(0)

    return buffer