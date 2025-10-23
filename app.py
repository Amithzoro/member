import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os

# Constants
EXCEL_FILE = "members.xlsx"
IST = pytz.timezone("Asia/Kolkata")

# Roles
USERS = {
    "owner": {"password": "ownerpass", "role": "Owner"},
    "staff": {"password": "staffpass", "role": "Staff"}
}

# Duration mapping
DURATION_MAP = {"Monthly": 30, "Quarterly": 90, "Yearly": 365}

# Ensure Excel file exists
if not os.path.exists(EXCEL_FILE):
    df = pd.DataFrame(columns=["Member_Name", "Start_Date", "Expiry_Date", "Registration_Time_IST", "Amount"])
    df.to_excel(EXCEL_FILE, index=False)

# Helper functions
def get_ist_now():
    return datetime.now(IST)

def load_members():
    return pd.read_excel(EXCEL_FILE)

def save_members(df):
    df.to_excel(EXCEL_FILE, index=False)

def get_expiring_members(df, days=7):
    today = get_ist_now().date()
    expiry_dates = pd.to_datetime(df["Expiry_Date"], errors="coerce").dt.date
    valid_mask = expiry_dates.notna()
    soon_expire_mask = valid_mask & ((expiry_dates - today).apply(lambda x: x.days) <= days)
    return df[soon_expire_mask].copy()

def register_member(df, username, duration_days=30, amount=0):
    now_ist = get_ist_now()
    start_date = now_ist.date()
    expiry_date = start_date + timedelta(days=duration_days)
    new_member = {
        "Member_Name": username,
        "Start_Date": start_date,
        "Expiry_Date": expiry_date,
        "Registration_Time_IST": now_ist,
        "Amount": amount
    }
    df = pd.concat([df, pd.DataFrame([new_member])], ignore_index=True)
    save_members(df)
    return df

def delete_member(df, member_name):
    df = df[df["Member_Name"] != member_name]
    save_members(df)
    return df

# Streamlit App
st.title("Gym Membership System")

# Login
st.sidebar.subheader("Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")
login_btn = st.sidebar.button("Login")

if login_btn:
    if username in USERS and USERS[username]["password"] == password:
        role = USERS[username]["role"]
        st.success(f"✅ Logged in as {username} ({role})")
        members_df = load_members()

        # Expiry Reminder for Owner & Staff
        expiring_df = get_expiring_members(members_df, days=7)
        if not expiring_df.empty:
            st.warning("⚠️ Members expiring within 7 days:")
            st.dataframe(expiring_df[["Member_Name", "Expiry_Date"]])

        # Add Member
        st.subheader("Add Member")
        new_name = st.text_input("Member Name")
        duration_option = st.selectbox("Membership Duration", list(DURATION_MAP.keys()))
        amount = st.number_input("Amount Paid", min_value=0, value=0)
        add_btn = st.button("Add Member")

        if add_btn:
            if new_name:
                members_df = register_member(members_df, new_name, DURATION_MAP[duration_option], amount)
                st.success(f"✅ Member '{new_name}' added with {duration_option} duration.")
            else:
                st.warning("Please enter a member name.")

        # Only Owner can delete or edit members
        if role == "Owner":
            st.subheader("Delete Member")
            member_to_delete = st.selectbox("Select Member", members_df["Member_Name"].tolist())
            delete_btn = st.button("Delete Member")
            if delete_btn:
                members_df = delete_member(members_df, member_to_delete)
                st.success(f"✅ Member '{member_to_delete}' deleted.")

        # Show all members
        st.subheader("All Members")
        st.dataframe(members_df)

    else:
        st.error("❌ Invalid username or password")
