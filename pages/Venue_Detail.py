import streamlit as st
import os
import pandas as pd
import datetime
import plotly.express as px
import base64
from utils.pdf_export import export_branded_report
SPECIAL_REVENUE_VENUES = ["CYO", "Paperbark"]

def show_pdf_viewer(pdf_path):

    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")

    pdf_display = f"""
        <iframe 
            src="data:application/pdf;base64,{base64_pdf}" 
            width="100%" 
            height="700px" 
            type="application/pdf">
        </iframe>
    """

    st.markdown(pdf_display, unsafe_allow_html=True)
from database import Session, Period, WasteLine, SalesLine
from kpi_engine import risk_rating
from utils.pdf_export import export_branded_report
DATA_FOLDER = "data"

# ============================= # PAGE SETUP # =============================
st.set_page_config(page_title="Venue Detail", layout="wide")

query_params = st.query_params
selected_venue = query_params.get("venue")

if isinstance(selected_venue, list):
    selected_venue = selected_venue[0]

if not selected_venue:
    st.warning("No venue selected.")
    st.stop()

venue_name = selected_venue
st.title(venue_name.replace("_", " "))

# ============================= # CONFIG # =============================
VENUE_CONFIG = {
    "The_Amberton": {"target": 30.0},
    "Hybla_Tavern": {"target": 30.0},
    "CYO_Village_Pub": {"target": 30.0},
    "Paperbark_Burger_Co": {"target": 32.0},
    "Tillys_Garden": {"target": 25.0},
    "The_Byford": {"target": 30.5},
    "The_Wellard": {"target": 31.0},
    "Melaleuka_Farm_Merchants": {"target": 75.0},
}
WASTE_TARGET = 1.0

# ============================= # LOGO # =============================
logo_path = f"assets/venues/{venue_name}.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=240)
else:
    st.warning("Logo not found for this venue.")

# ============================= # YTD DASHBOARD # =============================
st.divider()
st.subheader("Venue Performance Dashboard")

session = Session()
periods = (
    session.query(Period)
    .filter(Period.venue == venue_name)
    .order_by(Period.period)
    .all()
)

reports_28 = [p for p in periods if p.report_type == "28"]

if reports_28:
    # ============================= # PERIOD RANGE SELECTOR # =============================
    st.markdown("### Reporting Period Range")
    period_labels = [p.period for p in reports_28]

    # ============================= # DETERMINE FINANCIAL YEAR START # =============================
    today = datetime.date.today()
    if today.month >= 7:
        fy_start_year = today.year
    else:
        fy_start_year = today.year - 1
    fy_start_date = datetime.date(fy_start_year, 7, 1)
    
    fy_start_index = 0
    for i, p in enumerate(reports_28):
        if hasattr(p, "start_date") and p.start_date and p.start_date >= fy_start_date:
            fy_start_index = i
            break

    # ============================= # INITIALIZE SESSION STATE # =============================
    if "start_index" not in st.session_state:
        st.session_state.start_index = fy_start_index
    if "end_index" not in st.session_state:
        st.session_state.end_index = len(period_labels) - 1

    # ============================= # QUICK RANGE BUTTONS # =============================
    quick_range = st.radio(
        "Quick Range", ["Financial YTD", "Last 6 Periods", "Last 3 Periods", "Custom"], horizontal=True
    )

    if quick_range == "Financial YTD":
        st.session_state.start_index = fy_start_index
        st.session_state.end_index = len(period_labels) - 1
    elif quick_range == "Last 6 Periods":
        st.session_state.start_index = max(len(period_labels) - 6, 0)
        st.session_state.end_index = len(period_labels) - 1
    elif quick_range == "Last 3 Periods":
        st.session_state.start_index = max(len(period_labels) - 3, 0)
        st.session_state.end_index = len(period_labels) - 1

    colA, colB = st.columns(2)
    start_period = colA.selectbox("Start Period", period_labels, index=st.session_state.start_index)
    end_period = colB.selectbox("End Period", period_labels, index=st.session_state.end_index)

    st.session_state.start_index = period_labels.index(start_period)
    st.session_state.end_index = period_labels.index(end_period)

    filtered_reports = [p for p in reports_28 if start_period <= p.period <= end_period]

    if not filtered_reports:
        st.warning("No data available for selected period range.")
        st.stop()

    # ============================= # KPI CALCULATIONS # =============================
    total_revenue = sum(p.revenue for p in filtered_reports)
    total_purchases = sum(p.cogs for p in filtered_reports)
    total_waste = sum(p.waste_total for p in filtered_reports)
    opening_stock = filtered_reports[0].closing_stock
    closing_stock = filtered_reports[-1].closing_stock
    true_food_cost = opening_stock + total_purchases - closing_stock
    food_cost_ytd = (true_food_cost / total_revenue) * 100 if total_revenue else 0
    waste_percent_ytd = (total_waste / total_revenue) * 100 if total_revenue else 0

    # Initialize variables for metrics
    takeaway_pct, steakhouse_pct, inhouse_pct = 0, 0, 0
    takeaway_revenue, steakhouse_revenue, inhouse_revenue = 0, 0, 0

    # ============================= # SALES MIX # =============================
    sales_mix = (
        session.query(SalesLine)
        .join(Period)
        .filter(Period.venue == venue_name)
        .filter(Period.report_type == "28")
        .filter(Period.period >= start_period)
        .filter(Period.period <= end_period)
        .all()
    )

    if sales_mix:
        df_mix = pd.DataFrame([{"item": s.item_name, "revenue": s.revenue} for s in sales_mix])
        total_mix_revenue = df_mix["revenue"].sum()

        if venue_name == "Paperbark_Burger_Co":
            takeaway_revenue = df_mix[df_mix["item"].str.startswith("T/A", na=False)]["revenue"].sum()
            inhouse_revenue = df_mix[~df_mix["item"].str.startswith("T/A", na=False)]["revenue"].sum()
            takeaway_pct = (takeaway_revenue / total_mix_revenue) * 100 if total_mix_revenue else 0
            inhouse_pct = (inhouse_revenue / total_mix_revenue) * 100 if total_mix_revenue else 0

        elif venue_name == "CYO_Village_Pub":
            steakhouse_revenue = df_mix[df_mix["item"].str.startswith("SH", na=False)]["revenue"].sum()
            inhouse_revenue = df_mix[~df_mix["item"].str.startswith("SH", na=False)]["revenue"].sum()
            steakhouse_pct = (steakhouse_revenue / total_mix_revenue) * 100 if total_mix_revenue else 0
            inhouse_pct = (inhouse_revenue / total_mix_revenue) * 100 if total_mix_revenue else 0

    # KPI Metric Display
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Revenue", f"${total_revenue:,.0f}")
    col2.metric("Purchases", f"${total_purchases:,.0f}")
    col3.metric("Food Cost %", f"{food_cost_ytd:.2f}%")
    col4.metric("Waste %", f"{waste_percent_ytd:.2f}%")

    if venue_name == "Paperbark_Burger_Co":
        col5.metric("Takeaway %", f"{takeaway_pct:.1f}%")
        col6.metric("In House %", f"{inhouse_pct:.1f}%")
    elif venue_name == "CYO_Village_Pub":
        col5.metric("Steakhouse %", f"{steakhouse_pct:.1f}%")
        col6.metric("Pub Menu %", f"{inhouse_pct:.1f}%")
    else:
        col5.metric("Sales Mix", "N/A")
        col6.metric("Sales Mix", "N/A")

    # ============================= # DASHBOARD CHARTS # =============================
    if venue_name in ["Paperbark_Burger_Co", "CYO_Village_Pub"]:
        dashboard_left, dashboard_right = st.columns([1, 1.6])

        with dashboard_left:
            if sales_mix:
                st.markdown("### Sales Mix")

                if venue_name == "Paperbark_Burger_Co":
                    mix_df = pd.DataFrame({
                        "Segment": ["In House", "Takeaway"],
                        "Revenue": [inhouse_revenue, takeaway_revenue]
                    })

                elif venue_name == "CYO_Village_Pub":
                    mix_df = pd.DataFrame({
                        "Segment": ["Pub Menu", "Steakhouse"],
                        "Revenue": [inhouse_revenue, steakhouse_revenue]
                    })

                fig = px.pie(mix_df, names="Segment", values="Revenue", hole=0.55)
                fig.update_layout(showlegend=False, height=350, margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig, width='stretch')

        with dashboard_right:
            st.markdown("### KPI Trend")

            available_metrics = {
                "Revenue": "revenue",
                "Food Cost %": "food_cost",
                "Purchases": "purchases",
                "Waste %": "waste"
            }

            selected_metrics = st.multiselect(
                "Select Metrics to Display",
                options=list(available_metrics.keys()),
                default=["Revenue", "Food Cost %"]
            )

            trend_df = pd.DataFrame([
                {
                    "period": p.period,
                    "revenue": p.revenue,
                    "food_cost": p.food_cost_percent,
                    "purchases": p.cogs,
                    "waste": (p.waste_total / p.revenue * 100) if p.revenue else 0
                }
                for p in filtered_reports
            ]).sort_values("period")

            if selected_metrics:
                column_keys = [available_metrics[m] for m in selected_metrics]
                st.line_chart(trend_df.set_index("period")[column_keys])
            else:
                st.info("Please select at least one metric to view the trend.")

    else:

        st.markdown("### KPI Trend")

        available_metrics = {
            "Revenue": "revenue",
            "Food Cost %": "food_cost",
            "Purchases": "purchases",
            "Waste %": "waste"
        }

        selected_metrics = st.multiselect(
            "Select Metrics to Display",
            options=list(available_metrics.keys()),
            default=["Revenue", "Food Cost %"]
        )

        trend_df = pd.DataFrame([
            {
                "period": p.period,
                "revenue": p.revenue,
                "food_cost": p.food_cost_percent,
                "purchases": p.cogs,
                "waste": (p.waste_total / p.revenue * 100) if p.revenue else 0
            }
            for p in filtered_reports
        ]).sort_values("period")

        if selected_metrics:
            column_keys = [available_metrics[m] for m in selected_metrics]
            st.line_chart(trend_df.set_index("period")[column_keys])

    # ============================= # YTD ITEM PERFORMANCE # =============================
    st.markdown("### Item Performance (Selected Range)")
    df_main = pd.DataFrame()
    df_steakhouse = pd.DataFrame()
    df_takeaway = pd.DataFrame()

    if sales_mix:
        df_sales = pd.DataFrame([{"item": s.item_name, "qty": s.qty, "revenue": s.revenue, "gp_pct": s.gross_profit_percent} for s in sales_mix])
        df_sales["gp_dollars"] = df_sales["revenue"] * (df_sales["gp_pct"] / 100)
        df = df_sales.groupby("item", as_index=False).agg({"qty": "sum", "revenue": "sum", "gp_dollars": "sum"})
        df["gp_pct"] = (df["gp_dollars"] / df["revenue"] * 100).fillna(0)

        if not df.empty:
            df_steakhouse = df[df["item"].str.startswith("SH", na=False)].copy()
            df_takeaway = df[df["item"].str.startswith("T/A", na=False)].copy()
            df_main = df[~df["item"].str.startswith("SH", na=False) & ~df["item"].str.startswith("T/A", na=False)].copy()

            colA, colB, colC = st.columns(3)
            with colA:
                st.markdown("**Top Revenue Items**")
                for _, r in df_main.sort_values("revenue", ascending=False).head(5).iterrows():
                    st.write(f"{r['item']} — ${r['revenue']:,.0f}")
            with colB:
                st.markdown("**Top Profit Generators**")
                for _, r in df_main.sort_values("gp_dollars", ascending=False).head(5).iterrows():
                    st.write(f"{r['item']} — ${r['gp_dollars']:,.0f} ({r['gp_pct']:.1f}%)")
            with colC:
                st.markdown("**Top Sales by Volume**")
                for _, r in df_main.sort_values("qty", ascending=False).head(5).iterrows():
                    st.write(f"{r['item']} — {int(r['qty'])} sold")

    # ============================= # STEAKHOUSE / TAKEAWAY SECTIONS # =============================
    if venue_name == "CYO_Village_Pub" and not df_steakhouse.empty:
        df_steakhouse["item"] = df_steakhouse["item"].str.replace("SH", "", regex=False).str.strip()
        st.markdown("### 🥩 Steakhouse Performance (Selected Range)")
        colA, colB, colC = st.columns(3)
        with colA:
            st.markdown("**Top Revenue Items**")
            for _, r in df_steakhouse.sort_values("revenue", ascending=False).head(5).iterrows():
                st.write(f"{r['item']} — ${r['revenue']:,.0f}")
        with colB:
            st.markdown("**Top Profit Generators**")
            for _, r in df_steakhouse.sort_values("gp_dollars", ascending=False).head(5).iterrows():
                st.write(f"{r['item']} — ${r['gp_dollars']:,.0f} ({r['gp_pct']:.1f}%)")
        with colC:
            st.markdown("**Top Sales by Volume**")
            for _, r in df_steakhouse.sort_values("qty", ascending=False).head(5).iterrows():
                st.write(f"{r['item']} — {int(r['qty'])} sold")

    if venue_name == "Paperbark_Burger_Co" and not df_takeaway.empty:
        df_takeaway["item"] = df_takeaway["item"].str.replace("T/A", "", regex=False).str.strip()
        st.markdown("### 🥡 Takeaway Performance (Selected Range)")
        colA, colB, colC = st.columns(3)
        with colA:
            st.markdown("**Top Revenue Items**")
            for _, r in df_takeaway.sort_values("revenue", ascending=False).head(5).iterrows():
                st.write(f"{r['item']} — ${r['revenue']:,.0f}")
        with colB:
            st.markdown("**Top Profit Generators**")
            for _, r in df_takeaway.sort_values("gp_dollars", ascending=False).head(5).iterrows():
                st.write(f"{r['item']} — ${r['gp_dollars']:,.0f} ({r['gp_pct']:.1f}%)")
        with colC:
            st.markdown("**Top Sales by Volume**")
            for _, r in df_takeaway.sort_values("qty", ascending=False).head(5).iterrows():
                st.write(f"{r['item']} — {int(r['qty'])} sold")

def show_reference_documents(period_path):

    import os

    st.markdown("### 📎 Source Documents")

    pdf_files = [
        f for f in os.listdir(period_path)
        if f.lower().endswith(".pdf")
    ]

    if not pdf_files:
        st.info("No reference PDFs found for this period.")
        return

    for pdf in sorted(pdf_files):

        pdf_path = os.path.join(period_path, pdf)

        with open(pdf_path, "rb") as file:
            pdf_bytes = file.read()

        st.download_button(
            label=f"Download {pdf}",
            data=pdf_bytes,
            file_name=pdf,
            mime="application/pdf",
            width='stretch'
        )     
def format_vs_last(value, metric_type):
    if value is None:
        return ""

    # Default (good = up)
    good_when = "up"

    # Invert for cost-based metrics
    if metric_type in ["waste", "food_cost"]:
        good_when = "down"

    is_up = value > 0

    if (is_up and good_when == "up") or (not is_up and good_when == "down"):
        color = "green"
    else:
        color = "red"

    arrow = "↑" if is_up else "↓"

    return f"""
    <div style="font-size: 0.9em; color: {color};">
        {arrow} {abs(value):.2f}% vs Last Period
    </div>
    """ 

# =============================
# REPORT RENDER FUNCTION
# =============================

def render_full_period_report(p, session):

    prev_period=(
        session.query(Period)
        .filter(
            Period.venue == p.venue,
            Period.report_type == p.report_type,
            Period.period < p.period
        )
        .order_by(Period.period.desc())
        .first()
    )

    venue_config = VENUE_CONFIG.get(p.venue, {"target": 30.0})
    target_percent = venue_config["target"]

    purchase_budget = p.revenue * (target_percent / 100)
    purchase_variance = purchase_budget - p.cogs

    food_variance_percent = p.food_cost_percent - target_percent
    waste_variance_percent = p.waste_percent - WASTE_TARGET
    
    opening_stock = (
        prev_period.closing_stock
        if prev_period and prev_period.closing_stock is not None
        else p.closing_stock
    )

    rev_vs_last = None
    fc_vs_last = None
    waste_vs_last = None
    stock_movement = closing_stock-opening_stock
    stock_change = (
         p.closing_stock - prev_period.closing_stock
         if prev_period else 0
    )

    if prev_period:
        fc_vs_last = p.food_cost_percent - prev_period.food_cost_percent
        waste_vs_last = p.waste_percent - prev_period.waste_percent
        rev_vs_last = p.revenue - prev_period.revenue
    else:
        fc_vs_last = 0
        waste_vs_last = 0 
        rev_vs_last = 0

    with st.expander(f"📅 {p.period} ({p.report_type}-Day)", expanded=False):

        # ================= KPI SECTION =================

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Revenue",
            f"${p.revenue:,.0f}",
            delta=f"{rev_vs_last:+,.0f} vs Last Period"
        )

        col2.metric(
            "Purchases",
            f"${(p.purchases or 0):,.0f}"
        )
        col3.metric("COGS (Actual)", f"${p.cogs:,.0f}")

        col4.metric("Opening Stock", f"${opening_stock:,.0f}")


        col5, col6, col7, col8 = st.columns(4)
        # ================= VENUE SPECIFIC SALES =================

        if p.venue in SPECIAL_REVENUE_VENUES:

            col9, col10 = st.columns(2)

            steak_sales = getattr(p, "steakhouse_sales", 0)
            takeaway_sales = getattr(p, "takeaway_sales", 0)

            col9.metric(
                "Steakhouse Sales",
                f"${steak_sales:,.0f}"
            )

            col10.metric(
                "Takeaway Sales",
                f"${takeaway_sales:,.0f}"
            )
    

        col5.metric(
            f"Food Cost % (Target {target_percent:.1f}%)",
            f"{p.food_cost_percent:.2f}%",
            delta=f"{food_variance_percent:+.2f}% vs Target",
            delta_color="inverse",
        )

        if prev_period:
            col5.markdown(
                format_vs_last(fc_vs_last, "food_cost"),
                unsafe_allow_html=True
            )

        col6.metric(
            f"Waste % (Target {WASTE_TARGET:.1f}%)",
            f"{p.waste_percent:.2f}%",
            delta=f"{waste_variance_percent:+.2f}% vs Target",
            delta_color="inverse",
        )

        if prev_period:
            col6.markdown(
                format_vs_last(waste_vs_last, "waste"),
                unsafe_allow_html=True
            )

        col7.metric("Waste $", f"${p.waste_total:,.0f}")

        col8.metric(
            "Closing Stock",
            f"${p.closing_stock:,.0f}",
            delta=f"{stock_change:+,.0f}" if prev_period else None
        )
        

        # ================= EXECUTIVE COMMENTARY =================

        st.markdown("### 🧠 Executive Commentary")

        commentary = []

        if food_variance_percent < -1:
            commentary.append("Food cost performing strongly under target.")
        elif food_variance_percent < 0:
            commentary.append("Food cost slightly under target.")
        elif food_variance_percent <= 1:
            commentary.append("Food cost slightly above target — monitor closely.")
        else:
            commentary.append("Food cost materially above target — corrective action recommended.")

        waste_records = (
            session.query(WasteLine)
            .filter(WasteLine.period_id == p.id)
            .all()
        )

        if waste_records:

            df_waste = pd.DataFrame([{
                "Item": w.item,
                "Reason": w.reason,
                "Qty": w.qty,
                "Total ($)": w.total
            } for w in waste_records])

            waste_summary = (
                df_waste
                .groupby(["Item", "Reason"], as_index=False)
                .agg({"Qty": "sum", "Total ($)": "sum"})
                .sort_values("Total ($)", ascending=False)
            )

            # --- Top Waste Reason ---
            reason_summary = (
                df_waste.groupby("Reason", as_index=False)
                .agg({"Total ($)": "sum"})
                .sort_values("Total ($)", ascending=False)
            )

            largest_reason = reason_summary.iloc[0]["Reason"]
            largest_value = reason_summary.iloc[0]["Total ($)"]

            commentary.append(
                f"Primary waste driver: {largest_reason} (${largest_value:,.0f})."
            )

            # --- Top Wasted Item ---
            item_summary = (
                df_waste.groupby("Item", as_index=False)
                .agg({"Total ($)": "sum"})
                .sort_values("Total ($)", ascending=False)
            )

            top_item = item_summary.iloc[0]

            commentary.append(
                f"Highest wasted product: {top_item['Item']} (${top_item['Total ($)']:,.0f})."
            )

        else:
            waste_summary = pd.DataFrame()
            commentary.append("No structured waste recorded this period.")

        for line in commentary:
            st.markdown(f"- {line}")

       # =============================
        # TOP WASTED ITEMS TABLE
        # =============================

        with st.expander("### 🗑 Top 5 Wasted Items", expanded=True):

            waste_records = (
                session.query(WasteLine)
                .filter(WasteLine.period_id == p.id)
                .all()
            )

            if waste_records:

                df_waste = pd.DataFrame([{
                    "Item": w.item,
                    "Reason": w.reason,
                    "Qty": w.qty,
                    "Total ($)": w.total
                } for w in waste_records])

                summary = (
                    df_waste
                    .groupby(["Item", "Reason"], as_index=False)
                    .agg({
                        "Qty": "sum",
                        "Total ($)": "sum"
                    })
                    .sort_values("Total ($)", ascending=False)
                    .head(5)
                )

                summary["Qty"] = summary["Qty"].round(2)
                summary["Total ($)"] = summary["Total ($)"].round(2)

                st.dataframe(summary, width='stretch')

            else:
                st.info("No structured waste data available for this period.")

        # ================= ITEM PERFORMANCE =================

        st.markdown("### 📊 Item Performance")

        sales = (
            session.query(SalesLine)
            .filter(SalesLine.period_id == p.id)
            .all()
        )

        if sales:

            df_sales = pd.DataFrame([{
                "item": s.item_name,
                "qty": s.qty,
                "revenue": s.revenue,
                "gp_pct": s.gross_profit_percent
            } for s in sales])

            df_sales = df_sales[df_sales["qty"] > 0]

            df_sales["gp_dollars"] = df_sales["revenue"] * (df_sales["gp_pct"] / 100)

            df = (
                df_sales
                .groupby("item", as_index=False)
                .agg({
                    "qty": "sum",
                    "revenue": "sum",
                    "gp_dollars": "sum"
                })
            )

            df["gp_pct"] = (df["gp_dollars"] / df["revenue"]) * 100

            total_revenue = df["revenue"].sum()
            df["contribution"] = (df["revenue"] / total_revenue) * 100
            # ================= SALES SEGMENT SPLIT =================

            df_main = df.copy()
            df_steakhouse = pd.DataFrame()
            df_takeaway = pd.DataFrame()

            if p.venue == "CYO_Village_Pub":

                df_steakhouse = df[df["item"].str.startswith("SH", na=False)].copy()
                df_main = df[~df["item"].str.startswith("SH", na=False)].copy()

                df_steakhouse["item"] = (
                    df_steakhouse["item"]
                    .str.replace("SH", "", regex=False)
                    .str.strip()
                )

            elif p.venue == "Paperbark_Burger_Co":

                df_takeaway = df[df["item"].str.startswith("T/A", na=False)].copy()
                df_main = df[~df["item"].str.startswith("T/A", na=False)].copy()

                df_takeaway["item"] = (
                    df_takeaway["item"]
                    .str.replace("T/A", "", regex=False)
                    .str.strip()
                )

            col1, col2 = st.columns(2)

            with col1:

                st.markdown("**Top Sellers by Revenue**")
                for _, r in df_main.sort_values("revenue", ascending=False).head(5).iterrows():
                    st.write(f"{r['item']} — ${r['revenue']:,.0f}")

                st.markdown("**Top Sellers by Volume**")
                for _, r in df_main.sort_values("qty", ascending=False).head(5).iterrows():
                    st.write(f"{r['item']} ({int(r['qty'])})")

            with col2:

                st.markdown("**Top Profit Generators**")
                for _, r in df.sort_values("gp_dollars", ascending=False).head(5).iterrows():
                    st.write(
                        f"{r['item']} — ${r['gp_dollars']:,.0f} ({r['gp_pct']:.1f}% | {int(r['qty'])} sold)"
                    )

                st.markdown("**Lowest Sellers by Volume**")
                for _, r in df.sort_values("qty").head(5).iterrows():
                    st.write(f"{r['item']} ({int(r['qty'])})")

            top_item = df_main.sort_values("revenue", ascending=False).iloc[0]

            st.info(
                f"🔎 **{top_item['item']} contributes {top_item['contribution']:.1f}% of total revenue.**"
            )

        else:
            st.info("No item level sales data.")
            # ================= STEAKHOUSE PERFORMANCE =================

        if not df_steakhouse.empty:

            st.markdown("### 🥩 Steakhouse Performance")

            colA, colB, colC = st.columns(3)

            with colA:
                st.markdown("**Top Revenue Items**")
                for _, r in df_steakhouse.sort_values("revenue", ascending=False).head(5).iterrows():
                    st.write(f"{r['item']} — ${r['revenue']:,.0f}")

            with colB:
                st.markdown("**Top Profit Generators**")
                for _, r in df_steakhouse.sort_values("gp_dollars", ascending=False).head(5).iterrows():
                    st.write(f"{r['item']} — ${r['gp_dollars']:,.0f}")

            with colC:
                st.markdown("**Top Sellers by Volume**")
                for _, r in df_steakhouse.sort_values("qty", ascending=False).head(5).iterrows():
                    st.write(f"{r['item']} ({int(r['qty'])})")
             # ================= TAKEAWAY PERFORMANCE =================

        if not df_takeaway.empty:

            st.markdown("### 🥡 Takeaway Performance")

            colA, colB, colC = st.columns(3)

            with colA:
                st.markdown("**Top Revenue Items**")
                for _, r in df_takeaway.sort_values("revenue", ascending=False).head(5).iterrows():
                    st.write(f"{r['item']} — ${r['revenue']:,.0f}")

            with colB:
                st.markdown("**Top Profit Generators**")
                for _, r in df_takeaway.sort_values("gp_dollars", ascending=False).head(5).iterrows():
                    st.write(f"{r['item']} — ${r['gp_dollars']:,.0f}")

            with colC:
                st.markdown("**Top Sellers by Volume**")
                for _, r in df_takeaway.sort_values("qty", ascending=False).head(5).iterrows():
                    st.write(f"{r['item']} ({int(r['qty'])})")



            
        # =============================
        # REFERENCE DOCUMENTS
        # =============================

        with st.expander("📎 Reference Documents", expanded=False):

            venue = p.venue
            report_type = p.report_type
            period = p.period

            period_path = os.path.join(
                "data",
                venue,
                report_type,
                period
            )

            if os.path.exists(period_path):

                pdf_files = [
                    f for f in os.listdir(period_path)
                    if f.lower().endswith(".pdf")
                ]

                if pdf_files:

                    selected_pdf = st.selectbox(
                        "Select Source Report",
                        pdf_files,
                        key=f"pdf_select_{p.id}"
                    )

                    pdf_path = os.path.join(period_path, selected_pdf)

                    show_pdf_viewer(pdf_path)

                else:
                    st.info("No reference PDFs available.")

            else:
                st.warning("Report folder not found.")
        if st.button(f"Generate Executive PDF - {p.period}"):

            commentary_text = " ".join(commentary)

            waste_table = (
                waste_summary.head(10).values.tolist()
                if not waste_summary.empty
                else [["No data"]]
            )

            item_table = [["Item", "Qty", "Revenue", "GP %", "GP $"]]

            if sales:
                for _, row in df.sort_values("revenue", ascending=False).head(20).iterrows():
                    item_table.append([
                        row["item"],
                        int(row["qty"]),
                        f"${row['revenue']:,.0f}",
                        f"{row['gp_pct']:.1f}%",
                        f"${row['gp_dollars']:,.0f}"
                    ])

            worst_items = [["Item", "GP %", "Revenue"]]

            if sales:
                for _, row in df.sort_values("gp_pct").head(5).iterrows():
                    worst_items.append([
                        row["item"],
                        f"{row['gp_pct']:.1f}%",
                        f"${row['revenue']:,.0f}"
                    ])
            # -----------------------------
            # Collect reference PDFs
            # -----------------------------

            reference_pdf_paths = []

            period_path = os.path.join(
                DATA_FOLDER,
                p.venue,
                p.report_type,
                p.period
            )

            if os.path.exists(period_path):

                for f in sorted(os.listdir(period_path)):
                    if f.lower().endswith(".pdf"):
                        reference_pdf_paths.append(
                            os.path.join(period_path, f)
                        )
            # -----------------------------
            # Build Trend Data (last 6 periods)
            # -----------------------------

            trend_periods = (
                session.query(Period)
                .filter(
                    Period.venue == p.venue,
                    Period.report_type == p.report_type
                )
                .order_by(Period.period.desc())
                .limit(6)
                .all()
            )

            trend_periods = list(reversed(trend_periods))

            food_trend_labels = [x.period for x in trend_periods]
            food_trend_values = [x.food_cost_percent for x in trend_periods]

            waste_trend_labels = [x.period for x in trend_periods]
            waste_trend_values = [x.waste_percent for x in trend_periods]

            report_data = {

                "venue_name": p.venue.replace("_", " "),
                "period_label": f"{p.period} ({p.report_type} Day)",

                "commentary": commentary_text,

                "revenue": f"${p.revenue:,.0f}",
                "purchases": f"${p.cogs:,.0f}",
                "revenue_target": f"${purchase_budget:,.0f}",
                "revenue_var": f"${purchase_variance:,.0f}",

                "food_cost": f"{p.food_cost_percent:.2f}%",
                "food_target": f"{target_percent:.1f}%",

                "waste_pct": f"{p.waste_percent:.2f}%",
                "waste_target": f"{WASTE_TARGET:.1f}%",

                "stock": f"${p.closing_stock:,.0f}",
                "waste_total": f"${p.waste_total:,.0f}",

                "item_performance": item_table,
                "waste_table": waste_table
            }
            from utils.pdf_export import export_branded_report

            pdf_buffer = export_branded_report(report_data, reference_pdf_paths)

            st.success("Executive report generated!")
            st.download_button(
                "Download Executive PDF",
                pdf_buffer,
                file_name=f"{p.venue}_{p.period}_Executive_Report.pdf",
                mime="application/pdf",
                width='stretch'
            )
            
# =============================
# DETAILED PERIOD REPORTS
# =============================

st.divider()
st.header("Detailed Period Reports")

reports_28 = [p for p in periods if p.report_type == "28"]
reports_14 = [p for p in periods if p.report_type == "14"]

if reports_28:
    st.subheader("28 Day Reports")
    for p in sorted(reports_28, key=lambda x: x.period, reverse=True):
        render_full_period_report(p, session)

if reports_14:
    st.subheader("14 Day Reports")
    for p in sorted(reports_14, key=lambda x: x.period, reverse=True):
        render_full_period_report(p, session)