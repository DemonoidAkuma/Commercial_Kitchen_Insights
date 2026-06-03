import streamlit as st
from database import Session, User
from werkzeug.security import generate_password_hash


st.title("👥 User Management")


# ----------------------------
# Access control
# ----------------------------
if st.session_state.get("role") != "admin":
    st.error("Admin access only.")
    st.stop()


session = Session()


# ----------------------------
# Venue List
# ----------------------------
VENUES = [
    "The_Amberton",
    "Hybla_Tavern",
    "CYO_Village_Pub",
    "Paperbark_Burger_Co",
    "Tillys_Garden",
    "The_Byford",
    "The_Wellard",
    "Melaleuka_Farm_Merchants",
]


# ----------------------------
# Helper
# ----------------------------
def format_venues(user):

    if user.role == "admin":
        return "All Venues"

    if not user.venues:
        return "All Venues"

    if isinstance(user.venues, list):
        return ", ".join(
            v.replace("_", " ")
            for v in user.venues
        )

    return str(user.venues)


# ============================
# CREATE USER
# ============================

st.subheader("Create User")


# ----------------------------
# LIVE CONTROLS
# ----------------------------

role = st.selectbox(
    "Role",
    ["venue", "admin"]
)


if role == "admin":

    access_type = "All Venues"

    st.selectbox(
        "Venue Access",
        ["All Venues"],
        disabled=True
    )

    selected_venues = []

else:

    access_type = st.radio(
        "Venue Access",
        [
            "All Venues",
            "Selected Venues"
        ],
        horizontal=True
    )

    if access_type == "Selected Venues":

        selected_venues = st.multiselect(
            "Select Venues",
            options=VENUES
        )

    else:
        selected_venues = []


# ----------------------------
# USER FORM
# ----------------------------

with st.form("create_user"):

    username = st.text_input("Username")

    full_name = st.text_input("Full Name")

    password = st.text_input(
        "Password",
        type="password"
    )

    submitted = st.form_submit_button(
        "Create User"
    )

    if submitted:

        # Venue permissions
        if role == "admin":
            venue_data = None

        elif access_type == "All Venues":
            venue_data = None

        else:
            venue_data = selected_venues

        # Validation
        if not username:
            st.error("Username required.")

        elif not password:
            st.error("Password required.")

        elif role == "venue" and access_type == "Selected Venues" and not selected_venues:
            st.error("Please select at least one venue.")

        else:

            existing_user = (
                session.query(User)
                .filter_by(username=username)
                .first()
            )

            if existing_user:
                st.error("Username already exists.")

            else:

                user = User(
                    username=username,
                    full_name=full_name,
                    password_hash=generate_password_hash(password),
                    role=role,
                    venues=venue_data,
                    active=True
                )

                session.add(user)
                session.commit()

                st.success("User created successfully.")
                st.rerun()


st.divider()


# ============================
# USER LIST
# ============================

st.subheader("Current Users")

users = session.query(User).all()


for user in users:

    col1, col2, col3, col4 = st.columns([2, 2, 3, 1])

    col1.write(user.username)

    col2.write(user.role.title())

    col3.write(format_venues(user))

    can_delete = user.username != "Brandyn"

    if can_delete:

        if col4.button(
            "Delete",
            key=f"delete_{user.id}"
        ):
            session.delete(user)
            session.commit()
            st.rerun()

    else:
        col4.write("🔒 Locked")