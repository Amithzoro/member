import streamlit as st
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# -------------------------------
# Load secrets
# -------------------------------
EMAIL_USER = st.secrets["EMAIL_USER"]
EMAIL_PASS = st.secrets["EMAIL_PASS"]
TWILIO_SID = st.secrets["TWILIO_SID"]
TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
TWILIO_FROM = st.secrets["TWILIO_FROM"]

# -------------------------------
# Streamlit UI
# -------------------------------
st.title("📱 WhatsApp & Email Notification App")

option = st.selectbox("Choose a notification method:", ["WhatsApp", "Email"])

if option == "WhatsApp":
    st.header("Send WhatsApp Message")

    to_number = st.text_input("Receiver WhatsApp Number (e.g. +911234567890)")
    message_body = st.text_area("Message")

    if st.button("Send WhatsApp Message"):
        if to_number and message_body:
            try:
                client = Client(TWILIO_SID, TWILIO_AUTH)
                message = client.messages.create(
                    from_=TWILIO_FROM,
                    body=message_body,
                    to=f"whatsapp:{to_number}"
                )
                st.success(f"✅ Message sent successfully! SID: {message.sid}")
            except Exception as e:
                st.error(f"❌ Error sending message: {e}")
        else:
            st.warning("Please enter both phone number and message.")

elif option == "Email":
    st.header("Send Email")

    to_email = st.text_input("Receiver Email")
    subject = st.text_input("Subject")
    body = st.text_area("Message Body")

    if st.button("Send Email"):
        if to_email and body:
            try:
                msg = MIMEMultipart()
                msg["From"] = EMAIL_USER
                msg["To"] = to_email
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))

                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(EMAIL_USER, EMAIL_PASS)
                    server.send_message(msg)

                st.success("✅ Email sent successfully!")
            except Exception as e:
                st.error(f"❌ Error sending email: {e}")
        else:
            st.warning("Please fill in all fields.")
