import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime
import pytz
import os
import calendar

st.set_page_config(page_title="Gym Management Login", layout="centered")

EXCEL_FILE = "staff_logins.xlsx"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# ===================================
# LOAD / SAVE FUNCTIONS
# ===================================
def load_data(sheet_name="Users"):
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
        except ValueError:
            if sheet_name == "Login_Log":
                return pd.DataFrame(columns=["Username", "Role", "Login_Time"])
            else:
                return pd.DataFrame(columns=["Username", "Password", "Role"])
        return df
    else:
        if sheet_name == "Login_Log":
            return pd.DataFrame(columns=["Username", "Role", "Login_Time"])
        else:
            return pd.DataFrame(columns=["Username", "Password", "Role"])

def save_data(users_df, log_df):
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

    # Monthly backup
    month_name = calendar.month_name[datetime.now(TIMEZONE).month]
    backup_file = f"staff_logins_{month_name[:3]}.xlsx"
    with pd.ExcelWriter(backup_file, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

users_df = load_data("Users")
log_df = load_data("Login_Log")

# ===================================
# DEFAULT ACCOUNTS
# ===================================
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
    print("✅ Default owner account created: owner / gym123")

# ===================================
# AUTH FUNCTIONS
# ===================================
def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

# ===================================
# APP LAYOUT
# ===================================
st.title("🏋️ Gym Login System")
st.markdown("### For Owner and Staff Only")

menu = st.sidebar.radio("Menu", ["Login", "Add Staff (Owner Only)"])

# ===================================
# LOGIN SECTION
# ===================================
if menu == "Login":
    st.subheader("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")

    if login_btn:
        if username in users_df["Username"].values:
            user_row = users_df[users_df["Username"] == username].iloc[0]
            if check_password(password, user_row["Password"]):
                st.session_state["logged_in"] = True
                st.session_state["role"] = user_row["Role"]
                st.session_state["username"] = username

                login_time = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                log_df = pd.concat([log_df, pd.DataFrame([{
                    "Username": username,
                    "Role": user_row["Role"],
                    "Login_Time": login_time
                }])], ignore_index=True)
                save_data(users_df, log_df)
                st.success(f"Welcome, {username}!")

                st.rerun()
            else:
                st.error("❌ Incorrect password")
        else:
            st.error("❌ User not found")

# ===================================
# AFTER LOGIN
# ===================================
if "logged_in" in st.session_state and st.session_state["logged_in"]:
    role = st.session_state["role"]
    username = st.session_state["username"]

    st.sidebar.success(f"Logged in as {role}")
    logout = st.sidebar.button("Logout")

    if logout:
        st.session_state.clear()
        st.rerun()

    st.write(f"### Welcome, {username.upper()}!")

    # OWNER DASHBOARD
    if role == "owner":
        st.subheader("📋 Staff and Owner Logins")
        # ✅ Show only Username and Password
        st.dataframe(users_df[["Username", "Password"]])

        st.subheader("📅 Login History")
        st.dataframe(log_df.sort_values("Login_Time", ascending=False))

    # STAFF DASHBOARD
    elif role == "staff":
        st.subheader("📅 Your Login History")
        staff_logs = log_df[log_df["Username"] == username]
        st.dataframe(staff_logs.sort_values("Login_Time", ascending=False))

# ===================================
# OWNER ADD STAFF
# ===================================
if menu == "Add Staff (Owner Only)":
    st.subheader("👤 Add New Staff Account")
    username = st.text_input("New Staff Username")
    password = st.text_input("Password", type="password")

    if st.button("Create Staff Account"):
        if username in users_df["Username"].values:
            st.warning("Username already exists!")
        else:
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            new_staff = pd.DataFrame([{
                "Username": username,
                "Password": hashed_pw,
                "Role": "staff"
            }])
            users_df = pd.concat([users_df, new_staff], ignore_index=True)
            save_data(users_df, log_df)
            st.success(f"✅ Staff account created for '{username}'!")
