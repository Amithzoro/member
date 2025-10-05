import streamlit as st
import pandas as pd
import pytz
import bcrypt
from twilio.rest import Client
from datetime import datetime
import time

# ==========================
# 🔧 CONFIGURATION SETTINGS
# ==========================
# (Edit these values directly)
TWILIO_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH = "your_twilio_auth_token"
TWILIO_FROM = "whatsapp:+14155238886"  # Example Twilio sandbox number
OWNER_PHONE = "+919876543210"  # Your personal number shown in every message

ADMIN_USER = "admin"
ADMIN_PASSWORD = "1234"  # Change this to your own password

FILE_PATH = "membership.xlsx"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# Hash the admin password once
ADMIN_PASSWORD_HASH = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Initialize Twilio client
client = Client(TWILIO_SID, TWILIO_AUTH)

# ==========================
# 🔒 SESSION INITIALIZATION
# ==========================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])

# ==========================
# 📁 DATA FUNCTIONS
# ==========================
@st.cache_data(show_spinner="Loading membership data...")
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
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])

def save_data(df):
    try:
        df.to_excel(FILE_PATH, index=False)
        st.session_state.df = df
        load_data.clear()
        st.success("💾 Data saved successfully!")
    except Exception as e:
        st.error(f"Error saving data: {e}")

# ==========================
# 💬 WHATSAPP MESSAGES
# ==========================
def send_whatsapp_confirmation(name, phone):
    """Send WhatsApp message with owner number included."""
    try:
        message = (
            f"Hello {name}, welcome to our exclusive membership program! 🎉\n"
            f"Your registration is complete.\n\n"
            f"For help, contact the owner at {OWNER_PHONE}."
        )
        client.messages.create(
            body=message,
            from_=TWILIO_FROM,
            to=f"whatsapp:{phone}"
        )
        st.toast("✅ WhatsApp message sent successfully!")
    except Exception as e:
        st.warning(f"⚠️ Failed to send message. Error: {e}")

# ==========================
# 🔐 AUTHENTICATION
# ==========================
def check_admin_login(username, password):
    if username != ADMIN_USER:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), ADMIN_PASSWORD_HASH.encode('utf-8'))

def login_form():
    st.markdown("### 🔒 Admin Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", use_container_width=True)
        if submitted:
            if check_admin_login(username, password):
                st.session_state.logged_in = True
                st.session_state.df = load_data()
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

def logout():
    st.session_state.logged_in = False
    st.session_state.df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])
    st.toast("👋 Logged out successfully!")
    st.rerun()

# ==========================
# 🧭 DASHBOARD
# ==========================
def display_dashboard(df):
    st.subheader("📊 Membership Dashboard")
    total_members = len(df)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Members", total_members)
    if total_members > 0:
        latest_join = df["Join Date"].max()
        display_date = str(latest_join).split(" ")[0]
        col2.metric("Latest Join Date", display_date)
    else:
        col2.metric("Latest Join Date", "N/A")
    col3.metric("Unique Phone Contacts", df["Phone"].nunique())
    st.divider()

# ==========================
# ➕ ADD MEMBER
# ==========================
def add_member_section():
    st.subheader("➕ Register New Member")
    with st.form("add_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
            email = st.text_input("Email")
        with col2:
            phone = st.text_input("Phone (e.g. +919876543210)")
            password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Add Member", use_container_width=True)
        if submit:
            df = st.session_state.df
            if name and email and phone and password:
                if df['Email'].str.lower().eq(email.lower()).any():
                    st.warning("Member with this email already exists.")
                else:
                    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    new_member = {
                        "Name": name,
                        "Email": email,
                        "Phone": phone,
                        "Join Date": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
                        "Password": hashed_pw
                    }
                    new_df = pd.concat([df, pd.DataFrame([new_member])], ignore_index=True)
                    save_data(new_df)
                    send_whatsapp_confirmation(name, phone)
                    st.rerun()
            else:
                st.warning("Please fill all fields!")

# ==========================
# 📝 MANAGE MEMBERS
# ==========================
def manage_members_section():
    st.subheader("📝 Manage Members")
    df = st.session_state.df.copy()
    df_editable = df.drop(columns=["Password", "Join Date"], errors="ignore")
    edited_df = st.data_editor(df_editable, use_container_width=True, num_rows="dynamic")
    if st.button("Apply Changes", use_container_width=True):
        for i, row in edited_df.iterrows():
            if i < len(df):
                df.loc[i, "Name"] = row["Name"]
                df.loc[i, "Phone"] = row["Phone"]
        save_data(df)
        st.rerun()
    st.markdown("---")
    st.markdown("#### 🗑️ Delete Member")
    if not df.empty:
        to_delete = st.selectbox("Select member to delete", df["Email"].tolist())
        if st.button("Delete", type="primary", use_container_width=True):
            df = df[df["Email"] != to_delete]
            save_data(df)
            st.success(f"Deleted member: {to_delete}")
            st.rerun()
    else:
        st.info("No members available.")

# ==========================
# 🚀 APP ENTRY POINT
# ==========================
st.title("🛡️ Secure Membership Management Portal")
st.caption("Manage registrations and send WhatsApp updates instantly.")

if not st.session_state.logged_in:
    login_form()
else:
    st.sidebar.success(f"Logged in as {ADMIN_USER}")
    st.sidebar.button("Logout", on_click=logout, use_container_width=True)
    df = st.session_state.df
    display_dashboard(df)
    tab1, tab2 = st.tabs(["Add Member", "Manage Members"])
    with tab1:
        add_member_section()
    with tab2:
        manage_members_section()
