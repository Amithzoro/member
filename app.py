import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, timedelta
import pytz
import os
import calendar

# ==============================
# APP CONFIG
# ==============================
st.set_page_config(page_title="🏋️ Gym Membership System", layout="wide")

EXCEL_FILE = "membership.xlsx"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# ==============================
# LOAD / SAVE FUNCTIONS
# ==============================
def load_data(sheet_name="Members"):
    """Load Excel data safely."""
    if not os.path.exists(EXCEL_FILE):
        if sheet_name == "Members":
            return pd.DataFrame(columns=[
                "Username", "Password", "Role", "Name", "Phone",
                "Start_Date", "End_Date", "Membership_Type",
                "Amount", "Recorded_At", "Recorded_By"
            ])
        else:
            return pd.DataFrame(columns=["Username", "Role", "Login_Time"])

    try:
        return pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
    except Exception:
        if sheet_name == "Members":
            return pd.DataFrame(columns=[
                "Username", "Password", "Role", "Name", "Phone",
                "Start_Date", "End_Date", "Membership_Type",
                "Amount", "Recorded_At", "Recorded_By"
            ])
        else:
            return pd.DataFrame(columns=["Username", "Role", "Login_Time"])


def save_data(members_df, log_df):
    """Save to Excel and create monthly backup."""
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

    month_name = calendar.month_name[datetime.now(TIMEZONE).month]
    timestamp = datetime.now(TIMEZONE).strftime("%d-%H-%M-%S")
    monthly_file = f"membership_{month_name[:3]}_{timestamp}.xlsx"
    with pd.ExcelWriter(monthly_file, engine="openpyxl") as writer:
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)


members_df = load_data("Members")
log_df = load_data("Login_Log")

# ==============================
# PASSWORD FUNCTIONS
# ==============================
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

# ==============================
# UI
# ==============================
st.title("🏋️ Gym Membership Management System")

menu = st.sidebar.radio("Menu", ["Login", "Sign Up"])

# ==============================
# SIGNUP SECTION
# ==============================
if menu == "Sign Up":
    st.subheader("🧾 Create New Account")
    username = st.text_input("Create Username")
    password = st.text_input("Create Password", type="password")
    role = st.selectbox("Select Role", ["owner", "member"])
    signup_btn = st.button("Create Account")

    if signup_btn:
        if username.strip() == "" or password.strip() == "":
            st.warning("⚠️ Please fill all fields.")
        elif username in members_df["Username"].values:
            st.warning("⚠️ Username already exists.")
        else:
            hashed = hash_password(password)
            recorded_at = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            new_user = pd.DataFrame([{
                "Username": username,
                "Password": hashed,
                "Role": role,
                "Name": "",
                "Phone": "",
                "Start_Date": None,
                "End_Date": None,
                "Membership_Type": "",
                "Amount": 0,
                "Recorded_At": recorded_at,
                "Recorded_By": username
            }])
            members_df = pd.concat([members_df, new_user], ignore_index=True)
            save_data(members_df, log_df)
            st.success("✅ Account created successfully! Please login.")
            st.rerun()

# ==============================
# LOGIN SECTION
# ==============================
elif menu == "Login":
    st.subheader("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")

    if login_btn:
        if username in members_df["Username"].values:
            user_row = members_df[members_df["Username"] == username].iloc[0]
            if check_password(password, user_row["Password"]):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["role"] = user_row["Role"]
                st.success(f"Welcome {username}! Redirecting...")
                login_time = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                log_df = pd.concat([log_df, pd.DataFrame([{
                    "Username": username,
                    "Role": user_row["Role"],
                    "Login_Time": login_time
                }])], ignore_index=True)
                save_data(members_df, log_df)
                st.rerun()
            else:
                st.error("❌ Incorrect password.")
        else:
            st.error("❌ Username not found.")

# ==============================
# AFTER LOGIN
# ==============================
if st.session_state.get("logged_in", False):
    username = st.session_state["username"]
    role = st.session_state["role"]

    st.sidebar.success(f"✅ Logged in as {username} ({role})")
    logout = st.sidebar.button("Logout")
    if logout:
        st.session_state.clear()
        st.rerun()

    st.markdown(f"### 👋 Welcome, **{username}** ({role.upper()})")

    members_df = load_data("Members")
    log_df = load_data("Login_Log")

    # OWNER SECTION
    if role == "owner":
        st.subheader("🧾 Add / Update Member")
        with st.form("membership_form", clear_on_submit=True):
            name = st.text_input("Member Name")
            phone = st.text_input("Phone Number")
            start_date = st.date_input("Start Date", datetime.now().date())
            membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Half-Yearly", "Yearly"])
            amount = st.number_input("Amount", min_value=0)

            # Auto-calc end date
            if membership_type == "Monthly":
                end_date = start_date + timedelta(days=30)
            elif membership_type == "Quarterly":
                end_date = start_date + timedelta(days=90)
            elif membership_type == "Half-Yearly":
                end_date = start_date + timedelta(days=180)
            else:
                end_date = start_date + timedelta(days=365)

            submit = st.form_submit_button("Save Member")

            if submit:
                recorded_at = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                new_data = pd.DataFrame([{
                    "Username": username,
                    "Password": members_df.loc[members_df["Username"] == username, "Password"].values[0],
                    "Role": role,
                    "Name": name,
                    "Phone": phone,
                    "Start_Date": start_date,
                    "End_Date": end_date,
                    "Membership_Type": membership_type,
                    "Amount": amount,
                    "Recorded_At": recorded_at,
                    "Recorded_By": username
                }])
                members_df = pd.concat([members_df, new_data], ignore_index=True)
                save_data(members_df, log_df)
                st.success("✅ Member record saved and monthly backup created.")
                st.rerun()

        st.subheader("📋 All Members")
        if not members_df.empty:
            st.dataframe(members_df.sort_values("Recorded_At", ascending=False))
        else:
            st.info("No members found.")

        st.subheader("🔔 Expiry Reminders (Next 3 Days)")
        if "End_Date" in members_df.columns:
            members_df["End_Date"] = pd.to_datetime(members_df["End_Date"], errors="coerce")
            today = datetime.now(TIMEZONE).date()
            members_df["Days_Left"] = (members_df["End_Date"].dt.date - today).dt.days
            expiring = members_df[members_df["Days_Left"].between(0, 3)]
            if not expiring.empty:
                st.warning("⚠️ Memberships expiring soon:")
                st.table(expiring[["Name", "Phone", "End_Date", "Days_Left"]])
            else:
                st.success("✅ No memberships expiring soon.")

        st.subheader("📅 Login History")
        st.dataframe(log_df.sort_values("Login_Time", ascending=False))

    # MEMBER SECTION
    elif role == "member":
        st.subheader("📖 Your Membership Info")
        user_data = members_df[members_df["Recorded_By"] == username]
        if not user_data.empty:
            st.table(user_data[["Name", "Phone", "Start_Date", "End_Date", "Membership_Type", "Amount", "Recorded_At"]])
        else:
            st.info("No membership records yet.")
