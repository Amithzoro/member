import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- Page config ---
st.set_page_config(page_title="Membership Tracker", layout="wide")

EXCEL_FILE = "membership.xlsx"

# --- Create Excel file if not exists ---
if not os.path.exists(EXCEL_FILE):
    df_init = pd.DataFrame(columns=["Name", "Start_Date", "End_Date", "Phone"])
    df_init.to_excel(EXCEL_FILE, index=False)

# --- Functions ---
def load_data():
    return pd.read_excel(EXCEL_FILE)

def save_data(df):
    df.to_excel(EXCEL_FILE, index=False)

# --- Sidebar Login ---
st.sidebar.title("🔐 Login Panel")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")
login = st.sidebar.button("Login")

if login:
    if username == "owner" and password == "admin123":
        st.session_state["role"] = "owner"
        st.success("Welcome 👑 Owner!")
    elif username == "member" and password == "1234":
        st.session_state["role"] = "member"
        st.success("Welcome 🙋 Member!")
    else:
        st.error("❌ Invalid credentials")

# --- Dashboard ---
if "role" in st.session_state:
    role = st.session_state["role"]
    df = load_data()

    if role == "owner":
        st.title("👑 Owner Dashboard")

        # 🔔 Reminders
        st.subheader("🔔 Membership Reminders")
        if not df.empty:
            df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")
            today = datetime.now().date()
            expiring = df[(df["End_Date"].dt.date - today).between(0, 3)]

            if not expiring.empty:
                st.warning("⚠️ These memberships are expiring soon:")
                st.table(expiring[["Name", "End_Date"]])
            else:
                st.success("✅ No memberships expiring soon.")
        else:
            st.info("No members found yet.")

        st.divider()

        # ➕ Add or Update Member
        st.subheader("➕ Add / Update Member")

        name = st.text_input("Member Name")
        phone = st.text_input("Phone Number")
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        submit = st.button("Submit / Update")

        if submit:
            if name.strip() == "":
                st.error("Please enter a name.")
            else:
                # Update or Add
                if name in df["Name"].values:
                    df.loc[df["Name"] == name, ["Start_Date", "End_Date", "Phone"]] = [start_date, end_date, phone]
                    st.success(f"✅ Updated {name}'s record.")
                else:
                    new_row = {"Name": name, "Start_Date": start_date, "End_Date": end_date, "Phone": phone}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"✅ Added new member: {name}")

                save_data(df)
                st.rerun()

        st.divider()

        # 🧾 Show Members
        st.subheader("📋 All Members")
        st.dataframe(df)

    elif role == "member":
        st.title("🙋 Member Dashboard")
        st.info("You can view the current membership list below:")
        st.dataframe(df)
