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
TWILIO_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH = "your_twilio_auth_token"
TWILIO_FROM = "whatsapp:+14155238886"  # Example Twilio sandbox number
OWNER_PHONE = "+919876543210"  # Your owner number (used for backup login)

ADMIN_USER = "admin"
ADMIN_PASSWORD = "1234"  # Change this to your desired password

FILE_PATH = "membership.xlsx"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# Generate hashed password
ADMIN_PASSWORD_HASH = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Initialize Twilio
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
@st.cache_data(show_spinner="Loading data...")
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
# 💬 WHATSAPP MESSAGE
# ==========================
def send_whatsapp_confirmation(name, phone):
    """Send WhatsApp welcome message with owner number."""
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
        st.toast("✅ WhatsApp message sent!")
    except Exception as e:
        st.warning(f"⚠️ Failed to send message: {e}")

# ==========================
# 🔐 AUTHENTICATION
# ==========================
def check_admin_login(username, password):
    if username != ADMIN_USER:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), ADMIN_PASSWORD_HASH.encode('utf-8'))

def login_with_owner_number(owner_input):
    """Backup login using owner's number."""
    if owner_input.strip() == OWNER_PHONE:
        st.session_state.logged_in = True
        st.session_state.df = load_data()
        st.success("✅ Logged in using owner number.")
        st.rerun()
    else:
        st.error("❌ Invalid owner number. Access denied.")

def login_form():
    """Main login form with backup option."""
    st.markdown("### 🔒 Admin Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", use_container_width=True)
        if submitted:
            if check_admin_login(username, password):
                st.session_state.logged_in = True
                st.session_state.df = load_data()
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

    st.markdown("Forgot username or password?")
    if st.button("🔑 Log in using Owner's Number", use_container_width=True):
        st.session_state.show_backup_login = True
        st.rerun()

    if st.session_state.get("show_backup_login", False):
        st.markdown("### 📱 Backup Login (Owner Number)")
        with st.form("backup_login_form"):
            owner_input = st.text_input("Enter registered owner number")
            submitted = st.form_submit_button("Login via Owner Number")
            if submitted:
                login_with_owner_number(owner_input)

def logout():
    st.session_state.logged_in = False
    st.session_state.df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])
    st.session_state.show_backup_login = False
    st.toast("👋 Logged out successfully!")
    st.rerun()

# ==========================
# 📊 DASHBOARD
# ==========================
def display_dashboard(df):
    st.subheader("📊 Membership Dashboard")
    total_members = len(df)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Members", total_members)
    col2.metric("Latest Join Date", df["Join Date"].max() if total_members > 0 else "N/A")
    col3.metric("Unique Contacts", df["Phone"].nunique())
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
        if st.button("Delete Member", type="primary", use_container_width=True):
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
