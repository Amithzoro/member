import streamlit as st
import pandas as pd
import bcrypt
import random
import string
from datetime import datetime, timedelta
from twilio.rest import Client

# --------------------- OWNER DETAILS ---------------------
OWNER_EMAIL = "owner@gmail.com"  # Change this to your actual email
OWNER_NUMBER = "7019384280"      # Owner’s phone number
OWNER_PASSWORD = "owner123"      # Owner’s login password

# --------------------- TWILIO CONFIG ---------------------
TWILIO_SID = "your_twilio_sid_here"
TWILIO_AUTH = "your_twilio_auth_token_here"
TWILIO_PHONE = "+14155238886"  # Your Twilio number (use WhatsApp/SMS enabled)

# --------------------- INITIAL SESSION DATA ---------------------
if "users" not in st.session_state:
    st.session_state.users = {
        OWNER_EMAIL: {
            "password": bcrypt.hashpw(OWNER_PASSWORD.encode(), bcrypt.gensalt()),
            "role": "owner"
        }
    }

if "members" not in st.session_state:
    st.session_state.members = []

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = None


# --------------------- UTILITIES ---------------------
def send_sms(number, message):
    """Send SMS using Twilio"""
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        client.messages.create(from_=TWILIO_PHONE, body=message, to=f"+91{number}")
        st.success(f"SMS sent to {number} ✅")
    except Exception as e:
        st.warning(f"Failed to send SMS: {e}")


def generate_password(length=8):
    """Generate random password for new staff"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


# --------------------- LOGIN SYSTEM ---------------------
def login():
    st.title("🏋️ Gym Management System")
    email = st.text_input("Enter your email")
    password = st.text_input("Enter your password", type="password")

    if st.button("Login"):
        if email in st.session_state.users:
            hashed_pw = st.session_state.users[email]["password"]
            if bcrypt.checkpw(password.encode(), hashed_pw):
                st.session_state.logged_in = True
                st.session_state.role = st.session_state.users[email]["role"]
                st.success(f"Welcome {st.session_state.role.capitalize()} 👋")
                st.rerun()
            else:
                st.error("❌ Invalid password")
        else:
            st.error("❌ User not found")


# --------------------- OWNER DASHBOARD ---------------------
def owner_dashboard():
    st.sidebar.write("Role: Owner")
    st.title("👑 Owner Dashboard")

    # --- Add staff ---
    st.subheader("Add New Staff")
    new_email = st.text_input("Staff Email")
    if st.button("Add Staff"):
        if new_email in st.session_state.users:
            st.warning("Staff already exists!")
        else:
            temp_pw = gen_
