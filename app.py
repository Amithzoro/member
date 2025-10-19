import streamlit as st
import pandas as pd
import bcrypt
import calendar
from datetime import datetime, timedelta
import pytz
import os

# -----------------------------
# CONFIG
# -----------------------------
TIMEZONE = pytz.timezone("Asia/Kolkata")
EXCEL_FILE = "gym_data.xlsx"

# -----------------------------
# INITIAL SETUP
# -----------------------------
if not os.path.exists(EXCEL_FILE):
    users_df = pd.DataFrame([
        {"Username": "vineeth", "Password": bcrypt.hashpw("Panda@2006".encode(), bcrypt.gensalt()).decode(), "Role": "owner"},
        {"Username": "amith", "Password": bcrypt.hashpw("Amith@123".encode(), bcrypt.gensalt()).decode(), "Role": "staff"},
    ])
    members_df = pd.DataFrame(columns=["Full_Name", "Phone", "Membership_Type", "Join_Date", "Expiry_Date", "Added_By"])
    log_df = pd.DataFrame(columns=["Username", "Role", "Login_Time", "Date"])

    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

# -----------------------------
# LOAD / SAVE FUNCTIONS
# -----------------------------
def load_data():
    xls = pd.ExcelFile(EXCEL_FILE)
    users_df = pd.read_excel(xls, "Users")
    members_df = pd.read_excel(xls, "Members")
    log_df = pd.read_excel(xls, "Login_Log")

    # ✅ Ensure columns exist (prevents KeyErrors)
    for col in ["Full_Name", "Phone", "Membership_Type", "Join_Date", "Expiry_Date", "Added_By"]:
        if col not in members_df.columns:
            members_df[col] = ""

    return users_df, members_df, log_df


def save_data(users_df, members_df, log_df):
    users_df = users_df.astype(str)
    members_df = members_df.astype(str)
    log_df = log_df.astype(str)

    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

    # Monthly backup
    month_name = calendar.month_name[datetime.now(TIMEZONE).month]
    backup_file = f"gym_data_{month_name[:3]}.xlsx"
    with pd.ExcelWriter(backup_file, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

# -----------------------------
# LOGIN FUNCTION
# -----------------------------
def login(username, password, users_df):
    user = users_df[users_df["Username"] == username]
    if not user.empty:
        hashed_pw = user.iloc[0]["Password"].encode()
        if bcrypt.checkpw(password.encode(), hashed_pw):
            return user.iloc[0]["Role"]
    return None

# -----------------------------
# CALCULATE EXPIRY
# -----------------------------
def get_expiry_date(join_date, membership_type):
    if membership_type == "Monthly":
        return join_date + timedelta(days=30)
    elif membership_type == "Quarterly":
        return join_date + timedelta(days=90)
    elif membership_type == "Yearly":
        return join_date + timedelta(days=365)
    else:
        return join_date

# -----------------------------
# STREAMLIT APP
# -----------------------------
st.set_page_config(page_title="Gym Management", page_icon="💪", layout="wide")
st.title("🏋️‍♂️ Gym Management System")

users_df, members_df, log_df = load_data()

# -----------------------------
# SIDEBAR: REMINDERS
# -----------------------------
st.sidebar.header("🔔 Expiry Reminders")
if not members_df.empty:
    members_df["Expiry_Date"] = pd.to_datetime(members_df["Expiry_Date"], errors="coerce")
    soon_expiring = members_df[members_df["Expiry_Date"] <= datetime.now(TIMEZONE) + timedelta(days=7)]
    if soon_expiring.empty:
        st.sidebar.success("✅ No memberships expiring soon.")
    else:
        for _, row in soon_expiring.iterrows():
            st.sidebar.warning(f"{row['Full_Name']} ({row['Membership_Type']})\n📅 Expires: {row['Expiry_Date'].date()}")
else:
    st.sidebar.info("No members yet.")

# -----------------------------
# TABS
# -----------------------------
tab_login, tab_members, tab_logs = st.tabs(["🔑 Login", "👥 Members", "📘 Login Records"])

# -----------------------------
# LOGIN TAB
# -----------------------------
with tab_login:
    st.subheader("Login Portal")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        role = login(username, password, users_df)
        if role:
            now = datetime.now(TIMEZONE)
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%I:%M:%S %p")

            new_entry = pd.DataFrame([{
                "Username": username,
                "Role": role,
                "Login_Time": time_str,
                "Date": date_str
            }])

            log_df = pd.concat([log_df, new_entry], ignore_index=True)
            save_data(users_df, members_df, log_df)

            st.success(f"✅ Welcome {username}! Logged in as {role.upper()}.")
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = role
        else:
            st.error("❌ Invalid username or password")

# -----------------------------
# MEMBERS TAB
# -----------------------------
with tab_members:
    if "logged_in" in st.session_state and st.session_state["logged_in"]:
        role = st.session_state["role"]
        username = st.session_state["username"]

        st.subheader("➕ Add New Member")
        full_name = st.text_input("Full Name")
        phone = st.text_input("Phone Number")
        membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Yearly"])

        if st.button("Add Member"):
            if full_name and phone:
                join_date = datetime.now(TIMEZONE)
                expiry_date = get_expiry_date(join_date, membership_type)

                new_member = pd.DataFrame([{
                    "Full_Name": full_name,
                    "Phone": phone,
                    "Membership_Type": membership_type,
                    "Join_Date": join_date.strftime("%Y-%m-%d"),
                    "Expiry_Date": expiry_date.strftime("%Y-%m-%d"),
                    "Added_By": username
                }])

                members_df = pd.concat([members_df, new_member], ignore_index=True)
                save_data(users_df, members_df, log_df)
                st.success(f"✅ Member '{full_name}' added successfully!")
            else:
                st.warning("Please enter both name and phone number.")

        st.divider()
        st.subheader("📋 Member List")
        st.dataframe(members_df)

        # -----------------------------
        # OWNER ONLY: EDIT/DELETE
        # -----------------------------
        if role == "owner" and not members_df.empty:
            st.subheader("✏️ Edit or Delete Members")
            member_names = members_df["Full_Name"].tolist()
            selected = st.selectbox("Select Member", member_names)

            member_data = members_df[members_df["Full_Name"] == selected].iloc[0]

            new_phone = st.text_input("Phone", member_data["Phone"])
            new_type = st.selectbox(
                "Membership Type",
                ["Monthly", "Quarterly", "Yearly"],
                index=["Monthly", "Quarterly", "Yearly"].index(member_data["Membership_Type"])
            )

            if st.button("Update Member"):
                idx = members_df[members_df["Full_Name"] == selected].index[0]
                members_df.at[idx, "Phone"] = new_phone
                members_df.at[idx, "Membership_Type"] = new_type
                new_expiry = get_expiry_date(datetime.strptime(members_df.at[idx, "Join_Date"], "%Y-%m-%d"), new_type)
                members_df.at[idx, "Expiry_Date"] = new_expiry.strftime("%Y-%m-%d")
                save_data(users_df, members_df, log_df)
                st.success("✅ Member updated successfully!")

            if st.button("❌ Delete Member"):
                members_df = members_df[members_df["Full_Name"] != selected]
                save_data(users_df, members_df, log_df)
                st.warning(f"🗑️ Member '{selected}' deleted.")

    else:
        st.warning("Please log in first to manage members.")

# -----------------------------
# LOGIN RECORDS TAB
# -----------------------------
with tab_logs:
    st.subheader("📅 Login History")
    st.dataframe(log_df)

    if "logged_in" in st.session_state and st.session_state["logged_in"]:
        if st.session_state["role"] == "owner":
            if st.button("🧹 Clear Logs"):
                log_df = pd.DataFrame(columns=["Username", "Role", "Login_Time", "Date"])
                save_data(users_df, members_df, log_df)
                st.success("✅ Logs cleared successfully!")
