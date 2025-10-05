import streamlit as st
import pandas as pd
import bcrypt
import random
import string
from datetime import datetime
from twilio.rest import Client

# ===============================
# CONFIGURATION
# ===============================
FILE_PATH = "membership.xlsx"

# Twilio configuration (replace with your Twilio details)
TWILIO_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH = "your_twilio_auth_token"
TWILIO_FROM = "whatsapp:+14155238886"  # Example Twilio sandbox number
client = Client(TWILIO_SID, TWILIO_AUTH)

# ===============================
# SESSION INITIALIZATION
# ===============================
if "owner_email" not in st.session_state:
    st.session_state.owner_email = None
if "owner_phone" not in st.session_state:
    st.session_state.owner_phone = None
if "owner_password" not in st.session_state:
    st.session_state.owner_password = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])

# ===============================
# UTILITIES
# ===============================
def load_data():
    try:
        df = pd.read_excel(FILE_PATH)
        if "Password" not in df.columns:
            df["Password"] = ""
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])

def save_data(df):
    df.to_excel(FILE_PATH, index=False)
    st.session_state.df = df

def generate_random_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def send_whatsapp_confirmation(name, phone, email, password):
    """Send WhatsApp confirmation including owner contact."""
    try:
        message_body = (
            f"Hello {name}, welcome to our membership program! 🎉\n"
            f"Your registration is complete.\n\n"
            f"📧 Email: {email}\n🔐 Password: {password}\n\n"
            f"For any help, contact the owner at {st.session_state.owner_phone}."
        )

        client.messages.create(
            body=message_body,
            from_=TWILIO_FROM,
            to=f"whatsapp:{phone}"
        )
        st.toast("✅ WhatsApp message sent successfully!")
    except Exception as e:
        st.warning(f"⚠️ Failed to send WhatsApp message: {e}")

# ===============================
# FIRST TIME SETUP
# ===============================
def first_time_setup():
    st.markdown("## 👑 Owner Setup (First Time Use)")
    st.info("Please enter your email, phone number, and password to set up your admin access.")

    with st.form("setup_form"):
        email = st.text_input("Owner Email")
        phone = st.text_input("Owner Phone (with country code, e.g. +919876543210)")
        password = st.text_input("Create Password", type="password")
        submitted = st.form_submit_button("Save & Continue")

        if submitted:
            if not email or not phone or not password:
                st.warning("Please fill in all fields.")
                return
            st.session_state.owner_email = email
            st.session_state.owner_phone = phone
            st.session_state.owner_password = password
            st.success("Owner details saved successfully ✅")
            st.rerun()

# ===============================
# AUTHENTICATION
# ===============================
def check_login(email, password):
    if email == st.session_state.owner_email and password == st.session_state.owner_password:
        return True
    return False

def login_screen():
    st.markdown("### 🔐 Admin Login")
    email_or_phone = st.text_input("Enter Admin Email or Owner Phone")
    password = st.text_input("Enter Password (leave blank if using owner phone)", type="password")

    if st.button("Login", use_container_width=True):
        # Login by phone (no password needed)
        if email_or_phone == st.session_state.owner_phone:
            st.session_state.logged_in = True
            st.session_state.df = load_data()
            st.success("Logged in using owner phone ✅")
            st.rerun()
        elif check_login(email_or_phone, password):
            st.session_state.logged_in = True
            st.session_state.df = load_data()
            st.success("Login successful ✅")
            st.rerun()
        else:
            st.error("Invalid credentials. Try again.")

# ===============================
# LOGOUT
# ===============================
def logout():
    st.session_state.logged_in = False
    st.success("Logged out successfully 👋")
    st.rerun()

# ===============================
# ADD MEMBER
# ===============================
def add_member_section():
    st.subheader("➕ Register New Member")
    df = st.session_state.df

    with st.form("add_member_form"):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone (with country code, e.g. +919876543210)")
        submitted = st.form_submit_button("Register Member")

        if submitted:
            if not name or not email or not phone:
                st.warning("Please fill all required fields.")
                return

            if df["Email"].str.lower().eq(email.lower()).any():
                st.warning("Member with this email already exists!")
                return

            password = generate_random_password()
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

            new_member = {
                "Name": name,
                "Email": email,
                "Phone": phone,
                "Join Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Password": hashed_pw,
            }

            new_df = pd.concat([df, pd.DataFrame([new_member])], ignore_index=True)
            save_data(new_df)
            send_whatsapp_confirmation(name, phone, email, password)
            st.success(f"Member {name} added successfully ✅")

# ===============================
# MANAGE MEMBERS
# ===============================
def manage_members_section():
    st.subheader("📝 Manage Members")
    df = st.session_state.df

    if df.empty:
        st.info("No members found yet.")
        return

    st.dataframe(df[["Name", "Email", "Phone", "Join Date"]], use_container_width=True)

    email_to_delete = st.selectbox("Select Member Email to Delete", df["Email"].tolist())
    if st.button("Delete Selected Member", type="primary"):
        df = df[df["Email"] != email_to_delete]
        save_data(df)
        st.success("Member deleted successfully ✅")
        st.rerun()

# ===============================
# MAIN APP
# ===============================
st.title("🛡️ Membership Management Portal")
st.caption("Manage members, registrations, and WhatsApp confirmations.")

if not st.session_state.owner_email or not st.session_state.owner_phone:
    first_time_setup()
elif not st.session_state.logged_in:
    login_screen()
else:
    st.sidebar.success(f"Logged in as {st.session_state.owner_email}")
    st.sidebar.button("Logout", on_click=logout, use_container_width=True)

    tab1, tab2 = st.tabs(["New Registration", "Manage Members"])
    with tab1:
        add_member_section()
    with tab2:
        manage_members_section()

