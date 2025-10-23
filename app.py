import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os

EXCEL_FILE = "members.xlsx"
IST = pytz.timezone("Asia/Kolkata")

# Roles
USERS = {
    "vineeth": {"password": "panda@2006", "role": "Owner"},
    "rahul": {"password": "staff123", "role": "Staff"}
}

DURATION_MAP = {"Monthly": 30, "Quarterly": 90, "Yearly": 365}

# Ensure Excel file exists
if not os.path.exists(EXCEL_FILE):
    df = pd.DataFrame(columns=["Member_Name", "Start_Date", "Expiry_Date", "Registration_Time_IST", "Amount"])
    df.to_excel(EXCEL_FILE, index=False)

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

# --- Streamlit App ---
st.title("Gym Membership System")

# Login
st.sidebar.subheader("Login")
username = st.sidebar.text_input("Username", key="login_user")
password = st.sidebar.text_input("Password", type="password", key="login_pass")
login_btn = st.sidebar.button("Login", key="login_btn")

if login_btn:
    if username in USERS and USERS[username]["password"] == password:
        role = USERS[username]["role"]
        st.success(f"✅ Logged in as {username} ({role})")

        if "members_df" not in st.session_state:
            st.session_state.members_df = load_members()

        df = st.session_state.members_df

        # --- Expiring Members Reminder ---
        expiring_df = get_expiring_members(df, days=7)
        if not expiring_df.empty:
            st.warning("⚠️ Members expiring within 7 days:")
            st.dataframe(expiring_df[["Member_Name", "Expiry_Date"]])

        # --- Add Member Section ---
        st.subheader("Add Member")
        new_name = st.text_input("Member Name", key="add_name")
        duration_option = st.selectbox("Membership Duration", list(DURATION_MAP.keys()), key="add_duration")
        amount = st.number_input("Amount Paid", min_value=0, value=0, key="add_amount")
        if st.button("Add Member", key="add_btn"):
            if new_name:
                st.session_state.members_df = register_member(df, new_name, DURATION_MAP[duration_option], amount)
                st.success(f"✅ Member '{new_name}' added with {duration_option} duration.")
            else:
                st.warning("Please enter a member name.")

        # --- Delete Member (Owner Only) ---
        if role == "Owner":
            st.subheader("Delete Member")
            if not df.empty:
                member_to_delete = st.selectbox("Select Member to Delete", df["Member_Name"].tolist(), key="delete_select")
                if st.button("Delete Member", key="delete_btn"):
                    st.session_state.members_df = delete_member(df, member_to_delete)
                    st.success(f"✅ Member '{member_to_delete}' deleted.")

        # --- Show All Members ---
        st.subheader("All Members")
        st.dataframe(st.session_state.members_df)

    else:
        st.error("❌ Invalid username or password")
