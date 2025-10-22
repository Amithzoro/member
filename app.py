import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Gym Membership System", layout="wide")
INDIAN_TZ = pytz.timezone("Asia/Kolkata")
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def get_month_filename():
    month = datetime.now(INDIAN_TZ).strftime("%b_%Y")
    return os.path.join(DATA_DIR, f"{month}.xlsx")

def load_data():
    file = get_month_filename()
    if os.path.exists(file):
        return pd.read_excel(file)
    else:
        df = pd.DataFrame(columns=["Name", "Phone", "Join_Date", "Expiry_Date", "Time", "Password", "Added_By"])
        df.to_excel(file, index=False)
        return df

def save_data(df):
    df.to_excel(get_month_filename(), index=False)

def current_time():
    return datetime.now(INDIAN_TZ).strftime("%d-%m-%Y  %I:%M %p")

# -----------------------------
# LOGIN SYSTEM
# -----------------------------
def login_page():
    st.title("🏋️ Gym Membership Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username.lower() == "owner" and password == "admin123":
            st.session_state["logged_in"] = "owner"
            st.success("Logged in as Owner ✅")
            st.rerun()
        else:
            df = load_data()
            user = df[(df["Name"].str.lower() == username.lower()) & (df["Password"] == password)]
            if not user.empty:
                st.session_state["logged_in"] = "member"
                st.session_state["username"] = username
                st.success(f"Welcome back, {username}! 💪")
                st.rerun()
            else:
                st.error("Invalid username or password ❌")

# -----------------------------
# OWNER DASHBOARD
# -----------------------------
def owner_page():
    st.title("👑 Owner Dashboard")

    df = load_data()
    st.subheader("📋 Current Members")
    st.dataframe(df, use_container_width=True)

    with st.expander("➕ Add New Member"):
        name = st.text_input("Member Name")
        phone = st.text_input("Phone Number")
        join_date = st.date_input("Join Date", datetime.now(INDIAN_TZ).date())
        expiry_date = st.date_input("Expiry Date")
        password = st.text_input("Set Password for Member")

        if st.button("Add Member"):
            if name and phone and password:
                new_entry = {
                    "Name": name,
                    "Phone": phone,
                    "Join_Date": join_date.strftime("%d-%m-%Y"),
                    "Expiry_Date": expiry_date.strftime("%d-%m-%Y"),
                    "Time": current_time(),
                    "Password": password,
                    "Added_By": "Owner",
                }
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                save_data(df)
                st.success(f"✅ Member '{name}' added successfully!")
                st.rerun()
            else:
                st.warning("Please fill all fields.")

    if st.button("🔄 Refresh"):
        st.rerun()

# -----------------------------
# MEMBER PAGE
# -----------------------------
def member_page():
    df = load_data()
    username = st.session_state.get("username", "")
    member = df[df["Name"].str.lower() == username.lower()]

    if member.empty:
        st.error("Member not found.")
        return

    st.title(f"🏋️ Welcome, {username}")
    st.subheader("Your Membership Details")
    st.dataframe(member, use_container_width=True)

# -----------------------------
# MAIN LOGIC
# -----------------------------
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = None

    if st.session_state["logged_in"] == "owner":
        owner_page()
    elif st.session_state["logged_in"] == "member":
        member_page()
    else:
        login_page()

    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Logged out successfully!")
        st.rerun()

if __name__ == "__main__":
    main()
