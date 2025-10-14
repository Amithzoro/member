import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime
import pytz
import os
from openpyxl import load_workbook

st.set_page_config(page_title="Gym Membership Manager", page_icon="💪", layout="centered")

# ======================================
# FILE SETUP
# ======================================
MONTH_NAME = datetime.now().strftime("%b")  # Jan, Feb, Mar...
EXCEL_FILE = f"membership_{MONTH_NAME}.xlsx"

# Create default Excel if not exists
if not os.path.exists(EXCEL_FILE):
    members_df = pd.DataFrame(columns=[
        "Username", "Password", "Role", "Name", "Phone", "Start_Date",
        "End_Date", "Membership_Type", "Amount", "Recorded_At", "Recorded_By"
    ])
    log_df = pd.DataFrame(columns=["Username", "Role", "Login_Time"])
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

# ======================================
# LOAD DATA
# ======================================
def load_data():
    xls = pd.ExcelFile(EXCEL_FILE)
    members_df = pd.read_excel(xls, "Members")
    log_df = pd.read_excel(xls, "Login_Log")
    return members_df, log_df

def save_data(members_df, log_df):
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

# ======================================
# DEFAULT OWNER CREATION
# ======================================
members_df, log_df = load_data()

if "owner" not in members_df["Username"].values:
    hashed_pw = bcrypt.hashpw("gym123".encode(), bcrypt.gensalt()).decode()
    owner_row = pd.DataFrame([{
        "Username": "owner",
        "Password": hashed_pw,
        "Role": "owner",
        "Name": "Gym Owner",
        "Phone": "",
        "Start_Date": None,
        "End_Date": None,
        "Membership_Type": "",
        "Amount": 0,
        "Recorded_At": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
        "Recorded_By": "system"
    }])
    members_df = pd.concat([members_df, owner_row], ignore_index=True)
    save_data(members_df, log_df)

# ======================================
# LOGIN SYSTEM
# ======================================
st.title("🏋️ Gym Membership Management")

menu = ["Login", "Sign Up"]
choice = st.sidebar.selectbox("Select Action", menu)

members_df, log_df = load_data()

if choice == "Sign Up":
    st.subheader("Create New Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["member", "owner"])
    name = st.text_input("Full Name")
    phone = st.text_input("Phone")
    membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Yearly"])
    amount = st.number_input("Amount Paid (₹)", min_value=0)
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")

    if st.button("Create Account"):
        if username in members_df["Username"].values:
            st.warning("Username already exists!")
        else:
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            new_user = pd.DataFrame([{
                "Username": username,
                "Password": hashed_pw,
                "Role": role,
                "Name": name,
                "Phone": phone,
                "Start_Date": start_date,
                "End_Date": end_date,
                "Membership_Type": membership_type,
                "Amount": amount,
                "Recorded_At": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
                "Recorded_By": "system"
            }])
            members_df = pd.concat([members_df, new_user], ignore_index=True)
            save_data(members_df, log_df)
            st.success("Account created successfully!")
            st.rerun()

elif choice == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user_row = members_df[members_df["Username"] == username]
        if not user_row.empty and bcrypt.checkpw(password.encode(), user_row["Password"].values[0].encode()):
            st.success(f"Welcome, {username} 👋")
            role = user_row["Role"].values[0]

            # Record login time
            tz = pytz.timezone("Asia/Kolkata")
            now = datetime.now(tz).strftime("%Y-%m-%d %I:%M:%S %p")
            new_log = pd.DataFrame([{"Username": username, "Role": role, "Login_Time": now}])
            log_df = pd.concat([log_df, new_log], ignore_index=True)
            save_data(members_df, log_df)

            # Owner Dashboard
            if role == "owner":
                st.header("📋 Owner Dashboard")
                members_df["End_Date"] = pd.to_datetime(members_df["End_Date"], errors="coerce")
                today = pd.Timestamp.today()
                members_df["Days_Left"] = (members_df["End_Date"] - today).dt.days
                st.dataframe(members_df[[
                    "Username", "Name", "Phone", "Membership_Type",
                    "Start_Date", "End_Date", "Days_Left", "Amount"
                ]])

                st.subheader("🕒 Login Log")
                st.dataframe(log_df.tail(20))

            # Member Dashboard
            else:
                st.header("💼 Member Dashboard")
                user_data = user_row.iloc[0]
                st.write(f"**Name:** {user_data['Name']}")
                st.write(f"**Phone:** {user_data['Phone']}")
                st.write(f"**Membership:** {user_data['Membership_Type']}")
                st.write(f"**Start Date:** {user_data['Start_Date']}")
                st.write(f"**End Date:** {user_data['End_Date']}")
                st.write(f"**Amount Paid:** ₹{user_data['Amount']}")

                end_date = pd.to_datetime(user_data["End_Date"], errors="coerce")
                if pd.notna(end_date):
                    days_left = (end_date - pd.Timestamp.today()).days
                    st.write(f"⏳ Days Left: **{days_left}**")
                else:
                    st.write("End date not set properly.")

        else:
            st.error("Invalid username or password ❌")
