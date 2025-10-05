import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client

# ---- Load secrets ----
EMAIL_USER = st.secrets["EMAIL_USER"]
EMAIL_PASS = st.secrets["EMAIL_PASS"]
TWILIO_SID = st.secrets["TWILIO_SID"]
TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
TWILIO_FROM = st.secrets["TWILIO_FROM"]

# ---- Streamlit UI ----
st.set_page_config(page_title="Membership Form", page_icon="💌")

st.title("💬 Member Registration & Notification System")

st.write("Fill out this form to send a confirmation email and WhatsApp message!")

name = st.text_input("Full Name")
email = st.text_input("Email Address")
phone = st.text_input("WhatsApp Number (with country code, e.g. +1415...)")
message = st.text_area("Custom Message")

if st.button("Submit"):
    if name and email and phone:
        try:
            # ---- Send Email ----
            msg = MIMEMultipart()
            msg["From"] = EMAIL_USER
            msg["To"] = email
            msg["Subject"] = "Welcome to the Membership Program!"

            body = f"""
            Hi {name},

            Thank you for joining us!

            {message}

            — The Membership Team
            """
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASS)
                server.send_message(msg)

            # ---- Send WhatsApp Message ----
            client = Client(TWILIO_SID, TWILIO_AUTH)
            client.messages.create(
                body=f"Hi {name}! 🎉 Welcome to the Membership Program.\n\n{message}",
                from_=TWILIO_FROM,
                to=f"whatsapp:{phone}"
            )

            st.success("✅ Email and WhatsApp message sent successfully!")

        except Exception as e:
            st.error(f"❌ Something went wrong: {e}")
    else:
        st.warning("⚠️ Please fill in all required fields.")
