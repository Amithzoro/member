import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os

# ---------- CONFIG ----------
TIMEZONE = pytz.timezone("Asia/Kolkata")
DATA_FILE = "members.xlsx"
ACTIVITY_FILE = "activity_log.csv"
USERNAME = "amith"
PASSWORD = "panda@2006"

st.set_page_config(page_title="Gym Membership Tracker", layout="wide")

# ---------- HELPERS ----------
def now_str():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_excel(DATA_FILE)
    else:
        df = pd.DataFrame(columns=["Name","Phone","Start_Date","End_Date","Recorded_By","Added_At"])
        df.to_excel(DATA_FILE,index=False)
        return df

def save_data(df):
    df.to_excel(DATA_FILE,index=False)

def log_activity(action, detail):
    row = {"Timestamp": now_str(), "Action": action, "Details": detail}
    if os.path.exists(ACTIVITY_FILE):
        df = pd.read_csv(ACTIVITY_FILE)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])
    df.to_csv(ACTIVITY_FILE, index=False)

# ---------- SESSION STATE ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "members_df" not in st.session_state:
    st.session_state.members_df = load_data()
if "activity_df" not in st.session_state:
    if os.path.exists(ACTIVITY_FILE):
        st.session_state.activity_df = pd.read_csv(ACTIVITY_FILE)
    else:
        st.session_state.activity_df = pd.DataFrame(columns=["Timestamp","Action","Details"])

# ---------- LOGIN ----------
st.sidebar.header("Login")
username_input = st.sidebar.text_input("Username")
password_input = st.sidebar.text_input("Password", type="password")
if st.sidebar.button("Login"):
    if username_input==USERNAME and password_input==PASSWORD:
        st.session_state.logged_in = True
        st.sidebar.success("Logged in!")
    else:
        st.sidebar.error("Invalid username or password")

# ---------- MAIN APP ----------
if st.session_state.logged_in:
    st.title("Gym Membership Tracker")
    
    # --- Add/Edit Member ---
    st.subheader("Add or Edit Member")
    df = st.session_state.members_df.copy()
    member_names = [""] + df["Name"].tolist()
    selected_member = st.selectbox("Select member to edit (or leave blank to add new)", member_names)

    name = st.text_input("Name", value=selected_member if selected_member else "")
    phone = st.text_input("Phone", value=df[df["Name"]==selected_member]["Phone"].values[0] if selected_member else "")
    start_date = st.date_input("Start Date", value=df[df["Name"]==selected_member]["Start_Date"].values[0] if selected_member else datetime.now().date())
    end_date = st.date_input("End Date", value=df[df["Name"]==selected_member]["End_Date"].values[0] if selected_member else datetime.now().date())

    if st.button("Save Member"):
        if selected_member:
            st.session_state.members_df.loc[st.session_state.members_df["Name"]==selected_member, ["Name","Phone","Start_Date","End_Date"]] = [name, phone, start_date, end_date]
            action = f"Edited member: {selected_member} → {name}"
        else:
            new_row = {"Name":name,"Phone":phone,"Start_Date":start_date,"End_Date":end_date,"Recorded_By":USERNAME,"Added_At":now_str()}
            st.session_state.members_df = pd.concat([st.session_state.members_df, pd.DataFrame([new_row])], ignore_index=True)
            action = f"Added member: {name}"
        save_data(st.session_state.members_df)
        log_activity(action,name)
        st.success(f"✅ {action}")
        st.experimental_rerun()

    # --- View & Filter ---
    st.subheader("Member List")
    search_name = st.text_input("Search by Name")
    df_show = st.session_state.members_df.copy()
    if search_name:
        df_show = df_show[df_show["Name"].str.contains(search_name, case=False, na=False)]
    st.dataframe(df_show, height=400)
    st.download_button("Download CSV", df_show.to_csv(index=False).encode(), "members.csv")

    # --- Expiry Alert ---
    today = datetime.now(TIMEZONE).date()
    df_show["End_Date_parsed"] = pd.to_datetime(df_show["End_Date"], errors="coerce")
    df_show["Days_Left"] = df_show["End_Date_parsed"].apply(lambda x: (x.date()-today).days if pd.notnull(x) else None)
    expiring = df_show[(df_show["Days_Left"]>=0) & (df_show["Days_Left"]<=3)]
    if not expiring.empty:
        names = ", ".join(expiring["Name"].tolist())
        st.markdown(f"""
        <div style="
            position: fixed;
            top: 20px;
            right: 30px;
            background-color: #ffcc00;
            padding:15px 25px;
            border-radius:10px;
            font-weight:bold;
            z-index:9999;">
        ⚠️ Expiring soon: {names}
        </div>
        """, unsafe_allow_html=True)

    # --- Activity Log ---
    st.subheader("Activity Log")
    st.dataframe(st.session_state.activity_df.iloc[::-1].reset_index(drop=True), height=250)

    # --- Logout ---
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

else:
    st.info("Please login using the sidebar")
