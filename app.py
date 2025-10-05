import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------------------
# Basic Config
# ---------------------------
st.set_page_config(page_title="Gym Membership Manager", page_icon="💪", layout="centered")

# Owner credentials
OWNER_EMAIL = "yourowneremail@gmail.com"     # Change to owner's email
OWNER_PASSWORD = "admin123"                  # Change password
OWNER_APP_EMAIL = "yourowneremail@gmail.com" # Gmail for sending
OWNER_APP_PASSWORD = "your_app_password_here" # Gmail app password
OWNER_NUMBER = "7019384280"                  # Owner's contact number

# ---------------------------
# Utility Functions
# ---------------------------

def send_email(receiver_email, subject, body):
    """Send email using owner's Gmail account."""
    try:
        msg = MIMEMultipart()
        msg["From"] = OWNER_APP_EMAIL
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(OWNER_APP_EMAIL, OWNER_APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.warning(f"⚠️ Email sending failed: {e}")
        return False


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())


def calc_expiry(start_date, plan):
    plans = {
        "1 Month": 30,
        "3 Months": 90,
        "6 Months": 180,
        "1 Year": 365
    }
    return start_date + timedelta(days=plans[plan])


# ---------------------------
# Initialize Session State
# ---------------------------
if "users" not in st.session_state:
    st.session_state.users = {
        OWNER_EMAIL: {"password": hash_password(OWNER_PASSWORD), "role": "owner"}
    }

if "members" not in st.session_state:
    st.session_state.members = pd.DataFrame(columns=["Name", "Email", "Plan", "Start", "Expiry"])

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = None


# ---------------------------
# Authentication
# ---------------------------

def login_section():
    st.subheader("🔐 Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if email in st.session_state.users:
            user = st.session_state.users[email]
            if check_password(password, user["password"]):
                st.session_state.logged_in = True
                st.session_state.role = user["role"]
                st.success(f"Welcome, {user['role'].capitalize()}!")
                st.rerun()
            else:
                st.error("Incorrect password.")
        else:
            st.error("Email not registered.")


def register_section():
    st.subheader("🧾 Staff Registration")
    email = st.text_input("Staff Email")
    password = st.text_input("Create Password", type="password")

    if st.button("Register"):
        if email in st.session_state.users:
            st.warning("Email already registered.")
        else:
            st.session_state.users[email] = {
                "password": hash_password(password),
                "role": "staff"
            }
            st.success("✅ Staff registered successfully!")


# ---------------------------
# Dashboard
# ---------------------------

def dashboard():
    role = st.session_state.role.capitalize()
    st.sidebar.success(f"Role: {role}")

    if st.session_state.role == "owner":
        st.title("🏋️‍♂️ Owner Dashboard")
        menu = st.sidebar.radio("Menu", ["Add Member", "View Members", "Send Expiry Emails", "Logout"])
        if menu == "Add Member":
            add_member()
        elif menu == "View Members":
            view_members(editable=True)
        elif menu == "Send Expiry Emails":
            send_expiry_notifications()
        elif menu == "Logout":
            logout()

    elif st.session_state.role == "staff":
        st.title("👩‍💼 Staff Dashboard")
        menu = st.sidebar.radio("Menu", ["Add Member", "View Members", "Logout"])
        if menu == "Add Member":
            add_member()
        elif menu == "View Members":
            view_members(editable=False)
        elif menu == "Logout":
            logout()


# ---------------------------
# Member Management
# ---------------------------

def add_member():
    st.subheader("➕ Add New Member")
    name = st.text_input("Member Name")
    email = st.text_input("Member Email")
    plan = st.selectbox("Select Plan", ["1 Month", "3 Months", "6 Months", "1 Year"])
    start = st.date_input("Start Date", datetime.today())

    if st.button("Add Member"):
        expiry = calc_expiry(start, plan)
        new_member = pd.DataFrame([[name, email, plan, start, expiry]],
                                  columns=["Name", "Email", "Plan", "Start", "Expiry"])
        st.session_state.members = pd.concat([st.session_state.members, new_member], ignore_index=True)
        st.success(f"✅ {name} added successfully till {expiry.strftime('%d-%m-%Y')}.")

        # Send welcome email
        send_email(email, "Welcome to Gym Membership",
                   f"Hi {name}, your {plan} plan is active till {expiry.strftime('%d-%m-%Y')}.\n\n"
                   f"For any help, contact the owner at {OWNER_NUMBER}.\n\n- Gym Management")


def view_members(editable=False):
    st.subheader("📋 Member List")
    df = st.session_state.members

    if df.empty:
        st.info("No members found.")
        return

    st.dataframe(df)

    if editable:
        st.markdown("---")
        delete_email = st.selectbox("Select member to delete", df["Email"].tolist())
        if st.button("🗑️ Delete Member", type="primary"):
            delete_member(delete_email)

        if st.button("🧹 Clear All Members"):
            st.session_state.members = pd.DataFrame(columns=["Name", "Email", "Plan", "Start", "Expiry"])
            st.success("✅ All member data cleared.")


def delete_member(email):
    """Delete a member and send them a cancellation email."""
    df = st.session_state.members
    member = df[df["Email"] == email]

    if member.empty:
        st.warning("Member not found.")
        return

    name = member.iloc[0]["Name"]
    plan = member.iloc[0]["Plan"]
    expiry = member.iloc[0]["Expiry"]

    # Remove from DataFrame
    st.session_state.members = df[df["Email"] != email]

    # Send cancellation email
    send_email(email, "Membership Cancelled",
               f"Hi {name}, your {plan} membership (expiring on {expiry}) has been cancelled by the owner.\n\n"
               f"For any help, contact the owner at {OWNER_NUMBER}.\n\n- Gym Management System")

    st.success(f"🗑️ {name}'s membership deleted and cancellation email sent.")


def send_expiry_notifications():
    today = datetime.today().date()
    expired = st.session_state.members[pd.to_datetime(st.session_state.members["Expiry"]).dt.date <= today]

    if expired.empty:
        st.info("No expired memberships today.")
    else:
        for _, row in expired.iterrows():
            send_email(row["Email"], "Membership Expired",
                       f"Hi {row['Name']}, your {row['Plan']} plan expired on {row['Expiry']}.\n\n"
                       f"Please renew soon. Contact Owner: {OWNER_NUMBER}")
        st.success("✅ Expiry notifications sent successfully!")


def logout():
    st.session_state.logged_in = False
    st.session_state.role = None
    st.rerun()


# ---------------------------
# Main
# ---------------------------

def main():
    st.title("💪 Gym Membership System")

    if not st.session_state.logged_in:
        tab1, tab2 = st.tabs(["Login", "Register Staff"])
        with tab1:
            login_section()
        with tab2:
            register_section()
    else:
        dashboard()


if __name__ == "__main__":
    main()
