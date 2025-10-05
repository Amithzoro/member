import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import bcrypt
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Gym Membership Tracker", layout="wide")

# --- Custom CSS ---
st.markdown("""
<style>
    .stSelectbox, .stNumberInput, .stTextInput {
        background-color: #111827 !important;
        color: white !important;
        border-radius: 8px !important;
    }
    .stButton button {
        background-color: #2563eb;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        padding: 0.5em 1em;
        transition: 0.3s;
    }
    .stButton button:hover {
        background-color: #1e40af;
    }
</style>
""", unsafe_allow_html=True)

st.title("💪 Gym Membership & Sales Tracker")

# --- Load credentials ---
EMAIL_USER = st.secrets.get("EMAIL_USER", "")
EMAIL_PASS = st.secrets.get("EMAIL_PASS", "")
TWILIO_SID = st.secrets.get("TWILIO_SID", "")
TWILIO_AUTH = st.secrets.get("TWILIO_AUTH", "")
TWILIO_FROM = st.secrets.get("TWILIO_FROM", "")

# --- Helper Functions ---
def send_email(to, subject, body):
    if not EMAIL_USER or not EMAIL_PASS:
        st.warning("Email credentials not configured. Skipping email notifications.")
        return
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def send_whatsapp(phone, message):
    if not TWILIO_SID or not TWILIO_AUTH:
        st.warning("Twilio credentials not configured. Skipping WhatsApp notifications.")
        return
    client = Client(TWILIO_SID, TWILIO_AUTH)
    if not phone.startswith("+"):
        phone = "+91" + phone
    client.messages.create(from_=TWILIO_FROM, body=message, to=f"whatsapp:{phone}")

# --- Excel Data Handling ---
def load_data():
    path = "memberships.xlsx"
    expected_cols = [
        "Date", "Time", "Client Name", "Phone Number", "Client Email",
        "Membership Type", "Amount", "Payment Mode", "Notes",
        "Expiry Date", "Owner Email"
    ]
    try:
        df = pd.read_excel(path)
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        df = df[expected_cols]
    except FileNotFoundError:
        df = pd.DataFrame(columns=expected_cols)
        df.to_excel(path, index=False)
    return df

def save_data(df):
    df.to_excel("memberships.xlsx", index=False)

df = load_data()

# --- Owner Password File ---
PASSWORD_FILE = "owner_password.txt"

def set_owner_password(email, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    with open(PASSWORD_FILE, "wb") as f:
        f.write(hashed)
    with open("owner_email.txt", "w") as f:
        f.write(email)

def verify_owner_password(password):
    if not os.path.exists(PASSWORD_FILE):
        return False
    with open(PASSWORD_FILE, "rb") as f:
        hashed = f.read()
    return bcrypt.checkpw(password.encode(), hashed)

# --- Authentication ---
if "owner_logged_in" not in st.session_state:
    st.session_state["owner_logged_in"] = False

if not os.path.exists(PASSWORD_FILE):
    st.subheader("🧑‍💼 Create Owner Account")
    email = st.text_input("Owner Email")
    password = st.text_input("Create Password", type="password")
    confirm = st.text_input("Confirm Password", type="password")
    if st.button("Create Account"):
        if password == confirm and len(password) >= 6:
            set_owner_password(email, password)
            st.success("✅ Owner account created! Please log in.")
            st.stop()
        else:
            st.error("❌ Passwords do not match or too short.")
    st.stop()

if not st.session_state["owner_logged_in"]:
    st.subheader("🔐 Login")
    login_email = st.text_input("Email")
    login_password = st.text_input("Password", type="password")
    if st.button("Login"):
        if verify_owner_password(login_password):
            with open("owner_email.txt", "r") as f:
                saved_email = f.read().strip()
            if login_email.strip().lower() == saved_email.lower():
                st.session_state["owner_logged_in"] = True
                st.session_state["owner_email"] = login_email.strip().lower()
                st.success(f"✅ Logged in as {login_email}")
            else:
                st.error("❌ Email does not match the registered owner.")
        else:
            st.error("❌ Incorrect password.")
    st.stop()

owner_email = st.session_state["owner_email"]

st.sidebar.markdown(f"👋 Logged in as: **{owner_email}**")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.experimental_rerun()

# --- Main App ---
payment_modes = ["Cash", "UPI", "Card", "Net Banking", "Wallet"]

st.subheader("➕ Add New Member / Payment Entry")

col1, col2 = st.columns(2)
with col1:
    client_name = st.text_input("Client Name")
    phone_number = st.text_input("Phone Number (10 digits)")
    client_email = st.text_input("Client Email (optional)")
    membership_type = st.selectbox(
        "Membership Type",
        ["Monthly", "Quarterly", "Half-Yearly", "Yearly", "One-Time Session", "Other"]
    )
with col2:
    amount = st.number_input("Amount (₹)", min_value=0.0, step=0.01)
    payment_mode = st.selectbox("Payment Mode", payment_modes)
    notes = st.text_input("Notes (optional)")

if st.button("💾 Add Entry"):
    if not client_name.strip():
        st.error("⚠️ Please enter client name.")
    elif not phone_number.strip().isdigit() or len(phone_number.strip()) != 10:
        st.error("⚠️ Please enter a valid 10-digit phone number.")
    else:
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist)
        current_date = now_ist.strftime("%Y-%m-%d")
        current_time = now_ist.strftime("%I:%M:%S %p")

        plan_days = {
            "Monthly": 30,
            "Quarterly": 90,
            "Half-Yearly": 180,
            "Yearly": 365,
            "One-Time Session": 1,
            "Other": 0
        }
        duration_days = plan_days.get(membership_type, 0)
        expiry_date = (now_ist + timedelta(days=duration_days)).strftime("%Y-%m-%d") if duration_days > 0 else ""

        new_entry = {
            "Date": current_date,
            "Time": current_time,
            "Client Name": client_name.strip().title(),
            "Phone Number": phone_number.strip(),
            "Client Email": client_email.strip(),
            "Membership Type": membership_type,
            "Amount": amount,
            "Payment Mode": payment_mode,
            "Notes": notes,
            "Expiry Date": expiry_date,
            "Owner Email": owner_email
        }

        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        save_data(df)

        try:
            # Notify owner
            owner_msg = f"""
New Membership Added:

Client: {client_name.title()}
Phone: {phone_number}
Plan: {membership_type}
Amount: ₹{amount}
Expiry: {expiry_date}
Added by: {owner_email}
"""
            send_email(owner_email, f"New Member Added: {client_name.title()}", owner_msg)

            # Notify client
            client_msg = f"Hi {client_name.title()}, thanks for your payment of ₹{amount:.2f} for your {membership_type} plan! 💪 Expiry: {expiry_date}."
            send_whatsapp(phone_number, client_msg)

            if client_email:
                client_email_body = f"""
Hi {client_name.title()},

Thank you for your payment of ₹{amount:.2f} for your {membership_type} membership.

Payment Mode: {payment_mode}
Date: {current_date}, Time: {current_time}
Expiry Date: {expiry_date}

See you soon at the gym! 💪
"""
                send_email(client_email, "Membership Confirmation", client_email_body)

            st.success(f"✅ Entry added and notifications sent to {client_name.title()}!")

        except Exception as e:
            st.warning(f"⚠️ Entry saved, but failed to send notifications: {e}")

# --- Summary ---
st.subheader("📊 Membership Summary")

if not df.empty:
    df["Time"] = df["Time"].fillna("").replace("None", "")
    st.dataframe(df, use_container_width=True)

    total = df["Amount"].sum()
    st.markdown(f"### 💸 Total Income: ₹{total:.2f}")

    chart_data = df.groupby("Membership Type")["Amount"].sum().sort_values(ascending=False)
    st.bar_chart(chart_data)
else:
    st.info("No entries recorded yet.")

# --- Expiry Section ---
st.subheader("⏰ Expiring Soon (within 3 days)")
if not df.empty:
    today = datetime.now(pytz.timezone("Asia/Kolkata")).date()
    df["Expiry Date"] = pd.to_datetime(df["Expiry Date"], errors="coerce")
    expiring = df[(df["Expiry Date"] - pd.Timestamp(today)).dt.days.between(0, 3, inclusive="both")]

    if not expiring.empty:
        st.warning("⚠️ Some memberships are expiring soon!")
        st.dataframe(expiring[["Client Name", "Phone Number", "Client Email", "Membership Type", "Expiry Date"]], use_container_width=True)
    else:
        st.info("✅ No memberships expiring soon.")
