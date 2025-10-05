import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client

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

# --- Load credentials from Streamlit secrets ---
EMAIL_USER = st.secrets["EMAIL_USER"]
EMAIL_PASS = st.secrets["EMAIL_PASS"]

TWILIO_SID = st.secrets["TWILIO_SID"]
TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
TWILIO_FROM = st.secrets["TWILIO_FROM"]

# --- Helper functions ---
def send_email(to, subject, body):
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
    client = Client(TWILIO_SID, TWILIO_AUTH)
    if not phone.startswith("+"):
        phone = "+91" + phone
    client.messages.create(
        from_=TWILIO_FROM,
        body=message,
        to=f"whatsapp:{phone}"
    )

# --- Load/Save Excel ---
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

# ===============================
# 🔐 OWNER LOGIN SECTION
# ===============================
if "owner_logged_in" not in st.session_state:
    st.session_state["owner_logged_in"] = False

if not st.session_state["owner_logged_in"]:
    st.subheader("🔐 Owner Login")
    login_email = st.text_input("Enter your email")
    login_password = st.text_input("Enter password", type="password")

    if st.button("Login"):
        # Simple static password for now (can be stored in secrets or database)
        if login_email and login_password == "admin123":  # You can change this
            st.session_state["owner_logged_in"] = True
            st.session_state["owner_email"] = login_email.strip().lower()
            st.success(f"✅ Logged in as {login_email}")
        else:
            st.error("❌ Invalid email or password. Try again.")
    st.stop()  # stop app until login succeeds

owner_email = st.session_state["owner_email"]

st.sidebar.markdown(f"👋 Logged in as: **{owner_email}**")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.experimental_rerun()

# ===============================
# 🧾 MAIN APP (AFTER LOGIN)
# ===============================

# --- Payment modes ---
payment_modes = ["Cash", "UPI", "Card", "Net Banking", "Wallet"]

# --- Entry Form ---
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

# --- Add Entry ---
if st.button("💾 Add Entry"):
    if not client_name.strip():
        st.error("⚠️ Please enter the client name before saving.")
    elif not phone_number.strip().isdigit() or len(phone_number.strip()) != 10:
        st.error("⚠️ Please enter a valid 10-digit phone number.")
    else:
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist)
        current_date = now_ist.strftime("%Y-%m-%d")
        current_time = now_ist.strftime("%I:%M:%S %p")

        # Calculate expiry date
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

        # --- Send Notifications ---
        try:
            # Owner Email
            owner_msg = f"""
New Membership Added:

Client: {client_name.title()}
Phone: {phone_number}
Email: {client_email}
Plan: {membership_type}
Amount: ₹{amount}
Mode: {payment_mode}
Expiry Date: {expiry_date}
Notes: {notes}
Added by: {owner_email}
Time: {current_time}, {current_date}
"""
            send_email(owner_email, f"New Membership Added: {client_name.title()}", owner_msg)

            # Client WhatsApp
            client_msg = f"Hi {client_name.title()}, thanks for your payment of ₹{amount:.2f} for your {membership_type} plan! 💪 Expiry: {expiry_date}."
            send_whatsapp(phone_number, client_msg)

            # Client Email
            if client_email:
                client_email_body = f"""
Hi {client_name.title()},

Thank you for your payment of ₹{amount:.2f} for your {membership_type} membership.

Payment Mode: {payment_mode}
Date: {current_date}, Time: {current_time}
Expiry Date: {expiry_date}

See you soon at the gym! 💪
"""
                send_email(client_email, "Membership Payment Confirmation", client_email_body)

            st.success(f"✅ Entry added and notifications sent to {client_name.title()}!")

        except Exception as e:
            st.warning(f"⚠️ Entry saved, but failed to send notifications: {e}")

# --- Display and Summary ---
st.subheader("📊 Membership Summary")

if not df.empty:
    df["Time"] = df["Time"].fillna("").replace("None", "")
    st.dataframe(df, use_container_width=True)

    total = df["Amount"].sum()
    st.markdown(f"### 💸 Total Income: ₹{total:.2f}")

    chart_data = df.groupby("Membership Type")["Amount"].sum().sort_values(ascending=False)
    st.bar_chart(chart_data)
else:
    st.info("No entries recorded yet. Start by adding a new member!")

# --- Expiry Check Section ---
st.subheader("⏰ Expiring Soon (within 3 days)")
if not df.empty:
    today = datetime.now(pytz.timezone("Asia/Kolkata")).date()
    df["Expiry Date"] = pd.to_datetime(df["Expiry Date"], errors="coerce")
    expiring = df[(df["Expiry Date"] - pd.Timestamp(today)).dt.days.between(0, 3, inclusive="both")]

    if not expiring.empty:
        st.warning("⚠️ Some memberships are expiring soon!")
        st.dataframe(expiring[["Client Name", "Phone Number", "Client Email", "Membership Type", "Expiry Date", "Owner Email"]], use_container_width=True)
    else:
        st.info("✅ No memberships are expiring in the next 3 days.")
