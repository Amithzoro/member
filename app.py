# gym_tracker_final_fixed.py
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

OWNER_USERNAME = "amith"
OWNER_PASSWORD = "panda@2006"

st.set_page_config(page_title="💪 Gym Membership Tracker", layout="wide")

# ---------- HELPERS ----------
def now_str():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

def load_excel(path, cols):
    if os.path.exists(path):
        try:
            return pd.read_excel(path)
        except:
            return pd.DataFrame(columns=cols)
    else:
        return pd.DataFrame(columns=cols)

def save_excel(df, path):
    df.to_excel(path, index=False)

def load_csv(path, cols):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except:
            return pd.DataFrame(columns=cols)
    else:
        return pd.DataFrame(columns=cols)

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
                append_csv(ACTIVITY_LOG_FILE, {"Timestamp":added_at,"Action":"Add Member","Details":f"{name} (By: {recorded_by})"})
                st.session_state.activity_df = load_csv(ACTIVITY_LOG_FILE, ["Timestamp","Action","Details"])
                st.success(f"✅ Added member: {name}")

    # ---------- BULK CSV UPLOAD ----------
    st.subheader("📥 Upload Members CSV")
    st.markdown("CSV must have columns: Name, Phone, Start_Date, End_Date")
    uploaded_file = st.file_uploader("Choose CSV file", type=["csv"])
    if uploaded_file:
        try:
            df_new = pd.read_csv(uploaded_file)
            # Standardize column names
            df_new.columns = [c.strip() for c in df_new.columns]
            required_cols = ["Name","Phone","Start_Date","End_Date"]
            if not all(col in df_new.columns for col in required_cols):
                st.error(f"CSV must contain columns: {required_cols}")
            else:
                # Convert dates
                df_new['Start_Date'] = pd.to_datetime(df_new['Start_Date'], errors='coerce').dt.date
                df_new['End_Date'] = pd.to_datetime(df_new['End_Date'], errors='coerce').dt.date
                df_new["Recorded_By"] = st.session_state.username
                df_new["Added_At"] = now_str()
                # Reindex to match main df
                df_new = df_new.reindex(columns=st.session_state.members_df.columns, fill_value="")
                st.session_state.members_df = pd.concat([st.session_state.members_df, df_new], ignore_index=True)
                save_excel(st.session_state.members_df, DATA_FILE)
                for _, row in df_new.iterrows():
                    append_csv(ACTIVITY_LOG_FILE, {"Timestamp":row["Added_At"], "Action":"Add Member", "Details":f"{row['Name']} (By: {st.session_state.username})"})
                st.success(f"✅ Added {len(df_new)} members successfully!")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

    # ---------- VIEW & FILTER ----------
    st.subheader("📋 Member List")
    filter_name = st.text_input("Search by Name")
    members_show = st.session_state.members_df.copy()
    if filter_name:
        members_show = members_show[members_show["Name"].astype(str).str.contains(filter_name, case=False, na=False)]
    st.dataframe(members_show.reset_index(drop=True), height=400)
    st.download_button("📥 Download Members", data=members_show.to_csv(index=False).encode(), file_name="members.csv")

    # ---------- EXPIRY ALERT (Floating 12 sec) ----------
    today = datetime.now(TIMEZONE).date()
    df = members_show.copy()
    df["End_Date_parsed"] = pd.to_datetime(df["End_Date"], errors="coerce")
    df["Days_Left"] = df["End_Date_parsed"].apply(lambda x: (x.date()-today).days if pd.notnull(x) else None)
    expiring = df[(df["Days_Left"].notnull()) & (df["Days_Left"]>=0) & (df["Days_Left"]<=3)]
    if not expiring.empty:
        names = ", ".join(expiring["Name"].fillna("Unknown").tolist())
        alert_html = f"""
        <div style="
            position: fixed;
            top: 20px;
            right: 30px;
            background-color: #ffcc00;
            color: black;
            padding: 15px 25px;
            border-radius: 10px;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
            font-weight: 600;
            z-index: 9999;
        ">
        ⚠️ Memberships expiring soon: {names}
        </div>
        """
        st.markdown(alert_html, unsafe_allow_html=True)

    # ---------- ACTIVITY LOG ----------
    st.subheader("📝 Member Activity Log")
    if not st.session_state.activity_df.empty:
        st.dataframe(st.session_state.activity_df.iloc[::-1].reset_index(drop=True), height=300)
    else:
        st.write("No activity yet.")

    # ---------- LOGIN ISSUE LOG ----------
    st.subheader("⚠️ Login Issue Log")
    if not st.session_state.login_df.empty:
        st.dataframe(st.session_state.login_df.iloc[::-1].reset_index(drop=True), height=300)
    else:
        st.write("No login attempts yet.")

    # ---------- LOGOUT ----------
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.experimental_rerun()

else:
    st.info("👈 Please login using the sidebar to continue.")
