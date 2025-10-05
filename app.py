import streamlit as st
import pandas as pd
import pytz
import bcrypt
import random
import string
from twilio.rest import Client
from datetime import datetime

# ==========================
# 🔧 BASIC CONFIG
# ==========================
TWILIO_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH = "your_twilio_auth_token"
TWILIO_FROM = "whatsapp:+14155238886"  # Twilio sandbox number
OWNER_PHONE = "+919876543210"  # Your owner number for messages & backup login

ADMIN_USER = "admin"
ADMIN_PASSWORD = "1234"

FILE_PATH = "membership.xlsx"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# ==========================
# 🧂 HASH ADMIN PASSWORD
# ==========================
ADMIN_PASSWORD_HASH = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# ==========================
# 💬 TWILIO CLIENT
# ==========================
client = Client(TWILIO_SID, TWILIO_AUTH)

# ==========================
# 🧠 SESSION SETUP
# ==========================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])

# ==========================
# 📁 DATA HANDLERS
# ==========================
@st.cache_data(show_spinner="Loading members...")
def load_data():
    try:
        df = pd.read_excel(FILE_PATH)
        if 'Password' not in df.columns:
            df['Password'] = ''
        if 'Join Date' not in df.columns:
            df['Join Date'] = ''
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])

def save_data(df):
    df.to_excel(FILE_PATH, index=False)
    st.session_state.df = df
    load_data.clear()
    st.toast("✅ Data saved successfully!")

# ==========================
# 🔐 LOGIN SYSTEM
# ==========================
def check_admin_login(username, password):
    if username != ADMIN_USER:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), ADMIN_PASSWORD_HASH.encode('utf-8'))

def login_with_owner(owner_number):
    if owner_number.strip() == OWNER_PHONE:
        st.session_state.logged_in = True
        st.session_state.df = load_data()
        st.success("✅ Logged in via owner number.")
        st.rerun()
    else:
        st.error("❌ Invalid owner number.")

def login_page():
    st.title("🔐 Admin Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Log In", use_container_width=True)
        if submit:
            if check_admin_login(username, password):
                st.session_state.logged_in = True
                st.session_state.df = load_data()
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

    st.markdown("---")
    if st.button("Forgot Username/Password? Log in using Owner’s Number"):
        st.session_state.show_backup = True
        st.rerun()

    if st.session_state.get("show_backup", False):
        with st.form("owner_login"):
            owner_input = st.text_input("Enter Owner’s Number")
            submit = st.form_submit_button("Login")
            if submit:
                login_with_owner(owner_input)

def logout():
    st.session_state.logged_in = False
    st.session_state.df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])
    st.session_state.show_backup = False
    st.toast("👋 Logged out successfully!")
    st.rerun()

# ==========================
# 💬 WHATSAPP MESSAGE
# ==========================
def send_whatsapp_message(name, email, password, phone):
    try:
        msg = (
            f"Hello {name}, 👋\n"
            f"Welcome to our Membership Program!\n"
            f"📧 Email: {email}\n"
            f"🔑 Password: {password}\n"
            f"💬 For support, contact the owner at {OWNER_PHONE}."
        )
        client.messages.create(
            body=msg,
            from_=TWILIO_FROM,
            to=f"whatsapp:{phone}"
        )
        st.toast("✅ WhatsApp message sent successfully!")
    except Exception as e:
        st.warning(f"⚠️ Could not send WhatsApp: {e}")

# ==========================
# 🧮 DASHBOARD
# ==========================
def show_dashboard(df):
    st.subheader("📊 Dashboard Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Members", len(df))
    col2.metric("Unique Emails", df["Email"].nunique() if not df.empty else 0)
    col3.metric("Latest Join", df["Join Date"].max() if not df.empty else "N/A")
    st.divider()

# ==========================
# ➕ ADD MEMBER
# ==========================
def add_member():
    st.subheader("➕ Register a New Member")

    with st.form("add_member_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name")
            email = st.text_input("Email Address")
        with col2:
            phone = st.text_input("Phone Number (e.g. +919876543210)")

        submit = st.form_submit_button("Add Member")

        if submit:
            if not all([name, email, phone]):
                st.warning("Please fill all fields.")
                return

            df = st.session_state.df
            if df['Email'].str.lower().eq(email.lower()).any():
                st.warning("Member with this email already exists.")
                return

            random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            hashed_pw = bcrypt.hashpw(random_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            new_entry = {
                "Name": name,
                "Email": email,
                "Phone": phone,
                "Join Date": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
                "Password": hashed_pw
            }

            updated_df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            save_data(updated_df)
            send_whatsapp_message(name, email, random_password, phone)
            st.success(f"✅ Member added successfully!\nGenerated Password: {random_password}")
            st.rerun()

# ==========================
# 🧾 MANAGE MEMBERS
# ==========================
def manage_members():
    st.subheader("🧾 Manage Members")
    df = st.session_state.df.copy()

    if df.empty:
        st.info("No members yet.")
        return

    edited_df = st.data_editor(df.drop(columns=["Password"]), use_container_width=True)
    if st.button("💾 Save Changes"):
        df.update(edited_df)
        save_data(df)
        st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Delete Member")
    delete_email = st.selectbox("Select email to delete", df["Email"].tolist())
    if st.button("Delete", type="primary"):
        df = df[df["Email"] != delete_email]
        save_data(df)
        st.success(f"Deleted member: {delete_email}")
        st.rerun()

# ==========================
# 🚀 MAIN APP
# ==========================
st.set_page_config("Membership Portal", page_icon="🛡️")

if not st.session_state.logged_in:
    login_page()
else:
    st.sidebar.success(f"Logged in as {ADMIN_USER}")
    st.sidebar.button("Logout", on_click=logout, use_container_width=True)

    df = st.session_state.df
    show_dashboard(df)
    tab1, tab2 = st.tabs(["Add Member", "Manage Members"])
    with tab1:
        add_member()
    with tab2:
        manage_members()
