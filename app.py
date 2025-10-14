import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, timedelta
import pytz
import os

# ---------- CONFIG ----------
st.set_page_config(page_title="Gym Management System", layout="wide")
TIMEZONE = pytz.timezone("Asia/Kolkata")
USERS_FILE = "staff_logins.xlsx"
MEMBER_FILE = "gym_members.xlsx"

# ---------- LOAD / SAVE ----------
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            return pd.read_excel(USERS_FILE)
        except:
            pass
    return pd.DataFrame(columns=["Username", "Password", "Role"])

def save_users(df):
    df.to_excel(USERS_FILE, index=False)

def load_members():
    if os.path.exists(MEMBER_FILE):
        return pd.read_excel(MEMBER_FILE)
    return pd.DataFrame(columns=["Name", "Membership_Type", "Start_Date", "End_Date", "Added_By", "Added_On"])

def save_members(df):
    df.to_excel(MEMBER_FILE, index=False)

# ---------- INITIAL SETUP ----------
users_df = load_users()
if "owner" not in users_df["Username"].values:
    hashed = bcrypt.hashpw("gym123".encode(), bcrypt.gensalt()).decode()
    users_df = pd.concat([users_df, pd.DataFrame([{
        "Username": "owner",
        "Password": hashed,
        "Role": "owner"
    }])], ignore_index=True)
    save_users(users_df)

# ---------- PASSWORD CHECK ----------
def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

# ---------- LOGIN ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.title("🏋️ Gym Management System")

if not st.session_state.logged_in:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users_df["Username"].values:
            user = users_df[users_df["Username"] == username].iloc[0]
            if check_password(password, user["Password"]):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = user["Role"]
                st.success(f"✅ Welcome, {username}!")
                st.rerun()
            else:
                st.error("❌ Incorrect password")
        else:
            st.error("❌ User not found")

# ---------- AFTER LOGIN ----------
else:
    username = st.session_state.username
    role = st.session_state.role

    st.sidebar.success(f"Logged in as: {username} ({role})")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # Owner dashboard
    if role == "owner":
        tab1, tab2 = st.tabs(["👥 Staff Management", "💪 Member Management"])

        # ---------- STAFF TAB ----------
        with tab1:
            st.subheader("👥 Manage Staff")
            st.dataframe(users_df[["Username", "Role"]], use_container_width=True)

            st.markdown("### ➕ Add New Staff")
            new_user = st.text_input("Staff Username")
            new_pass = st.text_input("Staff Password", type="password")
            if st.button("Add Staff"):
                if new_user and new_pass:
                    if new_user in users_df["Username"].values:
                        st.warning("⚠️ Username already exists.")
                    else:
                        hashed_pw = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
                        new_row = pd.DataFrame([{"Username": new_user, "Password": hashed_pw, "Role": "staff"}])
                        users_df = pd.concat([users_df, new_row], ignore_index=True)
                        save_users(users_df)
                        st.success(f"✅ Staff '{new_user}' added successfully!")
                        st.rerun()
                else:
                    st.warning("Please enter both username and password.")

        # ---------- MEMBER TAB ----------
        with tab2:
            members_df = load_members()
            st.subheader("💪 Manage Members (Owner)")

            name = st.text_input("Member Name")
            membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Half-Yearly", "Yearly"])
            start_date = st.date_input("Start Date", datetime.now().date())
            end_date = st.date_input("End Date", datetime.now().date() + timedelta(days=30))

            if st.button("Add Member"):
                if name.strip():
                    added_on = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                    new_member = pd.DataFrame([{
                        "Name": name,
                        "Membership_Type": membership_type,
                        "Start_Date": start_date,
                        "End_Date": end_date,
                        "Added_By": username,
                        "Added_On": added_on
                    }])
                    members_df = pd.concat([members_df, new_member], ignore_index=True)
                    save_members(members_df)
                    st.success(f"✅ Member '{name}' added successfully!")
                    st.rerun()
                else:
                    st.warning("Please enter a member name.")

            st.markdown("### 🧾 Current Members")
            st.dataframe(members_df, use_container_width=True)

            # Expiring soon alert
            if not members_df.empty:
                members_df["End_Date"] = pd.to_datetime(members_df["End_Date"])
                today = datetime.now().date()
                expiring = members_df[
                    (members_df["End_Date"].dt.date <= today + timedelta(days=7)) &
                    (members_df["End_Date"].dt.date >= today)
                ]
                if not expiring.empty:
                    expiring_names = ", ".join(expiring["Name"].tolist())
                    st.toast(f"⚠️ Memberships expiring soon: {expiring_names}", icon="⏰")

    # Staff dashboard
    else:
        st.header("💪 Add Members")
        members_df = load_members()

        name = st.text_input("Member Name")
        membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Half-Yearly", "Yearly"])
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=30)

        if st.button("Add Member"):
            if name.strip():
                added_on = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                new_member = pd.DataFrame([{
                    "Name": name,
                    "Membership_Type": membership_type,
                    "Start_Date": start_date,
                    "End_Date": end_date,
                    "Added_By": username,
                    "Added_On": added_on
                }])
                members_df = pd.concat([members_df, new_member], ignore_index=True)
                save_members(members_df)
                st.success(f"✅ Member '{name}' added successfully!")
                st.rerun()
            else:
                st.warning("Please enter a member name.")

        st.markdown("### 🧾 Your Added Members")
        st.dataframe(members_df[members_df["Added_By"] == username], use_container_width=True)

        # Alert for expiring memberships
        if not members_df.empty:
            members_df["End_Date"] = pd.to_datetime(members_df["End_Date"])
            today = datetime.now().date()
            expiring = members_df[
                (members_df["End_Date"].dt.date <= today + timedelta(days=7)) &
                (members_df["End_Date"].dt.date >= today)
            ]
            if not expiring.empty:
                expiring_names = ", ".join(expiring["Name"].tolist())
                st.toast(f"⚠️ Memberships expiring soon: {expiring_names}", icon="⏰")
