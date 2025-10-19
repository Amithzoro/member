import streamlit as st
import pandas as pd
import bcrypt
import calendar
from datetime import datetime
import pytz
import os

# -----------------------------
# CONFIG
# -----------------------------
TIMEZONE = pytz.timezone("Asia/Kolkata")
EXCEL_FILE = "gym_data.xlsx"

# -----------------------------
# Initialize default data
# -----------------------------
if not os.path.exists(EXCEL_FILE):
    users_df = pd.DataFrame([
        {"Username": "vineeth", "Password": bcrypt.hashpw("Panda@2006".encode(), bcrypt.gensalt()).decode(), "Role": "owner"},
        {"Username": "amith", "Password": bcrypt.hashpw("Amith@123".encode(), bcrypt.gensalt()).decode(), "Role": "staff"},
    ])
    members_df = pd.DataFrame(columns=["Full_Name", "Phone", "Membership_Type", "Added_By", "Added_On"])
    log_df = pd.DataFrame(columns=["Username", "Role", "Login_Time", "Date"])

    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

# -----------------------------
# Load Data
# -----------------------------
def load_data():
    xls = pd.ExcelFile(EXCEL_FILE)
    users_df = pd.read_excel(xls, "Users")
    members_df = pd.read_excel(xls, "Members")
    log_df = pd.read_excel(xls, "Login_Log")
    return users_df, members_df, log_df

# -----------------------------
# Save Data
# -----------------------------
def save_data(users_df, members_df, log_df):
    # Convert to string to avoid Excel value type errors
    users_df = users_df.astype(str)
    members_df = members_df.astype(str)
    log_df = log_df.astype(str)

    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

    # Monthly auto-backup
    month_name = calendar.month_name[datetime.now(TIMEZONE).month]
    backup_file = f"gym_data_{month_name[:3]}.xlsx"
    with pd.ExcelWriter(backup_file, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

# -----------------------------
# Login Function
# -----------------------------
def login(username, password, users_df):
    user = users_df[users_df["Username"] == username]
    if not user.empty:
        hashed_pw = user.iloc[0]["Password"].encode()
        if bcrypt.checkpw(password.encode(), hashed_pw):
            return user.iloc[0]["Role"]
    return None

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Gym Manager", page_icon="💪", layout="centered")

st.title("🏋️‍♂️ Gym Management System")

users_df, members_df, log_df = load_data()

tab_login, tab_members, tab_logs = st.tabs(["🔑 Login", "👥 Members", "📘 Login Records"])

# -----------------------------
# LOGIN TAB
# -----------------------------
with tab_login:
    st.subheader("Login Portal")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        role = login(username, password, users_df)
        if role:
            now = datetime.now(TIMEZONE)
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%I:%M:%S %p")

            new_entry = pd.DataFrame([{
                "Username": username,
                "Role": role,
                "Login_Time": time_str,
                "Date": date_str
            }])

            log_df = pd.concat([log_df, new_entry], ignore_index=True)
            save_data(users_df, members_df, log_df)

            st.success(f"✅ Welcome {username}! Logged in as {role.upper()} at {time_str}")
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = role
        else:
            st.error("❌ Invalid username or password")

# -----------------------------
# MEMBERS TAB
# -----------------------------
with tab_members:
    if "logged_in" in st.session_state and st.session_state["logged_in"]:
        st.subheader("Add New Member")

        full_name = st.text_input("Full Name")
        phone = st.text_input("Phone Number")
        membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Yearly"])

        if st.button("Add Member"):
            if full_name and phone:
                now = datetime.now(TIMEZONE).strftime("%Y-%m-%d %I:%M:%S %p")
                added_by = st.session_state["username"]

                new_member = pd.DataFrame([{
                    "Full_Name": full_name,
                    "Phone": phone,
                    "Membership_Type": membership_type,
                    "Added_By": added_by,
                    "Added_On": now
                }])

                members_df = pd.concat([members_df, new_member], ignore_index=True)
                save_data(users_df, members_df, log_df)
                st.success(f"✅ Member '{full_name}' added successfully!")
            else:
                st.warning("Please enter both name and phone number.")

        st.divider()
        st.subheader("📋 Member List")
        st.dataframe(members_df)
    else:
        st.warning("Please log in first to access this section.")

# -----------------------------
# LOGIN RECORD TAB
# -----------------------------
with tab_logs:
    st.subheader("📅 Login History")
    st.dataframe(log_df)

    if "logged_in" in st.session_state and st.session_state["logged_in"]:
        if st.session_state["role"] == "owner":
            if st.button("🧹 Clear Logs"):
                log_df = pd.DataFrame(columns=["Username", "Role", "Login_Time", "Date"])
                save_data(users_df, members_df, log_df)
                st.success("✅ Logs cleared successfully!")
