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
EXCEL_FILE = "staff_logins.xlsx"

# -----------------------------
# Initialize default data
# -----------------------------
if not os.path.exists(EXCEL_FILE):
    df_users = pd.DataFrame([
        {"Username": "vineeth", "Password": bcrypt.hashpw("Panda@2006".encode(), bcrypt.gensalt()).decode(), "Role": "owner"},
        {"Username": "amith", "Password": bcrypt.hashpw("Amith@123".encode(), bcrypt.gensalt()).decode(), "Role": "staff"},
    ])
    df_log = pd.DataFrame(columns=["Username", "Role", "Login_Time", "Date"])
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        df_users.to_excel(writer, sheet_name="Users", index=False)
        df_log.to_excel(writer, sheet_name="Login_Log", index=False)

# -----------------------------
# Load Data
# -----------------------------
def load_data():
    xls = pd.ExcelFile(EXCEL_FILE)
    users_df = pd.read_excel(xls, "Users")
    log_df = pd.read_excel(xls, "Login_Log")
    return users_df, log_df

# -----------------------------
# Save Data Safely
# -----------------------------
def save_data(users_df, log_df):
    # Convert to strings to avoid Excel dtype errors
    users_df = users_df.astype(str)
    log_df = log_df.astype(str)

    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

    # Monthly auto-backup
    month_name = calendar.month_name[datetime.now(TIMEZONE).month]
    backup_file = f"staff_logins_{month_name[:3]}.xlsx"
    with pd.ExcelWriter(backup_file, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
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
# Streamlit App
# -----------------------------
st.set_page_config(page_title="Gym Login System", page_icon="💪", layout="centered")
st.title("🏋️‍♂️ Gym Login Portal")

users_df, log_df = load_data()

tab_login, tab_log = st.tabs(["🔑 Login", "📘 Login Records"])

with tab_login:
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
            save_data(users_df, log_df)

            st.success(f"✅ Welcome {username}! Logged in as {role.upper()} at {time_str}")
        else:
            st.error("❌ Invalid username or password")

with tab_log:
    st.subheader("📅 Login Records")
    st.dataframe(log_df)

    if st.button("🧹 Clear Logs (Owner Only)"):
        if "vineeth" in log_df["Username"].values:
            log_df = pd.DataFrame(columns=["Username", "Role", "Login_Time", "Date"])
            save_data(users_df, log_df)
            st.success("Logs cleared successfully.")
        else:
            st.warning("Only the owner can clear logs.")
