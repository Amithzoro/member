import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, timedelta
import pytz
import os
import calendar

# ---------- CONFIG ----------
st.set_page_config(page_title="Gym Management System", layout="centered")
EXCEL_FILE = "staff_logins.xlsx"
MEMBER_FILE = "gym_members.xlsx"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# ---------- LOAD / SAVE ----------
def load_data(sheet_name="Users"):
    if os.path.exists(EXCEL_FILE):
        try:
            return pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
        except:
            pass
    if sheet_name == "Login_Log":
        return pd.DataFrame(columns=["Username", "Role", "Login_Time"])
    else:
        return pd.DataFrame(columns=["Username", "Password", "Role"])

def save_data(users_df, log_df):
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

def load_members():
    if os.path.exists(MEMBER_FILE):
        return pd.read_excel(MEMBER_FILE)
    else:
        return pd.DataFrame(columns=["Name", "Membership_Type", "Start_Date", "End_Date"])

def save_members(df):
    df.to_excel(MEMBER_FILE, index=False)

# ---------- DEFAULT ACCOUNT ----------
users_df = load_data("Users")
log_df = load_data("Login_Log")

DEFAULT_OWNER = "owner"
DEFAULT_PASS = "gym123"

if DEFAULT_OWNER not in users_df["Username"].values:
    hashed_pw = bcrypt.hashpw(DEFAULT_PASS.encode(), bcrypt.gensalt()).decode()
    default_user = pd.DataFrame([{
        "Username": DEFAULT_OWNER,
        "Password": hashed_pw,
        "Role": "owner"
    }])
    users_df = pd.concat([users_df, default_user], ignore_index=True)
    save_data(users_df, log_df)

# ---------- PASSWORD CHECK ----------
def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

# ---------- APP ----------
st.title("🏋️ Gym Management System")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------- LOGIN ----------
if not st.session_state.logged_in:
    st.subheader("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in users_df["Username"].values:
            user_row = users_df[users_df["Username"] == username].iloc[0]
            if check_password(password, user_row["Password"]):
                st.session_state.logged_in = True
                st.session_state.role = user_row["Role"]
                st.session_state.username = username
                login_time = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                log_df = pd.concat([log_df, pd.DataFrame([{
                    "Username": username,
                    "Role": user_row["Role"],
                    "Login_Time": login_time
                }])], ignore_index=True)
                save_data(users_df, log_df)
                st.success(f"✅ Welcome, {username}!")
                st.rerun()
            else:
                st.error("❌ Incorrect password")
        else:
            st.error("❌ User not found")

# ---------- AFTER LOGIN ----------
else:
    username = st.session_state.username
    role = st.session_state.role
    st.sidebar.success(f"Logged in as: {username} ({role})")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.write(f"### Welcome, {username.upper()}!")

    # OWNER DASHBOARD
    if role == "owner":
        tab1, tab2, tab3 = st.tabs(["👥 Staff Logins", "🧾 Login History", "💪 Manage Members"])

        # TAB 1: Staff Logins
        with tab1:
            st.subheader("📋 Staff and Owner Logins")
            st.dataframe(users_df[["Username", "Password"]])

        # TAB 2: Login History
        with tab2:
            st.subheader("📅 Login History")
            st.dataframe(log_df.sort_values("Login_Time", ascending=False))

        # TAB 3: Manage Members
        with tab3:
            members_df = load_members()

            st.subheader("➕ Add New Member")
            name = st.text_input("Member Name")
            membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Half-Yearly", "Yearly"])
            start_date = st.date_input("Start Date", datetime.now().date())
            end_date = st.date_input("End Date", datetime.now().date() + timedelta(days=30))

            if st.button("Add Member"):
                if not name.strip():
                    st.warning("Please enter a member name.")
                else:
                    new_member = pd.DataFrame([{
                        "Name": name,
                        "Membership_Type": membership_type,
                        "Start_Date": start_date,
                        "End_Date": end_date
                    }])
                    members_df = pd.concat([members_df, new_member], ignore_index=True)
                    save_members(members_df)
                    st.success(f"✅ Member '{name}' added successfully!")

            st.markdown("### 🧾 Current Members")
            st.dataframe(members_df)

            # Expiring soon (7 days)
            if not members_df.empty:
                members_df["End_Date"] = pd.to_datetime(members_df["End_Date"])
                today = datetime.now().date()
                upcoming = members_df[
                    (members_df["End_Date"].dt.date <= today + timedelta(days=7)) &
                    (members_df["End_Date"].dt.date >= today)
                ]
                if not upcoming.empty:
                    expiring_names = ", ".join(upcoming["Name"].tolist())
                    st.toast(f"⚠️ Memberships expiring soon: {expiring_names}", icon="⏰")

    # STAFF DASHBOARD
    else:
        st.subheader("📅 Your Login History")
        staff_logs = log_df[log_df["Username"] == username]
        st.dataframe(staff_logs.sort_values("Login_Time", ascending=False))
