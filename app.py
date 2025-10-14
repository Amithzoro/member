import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, timedelta
import pytz
import os

# ---------- CONFIG ----------
TIMEZONE = pytz.timezone("Asia/Kolkata")
MEMBER_FILE = "gym_members.xlsx"
STAFF_FILE = "staff_list.xlsx"

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Gym Member Manager", layout="wide")
st.title("💪 Gym Management System")

# ---------- SESSION STATE INIT ----------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
if "members_df" not in st.session_state:
    st.session_state["members_df"] = pd.DataFrame()
if "staff_df" not in st.session_state:
    st.session_state["staff_df"] = pd.DataFrame()

# ---------- LOAD / SAVE FUNCTIONS ----------
def load_excel(path, cols):
    if os.path.exists(path):
        df = pd.read_excel(path)
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        return df[cols]
    else:
        return pd.DataFrame(columns=cols)

def save_excel(df, path):
    df.to_excel(path, index=False)

# ---------- CLEAN DATAFRAME FUNCTIONS ----------
def clean_members_df(df):
    df["Start_Date"] = pd.to_datetime(df["Start_Date"], errors="coerce")
    df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")
    df["Name"] = df["Name"].astype(str)
    df["Membership_Type"] = df["Membership_Type"].astype(str)
    df["Added_By"] = df["Added_By"].astype(str)
    df["Added_On"] = pd.to_datetime(df["Added_On"], errors="coerce")
    df["Last_Updated"] = pd.to_datetime(df["Last_Updated"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    return df

def clean_staff_df(df):
    df["Username"] = df["Username"].astype(str)
    df["Role"] = df["Role"].astype(str)
    df["Added_On"] = pd.to_datetime(df["Added_On"], errors="coerce")
    df["Password"] = df["Password"].astype(str)
    return df

# ---------- FILE STRUCTURE ----------
member_cols = ["Name", "Membership_Type", "Start_Date", "End_Date", "Amount", "Added_By", "Added_On", "Last_Updated"]
staff_cols = ["Username", "Password", "Role", "Added_On"]

# Load Excel files
if st.session_state["members_df"].empty:
    st.session_state["members_df"] = clean_members_df(load_excel(MEMBER_FILE, member_cols))
if st.session_state["staff_df"].empty:
    st.session_state["staff_df"] = clean_staff_df(load_excel(STAFF_FILE, staff_cols))

# ---------- DEFAULT OWNER ----------
if "amith" not in st.session_state["staff_df"]["Username"].values:
    default_owner_pw = bcrypt.hashpw("password".encode(), bcrypt.gensalt())
    st.session_state["staff_df"] = pd.concat([
        st.session_state["staff_df"],
        pd.DataFrame([{"Username": "amith", "Password": default_owner_pw.decode(), "Role": "Owner", "Added_On": datetime.now(TIMEZONE)}])
    ], ignore_index=True)
    save_excel(st.session_state["staff_df"], STAFF_FILE)

# ---------- LOGIN ----------
st.sidebar.header("🔐 Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

def verify_user(username, password):
    user_row = st.session_state["staff_df"][st.session_state["staff_df"]["Username"] == username]
    if not user_row.empty:
        hashed_pw = user_row.iloc[0]["Password"]
        hashed_pw = hashed_pw.encode()  # convert string → bytes
        if bcrypt.checkpw(password.encode(), hashed_pw):
            return True
    return False

if st.sidebar.button("Login"):
    if verify_user(username, password):
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        st.success(f"Welcome, {username.capitalize()}!")
    else:
        st.error("Invalid username or password.")

# ---------- AFTER LOGIN ----------
if st.session_state.get("logged_in"):
    user = st.session_state["username"]
    role = st.session_state["staff_df"].loc[st.session_state["staff_df"]["Username"]==user, "Role"].values[0]

    # -------- Membership Expiry Alert --------
    st.markdown("### ⚠️ Membership Expiry Alerts")
    today = datetime.now(TIMEZONE).date()
    expiring = st.session_state["members_df"][
        pd.to_datetime(st.session_state["members_df"]["End_Date"], errors='coerce').dt.date.between(today, today + timedelta(days=5))
    ]
    if not expiring.empty:
        for _, row in expiring.iterrows():
            st.warning(f"Member **{row['Name']}** membership ends on **{row['End_Date'].date()}**")
    else:
        st.info("No memberships nearing expiry.")

    # -------- Tabs --------
    tabs = st.tabs(["🏋️ Add Member", "📋 View Members", "👥 Staff (Owner Only)"])

    # -------- ADD MEMBER --------
    with tabs[0]:
        st.subheader("Add / Update Gym Member")
        with st.form("add_member_form"):
            name = st.text_input("Member Name")
            membership_type = st.selectbox("Membership Type", ["Tour (1 Day)", "Monthly", "Quarterly", "Yearly"])
            amount = st.number_input("Amount (₹)", min_value=0, step=1)
            start_date = datetime.now(TIMEZONE).date()
            if membership_type == "Tour (1 Day)":
                end_date = start_date + timedelta(days=1)
            elif membership_type == "Monthly":
                end_date = start_date + timedelta(days=30)
            elif membership_type == "Quarterly":
                end_date = start_date + timedelta(days=90)
            else:
                end_date = start_date + timedelta(days=365)

            submitted = st.form_submit_button("➕ Add / Update Member")
            if submitted:
                if name.strip() == "":
                    st.warning("Member name cannot be empty!")
                else:
                    # Check if member exists
                    idx = st.session_state["members_df"][st.session_state["members_df"]["Name"] == name].index
                    if not idx.empty:
                        # Update existing member
                        st.session_state["members_df"].loc[idx, ["Membership_Type","Start_Date","End_Date","Amount","Last_Updated"]] = [
                            membership_type, pd.to_datetime(start_date), pd.to_datetime(end_date), float(amount),
                            datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                        ]
                        st.success(f"Member **{name}** updated successfully!")
                    else:
                        # Add new member
                        new_entry = pd.DataFrame([{
                            "Name": name,
                            "Membership_Type": membership_type,
                            "Start_Date": pd.to_datetime(start_date),
                            "End_Date": pd.to_datetime(end_date),
                            "Amount": float(amount),
                            "Added_By": user,
                            "Added_On": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
                            "Last_Updated": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                        }])
                        st.session_state["members_df"] = pd.concat([st.session_state["members_df"], new_entry], ignore_index=True)
                        st.success(f"Member **{name}** added successfully!")

                    st.session_state["members_df"] = clean_members_df(st.session_state["members_df"])
                    save_excel(st.session_state["members_df"], MEMBER_FILE)

    # -------- VIEW MEMBERS --------
    with tabs[1]:
        st.subheader("Your Added Members")
        df_to_show = st.session_state["members_df"]
        if role != "Owner":
            df_to_show = df_to_show[df_to_show["Added_By"] == user]
        st.dataframe(df_to_show, use_container_width=True)

    # -------- STAFF MANAGEMENT (OWNER ONLY) --------
    with tabs[2]:
        if role == "Owner":
            st.subheader("Manage Staff Accounts")
            with st.form("add_staff_form"):
                new_staff = st.text_input("Staff Username")
                staff_password = st.text_input("Staff Password", type="password")
                staff_role = st.selectbox("Role", ["Trainer", "Receptionist", "Manager"])
                add_staff = st.form_submit_button("➕ Add Staff")
                if add_staff:
                    if new_staff.strip() == "" or staff_password.strip() == "":
                        st.warning("Username and Password cannot be empty!")
                    elif new_staff in st.session_state["staff_df"]["Username"].values:
                        st.warning("Staff username already exists!")
                    else:
                        hashed_pw = bcrypt.hashpw(staff_password.encode(), bcrypt.gensalt())
                        new_row = pd.DataFrame([{
                            "Username": new_staff,
                            "Password": hashed_pw.decode(),  # store as string
                            "Role": staff_role,
                            "Added_On": datetime.now(TIMEZONE)
                        }])
                        st.session_state["staff_df"] = pd.concat([st.session_state["staff_df"], new_row], ignore_index=True)
                        st.session_state["staff_df"] = clean_staff_df(st.session_state["staff_df"])
                        save_excel(st.session_state["staff_df"], STAFF_FILE)
                        st.success(f"Staff **{new_staff}** added successfully!")

            st.dataframe(st.session_state["staff_df"][["Username", "Role", "Added_On"]], use_container_width=True)
        else:
            st.info("You don’t have access to this section.")

else:
    st.info("👈 Please log in using the sidebar to continue.")
