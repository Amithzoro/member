# app.py
import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, date, timedelta
import pytz
import os
import calendar

# -------- CONFIG ----------
st.set_page_config(page_title="Gym Membership System", layout="wide")
EXCEL_FILE = "membership.xlsx"
TIMEZONE = pytz.timezone("Asia/Kolkata")
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# -------- HELPERS: LOAD / SAVE ----------
def ensure_file_sheets():
    # Ensure the file exists with required sheets (Users, Memberships, Login_Log)
    if not os.path.exists(EXCEL_FILE):
        users = pd.DataFrame(columns=["Username", "Password", "Role", "Created_At"])
        memberships = pd.DataFrame(columns=[
            "Member_ID", "Member_Name", "Phone", "Start_Date", "End_Date",
            "Membership_Type", "Amount", "Recorded_At", "Recorded_By"
        ])
        log = pd.DataFrame(columns=["Username", "Role", "Login_Time"])
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as w:
            users.to_excel(w, sheet_name="Users", index=False)
            memberships.to_excel(w, sheet_name="Memberships", index=False)
            log.to_excel(w, sheet_name="Login_Log", index=False)

def load_sheet(sheet_name):
    ensure_file_sheets()
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
    except Exception:
        # return appropriate empty frames
        if sheet_name == "Users":
            return pd.DataFrame(columns=["Username", "Password", "Role", "Created_At"])
        if sheet_name == "Memberships":
            return pd.DataFrame(columns=[
                "Member_ID", "Member_Name", "Phone", "Start_Date", "End_Date",
                "Membership_Type", "Amount", "Recorded_At", "Recorded_By"
            ])
        return pd.DataFrame(columns=["Username", "Role", "Login_Time"])
    # Ensure date columns parsed
    if "Start_Date" in df.columns:
        df["Start_Date"] = pd.to_datetime(df["Start_Date"], errors="coerce")
    if "End_Date" in df.columns:
        df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")
    return df

def save_all(users_df, memberships_df, log_df):
    # write main file
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        memberships_df.to_excel(writer, sheet_name="Memberships", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

    # monthly backup with timestamp (prevents overwrite)
    month_name = calendar.month_name[datetime.now(TIMEZONE).month]
    timestamp = datetime.now(TIMEZONE).strftime("%Y%m%d_%H%M%S")
    backup_file = f"membership_{month_name[:3]}_{timestamp}.xlsx"
    with pd.ExcelWriter(backup_file, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        memberships_df.to_excel(writer, sheet_name="Memberships", index=False)
        log_df.to_excel(writer, sheet_name="Login_Log", index=False)

# -------- HELPERS: AUTH ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

# -------- UTILS ----------
def now_str():
    return datetime.now(TIMEZONE).strftime(DATE_FORMAT)

def next_member_id(members_df):
    if members_df.empty:
        return 1
    else:
        if "Member_ID" not in members_df.columns:
            return 1
        max_id = pd.to_numeric(members_df["Member_ID"], errors="coerce").max()
        return int(max_id) + 1 if not pd.isna(max_id) else 1

def calc_end_date(start: date, membership_type: str):
    # Returns a date object for end date based on membership type
    if membership_type == "Monthly":
        return (pd.Timestamp(start) + pd.DateOffset(months=1)).date()
    if membership_type == "Quarterly":
        return (pd.Timestamp(start) + pd.DateOffset(months=3)).date()
    if membership_type == "Half-Yearly":
        return (pd.Timestamp(start) + pd.DateOffset(months=6)).date()
    if membership_type == "Yearly":
        return (pd.Timestamp(start) + pd.DateOffset(years=1)).date()
    return start

# -------- LOAD DATA ----------
users_df = load_sheet("Users")
memberships_df = load_sheet("Memberships")
log_df = load_sheet("Login_Log")

# -------- UI: Header ----------
st.title("🏋️ Gym Membership System — Fresh Start")
st.markdown("Secure login, owner & member roles, membership records, expiry reminders, and monthly backups.")

# -------- SIDEBAR: Login / Signup ----------
page = st.sidebar.selectbox("Choose", ["Login", "Sign Up", "About"])

if page == "About":
    st.sidebar.write("This app stores Users, Memberships and Login logs in `membership.xlsx` and creates monthly backups.")
    st.sidebar.write("Timezone: Asia/Kolkata")

if page == "Sign Up":
    st.subheader("Create Account")
    new_username = st.text_input("Username", key="su_user")
    new_password = st.text_input("Password", type="password", key="su_pass")
    role = st.selectbox("Role", ["member", "owner"], key="su_role")
    if st.button("Create Account"):
        if new_username.strip() == "" or new_password.strip() == "":
            st.warning("Username and password cannot be empty.")
        elif new_username in users_df["Username"].values:
            st.warning("Username already exists.")
        else:
            hashed = hash_password(new_password)
            new_row = {
                "Username": new_username,
                "Password": hashed,
                "Role": role,
                "Created_At": now_str()
            }
            users_df = pd.concat([users_df, pd.DataFrame([new_row])], ignore_index=True)
            save_all(users_df, memberships_df, log_df)
            st.success("Account created ✅ — you can now login.")
            st.experimental_rerun()

if page == "Login":
    st.subheader("Login")
    login_username = st.text_input("Username", key="li_user")
    login_password = st.text_input("Password", type="password", key="li_pass")
    if st.button("Login"):
        if login_username in users_df["Username"].values:
            user_row = users_df[users_df["Username"] == login_username].iloc[0]
            if check_password(login_password, user_row["Password"]):
                st.session_state["logged_in"] = True
                st.session_state["username"] = login_username
                st.session_state["role"] = user_row["Role"]
                # record login
                log_df = pd.concat([log_df, pd.DataFrame([{
                    "Username": login_username,
                    "Role": user_row["Role"],
                    "Login_Time": now_str()
                }])], ignore_index=True)
                save_all(users_df, memberships_df, log_df)
                st.success(f"Welcome {login_username} ({user_row['Role']})")
                st.experimental_rerun()
            else:
                st.error("Incorrect password.")
        else:
            st.error("User not found. Create account first.")

# -------- AFTER LOGIN ----------
if "logged_in" in st.session_state and st.session_state["logged_in"]:
    username = st.session_state["username"]
    role = st.session_state["role"]
    st.write(f"### Logged in as: **{username}** ({role})")
    st.write("---")

    # Refresh dataframes (re-read file in case of external changes)
    users_df = load_sheet("Users")
    memberships_df = load_sheet("Memberships")
    log_df = load_sheet("Login_Log")

    # === Membership form (owner can add members; members can add/update their own) ===
    st.subheader("Add Membership Record")
    with st.form("membership_form", clear_on_submit=True):
        # Owner can enter any Member name. Member sees their name prefilled (optional).
        member_name = st.text_input("Member Name", value=username if role == "member" else "")
        phone = st.text_input("Phone Number")
        start_date = st.date_input("Start Date", value=date.today())
        membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Half-Yearly", "Yearly"])
        # Optionally allow manual end-date; if user leaves blank, app will calculate
        manual_end = st.checkbox("Manually set End Date (otherwise auto-calc)", value=False)
        if manual_end:
            end_date_input = st.date_input("End Date", value=date.today())
        else:
            end_date_input = None
        amount = st.number_input("Amount (₹)", min_value=0.0, step=1.0)
        submit = st.form_submit_button("Save Membership")

        if submit:
            # Basic validation
            if member_name.strip() == "":
                st.warning("Member Name required.")
            elif phone.strip() == "":
                st.warning("Phone required.")
            else:
                # calculate end date if not manual
                if manual_end and end_date_input:
                    end_date = end_date_input
                else:
                    end_date = calc_end_date(start_date, membership_type)

                # create membership record
                mid = next_member_id(memberships_df)
                new_record = {
                    "Member_ID": mid,
                    "Member_Name": member_name.strip(),
                    "Phone": phone.strip(),
                    "Start_Date": pd.Timestamp(start_date),
                    "End_Date": pd.Timestamp(end_date),
                    "Membership_Type": membership_type,
                    "Amount": float(amount),
                    "Recorded_At": now_str(),
                    "Recorded_By": username
                }
                memberships_df = pd.concat([memberships_df, pd.DataFrame([new_record])], ignore_index=True)
                save_all(users_df, memberships_df, log_df)
                st.success("Membership record saved ✅")

    st.write("---")

    # === Owner dashboard ===
    if role == "owner":
        st.subheader("All Membership Records")
        if memberships_df.empty:
            st.info("No membership records yet.")
        else:
            # Show newest first
            display_df = memberships_df.copy()
            display_df = display_df.sort_values("Recorded_At", ascending=False)
            # Convert datetime columns for display
            if "Start_Date" in display_df.columns:
                display_df["Start_Date"] = display_df["Start_Date"].dt.date
            if "End_Date" in display_df.columns:
                display_df["End_Date"] = display_df["End_Date"].dt.date
            st.dataframe(display_df)

        st.subheader("Expiry Reminders (next 3 days)")
        today = datetime.now(TIMEZONE).date()
        if "End_Date" in memberships_df.columns and not memberships_df.empty:
            dd = memberships_df.copy()
            dd["Days_Left"] = dd["End_Date"].apply(lambda x: (x.date() - today).days if pd.notnull(x) else None)
            expiring = dd[(dd["Days_Left"] >= 0) & (dd["Days_Left"] <= 3)]
            if not expiring.empty:
                # show relevant columns
                show = expiring[["Member_ID", "Member_Name", "Phone", "End_Date", "Days_Left", "Recorded_By"]]
                show["End_Date"] = pd.to_datetime(show["End_Date"]).dt.date
                st.warning("⚠️ These memberships are expiring soon:")
                st.table(show)
            else:
                st.success("No memberships expiring in next 3 days.")
        else:
            st.info("No end date data.")

        st.subheader("Login History")
        if log_df.empty:
            st.info("No login history.")
        else:
            st.dataframe(log_df.sort_values("Login_Time", ascending=False))

    # === Member view ===
    if role == "member":
        st.subheader("Your Membership Records")
        my_records = memberships_df[memberships_df["Member_Name"] == username]
        if my_records.empty:
            st.info("No records found for your account name. (Owners may have recorded members under different names.)")
        else:
            view = my_records.sort_values("Recorded_At", ascending=False).copy()
            if "Start_Date" in view.columns:
                view["Start_Date"] = view["Start_Date"].dt.date
            if "End_Date" in view.columns:
                view["End_Date"] = view["End_Date"].dt.date
            st.dataframe(view[[
                "Member_ID", "Member_Name", "Phone", "Start_Date", "End_Date",
                "Membership_Type", "Amount", "Recorded_At", "Recorded_By"
            ]])

        st.subheader("Your Login History")
        my_log = log_df[log_df["Username"] == username].sort_values("Login_Time", ascending=False)
        if my_log.empty:
            st.info("No login records found.")
        else:
            st.dataframe(my_log)

    # Logout button
    if st.button("Logout"):
        for k in ["logged_in", "username", "role"]:
            if k in st.session_state:
                del st.session_state[k]
        st.experimental_rerun()
