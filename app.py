# ---------- Import Libraries ----------
import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime
import pytz
import os

# ---------- CONFIG ----------
TIMEZONE = pytz.timezone("Asia/Kolkata")
DATA_FILE = "members.xlsx"

# --- User credentials (you can add more users) ---
USERS = {
    "admin": bcrypt.hashpw("1234".encode(), bcrypt.gensalt()),  # username: admin, password: 1234
    "trainer": bcrypt.hashpw("gym2025".encode(), bcrypt.gensalt())
}

# ---------- PAGE SETTINGS ----------
st.set_page_config(page_title="💪 Gym Membership Tracker", layout="wide")

st.title("🏋️‍♂️ Gym Membership Tracker")
st.caption("Track members, expiry dates, and reminders easily.")

# ---------- LOAD / INITIALIZE DATA ----------
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Name", "Phone", "Start_Date", "End_Date", "Recorded_By"])
    df.to_excel(DATA_FILE, index=False)

members_df = pd.read_excel(DATA_FILE)

# ---------- LOGIN ----------
st.sidebar.header("🔐 Login")

username = st.sidebar.text_input("Username")
password_input = st.sidebar.text_input("Password", type="password")
login_btn = st.sidebar.button("Login")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

if login_btn:
    if username in USERS and bcrypt.checkpw(password_input.encode(), USERS[username]):
        st.session_state.logged_in = True
        st.session_state.username = username
        st.sidebar.success(f"✅ Welcome, {username}!")
    else:
        st.sidebar.error("❌ Invalid username or password")

# ---------- MAIN APP ----------
if st.session_state.logged_in:

    st.success(f"Logged in as **{st.session_state.username}**")

    # ---------- ADD NEW MEMBER ----------
    st.subheader("➕ Add New Member")
    with st.form("add_member_form"):
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        start_date = st.date_input("Start Date", datetime.now(TIMEZONE).date())
        end_date = st.date_input("End Date")
        recorded_by = st.text_input("Recorded By", st.session_state.username)

        submitted = st.form_submit_button("Add Member")
        if submitted:
            new_data = pd.DataFrame([{
                "Name": name,
                "Phone": phone,
                "Start_Date": start_date,
                "End_Date": end_date,
                "Recorded_By": recorded_by
            }])
            members_df = pd.concat([members_df, new_data], ignore_index=True)
            members_df.to_excel(DATA_FILE, index=False)
            st.success(f"✅ Added member: {name}")

    # ---------- VIEW & FILTER ----------
    st.subheader("📋 Member List")
    filter_name = st.text_input("Search by Name")
    if filter_name:
        filtered_df = members_df[members_df["Name"].str.contains(filter_name, case=False, na=False)]
        st.dataframe(filtered_df)
    else:
        st.dataframe(members_df)

    # ---------- EXPIRY REMINDERS ----------
    st.subheader("🔔 Expiry Reminders")

    members_df["End_Date"] = pd.to_datetime(members_df["End_Date"], errors="coerce")
    today = pd.Timestamp.now(TIMEZONE).normalize()

    members_df["Days_Left"] = members_df["End_Date"].apply(
        lambda x: (x - today).days if pd.notnull(x) else None
    )

    expiring = members_df[(members_df["Days_Left"] >= 0) & (members_df["Days_Left"] <= 3)]

    if not expiring.empty:
        st.warning("⚠️ Memberships expiring soon:")
        st.table(expiring[["Name", "Phone", "End_Date", "Days_Left", "Recorded_By"]])
    else:
        st.success("✅ No memberships expiring soon.")

    # ---------- LOGOUT ----------
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

else:
    st.info("👈 Please login using the sidebar to continue.")
