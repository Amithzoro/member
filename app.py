import streamlit as st
import pandas as pd
import pytz
import bcrypt
from twilio.rest import Client
from datetime import datetime
import time
from filelock import FileLock
import logging

# --- Basic Config ---
st.set_page_config(page_title="Membership Portal", page_icon="🛡️", layout="wide")
logging.basicConfig(filename="app.log", level=logging.ERROR)

# --- Initialize Session State ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])

FILE_PATH = "membership.xlsx"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# --- Load Secrets ---
try:
    TWILIO_SID = st.secrets["TWILIO_SID"]
    TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
    TWILIO_FROM = st.secrets["TWILIO_FROM"]
    ADMIN_USER = st.secrets.get("ADMIN_USER", "admin")
    ADMIN_PASSWORD_HASH = st.secrets["ADMIN_PASSWORD_HASH"]
except KeyError as e:
    st.error(f"❌ Missing secret key: {e}. Please define Twilio and Admin keys in Streamlit secrets.")
    st.stop()

# --- Initialize Twilio ---
client = Client(TWILIO_SID, TWILIO_AUTH)

# --- Data Functions ---
def load_data():
    """Load member data from Excel."""
    try:
        df = pd.read_excel(FILE_PATH)
        if 'Password' not in df.columns:
            df['Password'] = ''
        if 'Join Date' not in df.columns:
            df['Join Date'] = ''
        st.session_state.df = df
    except FileNotFoundError:
        st.session_state.df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])
    except Exception as e:
        logging.error(f"Error loading Excel file: {e}")
        st.error("⚠️ Error loading data file.")

def save_data(df):
    """Save DataFrame to Excel safely."""
    try:
        with FileLock(FILE_PATH + ".lock"):
            df.to_excel(FILE_PATH, index=False)
        st.session_state.df = df
        st.toast("💾 Data saved successfully!", icon="✅")
    except Exception as e:
        logging.error(f"Error saving data: {e}")
        st.error("⚠️ Failed to save data. Check logs for details.")

# --- Utility Functions ---
def send_whatsapp_confirmation(name, phone):
    """Send welcome message via WhatsApp."""
    try:
        client.messages.create(
            body=f"Hello {name}, welcome to our exclusive membership program! Your registration is complete 🎉",
            from_=TWILIO_FROM,
            to=f"whatsapp:{phone}"
        )
        st.toast("✅ WhatsApp message sent!")
    except Exception as e:
        logging.error(f"WhatsApp Error: {e}")
        st.warning(f"⚠️ Could not send WhatsApp message. Error: {e}")

def check_admin_login(username, password):
    """Check admin credentials."""
    if username != ADMIN_USER:
        return False
    try:
        return bcrypt.checkpw(password.encode('utf-8'), ADMIN_PASSWORD_HASH.encode('utf-8'))
    except Exception as e:
        logging.error(f"Password check error: {e}")
        return False

def logout():
    """Logout admin."""
    st.session_state.logged_in = False
    st.session_state.df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])
    st.toast("👋 Logged out successfully.")
    st.rerun()

# --- Login Form ---
def login_form():
    st.markdown("### 🔒 Administrator Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Log In", use_container_width=True)
        if login_btn:
            with st.spinner("Verifying..."):
                time.sleep(0.5)
                if check_admin_login(username, password):
                    st.session_state.logged_in = True
                    st.success("✅ Login successful!")
                    load_data()
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password.")

# --- Dashboard ---
def display_dashboard(df):
    st.subheader("📊 Membership Dashboard")
    total = len(df)
    latest_join = df["Join Date"].max() if not df.empty else "N/A"
    phones = df['Phone'].nunique() if not df.empty else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Members", total)
    col2.metric("Latest Join Date", str(latest_join).split(" ")[0] if latest_join != "N/A" else "N/A")
    col3.metric("Unique Phones", phones)
    st.divider()

# --- Add Member Section ---
def add_member_section():
    st.subheader("➕ Register New Member")
    with st.form("add_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", max_chars=50)
            email = st.text_input("Email")
        with col2:
            phone = st.text_input("Phone (+countrycode...)", placeholder="+919876543210")
            password = st.text_input("Password", type="password")

        add_btn = st.form_submit_button("Add Member", type="primary", use_container_width=True)

        if add_btn:
            df = st.session_state.df
            if not (name and email and phone and password):
                st.warning("⚠️ All fields are required.")
                return
            if not phone.startswith("+"):
                st.warning("⚠️ Phone number must start with + and country code.")
                return
            if df['Email'].str.contains(email, case=False).any():
                st.warning("⚠️ Email already exists.")
                return
            try:
                hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
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
                st.success(f"✅ {name} added successfully!")
                st.rerun()
            except Exception as e:
                logging.error(f"Error adding member: {e}")
                st.error("❌ Could not add member. See logs.")
    st.divider()

# --- Manage Members Section ---
def manage_members_section():
    st.subheader("📝 Edit & Delete Members")
    df = st.session_state.df.copy()
    if df.empty:
        st.info("No members found.")
        return

    df_display = df.drop(columns=['Password'], errors='ignore')
    search = st.text_input("🔍 Search by Name or Phone")
    if search:
        df_display = df_display[df_display["Name"].str.contains(search, case=False, na=False) |
                                df_display["Phone"].str.contains(search, na=False)]

    edited_df = st.data_editor(
        df_display,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Email": st.column_config.TextColumn("Email", disabled=True),
            "Join Date": st.column_config.DatetimeColumn("Join Date", disabled=True)
        }
    )

    if st.button("💾 Apply Changes", type="primary"):
        try:
            for idx, row in edited_df.iterrows():
                if idx < len(st.session_state.df):
                    st.session_state.df.loc[idx, 'Name'] = row['Name']
                    st.session_state.df.loc[idx, 'Phone'] = row['Phone']
            save_data(st.session_state.df)
            st.success("✅ Changes saved!")
            st.rerun()
        except Exception as e:
            logging.error(f"Edit error: {e}")
            st.error("❌ Failed to save edits.")

    st.markdown("### 🗑️ Delete Member")
    member_list = st.session_state.df['Email'].tolist()
    member_to_delete = st.selectbox("Select Email", member_list)
    if st.button("Confirm Delete", type="secondary"):
        df_new = st.session_state.df[st.session_state.df['Email'] != member_to_delete]
        save_data(df_new)
        st.success(f"✅ Member {member_to_delete} deleted.")
        st.rerun()

# --- Main App ---
st.title("🛡️ Secure Membership Management Portal")
st.caption("Manage members, track data, and send WhatsApp confirmations via Twilio.")

if not st.session_state.logged_in:
    login_form()
else:
    st.sidebar.success(f"Logged in as {ADMIN_USER}")
    st.sidebar.button("Logout", on_click=logout, use_container_width=True)

    df = st.session_state.df
    display_dashboard(df)

    tab1, tab2 = st.tabs(["➕ New Registration", "📝 Manage Members"])
    with tab1:
        add_member_section()
    with tab2:
        manage_members_section()
