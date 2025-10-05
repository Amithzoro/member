import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.text import MIMEText

# -----------------------------
# BASIC CONFIGURATION
# -----------------------------
OWNER_EMAIL = "owner@gmail.com"        # Owner’s Gmail (optional)
OWNER_NUMBER = "+917019384280"         # Owner’s number for contact
OWNER_APP_PASSWORD = "your_app_password_here"  # Only if you want email notifications
ADMIN_USER = "admin"
ADMIN_PASSWORD = "1234"

FILE_PATH = "membership.xlsx"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# -----------------------------
# Initialize Session
# -----------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=[
        "Name", "Email", "Phone", "Plan", "Join Date", "Expiry Date", "Password", "Status"
    ])

# -----------------------------
# Data Persistence
# -----------------------------
def load_data():
    try:
        df = pd.read_excel(FILE_PATH)
        st.session_state.df = df
    except FileNotFoundError:
        st.session_state.df = pd.DataFrame(columns=[
            "Name", "Email", "Phone", "Plan", "Join Date", "Expiry Date", "Password", "Status"
        ])

def save_data(df):
    df.to_excel(FILE_PATH, index=False)
    st.session_state.df = df
    st.success("💾 Data saved successfully!")

# -----------------------------
# Email Utility (optional)
# -----------------------------
def send_email(to_email, subject, message):
    """Send email using Gmail SMTP (optional)."""
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = OWNER_EMAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(OWNER_EMAIL, OWNER_APP_PASSWORD)
            server.send_message(msg)
        st.toast(f"📧 Email sent to {to_email}", icon="✅")
    except Exception as e:
        st.warning(f"Email failed: {e}")

# -----------------------------
# Authentication
# -----------------------------
def check_admin_login(username, password):
    return username == ADMIN_USER and password == ADMIN_PASSWORD

def login_form():
    st.markdown("### 🔒 Admin Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if check_admin_login(username, password):
                st.session_state.logged_in = True
                load_data()
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

def logout():
    st.session_state.logged_in = False
    st.rerun()

# -----------------------------
# Membership Plan Logic (1 month – 1 year)
# -----------------------------
PLAN_DURATIONS = {
    "1 Month": 30,
    "3 Months": 90,
    "6 Months": 180,
    "12 Months (1 Year)": 365
}

def calculate_expiry(join_date, plan):
    days = PLAN_DURATIONS.get(plan, 365)
    join_dt = datetime.strptime(join_date, "%Y-%m-%d %H:%M:%S")
    expiry = join_dt + timedelta(days=days)
    return expiry.strftime("%Y-%m-%d")

def update_membership_status(df):
    today = datetime.now(TIMEZONE).date()
    df["Status"] = df["Expiry Date"].apply(
        lambda x: "Expired" if datetime.strptime(x, "%Y-%m-%d").date() < today else "Active"
    )
    return df

def send_expiry_reminders(df):
    today = datetime.now(TIMEZONE).date()
    for _, row in df.iterrows():
        expiry = datetime.strptime(row["Expiry Date"], "%Y-%m-%d").date()
        days_left = (expiry - today).days
        if 0 < days_left <= 5:
            send_email(
                row["Email"],
                "Membership Expiry Reminder ⚠️",
                f"Dear {row['Name']},\n\nYour {row['Plan']} plan will expire on {row['Expiry Date']}."
                f"\nPlease renew soon.\n\nContact: {OWNER_NUMBER}"
            )

# -----------------------------
# Dashboard
# -----------------------------
def display_dashboard(df):
    st.subheader("📊 Membership Dashboard")

    df = update_membership_status(df)
    total = len(df)
    active = (df["Status"] == "Active").sum()
    expired = (df["Status"] == "Expired").sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Members", total)
    c2.metric("Active", active)
    c3.metric("Expired", expired)

    st.dataframe(df, use_container_width=True)

# -----------------------------
# Add Member
# -----------------------------
def add_member_section():
    st.subheader("➕ Register New Member")

    with st.form("add_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        plan = st.selectbox("Select Plan", list(PLAN_DURATIONS.keys()))
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Add Member", type="primary")

        if submitted:
            if not (name and email and phone and password):
                st.warning("Please fill all fields.")
                return
            df = st.session_state.df
            if email in df["Email"].values:
                st.error("This email already exists!")
                return

            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            join_date = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            expiry_date = calculate_expiry(join_date, plan)

            new_row = {
                "Name": name,
                "Email": email,
                "Phone": phone,
                "Plan": plan,
                "Join Date": join_date,
                "Expiry Date": expiry_date,
                "Password": hashed_pw,
                "Status": "Active"
            }

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)

            # Optional: email confirmation
            send_email(
                email,
                "Membership Activated ✅",
                f"Hello {name},\n\nYou have subscribed to the {plan} plan.\n"
                f"Your membership is valid until {expiry_date}.\n\nContact: {OWNER_NUMBER}"
            )
            st.success("✅ Member added successfully!")

# -----------------------------
# Manage Members
# -----------------------------
def manage_members_section():
    st.subheader("📝 Manage Members")
    df = st.session_state.df
    df = update_membership_status(df)

    edited = st.data_editor(
        df.drop(columns=["Password"], errors="ignore"),
        key="editor", use_container_width=True
    )

    if st.button("💾 Save Changes", type="primary"):
        for index, row in edited.iterrows():
            if index in df.index:
                df.loc[index, "Name"] = row["Name"]
                df.loc[index, "Phone"] = row["Phone"]
                df.loc[index, "Plan"] = row["Plan"]
                df.loc[index, "Status"] = row["Status"]
        save_data(df)
        st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Delete Member")
    emails = df["Email"].tolist()
    if emails:
        selected = st.selectbox("Select Email to Delete", emails)
        if st.button("Delete Member", type="danger"):
            df = df[df["Email"] != selected]
            save_data(df)
            st.success(f"Deleted member {selected}")
            st.rerun()
    else:
        st.info("No members found.")

# -----------------------------
# MAIN APP
# -----------------------------
st.title("🛡️ Membership Management Portal")
st.markdown("Manage membership plans (1 month to 1 year) and expiry easily.")

if not st.session_state.logged_in:
    login_form()
else:
    st.sidebar.button("Logout", on_click=logout, type="secondary")
    st.sidebar.info(f"📞 Owner Contact: {OWNER_NUMBER}")

    df = st.session_state.df
    df = update_membership_status(df)
    send_expiry_reminders(df)  # Optional email reminders

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Add Member", "🛠 Manage Members"])
    with tab1: display_dashboard(df)
    with tab2: add_member_section()
    with tab3: manage_members_section()
