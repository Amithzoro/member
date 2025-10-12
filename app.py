import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime
import pytz
import os
import calendar

st.set_page_config(page_title="Gym Membership System", layout="wide")

EXCEL_FILE = "membership.xlsx"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# ==========================
# LOAD / SAVE FUNCTIONS
# ==========================
def load_data(sheet_name="Members"):
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
        except ValueError:
            if sheet_name == "Login_Log":
                return pd.DataFrame(columns=["Username", "Role", "Login_Time"])
            else:
                return pd.DataFrame(columns=[
                    "Username", "Password", "Role", "Name", "Phone",
                    "Start_Date", "End_Date", "Membership_Type", "Amount", "Recorded_At", "Recorded_By"
                ])
        if "Start_Date" in df.columns:
            df["Start_Date"] = pd.to_datetime(df["Start_Date"], errors="coerce")
        if "End_Date" in df.columns:
            df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")
        return df
    else:
        if sheet_name == "Login_Log":
            return pd.DataFrame(columns=["Username", "Role", "Login_Time"])
        else:
            return pd.DataFrame(columns=[
                "Username", "Password", "Role", "Name", "Phone",
                "Start_Date", "End_Date", "Membership_Type", "Amount", "Recorded_At", "Recorded_By"
            ])

def save_data(members_df, log_df):
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

    # Auto-create a monthly backup file
    month_name = calendar.month_name[datetime.now(TIMEZONE).month]
    monthly_file = f"membership_{month_name[:3]}_{datetime.now(TIMEZONE).strftime('%d-%H-%M-%S')}.xlsx"
    with pd.ExcelWriter(monthly_file, engine="openpyxl") as writer:
        members_df.to_excel(writer, sheet_name="Members", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

members_df = load_data("Members")
log_df = load_data("Login_Log")

# ==========================
# AUTH FUNCTIONS
# ==========================
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

# ==========================
# LOGIN / SIGNUP
# ==========================
st.title("🏋️ Gym Membership Management")

menu = st.sidebar.radio("Menu", ["Login", "Sign Up"])

if menu == "Sign Up":
    st.subheader("Create Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["member", "owner"])
    create_btn = st.button("Create Account")

    if create_btn:
        if username in members_df["Username"].values:
            st.warning("⚠️ Username already exists!")
        else:
            hashed = hash_password(password).decode('utf-8')
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
                "Recorded_At": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
                "Recorded_By": username
            }])
            members_df = pd.concat([members_df, new_user], ignore_index=True)
            save_data(members_df, log_df)
            st.success("✅ Account created successfully!")

elif menu == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")

    if login_btn:
        if username in members_df["Username"].values:
            user_row = members_df[members_df["Username"] == username].iloc[0]
            if check_password(password, user_row["Password"]):
                st.session_state["logged_in"] = True
                st.session_state["role"] = user_row["Role"]
                st.session_state["username"] = username
                st.success(f"Welcome, {username}!")

                login_time = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                log_df = pd.concat([log_df, pd.DataFrame([{
                    "Username": username,
                    "Role": user_row["Role"],
                    "Login_Time": login_time
                }])], ignore_index=True)
                save_data(members_df, log_df)
            else:
                st.error("❌ Incorrect password")
        else:
            st.error("❌ User not found")

# ==========================
# AFTER LOGIN
# ==========================
if "logged_in" in st.session_state and st.session_state["logged_in"]:
    role = st.session_state["role"]
    username = st.session_state["username"]
    st.write(f"### Logged in as: **{role.upper()}**")

    members_df = load_data("Members")
    log_df = load_data("Login_Log")

    # ==========================
    # MEMBERSHIP FORM
    # ==========================
    with st.form("membership_form", clear_on_submit=True):
        st.subheader("🧾 Add / Update Membership")
        name = st.text_input("Member Name")
        phone = st.text_input("Phone Number")
        start_date = st.date_input("Start Date", datetime.now().date())
        end_date = st.date_input("End Date")
        membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Half-Yearly", "Yearly"])
        amount = st.number_input("Amount", min_value=0)
        submit = st.form_submit_button("Submit")

        if submit:
            recorded_at = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            hashed_password = members_df.loc[members_df["Username"] == username, "Password"].values[0]

            new_data = pd.DataFrame([{
                "Username": username,
                "Password": hashed_password,
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
            st.success("✅ Membership saved! Auto-saved monthly backup.")

    # ==========================
    # OWNER VIEW
    # ==========================
    if role == "owner":
        st.subheader("📋 All Members")
        if not members_df.empty:
            st.dataframe(members_df.sort_values("Recorded_At", ascending=False))
        else:
            st.info("No members found.")

        # ✅ FIXED EXPIRY REMINDER BLOCK
        st.subheader("🔔 Expiry Reminders")
        members_df["End_Date"] = pd.to_datetime(members_df["End_Date"], errors="coerce")
        today = datetime.now(TIMEZONE).normalize()
        members_df["Days_Left"] = members_df["End_Date"].apply(
            lambda x: (x - today).days if pd.notnull(x) else None
        )

        expiring = members_df[(members_df["Days_Left"] >= 0) & (members_df["Days_Left"] <= 3)]
        if not expiring.empty:
            st.warning("⚠️ Memberships expiring soon:")
            st.table(expiring[["Name", "Phone", "End_Date", "Days_Left", "Recorded_By"]])
        else:
            st.success("✅ No memberships expiring soon.")

        # Login history
        st.subheader("📅 Member Login History")
        if not log_df.empty:
            st.dataframe(log_df.sort_values("Login_Time", ascending=False))
        else:
            st.info("No login history found.")

    # ==========================
    # MEMBER VIEW
    # ==========================
    if role == "member":
        st.subheader("📖 Your Membership Info")
        user_data = members_df[members_df["Recorded_By"] == username].sort_values("Recorded_At", ascending=False)
        if not user_data.empty:
            st.dataframe(user_data[["Name", "Phone", "Start_Date", "End_Date", "Membership_Type", "Amount", "Recorded_At"]])
        else:
            st.info("No membership record found.")

        user_log = log_df[log_df["Username"] == username].sort_values("Login_Time", ascending=False)
        if not user_log.empty:
            st.subheader("📅 Your Login History")
            st.dataframe(user_log)
