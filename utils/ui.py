import streamlit as st
import base64


def apply_global_style():
    st.markdown("""
    <style>

    /* ==============================
       SIDEBAR STYLING
    ============================== */

    section[data-testid="stSidebar"] {
        background-color: #0B0B0B;
        border-right: 1px solid #1E1E1E;
    }

    section[data-testid="stSidebar"] * {
        color: #EAEAEA !important;
    }

    /* Sidebar nav spacing */
    [data-testid="stSidebarNav"] {
        padding-top: 0rem;
    }

    /* Hide venue detail page */
    [data-testid="stSidebarNav"] a[href*="Venue_Detail"] {
        display: none !important;
    }

    /* ==============================
       LOGOUT BUTTON (FORCE STYLE)
    ============================== */

    section[data-testid="stSidebar"] .stButton > button {
        background: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        min-height: 48px !important;
        font-weight: 700 !important;
        opacity: 1 !important;
    }

    /* FORCE BUTTON TEXT */
    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] .stButton > button span,
    section[data-testid="stSidebar"] .stButton > button p,
    section[data-testid="stSidebar"] .stButton > button div {
        color: #000000 !important;
        fill: #000000 !important;
        opacity: 1 !important;
        font-weight: 700 !important;
    }

    /* Hover */
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #E5C14A !important;
        border: none !important;
    }

    /* Prevent washout */
    section[data-testid="stSidebar"] .stButton {
        opacity: 1 !important;
    }

    </style>
    """, unsafe_allow_html=True)


def sidebar_branding():
    st.sidebar.markdown(
        f"""
        <div style='padding:20px 15px 10px 15px;'>
            <img src='data:image/png;base64,{get_base64_logo()}' width='100%'>
        </div>
        <hr style='border:1px solid #222;'>
        """,
        unsafe_allow_html=True
    )


def get_base64_logo():
    with open(
        "assets/cki_logo_reverse.png",
        "rb"
    ) as image_file:
        return base64.b64encode(
            image_file.read()
        ).decode()