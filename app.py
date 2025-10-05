import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, timedelta
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytz
import os

# -------------------------------
# Load secrets
# -------------------------------
EMAIL_USER = st.secrets["EMAIL_USER"]
EMAIL_PASS = st.secrets["EMAIL_PASS"]
TWILIO_SID = st.secrets["TWILIO_SID"]
TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
TWILIO_FROM = st.secrets["TWILIO_FROM"]

# -------------------------------
# Helper Functions
# -------------------------------

def send_whatsapp_message(to, message):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        client.messages.create(from_=TWILIO_FROM, body=message, to=f"whatsapp:{to}")
        return True
    except Exception as e:
        st.error(f"WhatsApp Error: {e}")
        return False

def send_email(to, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        return True
    except Exception as e:
        st.error(f"Email Error: {e}")
        return False

# -------------------------------
# Authentication
# -------------------------------
def check_login(email, password):
    if not os.path.exists("owners.csv"):
        return False
    owners = pd.read_csv("owners.csv")
    user = owners[owners["email"] == email]
    if not user.empty:
        stored_hash = user.iloc[0]["password"].encode()
        return bcrypt.checkpw(password.encode(), stored_hash)
    return False

def create_owner(email, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    df = pd.DataFrame([[email, hashed]], columns=["email", "password"])
    if os.path.exists("owners.csv"):
        df_existing = pd.read_csv("owners.csv")
        df = pd.concat([df_existing, df], ignore_index=True)
    df.to_csv("owners.csv", index=False)

# -------------------------------
# App Layout
# -------------------------------
st.title("🏋️ Gym Membership Manager")

menu = st.sidebar.radio("Navigation", ["Owner Login", "Add Member", "View Members", "Send Reminders"])

# -------------------------------
# Owner Login
# -------------------------------
if menu == "Owner Login":
    st.subheader("Create or Login as Owner")
    email = st.text_input("Owner Email")
    password = st.text_input("Password", type="password")

    if st.button("Create Account"):
        create_owner(email, password)
        st.success("✅ Owner account created!")

    if st.button("Login"):
        if check_login(email, password):
            st.success("✅ Login successful!")
        else:
            st.error("❌ Invalid credentials!")

# -------------------------------
# Add Member
# -------------------------------
elif menu == "Add Member":
    st.subheader("Add New Member")

    name = st.text_input("Client Name")
    phone = st.text_input("Phone (+countrycode...)")
    email = st.text_input("Email")
    plan = st.selectbox("Membership Plan", ["1 Month", "3 Months", "6 Months", "1 Year"])

    if st.button("Add Member"):
        if name and phone and email:
            start_date = datetime.now(pytz.timezone("Asia/Kolkata"))
            duration = {"1 Month": 30, "3 Months": 90, "6 Months": 180, "1 Year": 365}[plan]
            end_date = start_date + timedelta(days=duration)

            data = pd.DataFrame([[name, phone, email, plan, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]],
                                columns=["Name", "Phone", "Email", "Plan", "Start Date", "End Date"])

            if os.path.exists("members.xlsx"):
                df_existing = pd.read_excel("members.xlsx")
                df = pd.concat([df_existing, data], ignore_index=True)
            else:
                df = data

            df.to_excel("members.xlsx", index=False)
            st.success("✅ Member added successfully and Excel updated automatically!")
        else:
            st.warning("Please fill all fields!")

# -------------------------------
# View Members
# -------------------------------
elif menu == "View Members":
    st.subheader("📋 Current Members")
    if os.path.exists("members.xlsx"):
        df = pd.read_excel("members.xlsx")
        st.dataframe(df)
    else:
        st.info("No members added yet!")

# -------------------------------
# Send Reminders
# -------------------------------
elif menu == "Send Reminders":
    st.subheader("📅 Send Expiry Reminders")

    if os.path.exists("members.xlsx"):
        df = pd.read_excel("members.xlsx")
        today = datetime.now(pytz.timezone("Asia/Kolkata")).date()

        for _, row in df.iterrows():
            end_date = pd.to_datetime(row["End Date"]).date()
            days_left = (end_date - today).days

            if days_left <= 3 and days_left >= 0:
                msg = f"Hi {row['Name']}, your gym membership expires on {end_date}. Please renew soon to continue your training!"
                owner_msg = f"Reminder: {row['Name']}'s plan ends on {end_date}."

                # Send WhatsApp
                send_whatsapp_message(row["Phone"], msg)
                # Send Email
                send_email(row["Email"], "Membership Expiry Reminder", msg)
                # Send Owner Copy
                send_email(EMAIL_USER, f"Client Expiry Alert - {row['Name']}", owner_msg)

        st.success("✅ Reminders sent to clients and owner!")
    else:
        st.warning("No member data found!")
