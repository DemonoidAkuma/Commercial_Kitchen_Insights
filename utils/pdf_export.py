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
        color = colors.HexColor("#E8F5E9")

    elif good is False:
        color = colors.HexColor("#FDECEA")

    data = [[
        Paragraph(f"<b>{title}</b>", BODY),
        Paragraph(f"<b>{value}</b>", BODY)
    ]]

    if subtitle:
        data.append([
            Paragraph(
                f"<font size=8 color='grey'>{subtitle}</font>",
                BODY
            ),
            ""
        ])

    table = Table(
        data,
        colWidths=[60 * mm, 40 * mm]
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("BOX", (0, 0), (-1, -1), 1, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))

    return table


# =============================
# TABLE STYLING
# =============================

def styled_table(data):

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#F1F5F9")),
        ("FONTNAME", (0, 0), (-1, 0),
         "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [colors.white, colors.whitesmoke]
        ),
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
            elements.append(
                Paragraph(f"• {line}", BODY)
            )
            elements.append(
                Spacer(1, 4)
            )

    return elements
def performance_status(report_data):

    food_cost = report_data.get("food_cost", 0)
    target = report_data.get("food_target", 0)
    waste = report_data.get("waste_pct", 0)

    fc_variance = food_cost - target

    if fc_variance > 3 or waste > 2:
        return "Needs Attention"

    elif fc_variance > 1:
        return "Watch"

    return "Strong"

# =============================
# MAIN EXPORT
# =============================

def export_branded_report(
    report_data,
    reference_pdf_paths=None
):

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
    # HEADER WITH LOGOS
    # =============================

    cki_logo = "assets/cki_logo_primary.png"

    if os.path.exists(cki_logo):

        elements.append(
            Image(
                cki_logo,
                width=180,
                height=50
            )
        )

    logo_path = (
        f"assets/venues/"
        f"{report_data['venue_name'].replace(' ', '_')}.png"
    )

    header_data = []

    venue_title = Paragraph(
        f"<b>{report_data['venue_name']}</b>"
        f"<br/>{report_data['period_label']}",
        TITLE
    )

    if os.path.exists(logo_path):

        logo = Image(
            logo_path,
            width=40 * mm,
            height=20 * mm
        )

        header_data.append([
            logo,
            venue_title
        ])

    else:
        header_data.append([
            venue_title
        ])

    header_table = Table(header_data)

    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # =============================
    # EXECUTIVE SUMMARY
    # =============================

    status = performance_status(report_data)

    previous_revenue = (
        report_data.get("previous_revenue", 0)
        or 0
    )

    revenue_change = (
        report_data["revenue"]
        - previous_revenue
    )

    revenue_change_pct = (
        (revenue_change / previous_revenue) * 100
        if previous_revenue > 0
        else 0
    )

    revenue_pct = 0
    if previous_revenue > 0:
        revenue_pct = (
            revenue_change / previous_revenue
        ) * 100

    food_variance = (
        report_data.get("food_cost", 0)
        - report_data.get("food_target", 0)
    )

    if food_variance > 0:
        fc_text = (
            f"{abs(food_variance):.1f}pts "
            f"above target"
        )

    elif food_variance < 0:
        fc_text = (
            f"{abs(food_variance):.1f}pts "
            f"below target"
        )

    else:
        fc_text = "on target"

    summary = (
        f"Revenue "
        f"{'increased' if revenue_change >= 0 else 'decreased'} "
        f"{abs(revenue_pct):.1f}% vs previous comparable period. "
        f"Food cost finished {fc_text}."
    )
        
    elements.append(
        Paragraph(
            f"<b>Performance: {status}</b>",
            SUBTITLE
        )
    )

    elements.append(
        Paragraph(summary, BODY)
    )

    elements.append(
        Spacer(1, 14)
    )

    # =============================
    # FINANCIAL PERFORMANCE
    # =============================

    elements.append(
        Paragraph(
            "Financial Performance",
            SUBTITLE
        )
    )

    financial_kpis = [

        kpi_card(
            "Revenue",
            f"${report_data.get('revenue', 0):,.0f}",
            (
                f"{revenue_pct:+.1f}% vs prior"
                if previous_revenue
                else "No comparison"
            ),
            good=revenue_change >= 0
        ),

        kpi_card(
        "Revenue Variance",
        (
            f"${revenue_change:,.0f} "
            f"({revenue_change_pct:+.1f}%)"
        ),
        "vs previous comparable period",
        good=revenue_change >= 0
    ),

        kpi_card(
            "Purchases",
            f"${report_data.get('purchases', 0):,.0f}"
        ),

        kpi_card(
            "Purchase Variance",
            f"${report_data.get('purchase_variance', 0):,.0f}",
            "vs budget",
            good=(
                report_data.get(
                    "purchase_variance",
                    0
                ) <= 0
            )
        ),

        kpi_card(
            "Food Cost Variance",
            f"{food_variance:+.1f}%",
            "vs target",
            good=food_variance <= 0
        ),
    ]

    financial_grid = []
    row = []

    for i, kpi in enumerate(financial_kpis, start=1):

        row.append(kpi)

        if i % 2 == 0:
            financial_grid.append(row)
            row = []

    if row:
        financial_grid.append(row)

    elements.append(
        Table(financial_grid)
    )

    # =============================
    # OPERATIONAL KPIs
    # =============================

    elements.append(
        Paragraph(
            "Operational KPIs",
            SUBTITLE
        )
    )

    food_good = (
        report_data.get("food_cost", 0)
        <= report_data.get("food_target", 0)
    )

    waste_good = (
        report_data.get("waste_pct", 0)
        <= 2
    )

    ops_kpis = [

        kpi_card(
            "Food Cost %",
            f"{report_data.get('food_cost',0):.2f}%",
            (
                f"Target "
                f"{report_data.get('food_target',0):.1f}%"
            ),
            good=food_variance <= 0
        ),

        kpi_card(
            "Waste %",
            f"{report_data.get('waste_pct',0):.2f}%",
            good=waste_good
        ),

        kpi_card(
            "Waste $",
            f"${report_data.get('waste_total',0):,.0f}"
        ),

        kpi_card(
            "Closing Stock",
            f"${report_data.get('closing_stock',0):,.0f}"
        )
    ]

    ops_grid = []
    row = []

    for i, kpi in enumerate(ops_kpis, start=1):
        row.append(kpi)

        if i % 2 == 0:
            ops_grid.append(row)
            row = []

    if row:
        ops_grid.append(row)

    elements.append(Table(ops_grid))

    elements.append(Spacer(1, 12))

    # =============================
    # STOCK POSITION
    # =============================

    elements.append(
        Paragraph(
            "Stock Position",
            SUBTITLE
        )
    )

    stock_kpis = [[

        kpi_card(
            "Opening Stock",
            f"${report_data.get('opening_stock',0):,.0f}"
        ),

        kpi_card(
            "Closing Stock",
            f"${report_data.get('closing_stock',0):,.0f}"
        )
    ]]

    elements.append(Table(stock_kpis))

    elements.append(Spacer(1, 16))

    # =============================
    # REVENUE MIX
    # =============================

    steakhouse_pct = report_data.get(
        "steakhouse_pct",
        0
    )

    takeaway_pct = report_data.get(
        "takeaway_pct",
        0
    )

    inhouse_pct = report_data.get(
        "inhouse_pct",
        0
    )

    if steakhouse_pct > 0 or takeaway_pct > 0:

        elements.append(
            Paragraph(
                "Revenue Mix",
                SUBTITLE
            )
        )

        mix_data = [
            ["Segment", "% of Revenue"],
            ["In-House", f"{inhouse_pct:.1f}%"]
        ]

        if steakhouse_pct > 0:
            mix_data.append([
                "Steakhouse",
                f"{steakhouse_pct:.1f}%"
            ])

        if takeaway_pct > 0:
            mix_data.append([
                "Takeaway",
                f"{takeaway_pct:.1f}%"
            ])

        elements.append(
            styled_table(mix_data)
        )

        elements.append(
            Spacer(1, 12)
        )

    # =============================
    # COMMENTARY
    # =============================

    elements.append(
        Paragraph(
            "Executive Commentary",
            SUBTITLE
        )
    )

    elements.extend(
        format_commentary(
            report_data.get(
                "commentary",
                ""
            )
        )
    )

    elements.append(
        Spacer(1, 12)
    )

    # =============================
    # PROBLEM CHILDREN
    # =============================

    problem_items = []

    for row in report_data.get(
        "item_performance",
        []
    )[1:]:

        try:
            gp_pct = float(
                str(row[3]).replace("%", "")
            )

            revenue = float(
                str(row[2])
                .replace("$", "")
                .replace(",", "")
            )

            if gp_pct <= 5 and revenue > 300:
                problem_items.append(
                    [row[0], row[3], row[2]]
                )

        except:
            pass

    if problem_items:

        elements.append(
            Paragraph(
                "Menu Attention Required",
                SUBTITLE
            )
        )

        table_data = [
            ["Item", "GP %", "Revenue"]
        ] + problem_items

        elements.append(
            styled_table(table_data)
        )

        elements.append(
            Spacer(1, 14)
        )
    # =============================
    # WASTE TABLE
    # =============================

    elements.append(
        Paragraph(
            "Top Wasted Items",
            SUBTITLE
        )
    )

    elements.append(
        Spacer(1, 8)
    )

    waste_data = [
        [
            "Item",
            "Reason",
            "Qty",
            "Total ($)"
        ]
    ]

    for row in report_data.get(
        "waste_table",
        []
    ):

        if len(row) >= 4:
            waste_data.append(row)

    elements.append(
        styled_table(waste_data)
    )

    elements.append(
        Spacer(1, 20)
    )

    # =============================
    # ITEM PERFORMANCE
    # =============================

    elements.append(
        Paragraph(
            "Item Performance",
            SUBTITLE
        )
    )

    elements.append(
        Spacer(1, 8)
    )

    elements.append(
        styled_table(
            report_data.get(
                "item_performance",
                [["No Data"]]
            )
        )
    )

    # =============================
    # =============================
    # FOOTER DISCLAIMER
    # =============================

    elements.append(Spacer(1, 25))

    if str(report_data.get("report_type")) == "14":

        disclaimer = (
            "14-day reports do not factor stock "
            "adjustments, discount-backed COGS "
            "or staff meal COGS."
        )

    else:

        disclaimer = (
            "28-day reports include stock "
            "adjustments to calculate true COGS. "
            "Discount-backed COGS and staff "
            "meal COGS are not currently factored."
        )

    elements.append(
        Paragraph(
    f"<font color='grey'><i>{disclaimer}</i></font>",
    BODY
)
    )

    elements.append(
        Spacer(1, 6)
    )

    elements.append(
        Paragraph(
            "Generated by Commercial Kitchen Insights",
            styles["Italic"]
        )
    )

    # =============================
    # BUILD
    # =============================

    doc.build(elements)

    buffer.seek(0)

    return buffer