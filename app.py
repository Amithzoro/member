import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client

# --- Page Config ---
st.set_page_config(page_title="Membership Tracker", layout="wide")

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

# --- Payment modes ---
payment_modes = ["Cash", "UPI", "Card", "Net Banking", "Wallet"]

# --- Load credentials from secrets ---
EMAIL_USER = st.secrets["EMAIL_USER"]
EMAIL_PASS = st.secrets["EMAIL_PASS"]
OWNER_EMAIL = st.secrets["OWNER_EMAIL"]

TWILIO_SID = st.secrets["TWILIO_SID"]
TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
TWILIO_FROM = st.secrets["TWILIO_FROM"]

# --- Helper: send email ---
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

# --- Helper: send WhatsApp/SMS ---
def send_whatsapp(phone, message):
    client = Client(TWILIO_SID, TWILIO_AUTH)
    # Ensure phone number includes country code (e.g., +91)
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
        "Date", "Time", "Client Name", "Phone Number",
        "Membership Type", "Amount", "Payment Mode", "Notes"
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

# --- Entry Form ---
st.subheader("➕ Add New Member / Payment Entry")

col1, col2 = st.columns(2)
with col1:
    client_name = st.text_input("Client Name")
    phone_number = st.text_input("Phone Number (10 digits)")
    membership_type = st.selectbox(
        "Membership Type",
        ["Monthly", "Quarterly", "Half-Yearly", "Yearly", "One-Time Session", "Other"]
    )

with col2:
    amount = st.number_input("Amount (₹)", min_value=0.0, step=0.01)
    payment_mode = st.selectbox("Payment Mode", payment_modes)
    notes = st.text_input("Notes (optional)")

# --- Add Entry Button ---
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

        new_entry = {
            "Date": current_date,
            "Time": current_time,
            "Client Name": client_name.strip().title(),
            "Phone Number": phone_number.strip(),
            "Membership Type": membership_type,
            "Amount": amount,
            "Payment Mode": payment_mode,
            "Notes": notes
        }

        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        save_data(df)

        # --- Notifications ---
        try:
            # Owner email
            owner_msg = f"""
New membership entry added:

Client: {client_name.title()}
Phone: {phone_number}
Type: {membership_type}
Amount: ₹{amount}
Mode: {payment_mode}
Notes: {notes}
Time: {current_time}, {current_date}
"""
            send_email(OWNER_EMAIL, f"New Membership: {client_name.title()}", owner_msg)

            # Client WhatsApp
            client_msg = f"Hi {client_name.title()}, thank you for your payment of ₹{amount:.2f} for your {membership_type} membership at our gym! 💪 See you soon!"
            send_whatsapp(phone_number, client_msg)

            st.success(f"✅ Entry added for {client_name.title()} and notifications sent!")
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
