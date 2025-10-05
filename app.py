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

OWNER_EMAIL = "yourowneremail@gmail.com"  # change this to your Gmail
OWNER_PASSWORD = "yourapppassword"  # generated app password
OWNER_NUMBER = "7019384280"

# ---------------------------
# Functions
# ---------------------------

def send_email(receiver_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = OWNER_EMAIL
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(OWNER_EMAIL, OWNER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.warning(f"Email sending failed: {e}")
        return False


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())


def calc_expiry(start_date, plan):
    plan_days = {
        "1 Month": 30,
        "3 Months": 90,
        "6 Months": 180,
        "1 Year": 365
    }
    return start_date + timedelta(days=plan_days[plan])


# ---------------------------
# Data Storage (in memory for demo)
# ---------------------------
if "users" not in st.session_state:
    st.session_state.users = {
        OWNER_EMAIL: {"password": hash_password("admin123"), "role": "owner"}
    }

if "members" not in st.session_state:
    st.session_state.members = pd.DataFrame(columns=["Name", "Email", "Plan", "Start", "Expiry"])


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
                st.success(f"Welcome {user['role'].capitalize()}!")
            else:
                st.error("Incorrect password.")
        else:
            st.error("Email not found.")

    st.markdown("---")
    st.write("Don't have an account? Register below.")


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
            st.success("Staff registered successfully!")


# ---------------------------
# Main Owner/Staff Dashboard
# ---------------------------

def dashboard():
    role_display = st.session_state.role.capitalize() if st.session_state.role else "Not Logged In"
    st.sidebar.success(f"Role: {role_display}")

    if st.session_state.role == "owner":
        st.title("🏋️‍♂️ Owner Dashboard")
        st.write("Manage all members and staff here.")

        menu = st.sidebar.radio("Menu", ["Add Member", "View Members", "Send Expiry Emails", "Logout"])

        if menu == "Add Member":
            add_member()
        elif menu == "View Members":
            view_members(editable=True)
        elif menu == "Send Expiry Emails":
            send_expiry_notifications()
        elif menu == "Logout":
            st.session_state.logged_in = False
            st.experimental_rerun()

    elif st.session_state.role == "staff":
        st.title("👩‍💼 Staff Dashboard")
        st.write("You can add and view members (editing disabled).")

        menu = st.sidebar.radio("Menu", ["Add Member", "View Members", "Logout"])
        if menu == "Add Member":
            add_member()
        elif menu == "View Members":
            view_members(editable=False)
        elif menu == "Logout":
            st.session_state.logged_in = False
            st.experimental_rerun()


# ---------------------------
# Member Functions
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
        st.success(f"Member {name} added successfully until {expiry.strftime('%d-%m-%Y')}.")

        # Notify via email
        send_email(email, "Welcome to Gym Membership",
                   f"Hi {name}, your {plan} membership is active till {expiry.strftime('%d-%m-%Y')}.\n- {OWNER_EMAIL}")


def view_members(editable=False):
    st.subheader("📋 Member List")
    if st.session_state.members.empty:
        st.info("No members yet.")
    else:
        st.dataframe(st.session_state.members)
        if editable and st.button("Clear All Members"):
            st.session_state.members = pd.DataFrame(columns=["Name", "Email", "Plan", "Start", "Expiry"])
            st.success("All member data cleared.")


def send_expiry_notifications():
    today = datetime.today().date()
    expired = st.session_state.members[pd.to_datetime(st.session_state.members["Expiry"]).dt.date <= today]

    if expired.empty:
        st.info("No memberships expired today.")
    else:
        for _, row in expired.iterrows():
            send_email(row["Email"], "Membership Expired",
                       f"Hi {row['Name']}, your {row['Plan']} plan expired on {row['Expiry']}. Please renew soon.")
        st.success("Expiry emails sent successfully!")


# ---------------------------
# App Flow
# ---------------------------

def main():
    st.title("💪 Gym Membership System")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "role" not in st.session_state:
        st.session_state.role = None

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
