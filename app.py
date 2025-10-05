import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import os

# --- Page Config ---
st.set_page_config(page_title="Membership Tracker", layout="wide")

# --- Load Secrets (required) ---
required_keys = ["EMAIL_USER", "EMAIL_PASS", "TWILIO_SID", "TWILIO_AUTH", "TWILIO_FROM"]
missing_keys = [key for key in required_keys if key not in st.secrets]
if missing_keys:
    st.error(f"❌ Missing credentials: {', '.join(missing_keys)}. Please set them in .streamlit/secrets.toml.")
    st.stop()

EMAIL_USER = st.secrets["EMAIL_USER"]
EMAIL_PASS = st.secrets["EMAIL_PASS"]
TWILIO_SID = st.secrets["TWILIO_SID"]
TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
TWILIO_FROM = st.secrets["TWILIO_FROM"]

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

st.title("💪 Membership & Client Tracker")

# --- Helper Functions ---
def send_email(receiver_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"❌ Email sending failed: {e}")
        return False

def send_whatsapp(phone_number, message):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        client.messages.create(
            from_=TWILIO_FROM,
            body=message,
            to=f"whatsapp:+91{phone_number}"
        )
        return True
    except Exception as e:
        st.error(f"❌ WhatsApp sending failed: {e}")
        return False

def load_data():
    if os.path.exists("memberships.csv"):
        return pd.read_csv("memberships.csv")
    else:
        return pd.DataFrame(columns=[
            "Date", "Time", "Client Name", "Phone Number", "Email",
            "Membership Type", "Amount", "Payment Mode", "Notes", "Expiry Date"
        ])

def save_data(df):
    df.to_csv("memberships.csv", index=False)

def get_expiry_date(membership_type):
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    if membership_type == "Monthly":
        return now + timedelta(days=30)
    elif membership_type == "Quarterly":
        return now + timedelta(days=90)
    elif membership_type == "Half-Yearly":
        return now + timedelta(days=180)
    elif membership_type == "Yearly":
        return now + timedelta(days=365)
    else:
        return now + timedelta(days=1)

# --- Owner Login ---
st.sidebar.header("🔐 Owner / Staff Login")
owner_email = st.sidebar.text_input("Owner Email", placeholder="owner@example.com")
owner_pass = st.sidebar.text_input("Password", type="password")

if not owner_email or not owner_pass:
    st.sidebar.warning("Please log in to continue.")
    st.stop()
else:
    st.sidebar.success(f"Welcome, {owner_email}")

# --- Load existing data ---
df = load_data()

# --- Add New Entry ---
st.subheader("➕ Add New Member / Payment Entry")

col1, col2 = st.columns(2)
with col1:
    client_name = st.text_input("Client Name")
    phone_number = st.text_input("Phone Number (10 digits)")
    client_email = st.text_input("Client Email (Required)")
    membership_type = st.selectbox(
        "Membership Type",
        ["Monthly", "Quarterly", "Half-Yearly", "Yearly", "One-Time Session", "Other"]
    )

with col2:
    amount = st.number_input("Amount (₹)", min_value=0.0, step=0.01)
    payment_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Card", "Net Banking", "Wallet"])
    notes = st.text_input("Notes (optional)")

if st.button("💾 Add Entry"):
    if not client_name.strip() or not client_email.strip():
        st.error("⚠️ Client name and email are required.")
    elif not phone_number.strip().isdigit() or len(phone_number.strip()) != 10:
        st.error("⚠️ Invalid 10-digit phone number.")
    else:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%I:%M:%S %p")
        expiry_date = get_expiry_date(membership_type).strftime("%Y-%m-%d")

        new_entry = {
            "Date": current_date,
            "Time": current_time,
            "Client Name": client_name.strip().title(),
            "Phone Number": phone_number.strip(),
            "Email": client_email.strip(),
            "Membership Type": membership_type,
            "Amount": amount,
            "Payment Mode": payment_mode,
            "Notes": notes,
            "Expiry Date": expiry_date
        }

        # Add to dataframe and auto-save
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        save_data(df)  # 🔥 Auto-updates memberships.csv instantly

        # Send email + WhatsApp
        email_body = f"""
        Hi {client_name.title()},
        Your {membership_type} membership has been activated.

        💰 Amount Paid: ₹{amount}
        📅 Expiry Date: {expiry_date}

        Thank you for choosing us!
        """
        send_email(client_email, "Membership Confirmation", email_body)
        send_email(owner_email, f"New Membership Added: {client_name}", email_body)
        send_whatsapp(phone_number, f"Hi {client_name}, your {membership_type} membership is active till {expiry_date}. Thank you!")

        st.success(f"✅ Entry added for {client_name.title()} and saved automatically!")

# --- Display and Summary ---
st.subheader("📊 Membership Summary")

if not df.empty:
    st.dataframe(df, use_container_width=True)
    total = df["Amount"].sum()
    st.markdown(f"### 💸 Total Income: ₹{total:.2f}")
    chart_data = df.groupby("Membership Type")["Amount"].sum().sort_values(ascending=False)
    st.bar_chart(chart_data)
else:
    st.info("No entries yet — add one above.")
