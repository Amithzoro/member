import streamlit as st
import pandas as pd
import pytz
import bcrypt
from twilio.rest import Client
from datetime import datetime

# ✅ Load secrets safely
try:
    EMAIL_USER = st.secrets["EMAIL_USER"]
    EMAIL_PASS = st.secrets["EMAIL_PASS"]
    TWILIO_SID = st.secrets["TWILIO_SID"]
    TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
    TWILIO_FROM = st.secrets["TWILIO_FROM"]
except KeyError as e:
    st.error(f"Missing secret key: {e}")
    st.stop()

# ✅ Initialize Twilio client
client = Client(TWILIO_SID, TWILIO_AUTH)

st.title("📋 Membership Management App")

# ✅ Load or create Excel
file_path = "membership.xlsx"

try:
    df = pd.read_excel(file_path)
except FileNotFoundError:
    df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])
    df.to_excel(file_path, index=False)

# ✅ Add new member
st.subheader("Add New Member")
name = st.text_input("Name")
email = st.text_input("Email")
phone = st.text_input("Phone (with country code)")
password = st.text_input("Password", type="password")

if st.button("Add Member"):
    if name and email and phone and password:
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        new_member = {
            "Name": name,
            "Email": email,
            "Phone": phone,
            "Join Date": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
            "Password": hashed_pw,
        }

        df = pd.concat([df, pd.DataFrame([new_member])], ignore_index=True)
        df.to_excel(file_path, index=False)
        st.success(f"Member {name} added successfully!")

        # ✅ Send WhatsApp confirmation
        try:
            client.messages.create(
                body=f"Hello {name}, welcome to our membership program!",
                from_=TWILIO_FROM,
                to=f"whatsapp:{phone}"
            )
            st.info("WhatsApp message sent successfully!")
        except Exception as e:
            st.error(f"Failed to send WhatsApp message: {e}")

    else:
        st.warning("Please fill all fields!")

# ✅ Display members
st.subheader("📄 Current Members")
st.dataframe(df)
