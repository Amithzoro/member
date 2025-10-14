import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, timedelta
import pytz
import os

# ---------- CONFIG ----------
TIMEZONE = pytz.timezone("Asia/Kolkata")
MEMBER_FILE = "gym_members.xlsx"
STAFF_FILE = "staff_list.xlsx"

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Gym Member Manager", layout="wide")
st.title("💪 Gym Management System")

# ---------- USERS ----------
# Owner credentials: username "amith", password "password"
# Demo staff: username "staff", password "staff@123"
USERS = {
    "amith": bcrypt.hashpw("password".encode(), bcrypt.gensalt()),
    "staff": bcrypt.hashpw("staff@123".encode(), bcrypt.gensalt())
}

# ---------- SESSION STATE INIT ----------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""

# ---------- LOAD / SAVE FUNCTIONS ----------
def load_excel(path, cols):
    if os.path.exists(path):
        df = pd.read_excel(path)
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        return df[cols]
    else:
        return pd.DataFrame(columns=cols)

def save_excel(df, path):
    df.to_excel(path, index=False)

# ---------- CLEAN DATAFRAME FUNCTION ----------
def clean_members_df(df):
    """Ensure consistent types for PyArrow / Streamlit"""
    df["Start_Date"] = pd.to_datetime(df["Start_Date"], errors="coerce")
    df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")
    df["Name"] = df["Name"].astype(str)
    df["Membership_Type"] = df["Membership_Type"].astype(str)
    df["Added_By"] = df["Added_By"].astype(str)
    df["Added_On"] = pd.to_datetime(df["Added_On"], errors="coerce")
    return df

# ---------- FILE STRUCTURE ----------
member_cols = ["Name", "Membership_Type", "Start_Date", "End_Date", "Added_By", "Added_On"]
staff_cols = ["Username", "Role", "Added_On"]

# Load excel files into session_state
if "members_df" not in st.session_state:
    st.session_state["members_df"] = clean_members_df(load_excel(MEMBER_FILE, member_cols))
if "staff_df" not in st.session_state:
    st.session_state["staff_df"] = load_excel(STAFF_FILE, staff_cols)

# ---------- LOGIN ----------
st.sidebar.header("🔐 Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

def verify_user(username, password):
    if username in USERS and bcrypt.checkpw(password.encode(), USERS[username]):
        return True
    return False

if st.sidebar.button("Login"):
    if verify_user(username, password):
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        st.success(f"Welcome, {username.capitalize()}!")
    else:
        st.error("Invalid username or password.")

# ---------- AFTER LOGIN ----------
if st.session_state.get("logged_in"):

    user = st.session_state["username"]

    # -------- Membership Expiry Alert --------
    st.markdown("### ⚠️ Membership Expiry Alerts")
    today = datetime.now(TIMEZONE).date()
    expiring = st.session_state["members_df"][
        pd.to_datetime(st.session_state["members_df"]["End_Date"], errors='coerce').dt.date.between(today, today + timedelta(days=5))
    ]
    if not expiring.empty:
        for _, row in expiring.iterrows():
            st.warning(f"Member **{row['Name']}** membership ends on **{row['End_Date'].date()}**")
    else:
        st.info("No memberships nearing expiry.")

    # -------- Tabs --------
    tabs = st.tabs(["🏋️ Add Member", "📋 View Members", "👥 Staff (Owner Only)"])

    # -------- ADD MEMBER --------
    with tabs[0]:
        st.subheader("Add New Gym Member")
        with st.form("add_member_form"):
            name = st.text_input("Member Name")
            membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Yearly"])
            start_date = datetime.now(TIMEZONE).date()
            if membership_type == "Monthly":
                end_date = start_date + timedelta(days=30)
            elif membership_type == "Quarterly":
                end_date = start_date + timedelta(days=90)
            else:
                end_date = start_date + timedelta(days=365)

            submitted = st.form_submit_button("➕ Add Member")
            if submitted:
                if name.strip() == "":
                    st.warning("Member name cannot be empty!")
                else:
                    new_entry = pd.DataFrame([{
                        "Name": name,
                        "Membership_Type": membership_type,
                        "Start_Date": start_date,
                        "End_Date": end_date,
                        "Added_By": user,
                        "Added_On": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    st.session_state["members_df"] = pd.concat([st.session_state["members_df"], new_entry], ignore_index=True)
                    st.session_state["members_df"] = clean_members_df(st.session_state["members_df"])
                    save_excel(st.session_state["members_df"], MEMBER_FILE)
                    st.success(f"Member **{name}** added successfully!")

    # -------- VIEW MEMBERS --------
    with tabs[1]:
        st.subheader("Your Added Members")
        df_to_show = st.session_state["members_df"]
        if user != "amith":  # non-owner staff sees only their members
            df_to_show = df_to_show[df_to_show["Added_By"] == user]
        st.dataframe(df_to_show, use_container_width=True)

    # -------- STAFF MANAGEMENT (OWNER ONLY) --------
    with tabs[2]:
        if user == "amith":
            st.subheader("Manage Staff Accounts")
            with st.form("add_staff_form"):
                new_staff = st.text_input("Staff Username")
                role = st.selectbox("Role", ["Trainer", "Receptionist", "Manager"])
                add_staff = st.form_submit_button("➕ Add Staff")
                if add_staff:
                    if new_staff.strip() == "":
                        st.warning("Staff username cannot be empty!")
                    elif new_staff in st.session_state["staff_df"]["Username"].values:
                        st.warning("Staff username already exists!")
                    else:
                        new_row = pd.DataFrame([{
                            "Username": new_staff,
                            "Role": role,
                            "Added_On": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        st.session_state["staff_df"] = pd.concat([st.session_state["staff_df"], new_row], ignore_index=True)
                        save_excel(st.session_state["staff_df"], STAFF_FILE)
                        st.success(f"Staff **{new_staff}** added successfully!")

            st.dataframe(st.session_state["staff_df"], use_container_width=True)
        else:
            st.info("You don’t have access to this section.")

else:
    st.info("👈 Please log in using the sidebar to continue.")
