# app.py
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

# ---------- OWNER CREDENTIALS (plain for reliability) ----------
OWNER_USERNAME = "amith"
OWNER_PASSWORD = "panda@2006"

# ---------- PAGE SETTINGS ----------
st.set_page_config(page_title="💪 Gym Membership Tracker", layout="wide")

# ---------- CUSTOM ALERT STYLE ----------
st.markdown(
    """
    <style>
    .floating-alert {
        position: fixed;
        top: 20px;
        right: 30px;
        background-color: #ffcc00;
        color: black;
        padding: 12px 18px;
        border-radius: 10px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.25);
        font-weight: 600;
        z-index: 9999;
    }
    [data-testid="stSidebar"] { background-color: #1e1e1e; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- FILE HELPERS ----------
def load_members():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["Name", "Phone", "Start_Date", "End_Date", "Recorded_By", "Added_At"])
        df.to_excel(DATA_FILE, index=False)
    else:
        df = pd.read_excel(DATA_FILE)
        # ensure columns exist
        for col in ["Name", "Phone", "Start_Date", "End_Date", "Recorded_By", "Added_At"]:
            if col not in df.columns:
                df[col] = None
    return df

def save_members(df):
    df.to_excel(DATA_FILE, index=False)

def load_log(csv_path, cols):
    if os.path.exists(csv_path):
        try:
            return pd.read_csv(csv_path)
        except Exception:
            # fallback to empty DF with proper cols
            return pd.DataFrame(columns=cols)
    else:
        return pd.DataFrame(columns=cols)

def append_log(csv_path, row_dict):
    cols = list(row_dict.keys())
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
        except Exception:
            df = pd.DataFrame([row_dict])
    else:
        df = pd.DataFrame([row_dict])
    df.to_csv(csv_path, index=False)

# ---------- SESSION STATE INITIALIZATION ----------
if "members_df" not in st.session_state:
    st.session_state.members_df = load_members()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

if "activity_log_df" not in st.session_state:
    st.session_state.activity_log_df = load_log(ACTIVITY_LOG_FILE, ["Timestamp", "Action", "Details"])

if "login_log_df" not in st.session_state:
    st.session_state.login_log_df = load_log(LOGIN_LOG_FILE, ["Timestamp", "Username", "Status"])

# ---------- LOGIN UI ----------
st.sidebar.header("🔐 Login")
username_input = st.sidebar.text_input("Username")
password_input = st.sidebar.text_input("Password", type="password")
login_btn = st.sidebar.button("Login")

def now_str():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

if login_btn:
    ts = now_str()
    if username_input == OWNER_USERNAME and password_input == OWNER_PASSWORD:
        st.session_state.logged_in = True
        st.session_state.username = username_input
        st.sidebar.success(f"✅ Welcome, {username_input}!")
        # log success
        row = {"Timestamp": ts, "Username": username_input, "Status": "Success"}
        append_log(LOGIN_LOG_FILE, row)
        # update session copy
        st.session_state.login_log_df = load_log(LOGIN_LOG_FILE, ["Timestamp", "Username", "Status"])
    else:
        st.sidebar.error("❌ Invalid username or password")
        row = {"Timestamp": ts, "Username": username_input or "<empty>", "Status": "Failed"}
        append_log(LOGIN_LOG_FILE, row)
        st.session_state.login_log_df = load_log(LOGIN_LOG_FILE, ["Timestamp", "Username", "Status"])

# ---------- MAIN APP ----------
if st.session_state.logged_in:
    st.title("🏋️‍♂️ Gym Membership Tracker")
    st.caption("Track members, expiry dates, and reminders easily.")
    st.success(f"Logged in as **{st.session_state.username}**")

    # ---------- ADD NEW MEMBER ----------
    st.subheader("➕ Add New Member")
    with st.form("add_member_form"):
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        start_date = st.date_input("Start Date", value=datetime.now(TIMEZONE).date())
        end_date = st.date_input("End Date")
        recorded_by = st.text_input("Recorded By", st.session_state.username)
        submitted = st.form_submit_button("Add Member")

        if submitted:
            if not name or name.strip() == "":
                st.warning("⚠️ Please enter a name.")
            else:
                added_at = now_str()
                new_row = {
                    "Name": name.strip(),
                    "Phone": phone.strip(),
                    "Start_Date": pd.to_datetime(start_date).date() if start_date else None,
                    "End_Date": pd.to_datetime(end_date).date() if end_date else None,
                    "Recorded_By": recorded_by or st.session_state.username,
                    "Added_At": added_at,
                }
                # append to members DF and save
                st.session_state.members_df = pd.concat([st.session_state.members_df, pd.DataFrame([new_row])], ignore_index=True)
                save_members(st.session_state.members_df)
                # append activity log (persistent)
                action_row = {"Timestamp": added_at, "Action": "Add Member", "Details": f"{name} (By: {new_row['Recorded_By']})"}
                append_log(ACTIVITY_LOG_FILE, action_row)
                st.session_state.activity_log_df = load_log(ACTIVITY_LOG_FILE, ["Timestamp", "Action", "Details"])
                st.success(f"✅ Added member: {name}")
                # optional: scroll to top or refresh UI
                st.experimental_rerun()

    # ---------- VIEW & FILTER ----------
    st.subheader("📋 Member List")
    filter_name = st.text_input("Search by Name")
    members_to_show = st.session_state.members_df.copy()
    # normalize Start_Date and End_Date columns for display
    if "Start_Date" in members_to_show.columns:
        members_to_show["Start_Date"] = pd.to_datetime(members_to_show["Start_Date"], errors="coerce").dt.date
    if "End_Date" in members_to_show.columns:
        members_to_show["End_Date"] = pd.to_datetime(members_to_show["End_Date"], errors="coerce").dt.date

    if filter_name:
        mask = members_to_show["Name"].astype(str).str.contains(filter_name, case=False, na=False)
        st.dataframe(members_to_show[mask].reset_index(drop=True))
    else:
        st.dataframe(members_to_show.reset_index(drop=True))

    # ---------- EXPIRY REMINDERS ----------
    df_copy = members_to_show.copy()
    df_copy["End_Date_parsed"] = pd.to_datetime(df_copy["End_Date"], errors="coerce")
    today = datetime.now(TIMEZONE).date()
    def compute_days_left(val):
        if pd.isna(val):
            return None
        try:
            return (val.date() - today).days
        except Exception:
            return None
    df_copy["Days_Left"] = df_copy["End_Date_parsed"].apply(compute_days_left)
    expiring = df_copy[(df_copy["Days_Left"].notnull()) & (df_copy["Days_Left"] >= 0) & (df_copy["Days_Left"] <= 3)]

    if not expiring.empty:
        names = ", ".join(expiring["Name"].fillna("Unknown").tolist())
        st.markdown(f"""
            <div class="floating-alert">
                ⚠️ Memberships expiring soon!<br>{names}
            </div>
            """, unsafe_allow_html=True)
        st.table(expiring[["Name", "Phone", "End_Date", "Days_Left", "Recorded_By"]].rename(columns={"End_Date":"End_Date (Y-M-D)"}))
    else:
        st.success("✅ No memberships expiring soon.")

    # ---------- MEMBER ACTIVITY LOG ----------
    st.subheader("📝 Member Activity Log")
    if not st.session_state.activity_log_df.empty:
        # show newest first
        df_act = st.session_state.activity_log_df.copy().iloc[::-1].reset_index(drop=True)
        st.dataframe(df_act)
    else:
        st.write("No member activity yet.")

    # ---------- LOGIN ISSUE LOG ----------
    st.subheader("⚠️ Login Issue Log")
    if not st.session_state.login_log_df.empty:
        df_login = st.session_state.login_log_df.copy().iloc[::-1].reset_index(drop=True)
        st.dataframe(df_login)
    else:
        st.write("No login attempts yet.")

    # ---------- LOGOUT ----------
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.experimental_rerun()

else:
    st.info("👈 Please login using the sidebar to continue.")
    # also show recent login attempts below login box for convenience
    if not st.session_state.login_log_df.empty:
        st.sidebar.markdown("**Recent login attempts (newest first)**")
        recent = st.session_state.login_log_df.copy().iloc[::-1].head(5)
        for _, row in recent.iterrows():
            st.sidebar.write(f"{row['Timestamp']} — {row['Username']} — {row['Status']}")
