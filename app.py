# gym_tracker_final_clean.py
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

def load_excel(path, cols):
    return pd.read_excel(path) if os.path.exists(path) else pd.DataFrame(columns=cols)

def save_excel(df, path):
    df.to_excel(path, index=False)

def append_csv(path, row):
    df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=row.keys())
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False)

# ---------- SESSION STATE ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "members_df" not in st.session_state:
    st.session_state.members_df = load_excel(DATA_FILE, ["Name","Phone","Start_Date","End_Date","Recorded_By","Added_At"])
if "activity_df" not in st.session_state:
    st.session_state.activity_df = pd.read_csv(ACTIVITY_FILE) if os.path.exists(ACTIVITY_FILE) else pd.DataFrame(columns=["Timestamp","Action","Details"])

# ---------- LOGIN ----------
st.sidebar.header("Login")
u = st.sidebar.text_input("Username")
p = st.sidebar.text_input("Password", type="password")
if st.sidebar.button("Login"):
    if u == USERNAME and p == PASSWORD:
        st.session_state.logged_in = True
        st.session_state.username = u
        st.sidebar.success("Logged in!")
    else:
        st.sidebar.error("Invalid username or password")

# ---------- MAIN APP ----------
if st.session_state.logged_in:
    st.title("Gym Membership Tracker")
    st.success(f"Logged in as {st.session_state.username}")

    # ---------- ADD / EDIT MEMBER ----------
    st.subheader("Add / Edit Member")
    df = st.session_state.members_df.copy()
    member_names = df["Name"].tolist()
    selected_member = st.selectbox("Select member to edit (or leave blank to add new)", [""] + member_names)

    name = st.text_input("Name", value=selected_member if selected_member else "")
    phone = st.text_input("Phone", value=df[df["Name"]==selected_member]["Phone"].values[0] if selected_member else "")
    start_date = st.date_input("Start Date", value=df[df["Name"]==selected_member]["Start_Date"].values[0] if selected_member else pd.Timestamp.now().date())
    end_date = st.date_input("End Date", value=df[df["Name"]==selected_member]["End_Date"].values[0] if selected_member else pd.Timestamp.now().date())

    if st.button("Save Member"):
        if selected_member:  # Edit
            st.session_state.members_df.loc[st.session_state.members_df["Name"]==selected_member, ["Name","Phone","Start_Date","End_Date"]] = [name, phone, start_date, end_date]
            action = f"Edited member: {selected_member} → {name}"
        else:  # Add new
            new_row = {"Name":name,"Phone":phone,"Start_Date":start_date,"End_Date":end_date,"Recorded_By":st.session_state.username,"Added_At":now_str()}
            st.session_state.members_df = pd.concat([st.session_state.members_df, pd.DataFrame([new_row])], ignore_index=True)
            action = f"Added member: {name}"
        save_excel(st.session_state.members_df, DATA_FILE)
        append_csv(ACTIVITY_FILE, {"Timestamp":now_str(),"Action":action,"Details":name})
        st.success(f"✅ {action}")
        st.experimental_rerun()  # Refresh to show updated info

    # ---------- VIEW & FILTER ----------
    st.subheader("Member List")
    filter_name = st.text_input("Search by Name")
    df_show = st.session_state.members_df.copy()
    if filter_name:
        df_show = df_show[df_show["Name"].str.contains(filter_name, case=False, na=False)]
    st.dataframe(df_show.reset_index(drop=True), height=400)
    st.download_button("Download Members CSV", df_show.to_csv(index=False).encode(), "members.csv")

    # ---------- EXPIRY ALERT ----------
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

    # ---------- Activity Log ----------
    st.subheader("Activity Log")
    if not st.session_state.activity_df.empty:
        st.dataframe(st.session_state.activity_df.iloc[::-1].reset_index(drop=True), height=250)
    else:
        st.write("No activity yet.")

    # ---------- Logout ----------
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.experimental_rerun()

else:
    st.info("Please login using the sidebar")
