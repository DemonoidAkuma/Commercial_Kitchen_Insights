import streamlit as st
from utils.ui import apply_global_style, sidebar_branding

st.set_page_config(
    page_title="Commercial Kitchen Insights",
    page_icon="assets/cki_icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_global_style()
sidebar_branding()
import os
import pandas as pd
from collections import defaultdict

if st.session_state.get("role") != "admin":
    st.error("Admin access only.")
    st.stop()

st.markdown("""
<style>

/* ---------- SIDEBAR ---------- */
section[data-testid="stSidebar"] {
    background-color: #111111;
    border-right: 1px solid #222;
}

/* Default sidebar text stays light */
section[data-testid="stSidebar"] * {
    color: #EAEAEA !important;
}

/* ---------- SELECTBOX TEXT (black inside white boxes) ---------- */
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] * {
    color: black !important;
}

/* Dropdown menu items */
div[data-baseweb="menu"] * {
    color: black !important;
}

/* ---------- EXPANDER HEADER ---------- */
/* Keep venue names white */
section[data-testid="stSidebar"] .streamlit-expanderHeader {
    color: #EAEAEA !important;
    font-weight: 600;
}

/* ---------- BUTTONS ---------- */
.stButton > button {
    background-color: #202020;
    color: white;
    border-radius: 12px;
    border: 1px solid #333;
    font-weight: 600;
    width: 100%;
}

.stButton > button:hover {
    border: 1px solid #666;
    background-color: #2B2B2B;
    color: white;
}

</style>
""", unsafe_allow_html=True)           

from database import SalesLine, WasteLine
from database import Session, Period
from parser import (
    extract_revenue,
    extract_cogs,
    extract_stock_value,
    extract_food_cost_percent,
    extract_waste_lines,
)
from kpi_engine import calculate_waste_percent, risk_rating


from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FOLDER = PROJECT_ROOT / "data"


VENUE_CONFIG = {
    "The_Amberton": {"target": 30.0, "type": "HOSPITALITY"},
    "Hybla_Tavern": {"target": 30.0, "type": "HOSPITALITY"},
    "CYO_Village_Pub": {"target": 30.0, "type": "HOSPITALITY"},
    "Paperbark_Burger_Co": {"target": 32.0, "type": "HOSPITALITY"},
    "Tillys_Garden": {"target": 25.0, "type": "HOSPITALITY"},
    "The_Byford": {"target": 30.5, "type": "HOSPITALITY"},
    "The_Wellard": {"target": 31.0, "type": "HOSPITALITY"},
    "Melaleuka_Farm_Merchants": {"target": 75.0, "type": "RETAIL"},
}

WASTE_TARGET = 1.0

if not os.path.exists(DATA_FOLDER):
    st.error("Data folder not found. Please create a 'data' folder.")
    st.stop()

venues = os.listdir(DATA_FOLDER)

if not venues:
    st.warning("No venues found in data folder.")
    st.stop()

# -----------------------------
# Processing Function
# -----------------------------
def process_period(venue, period_path, report_type):

    session = Session()
    files = os.listdir(period_path)
    period_name = os.path.basename(period_path)
    financial_year = os.path.basename(
        os.path.dirname(
            os.path.dirname(period_path)
        )
    )

    revenue_file = next((f for f in files if "Revenue" in f and f.endswith(".pdf")), None)
    purchases_file = next((f for f in files if "Purchases" in f and f.endswith(".pdf")), None)
    stock_file = next((f for f in files if "Stock" in f and f.endswith(".pdf")), None)
    waste_file = next((f for f in files if "Wastage Record" in f and f.endswith(".pdf")), None)

    revenue = 0
    cogs = 0
    closing_stock = 0
    food_cost_percent = 0
    waste = 0
    waste_percent = 0
    waste_lines = []

# -----------------------------
# Extract Waste Lines (Structured)
# -----------------------------
    if waste_file:
       waste_lines = extract_waste_lines(
        os.path.join(period_path, waste_file)
    )

    waste = sum(line["total"] for line in waste_lines)


    if waste_lines:
       df_waste = pd.DataFrame(waste_lines)

    # -----------------------------
    # Get Targets FIRST (FIXED)
    # -----------------------------
    venue_config = VENUE_CONFIG.get(
        venue, {"target": 30.0, "type": "HOSPITALITY"}
    )
    food_target = venue_config["target"]
    waste_target = WASTE_TARGET

    # -----------------------------
    # 14 DAY
    # -----------------------------

    if report_type == "14":

     if revenue_file:
         revenue = extract_revenue(
             os.path.join(period_path, revenue_file)
         )

     if purchases_file:
         purchases = extract_cogs(
             os.path.join(period_path, purchases_file)
         )
         cogs = purchases

     if purchases_file:
         food_cost_percent = extract_food_cost_percent(
             os.path.join(period_path, purchases_file)
         )

    # -----------------------------
    # 28 DAY
    # -----------------------------
    elif report_type == "28":

        if not revenue_file or not purchases_file or not stock_file:
            st.error("Missing Revenue, Purchases or Stock file.")
            session.close()
            return

        revenue = extract_revenue(os.path.join(period_path, revenue_file))
        purchases = extract_cogs(os.path.join(period_path, purchases_file))
        closing_stock = extract_stock_value(os.path.join(period_path, stock_file))

        previous_period = (
            session.query(Period)
            .filter(
                Period.venue == venue,
                Period.report_type == "28",
                Period.period < period_name,
            )
            .order_by(Period.period.desc())
            .first()
        )

        if previous_period:
            opening_stock = previous_period.closing_stock
        else:
            opening_stock = closing_stock

        stock_variance = opening_stock - closing_stock
        adjusted_cogs = purchases + stock_variance

        food_cost_percent = (adjusted_cogs / revenue) * 100 if revenue else 0
        cogs = adjusted_cogs

        
        # -------------------------------------------------
    # SAVE / UPDATE PERIOD
    # -------------------------------------------------
    # -----------------------------
    # Final Waste Calculations
    # -----------------------------
    waste_percent = calculate_waste_percent(waste, revenue)

    # -----------------------------
    # Variances & Risk
    # -----------------------------
    food_variance = food_cost_percent - food_target
    waste_variance = waste_percent - waste_target

    rating = risk_rating(
        food_cost_percent,
        waste_percent,
        food_target,
        waste_target,
    )
    existing = session.query(Period).filter_by(
        venue=venue,
        financial_year=selected_fy,
        period=period_name,
        report_type=report_type,
    ).first()

    if existing:
        existing.revenue = revenue
        existing.cogs = cogs
        existing.financial_year = financial_year
        existing.food_cost_percent = food_cost_percent
        existing.waste_total = waste
        existing.waste_percent = waste_percent
        existing.food_cost_target = food_target
        existing.waste_target = waste_target
        existing.food_cost_variance = food_variance
        existing.waste_variance = waste_variance
        existing.risk_rating = rating
        existing.closing_stock = closing_stock
        existing.purchases = purchases
        existing.cogs = cogs

        period_record = existing

    else:
        new_period = Period(
            venue=venue,   # ✅ SINGLE STRING
            financial_year=selected_fy,
            period=period_name,
            report_type=report_type,
            revenue=revenue,
            cogs=cogs,
            food_cost_percent=food_cost_percent,
            waste_total=waste,
            waste_percent=waste_percent,
            food_cost_target=food_target,
            waste_target=waste_target,
            food_cost_variance=food_variance,
            waste_variance=waste_variance,
            risk_rating=rating,
            closing_stock=closing_stock,
            purchases = purchases
        )

        session.add(new_period)
        session.commit()  # commit so ID is generated
        period_record = new_period

    session.commit()  # commit updates if existing
        # -----------------------------------
    # SAVE STRUCTURED WASTE LINES
    # -----------------------------------

    # Delete existing waste lines for this period
    session.query(WasteLine).filter(
        WasteLine.period_id == period_record.id
    ).delete()

    # Insert fresh waste lines
    for line in waste_lines:
        new_waste = WasteLine(
            period_id=period_record.id,
            item=line["item"],
            qty=float(line["qty"]) if line["qty"] else 0,
            total=float(line["total"]),
            reason=line["reason"],
        )
        session.add(new_waste)

    session.commit()


        # -------------------------------------------------
    # PROCESS SALES EXCEL
    # -------------------------------------------------

    excel_file = next(
        (f for f in os.listdir(period_path)
         if f.lower().endswith((".xlsx", ".xls"))),
        None
    )

    if excel_file:


        df = pd.read_excel(
            os.path.join(period_path, excel_file),
            header=5
        )

        df.columns = df.columns.str.strip()
        df["Description"] = df["Description"].str.strip().str.upper()

        # Remove blank descriptions
        df = df.dropna(subset=["Description"])
        df = df[df["Description"] != ""]

        # Remove modifier lines
        df["Description"] = df["Description"].astype(str).str.strip()

        # Remove existing lines for this period
        session.query(SalesLine).filter(
            SalesLine.period_id == period_record.id
        ).delete()

        inserted = 0

        for _, row in df.iterrows():

            qty = pd.to_numeric(row["Quantity Sold"], errors="coerce")

            if pd.isna(qty) or qty <= 0:
                continue

            # -----------------------------
            # Extract revenue (INC GST)
            # -----------------------------
            revenue_inc_gst = pd.to_numeric(
                row["Discounted Amount"], errors="coerce"
            )

            if pd.isna(revenue_inc_gst) or revenue_inc_gst <= 0:
                continue

            # Remove GST (Australia 10%)
            revenue_ex_gst = revenue_inc_gst / 1.1

            # -----------------------------
            # Gross Profit %
            # -----------------------------
            gp_raw = pd.to_numeric(
                row["Theoretical Gross Profit %"],
                errors="coerce"
            )

            if pd.isna(gp_raw):
                gp_value = None
            else:
                gp_value = gp_raw * 100 if gp_raw <= 1 else gp_raw

            # -----------------------------
            # Save Sales Line
            # -----------------------------
            new_line = SalesLine(
                period_id=period_record.id,
                item_name=str(row["Description"]).strip(),
                qty=float(qty),
                revenue=round(float(revenue_ex_gst), 2),
                gross_profit_percent=float(gp_value) if gp_value is not None else None,
            )

            session.add(new_line)
            inserted += 1

        session.commit()


    else:
        st.warning("No Excel file found in this period folder.")
# -----------------------------
# Sidebar
# -----------------------------
# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header("Process New Period")

# Detect Financial Years
fy_set = set()

for venue in os.listdir(DATA_FOLDER):

    venue_path = os.path.join(DATA_FOLDER, venue)

    if not os.path.isdir(venue_path):
        continue

    try:
        folders = os.listdir(venue_path)
    except Exception:
        continue

    for folder in folders:

        folder_path = os.path.join(
            venue_path,
            folder
        )

        if (
            os.path.isdir(folder_path)
            and folder.upper().startswith("FY")
        ):
            fy_set.add(folder.upper())

# -----------------------------
# Available FYs
# -----------------------------
AVAILABLE_FYS = sorted(
    list(fy_set),
    reverse=True
)

# Safety check
if not AVAILABLE_FYS:
    st.error(
        "No FY folders found.\n\n"
        "Expected structure:\n"
        "data/Venue/FY26/14/01/"
    )
    st.stop()

# -----------------------------
# Sidebar Controls
# -----------------------------
selected_fy = st.sidebar.selectbox(
    "Financial Year",
    AVAILABLE_FYS,
    index=0
)

report_type = st.sidebar.selectbox(
    "Report Type",
    ["14", "28"],
    index=0
)

# -----------------------------
# Reprocess All
# -----------------------------
if st.sidebar.button("🚀 Reprocess ALL Venues"):

    processed_count = 0

    for venue in venues:

        venue_path = os.path.join(
            DATA_FOLDER,
            venue
        )

        report_folder = os.path.join(
            venue_path,
            selected_fy,
            report_type
        )

        if not os.path.isdir(report_folder):
            continue

        periods = sorted(
            os.listdir(report_folder),
            reverse=True
        )

        for period in periods:

            period_path = os.path.join(
                report_folder,
                period
            )

            if os.path.isdir(period_path):
                process_period(
                    venue,
                    period_path,
                    report_type
                )
                processed_count += 1

    st.success(
        f"✅ Reprocessed {processed_count} periods successfully."
    )



# -----------------------------
# Sidebar Processing Panel
# -----------------------------

session = Session()

for venue in sorted(venues):

    venue_path = os.path.join(DATA_FOLDER, venue)

    if not os.path.isdir(venue_path):
        continue

    report_folder = os.path.join(
        venue_path,
        selected_fy,
        report_type
    )

    if not os.path.exists(report_folder):
        continue

    periods = sorted(os.listdir(report_folder), reverse=True)

    with st.sidebar.expander(f"📍 {venue}", expanded=False):

        # -----------------------------
        # Batch Process Missing
        # -----------------------------
        if st.button(f"⚙ Process Missing Periods", key=f"process_missing_{venue}"):

            periods_to_process = []

            for period in periods:

                period_path = os.path.join(report_folder, period)

                existing = session.query(Period).filter_by(
                    venue=venue,
                    financial_year=selected_fy,
                    period=period,
                    report_type=report_type
                ).first()

                if not existing:
                    periods_to_process.append((period, period_path))
                total = len(periods_to_process)

                if total == 0:
                    st.info("No missing periods to process.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                for i, (period, period_path) in enumerate(periods_to_process, start=1):

                    status_text.text(f"Processing {venue} — {period} ({i}/{total})")

                    process_period(venue, period_path, report_type)

                    progress_bar.progress(i / total)
                status_text.text(f"✅ Finished processing {total} periods.")
                    


        # -----------------------------
        # Period Status List
        # -----------------------------
        for period in periods:

            period_path = os.path.join(report_folder, period)

            existing = session.query(Period).filter_by(
                venue=venue,
                financial_year=selected_fy,
                period=period,
                report_type=report_type
            ).first()

            processed = existing is not None

            files = os.listdir(period_path)

            has_revenue = any("Revenue" in f for f in files)
            has_purchases = any("Purchases" in f for f in files)

            if report_type == "28":
                has_stock = any("Stock" in f for f in files)
                missing_files = not (has_revenue and has_purchases and has_stock)
            else:
                missing_files = not (has_revenue and has_purchases)

            if missing_files:
                label = f"❌ {period}"
            elif processed:
                label = f"✅ {period}"
            else:
                label = f"🟡 {period}"

            if st.button(label, key=f"{venue}_{period}"):
                process_period(venue, period_path, report_type)

session.close()
# -----------------------------
# Executive Overview
# -----------------------------
st.header("Executive Overview")

session = Session()


periods = (
    session.query(Period)
    .order_by(Period.venue, Period.period)
    .all()
)

if not periods:
    st.info("No processed data yet. Click 'Process' in sidebar.")
else:

    from collections import defaultdict
    import pandas as pd

    from collections import defaultdict

# --------------------------------
# Group: Venue → FY → Period
# --------------------------------
# --------------------------------
# Group: Venue → FY → Report Type → Period
# --------------------------------
venue_history = defaultdict(
    lambda: defaultdict(
        lambda: defaultdict(list)
    )
)

for p in periods:
    fy = p.financial_year or "Unknown FY"

    venue_history[p.venue][fy][
        p.report_type
    ].append(p)

for venue, fy_groups in venue_history.items():

    st.markdown("---")
    st.subheader(f"📍 {venue}")

    # -----------------------------
    # Financial Year
    # -----------------------------
    for fy in sorted(
        fy_groups.keys(),
        reverse=True
    ):

        with st.expander(
            f"📁 {fy}",
            expanded=(fy == selected_fy)
        ):

            # -----------------------------
            # Report Type Folder
            # -----------------------------
            for rpt_type in ["14", "28"]:

                if rpt_type not in fy_groups[fy]:
                    continue

                with st.expander(
                    f"📂 {rpt_type}-Day Reports",
                    expanded=False
                ):

                    venue_periods = sorted(
                        fy_groups[fy][rpt_type],
                        key=lambda x: x.period,
                        reverse=True
                    )

                    previous = None

                    for p in venue_periods:

                        with st.expander(
                            f"📅 Period {p.period}",
                            expanded=False
                        ):

                            venue_config = VENUE_CONFIG.get(
                                venue,
                                {"target": 30.0}
                            )

                            target_percent = venue_config["target"]

                            purchase_budget = (
                                p.revenue *
                                (target_percent / 100)
                            )

                            purchase_variance = (
                                purchase_budget - p.cogs
                            )

                            food_variance_percent = (
                                p.food_cost_percent
                                - target_percent
                            )

                            waste_variance_percent = (
                                p.waste_percent
                                - WASTE_TARGET
                            )

                            food_arrow = ""
                            waste_arrow = ""

                            if previous:

                                if p.food_cost_percent > previous.food_cost_percent:
                                    food_arrow = "↑"
                                elif p.food_cost_percent < previous.food_cost_percent:
                                    food_arrow = "↓"

                                if p.waste_percent > previous.waste_percent:
                                    waste_arrow = "↑"
                                elif p.waste_percent < previous.waste_percent:
                                    waste_arrow = "↓"

                            # =============================
                            # KPI SECTION
                            # =============================

                            col1, col2, col3, col4 = st.columns(4)

                            col1.metric("Revenue", f"${p.revenue:,.0f}")
                            col2.metric("Purchases", f"${p.cogs:,.0f}")
                            col3.metric("Budget $", f"${purchase_budget:,.0f}")
                            col4.metric(
                                "Variance $",
                                f"${purchase_variance:,.0f}",
                            )

                            col5, col6, col7, col8 = st.columns(4)

                            col5.metric(
                                f"Food Cost % (Target {target_percent:.1f}%)",
                                f"{p.food_cost_percent:.2f}% {food_arrow}",
                                delta=f"{food_variance_percent:+.2f}% vs Target",
                                delta_color="inverse",
                            )

                            col6.metric(
                                f"Waste % (Target {WASTE_TARGET:.1f}%)",
                                f"{p.waste_percent:.2f}% {waste_arrow}",
                                delta=f"{waste_variance_percent:+.2f}% vs Target",
                                delta_color="inverse",
                            )

                            col7.metric(
                                "Closing Stock",
                                f"${p.closing_stock:,.0f}"
                            )

                            col8.metric(
                                "Waste $",
                                f"${p.waste_total:,.0f}"
                            )

                            previous = p
                                                # =============================
                    # EXECUTIVE COMMENTARY
                    # =============================

                    commentary = []

                    # ---- Food Cost Commentary ----
                    if food_variance_percent < -1:
                        commentary.append(
                            "Food cost performing strongly under target."
                        )
                    elif food_variance_percent < 0:
                        commentary.append(
                            "Food cost slightly under target."
                        )
                    elif food_variance_percent <= 1:
                        commentary.append(
                            "Food cost slightly above target — monitor closely."
                        )
                    else:
                        commentary.append(
                            "Food cost materially above target — corrective action recommended."
                        )

                    # ---- Waste Driver Commentary ----
                    waste_records = (
                        session.query(WasteLine)
                        .filter(WasteLine.period_id == p.id)
                        .all()
                    )

                    if waste_records:

                        df_waste = pd.DataFrame([{
                            "item": w.item,
                            "reason": w.reason,
                            "total": w.total
                        } for w in waste_records])

                        # Top Waste Reason
                        reason_summary = (
                            df_waste.groupby(
                                "reason",
                                as_index=False
                            )
                            .agg({"total": "sum"})
                            .sort_values(
                                "total",
                                ascending=False
                            )
                        )

                        largest_reason = reason_summary.iloc[0]["reason"]
                        largest_value = reason_summary.iloc[0]["total"]

                        commentary.append(
                            f"Primary waste driver: "
                            f"{largest_reason} "
                            f"(${largest_value:,.0f})."
                        )

                        # Top Wasted Item
                        item_summary = (
                            df_waste.groupby(
                                "item",
                                as_index=False
                            )
                            .agg({"total": "sum"})
                            .sort_values(
                                "total",
                                ascending=False
                            )
                        )

                        top_item = item_summary.iloc[0]

                        commentary.append(
                            f"Highest wasted product: "
                            f"{top_item['item']} "
                            f"(${top_item['total']:,.0f})."
                        )

                    else:
                        commentary.append(
                            "No structured waste recorded this period."
                        )

                    # ---- Period Comparison ----
                    if previous:

                        if (
                            p.food_cost_percent
                            < previous.food_cost_percent
                        ):
                            commentary.append(
                                "Food cost improving vs prior period."
                            )
                        elif (
                            p.food_cost_percent
                            > previous.food_cost_percent
                        ):
                            commentary.append(
                                "Food cost deteriorating vs prior period."
                            )

                        if (
                            p.waste_percent
                            < previous.waste_percent
                        ):
                            commentary.append(
                                "Waste improving vs prior period."
                            )
                        elif (
                            p.waste_percent
                            > previous.waste_percent
                        ):
                            commentary.append(
                                "Waste increasing vs prior period."
                            )

                    st.markdown(
                        "### 🧠 Executive Commentary"
                    )

                    for line in commentary:
                        st.markdown(f"- {line}")

                    
                # =============================
                # ITEM PERFORMANCE
                # =============================

                    with st.expander("### 📊 Item Performance", expanded=True):

                     sales = (
                         session.query(SalesLine)
                         .filter(SalesLine.period_id == p.id)
                         .all()
                     )

                     if not sales:
                         st.info("No item-level sales data available.")
                     else:

                         df_raw = pd.DataFrame([{
                             "item": s.item_name,
                             "qty": s.qty,
                             "revenue": s.revenue,
                             "gp_pct": s.gross_profit_percent
                         } for s in sales])

                         df_raw = df_raw[df_raw["qty"] > 0]

                         if not df_raw.empty:

                         # Weighted GP calculation
                             df_raw["gp_dollars"] = df_raw["revenue"] * (df_raw["gp_pct"] / 100)

                             df = (
                                 df_raw
                                 .groupby("item", as_index=False)
                                 .agg({
                                     "qty": "sum",
                                     "revenue": "sum",
                                     "gp_dollars": "sum"
                                 })
                             )

                             df["gp_pct"] = (df["gp_dollars"] / df["revenue"]) * 100
                             df["gp_pct"] = df["gp_pct"].round(1)
                             df["gp_dollars"] = df["gp_dollars"].round(2)

                             if not df.empty:

                                 colA, colB = st.columns(2)

                                 with colA:
                                     st.markdown("**Top Sellers by Revenue**")
                                     for _, row in df.sort_values("revenue", ascending=False).head(5).iterrows():
                                         st.write(f"{row['item']} — ${row['revenue']:,.0f}")

                                     st.markdown("**Top Sellers by Volume**")
                                     for _, row in df.sort_values("qty", ascending=False).head(5).iterrows():
                                         st.write(f"{row['item']} ({int(row['qty'])})")

                                 with colB:
                                     st.markdown("**Top Profit Generators**")
                                     for _, row in df.sort_values("gp_dollars", ascending=False).head(5).iterrows():
                                         st.write(
                                             f"{row['item']} — ${row['gp_dollars']:,.0f} "
                                             f"({row['gp_pct']:.1f}% | {int(row['qty'])} sold)"
                                         )

                                     st.markdown("**Lowest Sellers by Volume**")
                                     for _, row in df.sort_values("qty").head(5).iterrows():
                                         st.write(f"{row['item']} ({int(row['qty'])})")

                             # Revenue concentration
                                 top_item = df.sort_values("revenue", ascending=False).iloc[0]
                                 if p.revenue > 0:
                                     contribution = (top_item["revenue"] / p.revenue) * 100
                                 else:
                                     contribution = 0

                                 st.markdown(
                                     f"🔎 **{top_item['item']} contributes {contribution:.1f}% of total revenue.**"
                                 )

                                 if contribution > 15:
                                     st.warning("High revenue concentration risk detected.")

                             # =============================
                             # MENU PERFORMANCE SUMMARY
                             # =============================

                                 with st.expander("### 📊 Menu Performance Summary", expanded=True):

                                     avg_margin = df["gp_pct"].mean()
                                     avg_qty = df["qty"].mean()

                                     risk_items = df[
                                         (df["qty"] > avg_qty) &
                                         (df["gp_pct"] < avg_margin)
                                     ].sort_values("qty", ascending=False)

                                     if not risk_items.empty:
                                         st.markdown("#### ⚠ High Volume, Low Margin (Review Pricing)")
                                         for _, row in risk_items.head(5).iterrows():
                                             st.write(
                                                 f"{row['item']} — {row['qty']} sold | {row['gp_pct']:.1f}% GP"
                                            )

                                     low_volume = df[df["qty"] < avg_qty].sort_values("qty")

                                     if not low_volume.empty:
                                         st.markdown("#### 💤 Low Volume Items")
                                         for _, row in low_volume.head(5).iterrows():
                                             st.write(
                                                 f"{row['item']} — {row['qty']} sold"
                                             )


session.close()