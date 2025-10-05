import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import hashlib

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
    client.messages.create(from_=TWILIO_FROM, body=message, to=f"whatsapp:{phone}")

# --- Load/Save Excel ---
def load_data(path, expected_cols):
    try:
        df = pd.read_excel(path)
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        return df[expected_cols]
    except FileNotFoundError:
        df = pd.DataFrame(columns=expected_cols)
        df.to_excel(path, index=False)
        return df

def save_data(df, path):
    df.to_excel(path, index=False)

# --- Hash Passwords ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ===============================
# 🔐 OWNER LOGIN/REGISTER SECTION
# ===============================

# Load owner accounts
owners_file = "owners.xlsx"
owners_cols = ["Email", "PasswordHash", "Role"]
owners_df = load_data(owners_file, owners_cols)

if "owner_logged_in" not in st.session_state:
    st.session_state["owner_logged_in"] = False

tab1, tab2 = st.tabs(["🔑 Login", "🆕 Create Account"])

# --- LOGIN TAB ---
with tab1:
    st.subheader("Owner / Staff Login")
    login_email = st.text_input("Enter your email")
    login_password = st.text_input("Enter password", type="password")

    if st.button("Login"):
        if login_email and login_password:
            hashed_pw = hash_password(login_password)
            match = owners_df[
                (owners_df["Email"].str.lower() == login_email.strip().lower()) &
                (owners_df["PasswordHash"] == hashed_pw)
            ]
            if not match.empty:
                st.session_state["owner_logged_in"] = True
                st.session_state["owner_email"] = login_email.strip().lower()
                st.success(f"✅ Logged in as {login_email}")
                st.experimental_rerun()
            else:
                st.error("❌ Invalid email or password.")
        else:
            st.warning("Please enter both email and password.")

# --- REGISTER TAB ---
with tab2:
    st.subheader("Register New Owner / Staff")
    new_email = st.text_input("New Email")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    role = st.selectbox("Role", ["Owner", "Staff"])

    if st.button("Create Account"):
        if not new_email or not new_password:
            st.warning("Please fill all fields.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        elif new_email.lower() in owners_df["Email"].str.lower().values:
            st.error("Email already registered.")
        else:
            new_entry = {
                "Email": new_email.strip().lower(),
                "PasswordHash": hash_password(new_password),
                "Role": role
            }
            owners_df = pd.concat([owners_df, pd.DataFrame([new_entry])], ignore_index=True)
            save_data(owners_df, owners_file)
            st.success(f"✅ Account created for {new_email} ({role})! You can now log in.")

if not st.session_state["owner_logged_in"]:
    st.stop()

# ===============================
# 🧾 MAIN APP (AFTER LOGIN)
# ===============================

owner_email = st.session_state["owner_email"]

st.sidebar.markdown(f"👋 Logged in as: **{owner_email}**")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.experimental_rerun()

# --- Load membership data ---
members_cols = [
    "Date", "Time", "Client Name", "Phone Number", "Client Email",
    "Membership Type", "Amount", "Payment Mode", "Notes",
    "Expiry Date", "Owner Email"
]
df = load_data("memberships.xlsx", members_cols)

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
        save_data(df, "memberships.xlsx")

        st.success(f"✅ Entry added for {client_name.title()}!")

# --- Display and Summary ---
st.subheader("📊 Membership Summary")
if not df.empty:
    st.dataframe(df, use_container_width=True)
    total = df["Amount"].sum()
    st.markdown(f"### 💸 Total Income: ₹{total:.2f}")
else:
    st.info("No entries recorded yet. Start by adding a new member!")

# --- Expiry Check ---
st.subheader("⏰ Expiring Soon (within 3 days)")
if not df.empty:
    today = datetime.now(pytz.timezone("Asia/Kolkata")).date()
    df["Expiry Date"] = pd.to_datetime(df["Expiry Date"], errors="coerce")
    expiring = df[(df["Expiry Date"] - pd.Timestamp(today)).dt.days.between(0, 3, inclusive="both")]
    if not expiring.empty:
        st.warning("⚠️ Some memberships are expiring soon!")
        st.dataframe(expiring[["Client Name", "Phone Number", "Expiry Date", "Owner Email"]], use_container_width=True)
    else:
        st.info("✅ No memberships expiring soon.")
