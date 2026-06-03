import pandas as pd
import os
import base64
import textwrap
import streamlit as st

# Hide sidebar before login
if not st.session_state.get("authenticated", False):
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            display: none;
        }

        button[kind="header"] {
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)
from database import Session, Period
from database import engine
from database import Session, Period, User
from werkzeug.security import check_password_hash
from sqlalchemy import text
import streamlit as st
from utils.ui import apply_global_style, sidebar_branding

st.set_page_config(
    page_title="Commercial Kitchen Insights",
    page_icon="assets/cki_icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global styling + logo
apply_global_style()
sidebar_branding()

def check_password():

    session = Session()

    def login():

        username = st.session_state["username"]
        password = st.session_state["password"]

        user = session.query(User).filter(
            User.username == username,
            User.active == True
        ).first()

        if user and check_password_hash(
            user.password_hash,
            password
        ):

            st.session_state["authenticated"] = True
            st.session_state["login_failed"] = False
            st.session_state["username"] = user.username
            st.session_state["role"] = user.role
            st.session_state["venues"] = (
                user.venues
                if user.venues
                else "ALL"
            )
            st.session_state["full_name"] = user.full_name

        else:
            st.session_state["authenticated"] = False
            st.session_state["login_failed"] = True

    if not st.session_state.get("authenticated"):

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:

            st.markdown("<br><br>", unsafe_allow_html=True)

            left, center, right = st.columns([1, 2, 1])

            with center:
                st.image(
                    "assets/cki_logo_primary.png",
                    width=420
                )

            st.markdown(
                """
                <h3 style='text-align:center;'>
                    Commercial Kitchen Insights
                </h3>
                """,
                unsafe_allow_html=True
            )

            st.text_input(
                "Username",
                key="username"
            )

            st.text_input(
                "Password",
                type="password",
                key="password"
            )

            # Failed login message
            if st.session_state.get(
                "login_failed",
                False
            ):
                st.error(
                    "Invalid username or password. Please try again."
                )

            st.button(
                "Login",
                on_click=login,
                use_container_width=True
            )

        return False

    return True

    if not st.session_state.get("authenticated"):

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:

            st.markdown("<br><br>", unsafe_allow_html=True)

            left, center, right = st.columns([1,2,1])

            with center:
                st.image(
                    "assets/cki_logo_primary.png",
                    width=420
                )

            st.markdown(
                """
                <h3 style='text-align:center;'>
                    Commercial Kitchen Insights
                </h3>
                """,
                unsafe_allow_html=True
            )

            st.text_input(
                "Username",
                key="username"
            )

            st.text_input(
                "Password",
                type="password",
                key="password"
            )

            st.button(
                "Login",
                on_click=login,
                width='stretch'
            )

        return False

    return True
if not check_password():
    st.stop()

# ==============================
# LOGOUT BUTTON
# ==============================

with st.sidebar:

    st.markdown("---")

    st.write(
        f"👋 {st.session_state.get('full_name', 'User')}"
    )

    if st.button(
        "🚪 Logout",
        use_container_width=True
    ):
        st.session_state.clear()
        st.rerun()



# ==============================
# CUSTOM CSS
# ==============================

st.markdown("""
<style>

.stApp {
    background-color: #f5f6f8;
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

# ==============================
# HEADER
# ==============================

left_space, logo_col, right_space = st.columns([1.8, 3, 0.2])

with logo_col:
    st.image(
        "assets/cki_logo_primary.png",
        width=520
    )

# Black divider line
st.markdown("""
<hr style="
    border:none;
    height:2px;
    background:#000000;
    margin-top:0px;
    margin-bottom:30px;
">
""", unsafe_allow_html=True)
# ==============================
# LOAD DATA
# ==============================

session = Session()
allowed_venues = st.session_state.get("venues")

if allowed_venues == "ALL":
    all_periods = session.query(Period).all()

else:
    all_periods = (
        session.query(Period)
        .filter(Period.venue.in_(allowed_venues))
        .all()
    )

if not all_periods:
    st.info("No reporting periods processed yet.")
    session.close()
    st.stop()

df = pd.DataFrame([{
    "id": p.id,
    "venue": p.venue,   # ✅ FIXED (no [0] needed anymore)
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

# Previous comparable report type
df["previous_food_cost"] = (
    df.groupby(["venue", "report_type"])["food_cost_percent"]
    .shift(1)
)

df["previous_revenue"] = (
    df.groupby(["venue", "report_type"])["revenue"]
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
# ==============================
# PORTFOLIO KPI HEADER
# ==============================

# Exclude MFM from portfolio KPIs
portfolio_df = df_latest[
    df_latest["venue"] != "Melaleuka_Farm_Merchants"
].copy()

portfolio_revenue = portfolio_df["revenue"].sum()

portfolio_fc = (
    (
        portfolio_df["food_cost_percent"]
        * portfolio_df["revenue"]
    ).sum() / portfolio_revenue
    if portfolio_revenue else 0
)

portfolio_waste = (
    (
        portfolio_df["waste_percent"]
        * portfolio_df["revenue"]
    ).sum() / portfolio_revenue
    if portfolio_revenue else 0
)

venues_above_target = (
    portfolio_df["food_cost_percent"]
    > portfolio_df["food_cost_target"]
).sum()

total_venues = len(portfolio_df)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric(
    "Portfolio Revenue",
    f"${portfolio_revenue:,.0f}"
)

kpi2.metric(
    "Weighted Food Cost %",
    f"{portfolio_fc:.1f}%"
)

kpi3.metric(
    "Weighted Waste %",
    f"{portfolio_waste:.1f}%"
)

kpi4.metric(
    "Venues Above Target",
    f"{venues_above_target}/{total_venues}"
)

st.markdown("<br>", unsafe_allow_html=True)
# ==============================
# PORTFOLIO COMMENTARY
# ==============================

st.markdown("### 🧠 Portfolio Commentary")

commentary = []

# Food cost commentary
weighted_target = (
    (
        portfolio_df["food_cost_target"]
        * portfolio_df["revenue"]
    ).sum() / portfolio_revenue
    if portfolio_revenue else 0
)

fc_variance = portfolio_fc - weighted_target

if fc_variance < -1:
    commentary.append(
        "Portfolio food cost is performing strongly below target."
    )
elif fc_variance < 0:
    commentary.append(
        "Portfolio food cost is slightly below target."
    )
elif fc_variance <= 1:
    commentary.append(
        "Portfolio food cost is slightly above target and should be monitored."
    )
else:
    commentary.append(
        "Portfolio food cost is materially above target and requires corrective action."
    )

# Venue target performance
commentary.append(
    f"{venues_above_target} of {total_venues} venues are currently above food cost target."
)

# Waste commentary
if portfolio_waste <= 1:
    commentary.append(
        f"Portfolio waste remains controlled at {portfolio_waste:.1f}%."
    )
else:
    commentary.append(
        f"Portfolio waste is elevated at {portfolio_waste:.1f}%."
    )

# Best FC performer
best_fc = portfolio_df.loc[
    portfolio_df["food_cost_percent"].idxmin()
]

commentary.append(
    f"{best_fc['venue'].replace('_', ' ')} recorded the strongest food cost result "
    f"at {best_fc['food_cost_percent']:.1f}%."
)

# Best revenue growth
growth_df = portfolio_df.dropna(
    subset=["previous_revenue"]
).copy()

if not growth_df.empty:

    growth_df["revenue_growth_pct"] = (
        (
            growth_df["revenue"]
            - growth_df["previous_revenue"]
        )
        / growth_df["previous_revenue"]
    ) * 100

    top_growth = growth_df.loc[
        growth_df["revenue_growth_pct"].idxmax()
    ]

    commentary.append(
        f"{top_growth['venue'].replace('_', ' ')} delivered the strongest revenue growth "
        f"({top_growth['revenue_growth_pct']:+.1f}% vs previous comparable period)."
    )

for line in commentary:
    st.markdown(f"- {line}")
st.caption(
    "Portfolio metrics and commentary exclude Melaleuka Farm Merchants (MFM) due to its different operating model and food cost structure."
)


num_cols = 3
rows = [df_latest[i:i+num_cols] for i in range(0, len(df_latest), num_cols)]

def get_base64_image(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

for row_group in rows:

    cols = st.columns(num_cols)

    for col, (_, row) in zip(cols, row_group.iterrows()):

        venue_data = row["venue"]
        venue = venue_data if venue_data else "Unknown"
        revenue = row["revenue"] or 0
        food_cost = row["food_cost_percent"] or 0
        target = row["food_cost_target"] or 0
        previous_fc = row["previous_food_cost"]
        previous_revenue = row["previous_revenue"]
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
            # REVENUE TREND
            # ==============================

            revenue_indicator = ""
            revenue_colour = "#888"

            if (
                pd.notnull(previous_revenue)
                and previous_revenue > 0
            ):

                revenue_diff = revenue - previous_revenue

                revenue_change_pct = (
                    revenue_diff / previous_revenue
                ) * 100

                if revenue_diff > 0:
                    revenue_colour = "#4CAF50"
                    revenue_indicator = (
                        f"▲ ${abs(revenue_diff):,.0f} "
                        f"(+{revenue_change_pct:.1f}%)"
                    )

                elif revenue_diff < 0:
                    revenue_colour = "#F44336"
                    revenue_indicator = (
                        f"▼ ${abs(revenue_diff):,.0f} "
                        f"(-{abs(revenue_change_pct):.1f}%)"
                    )

                else:
                    revenue_indicator = "$0 (0.0%)"
                

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

        safe_venue = venue if venue else "unknown"
        logo_path = f"assets/venues/{safe_venue}.png"

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
<div class="venue-card">
<div class="performance-bar" style="background:{performance_colour};"></div>

{logo_html}

<div class="venue-title">{venue.replace("_", " ")}</div>

<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">

<div>
<div class="metric-label">Revenue</div>
<div class="metric-value">
${revenue:,.0f}
<div style="
    font-size:0.8rem;
    color:{revenue_colour};
    margin-top:4px;
">
P {revenue_indicator}
</div>
</div>
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


</div>
</a>
""")

        with col:
            st.markdown(card_html, unsafe_allow_html=True)

            if st.button(
                f"➜ View Full Report",
                key=f"venue_{venue}",
                use_container_width=True
            ):
                st.session_state["selected_venue"] = venue
                st.switch_page("pages/02_Venue_Detail.py")

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)