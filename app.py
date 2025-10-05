import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, timedelta
import pytz
import os

# --- CONFIGURATION ---
OWNER_EMAIL = "owner@gmail.com"  # your email
OWNER_PHONE = "7019384280"       # your number
OWNER_PASSWORD = "admin123"      # owner password

TIMEZONE = pytz.timezone("Asia/Kolkata")
FILE_PATH = "membership.xlsx"

# --- INITIAL STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "email" not in st.session_state:
    st.session_state.email = None


# --- LOAD / SAVE DATA ---
def load_data():
    if os.path.exists(FILE_PATH):
        try:
            df = pd.read_excel(FILE_PATH)
        except Exception:
            df = pd.DataFrame(columns=["Name", "Email", "Phone", "Plan", "Join Date", "Expiry Date", "Added By"])
    else:
        df = pd.DataFrame(columns=["Name", "Email", "Phone", "Plan", "Join Date", "Expiry Date", "Added By"])
    return df

def save_data(df):
    df.to_excel(FILE_PATH, index=False)
    st.success("✅ Data saved successfully!")


# --- LOGIN SYSTEM ---
def login_form():
    st.title("🔐 Membership Portal Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")

    if login_btn:
        if email == OWNER_EMAIL and password == OWNER_PASSWORD:
            st.session_state.logged_in = True
            st.session_state.role = "owner"
            st.session_state.email = email
            st.success("Welcome Owner!")
            st.rerun()
        else:
            df_staff = load_data()
            if email in df_staff["Added By"].values:
                st.session_state.logged_in = True
                st.session_state.role = "staff"
                st.session_state.email = email
                st.success(f"Welcome {email} (Staff)")
                st.rerun()
            else:
                st.error("Invalid credentials or unauthorized email.")


def logout():
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.email = None
    st.rerun()


# --- MEMBER MANAGEMENT ---
def calculate_expiry(plan):
    now = datetime.now(TIMEZONE)
    if plan == "1 Month":
        return now + timedelta(days=30)
    elif plan == "3 Months":
        return now + timedelta(days=90)
    elif plan == "6 Months":
        return now + timedelta(days=180)
    elif plan == "1 Year":
        return now + timedelta(days=365)
    else:
        return now

def add_member():
    st.subheader("🧾 Register New Member")

    df = load_data()

    name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")
    plan = st.selectbox("Select Membership Plan", ["1 Month", "3 Months", "6 Months", "1 Year"])

    if st.button("Add Member"):
        if not name or not email or not phone:
            st.warning("Please fill all fields.")
            return

        if email in df["Email"].values:
            st.warning("Member already exists!")
            return

        join_date = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
        expiry_date = calculate_expiry(plan).strftime("%Y-%m-%d %H:%M:%S")

        new_member = pd.DataFrame([{
            "Name": name,
            "Email": email,
            "Phone": phone,
            "Plan": plan,
            "Join Date": join_date,
            "Expiry Date": expiry_date,
            "Added By": st.session_state.email
        }])

        df = pd.concat([df, new_member], ignore_index=True)
        save_data(df)
        st.success(f"Member {name} added successfully with {plan} plan.")
        st.info(f"Expiry Date: {expiry_date}")


def view_members():
    st.subheader("📋 Member Records")
    df = load_data()

    if df.empty:
        st.info("No members found.")
        return

    st.dataframe(df, use_container_width=True)


def manage_members():
    st.subheader("⚙️ Manage Members (Owner Only)")
    df = load_data()

    if df.empty:
        st.info("No members found.")
        return

    st.dataframe(df, use_container_width=True)

    selected_email = st.selectbox("Select member to delete", df["Email"].tolist())

    if st.button("Delete Member"):
        df = df[df["Email"] != selected_email]
        save_data(df)
        st.success("Member deleted successfully.")
        st.rerun()


def dashboard():
    st.subheader("📊 Dashboard")
    df = load_data()

    if df.empty:
        st.info("No members to display.")
        return

    df["Expiry Date"] = pd.to_datetime(df["Expiry Date"], errors="coerce")
    today = datetime.now(TIMEZONE)
    active = df[df["Expiry Date"] > today]
    expired = df[df["Expiry Date"] <= today]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Members", len(df))
    col2.metric("Active Members", len(active))
    col3.metric("Expired Members", len(expired))

    st.dataframe(df, use_container_width=True)


# --- MAIN APP ---
def main():
    if not st.session_state.logged_in:
        login_form()
        return

    st.sidebar.write(f"👤 Logged in as: {st.session_state.email}")
    st.sidebar.write(f"Role: {st.session_state.role.capitalize()}")
    st.sidebar.button("Logout", on_click=logout)

    if st.session_state.role == "owner":
        dashboard()
        tab1, tab2, tab3 = st.tabs(["Add Member", "View Members", "Manage Members"])
        with tab1:
            add_member()
        with tab2:
            view_members()
        with tab3:
            manage_members()

    elif st.session_state.role == "staff":
        st.info("Staff Access: You can only add new members.")
        add_member()
        st.divider()
        view_members()

    else:
        st.error("Unknown role! Please log in again.")


if __name__ == "__main__":
    main()
