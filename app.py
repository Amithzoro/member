import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os

# ---------- CONFIG ----------
TIMEZONE = pytz.timezone("Asia/Kolkata")
DATA_FILE = "members.xlsx"
ACTIVITY_LOG_FILE = "activity_log.csv"
LOGIN_LOG_FILE = "login_log.csv"

# ---------- OWNER CREDENTIALS ----------
OWNER_USERNAME = "amith"
OWNER_PASSWORD = "panda@2006"

# ---------- PAGE SETTINGS ----------
st.set_page_config(page_title="💪 Gym Membership Tracker", layout="wide")

# ---------- HELPER FUNCTIONS ----------
def now_str():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

def load_excel(path, columns):
    if os.path.exists(path):
        try:
            return pd.read_excel(path)
        except:
            return pd.DataFrame(columns=columns)
    else:
        return pd.DataFrame(columns=columns)

def load_csv(path, columns):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except:
            return pd.DataFrame(columns=columns)
    else:
        return pd.DataFrame(columns=columns)

def save_excel(df, path):
    df.to_excel(path, index=False)

def append_csv(path, row):
    df = load_csv(path, row.keys())
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False)

# ---------- SESSION STATE ----------
if "members_df" not in st.session_state:
    st.session_state.members_df = load_excel(DATA_FILE, ["Name","Phone","Start_Date","End_Date","Recorded_By","Added_At"])
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
if "activity_df" not in st.session_state:
    st.session_state.activity_df = load_csv(ACTIVITY_LOG_FILE, ["Timestamp","Action","Details"])
if "login_df" not in st.session_state:
    st.session_state.login_df = load_csv(LOGIN_LOG_FILE, ["Timestamp","Username","Status"])

# ---------- LOGIN ----------
st.sidebar.header("🔐 Login")
username_input = st.sidebar.text_input("Username")
password_input = st.sidebar.text_input("Password", type="password")
login_btn = st.sidebar.button("Login")

if login_btn:
    ts = now_str()
    if username_input == OWNER_USERNAME and password_input == OWNER_PASSWORD:
        st.session_state.logged_in = True
        st.session_state.username = username_input
        st.sidebar.success(f"✅ Welcome, {username_input}!")
        append_csv(LOGIN_LOG_FILE, {"Timestamp":ts,"Username":username_input,"Status":"Success"})
        st.session_state.login_df = load_csv(LOGIN_LOG_FILE, ["Timestamp","Username","Status"])
    else:
        st.sidebar.error("❌ Invalid username or password")
        append_csv(LOGIN_LOG_FILE, {"Timestamp":ts,"Username":username_input or "<empty>","Status":"Failed"})
        st.session_state.login_df = load_csv(LOGIN_LOG_FILE, ["Timestamp","Username","Status"])

# ---------- MAIN APP ----------
if st.session_state.logged_in:
    st.title("🏋️‍♂️ Gym Membership Tracker")
    st.success(f"Logged in as **{st.session_state.username}**")

    # ---------- ADD MEMBER ----------
    st.subheader("➕ Add Member")
    with st.form("add_member_form"):
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        recorded_by = st.text_input("Recorded By", st.session_state.username)
        submitted = st.form_submit_button("Add Member")
        if submitted:
            if not name.strip():
                st.warning("⚠️ Enter member name")
            else:
                added_at = now_str()
                new_row = {
                    "Name": name.strip(),
                    "Phone": phone.strip(),
                    "Start_Date": start_date,
                    "End_Date": end_date,
                    "Recorded_By": recorded_by,
                    "Added_At": added_at
                }
                st.session_state.members_df = pd.concat([st.session_state.members_df, pd.DataFrame([new_row])], ignore_index=True)
                save_excel(st.session_state.members_df, DATA_FILE)
                # log activity
                append_csv(ACTIVITY_LOG_FILE, {"Timestamp":added_at,"Action":"Add Member","Details":f"{name} (By: {recorded_by})"})
                st.session_state.activity_df = load_csv(ACTIVITY_LOG_FILE, ["Timestamp","Action","Details"])
                st.success(f"✅ Added member: {name}")
                st.experimental_rerun()

    # ---------- VIEW MEMBERS ----------
    st.subheader("📋 Member List")
    filter_name = st.text_input("Search by Name")
    members_show = st.session_state.members_df.copy()
    if filter_name:
        members_show = members_show[members_show["Name"].astype(str).str.contains(filter_name, case=False, na=False)]
    st.dataframe(members_show.reset_index(drop=True))

    # ---------- EXPIRY ALERTS ----------
    today = datetime.now(TIMEZONE).date()
    df = members_show.copy()
    df["End_Date_parsed"] = pd.to_datetime(df["End_Date"], errors="coerce")
    df["Days_Left"] = df["End_Date_parsed"].apply(lambda x: (x.date()-today).days if pd.notnull(x) else None)
    expiring = df[(df["Days_Left"].notnull()) & (df["Days_Left"]>=0) & (df["Days_Left"]<=3)]
    if not expiring.empty:
        names = ", ".join(expiring["Name"].fillna("Unknown").tolist())
        st.markdown(f'<div style="position:fixed;top:20px;right:30px;background-color:#ffcc00;padding:12px 18px;border-radius:10px;font-weight:600;">⚠️ Memberships expiring soon: {names}</div>', unsafe_allow_html=True)
        st.table(expiring[["Name","Phone","End_Date","Days_Left","Recorded_By"]])
    else:
        st.success("✅ No memberships expiring soon.")

    # ---------- ACTIVITY LOG ----------
    st.subheader("📝 Member Activity Log")
    if not st.session_state.activity_df.empty:
        st.dataframe(st.session_state.activity_df.iloc[::-1].reset_index(drop=True))
    else:
        st.write("No member activity yet.")

    # ---------- LOGIN ISSUE LOG ----------
    st.subheader("⚠️ Login Issue Log")
    if not st.session_state.login_df.empty:
        st.dataframe(st.session_state.login_df.iloc[::-1].reset_index(drop=True))
    else:
        st.write("No login attempts yet.")

    # ---------- LOGOUT ----------
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.experimental_rerun()

else:
    st.info("👈 Please login using the sidebar to continue.")
