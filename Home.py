import streamlit as st

def check_password():
    def password_entered():
        if st.session_state["password"] == "chef123":  # change this
            st.session_state["authenticated"] = True
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state["authenticated"]

if not check_password():
    st.stop()
import pandas as pd
import os
import base64
import textwrap
from database import Session, Period
from database import engine
from sqlalchemy import text


with engine.connect() as conn:
    conn.commit()

# ==============================
# PAGE CONFIG
# ==============================

st.set_page_config(
    page_title="Commercial Kitchen Insights",
    page_icon="assets/cki_icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# CUSTOM CSS
# ==============================

st.markdown("""
<style>

.stApp {
    background-color: #f5f6f8;
}

section[data-testid="stSidebar"] {
    background-color: #ffffff;
}
section[data-testid="stSidebar"] * {
    color: #222 !important;
}

.block-container {
    padding-top: 2rem;
}

.venue-card {
    background-color: #ffffff;
    padding: 1.75rem 1.5rem;
    border-radius: 14px;
    border: 1px solid #e6e6e6;
    box-shadow: 0 4px 18px rgba(0,0,0,0.04);
    transition: 0.2s ease;
    height: 100%;
    cursor: pointer;
}

.venue-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 6px 24px rgba(0,0,0,0.08);
}

.performance-bar {
    height: 6px;
    width: 100%;
    border-radius: 10px 10px 0 0;
    margin: -1.75rem -1.5rem 1rem -1.5rem;
}

.logo-area {
    height: 100px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1rem;
}

.venue-title {
    font-size: 1.15rem;
    font-weight: 600;
    margin-bottom: 1rem;
    text-align: center;
    color: #111;
}

.metric-label {
    font-size: 0.75rem;
    color: #888;
    margin-top: 0.6rem;
}

.metric-value {
    font-size: 1.05rem;
    font-weight: 600;
    color: #111;
}

.card-cta {
    text-align: center;
    font-size: 0.85rem;
    color: #D4AF37;
    margin-top: 1.5rem;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)

# ==============================
# SIDEBAR
# ==============================

with st.sidebar:
    st.image("assets/cki_logo_reverse.png", width="stretch")
    st.divider()

# ==============================
# HEADER
# ==============================

st.title("Commercial Kitchen Insights")
st.subheader("Operational Intelligence Dashboard")

# ==============================
# LOAD DATA
# ==============================

session = Session()
all_periods = session.query(Period).all()

if not all_periods:
    st.info("No reporting periods processed yet.")
    session.close()
    st.stop()

df = pd.DataFrame([{
    "id": p.id,
    "venue": p.venue,
    "period": p.period,
    "revenue": p.revenue,
    "food_cost_percent": p.food_cost_percent,
    "food_cost_target": p.food_cost_target,
    "waste_percent": p.waste_percent,
    "report_type": p.report_type
} for p in all_periods])

# ==============================
# PERIOD PROCESSING
# ==============================

df["period_start"] = pd.to_datetime(
    df["period"].str.split("_to_").str[0],
    errors="coerce"
)

df["period_end"] = pd.to_datetime(
    df["period"].str.split("_to_").str[1],
    errors="coerce"
)

# Sort and calculate previous period
df = df.sort_values(["venue", "period_end"])

df["previous_food_cost"] = (
    df.groupby("venue")["food_cost_percent"]
    .shift(1)
)

# Latest period per venue
df_latest = (
    df.sort_values("period_end")
    .groupby("venue")
    .tail(1)
    .reset_index(drop=True)
)

session.close()

# ==============================
# CARD GRID
# ==============================

st.subheader("📊 Latest Performance by Venue")
st.caption("▼ = Improvement  |  ▲ = Worsening  |  T = vs Target  |  P = vs Previous Report")

num_cols = 3
rows = [df_latest[i:i+num_cols] for i in range(0, len(df_latest), num_cols)]

def get_base64_image(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

for row_group in rows:

    cols = st.columns(num_cols)

    for col, (_, row) in zip(cols, row_group.iterrows()):

        venue = row["venue"]
        revenue = row["revenue"] or 0
        food_cost = row["food_cost_percent"] or 0
        target = row["food_cost_target"] or 0
        previous_fc = row["previous_food_cost"]
        waste = row["waste_percent"] or 0
        report_type = row["report_type"] or 0
        period_start = row["period_start"]
        period_end = row["period_end"]

        # ==============================
        # TARGET VARIANCE
        # ==============================

        variance = food_cost - target

        if variance < 0:
            indicator = f"▼{abs(variance):.1f}"
            indicator_colour = "#4CAF50"
        elif variance > 0:
            indicator = f"▲{abs(variance):.1f}"
            indicator_colour = "#F44336"
        else:
            indicator = "●0"
            indicator_colour = "#888"

        # ==============================
        # TREND VS LAST PERIOD
        # ==============================

        trend_indicator = ""
        trend_colour = "#888"

        if pd.notnull(previous_fc):

            trend = food_cost - previous_fc

            if trend < 0:
                trend_indicator = f"▼{abs(trend):.1f}"
                trend_colour = "#4CAF50"

            elif trend > 0:
                trend_indicator = f"▲{abs(trend):.1f}"
                trend_colour = "#F44336"

            else:
                trend_indicator = "●0"

        # ==============================
        # PERIOD LABEL
        # ==============================

        period_label = ""
        if pd.notnull(period_start) and pd.notnull(period_end):
            period_label = f"{period_start.strftime('%d %b')} – {period_end.strftime('%d %b')}"

        # ==============================
        # PERFORMANCE COLOUR
        # ==============================

        if food_cost <= 30:
            performance_colour = "#4CAF50"
        elif food_cost <= 32:
            performance_colour = "#FFC107"
        else:
            performance_colour = "#F44336"

        # ==============================
        # LOGO
        # ==============================

        logo_path = f"assets/venues/{venue}.png"

        logo_html = ""

        if os.path.exists(logo_path):
            img_base64 = get_base64_image(logo_path)

            logo_html = f"""
<div class="logo-area">
<img src="data:image/png;base64,{img_base64}"
style="max-height:80px; max-width:100%; object-fit:contain;">
</div>
"""

        # ==============================
        # CARD HTML
        # ==============================

        card_html = textwrap.dedent(f"""
<a href="/Venue_Detail?venue={venue}" style="text-decoration:none; color:inherit;">

<div class="venue-card">
<div class="performance-bar" style="background:{performance_colour};"></div>

{logo_html}

<div class="venue-title">{venue.replace("_", " ")}</div>

<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">

<div>
<div class="metric-label">Revenue</div>
<div class="metric-value">${revenue:,.0f}</div>
</div>

<div>
<div class="metric-label">Waste</div>
<div class="metric-value">{waste:.1f}%</div>
</div>

<div>
<div class="metric-label">Food Cost</div>
<div class="metric-value" style="color:{performance_colour}">
{food_cost:.1f}%
<span style="font-size:0.8rem; color:{indicator_colour}; margin-left:6px;">
T {indicator}
</span>
<span style="font-size:0.8rem; color:{trend_colour}; margin-left:6px;">
P {trend_indicator}
</span>
</div>
</div>

<div>
<div class="metric-label">Target</div>
<div class="metric-value">{target:.1f}%</div>
</div>

<div>
<div class="metric-label">Period</div>
<div class="metric-value">{period_label}</div>
</div>

<div>
<div class="metric-label">Length</div>
<div class="metric-value">{report_type} Days</div>
</div>

</div>

<div class="card-cta">
➜ View Full Report
</div>

</div>
</a>
""")

        with col:
            st.markdown(card_html, unsafe_allow_html=True)
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)