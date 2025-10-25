import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os

# --- Configuration ---
EXCEL_FILE = "members.xlsx"
IST = pytz.timezone("Asia/Kolkata")

# --- User credentials ---
USERS = {
    "vineeth": {"password": "panda@2006", "role": "Owner"},
    "rahul": {"password": "staff123", "role": "Staff"}
}

# --- Duration options ---
DURATION_MAP = {"Monthly": 30, "Quarterly": 90, "Yearly": 365}

# --- Ensure Excel file exists ---
if not os.path.exists(EXCEL_FILE):
    df = pd.DataFrame(columns=[
        "Member_Name", "Start_Date", "Expiry_Date",
        "Registration_Time_IST", "Duration", "Amount"
    ])
    df.to_excel(EXCEL_FILE, index=False)

# --- Helper functions ---
def get_ist_now():
    return datetime.now(IST)

def load_members():
    return pd.read_excel(EXCEL_FILE)

def save_members(df):
    df.to_excel(EXCEL_FILE, index=False)

def get_expiring_members(df, days=7):
    today = get_ist_now().date()
    expiry_dates = pd.to_datetime(df["Expiry_Date"], errors="coerce").dt.date
    soon_expire_mask = expiry_dates.notna() & (
        (expiry_dates - today).apply(lambda x: x.days <= days and x.days >= 0)
    )
    return df[soon_expire_mask].copy()

def add_member(df, name, start_date, duration_days, amount):
    now = get_ist_now()
    expiry_date = start_date + timedelta(days=duration_days)
    new_member = {
        "Member_Name": name,
        "Start_Date": start_date,
        "Expiry_Date": expiry_date,
        "Registration_Time_IST": now.strftime("%Y-%m-%d %H:%M:%S"),
        "Duration": f"{duration_days} days",
        "Amount": amount
    }
    df = pd.concat([df, pd.DataFrame([new_member])], ignore_index=True)
    save_members(df)
    return df

def delete_member(df, name):
    df = df[df["Member_Name"] != name]
    save_members(df)
    return df

# --- Streamlit App ---
st.set_page_config("Gym Membership System", layout="centered")
st.title("🏋️ Gym Membership Management")

# --- Session state ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = None

# --- Login Section ---
if not st.session_state.logged_in:
    st.sidebar.header("🔐 Login")
    username = st.sidebar.text_input("Username", key="login_user")
    password = st.sidebar.text_input("Password", type="password", key="login_pass")
    login_btn = st.sidebar.button("Login")

    if login_btn:
        if username in USERS and USERS[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.role = USERS[username]["role"]
            st.session_state.username = username
            st.success(f"✅ Logged in as {username} ({st.session_state.role})")
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

else:
    # --- Logged in UI ---
    st.sidebar.success(f"Logged in as {st.session_state.username} ({st.session_state.role})")
    logout = st.sidebar.button("Logout 🚪")
    if logout:
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = None
        st.rerun()

    # Load members
    members_df = load_members()

    # --- Stats Section ---
    total_members = len(members_df)
    expiring_df = get_expiring_members(members_df)
    expiring_count = len(expiring_df)

    st.markdown(
        f"""
        ### 📊 Summary
        - 👥 **Total Members:** {total_members}  
        - ⏳ **Expiring Soon (within 7 days):** {expiring_count}
        """
    )

    # --- Reminder Section ---
    if not expiring_df.empty:
        st.warning("⚠️ Members expiring within 7 days:")
        st.dataframe(expiring_df[["Member_Name", "Expiry_Date"]])

    # --- Add Member Section ---
    st.subheader("➕ Add / Register Member")
    with st.form("add_member_form"):
        name = st.text_input("Member Name")
        start_date = st.date_input("Start Date", value=datetime.now().date())
        duration = st.selectbox("Membership Duration", list(DURATION_MAP.keys()))
        amount = st.number_input("Amount Paid (₹)", min_value=0, value=0)

        expiry_preview = start_date + timedelta(days=DURATION_MAP[duration])
        st.info(f"📅 Expected Expiry Date: **{expiry_preview}**")

        submitted = st.form_submit_button("Add Member")
        if submitted:
            if name.strip():
                members_df = add_member(members_df, name, start_date, DURATION_MAP[duration], amount)
                st.success(f"✅ Member '{name}' added successfully! Expiry: {expiry_preview}")
            else:
                st.warning("Please enter a valid member name.")

    # --- Delete Member (Owner only) ---
    if st.session_state.role == "Owner":
        st.subheader("🗑 Delete Member")
        if not members_df.empty:
            delete_name = st.selectbox("Select member to delete", members_df["Member_Name"].tolist())
            if st.button("Delete Selected Member"):
                members_df = delete_member(members_df, delete_name)
                st.success(f"🗑 Member '{delete_name}' deleted successfully.")
        else:
            st.info("No members to delete.")

    # --- All Members ---
    st.subheader("📋 All Members")
    if not members_df.empty:
        st.dataframe(members_df)
    else:
        st.info("No members found.")
