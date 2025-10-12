import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Membership System", layout="wide")

EXCEL_FILE = "membership.xlsx"

# --- Initialize file if not exists ---
if not os.path.exists(EXCEL_FILE):
    df_init = pd.DataFrame(columns=["Name", "Start_Date", "End_Date", "Phone"])
    df_init.to_excel(EXCEL_FILE, index=False)

# --- Function to load and save data ---
def load_data():
    return pd.read_excel(EXCEL_FILE)

def save_data(df):
    df.to_excel(EXCEL_FILE, index=False)

# --- Sidebar login ---
st.sidebar.title("🔐 Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")
login_btn = st.sidebar.button("Login")

# --- Login validation ---
if login_btn:
    if username == "owner" and password == "admin123":
        st.session_state["role"] = "owner"
        st.success("Welcome, Owner 👑")
    elif username == "member" and password == "1234":
        st.session_state["role"] = "member"
        st.success("Welcome, Member 🙋‍♂️")
    else:
        st.error("Invalid credentials ❌")

# --- Dashboard after login ---
if "role" in st.session_state:
    role = st.session_state["role"]
    df = load_data()

    # --- Owner dashboard ---
    if role == "owner":
        st.title("👑 Owner Dashboard")

        # Reminder section
        st.subheader("🔔 Membership Reminders")
        if not df.empty and "End_Date" in df.columns:
            df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")
            today = datetime.now().date()
            due_members = df[(df["End_Date"].dt.date - today).between(0, 3)]

            if not due_members.empty:
                st.warning("⏰ Memberships expiring soon!")
                st.table(due_members[["Name", "End_Date"]])
            else:
                st.success("✅ All memberships are active.")
        else:
            st.info("No End_Date column found in the data.")

        st.divider()

        # --- Add / Update Member ---
        st.subheader("➕ Add or Update Member")

        name = st.text_input("Member Name")
        phone = st.text_input("Phone Number")
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        submit = st.button("Submit / Update")

        if submit:
            # check if member exists
            if name in df["Name"].values:
                df.loc[df["Name"] == name, ["Start_Date", "End_Date", "Phone"]] = [start_date, end_date, phone]
                st.success(f"✅ Updated existing member: {name}")
            else:
                new_row = {"Name": name, "Start_Date": start_date, "End_Date": end_date, "Phone": phone}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                st.success(f"✅ Added new member: {name}")

            save_data(df)  # <-- auto update Excel
            st.rerun()

        st.divider()

        # --- Show all members ---
        st.subheader("📋 All Members")
        st.dataframe(df)

    # --- Member dashboard ---
    elif role == "member":
        st.title("🙋‍♂️ Member Dashboard")
        st.info("Welcome! You can view membership info below.")
        st.dataframe(df)
