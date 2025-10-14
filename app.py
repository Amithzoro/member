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

# ---------- SESSION STATE ----------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
if "members_df" not in st.session_state:
    st.session_state["members_df"] = pd.DataFrame()
if "staff_df" not in st.session_state:
    st.session_state["staff_df"] = pd.DataFrame()

# ---------- LOAD / SAVE ----------
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
    # Ensure no bytes objects remain in dataframe before saving
    if "Password" in df.columns:
        df = df.copy()
        df["Password"] = df["Password"].apply(lambda x: x.decode() if isinstance(x, (bytes, bytearray)) else ("" if pd.isna(x) else str(x)))
    df.to_excel(path, index=False)

# ---------- CLEAN DATAFRAME ----------
def clean_members_df(df):
    if df.empty:
        return df
    df = df.copy()
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
    if df.empty:
        return df
    df = df.copy()
    df["Username"] = df["Username"].astype(str)
    df["Role"] = df["Role"].astype(str)
    df["Added_On"] = pd.to_datetime(df["Added_On"], errors="coerce")
    # Convert password column to string safely
    df["Password"] = df["Password"].apply(lambda x: x.decode() if isinstance(x, (bytes, bytearray)) else ("" if pd.isna(x) else str(x)))
    return df

# ---------- FILE STRUCTURE ----------
member_cols = ["Name", "Membership_Type", "Start_Date", "End_Date", "Amount", "Added_By", "Added_On", "Last_Updated"]
staff_cols = ["Username", "Password", "Role", "Added_On"]

# Load Excel files into session_state if empty
if st.session_state["members_df"].empty:
    st.session_state["members_df"] = clean_members_df(load_excel(MEMBER_FILE, member_cols))
if st.session_state["staff_df"].empty:
    st.session_state["staff_df"] = clean_staff_df(load_excel(STAFF_FILE, staff_cols))

# ---------- DEFAULT OWNER (ensure exists with desired password) ----------
owner_username = "amith"
owner_plain_password = "panda"  # <-- your requested owner password

owner_exists = owner_username in st.session_state["staff_df"]["Username"].values if not st.session_state["staff_df"].empty else False

if not owner_exists:
    # create owner with hashed password stored as string
    hashed_owner = bcrypt.hashpw(owner_plain_password.encode(), bcrypt.gensalt()).decode()
    owner_row = pd.DataFrame([{
        "Username": owner_username,
        "Password": hashed_owner,
        "Role": "Owner",
        "Added_On": datetime.now(TIMEZONE)
    }])
    st.session_state["staff_df"] = pd.concat([st.session_state["staff_df"], owner_row], ignore_index=True)
    st.session_state["staff_df"] = clean_staff_df(st.session_state["staff_df"])
    save_excel(st.session_state["staff_df"], STAFF_FILE)

# ---------- TWO LOGIN OPTIONS (sidebar) ----------
st.sidebar.header("🔐 Owner Login")
owner_user_input = st.sidebar.text_input("Owner Username", key="owner_user")
owner_pw_input = st.sidebar.text_input("Owner Password", type="password", key="owner_pw")
if st.sidebar.button("Owner Login"):
    if owner_user_input.strip() == "":
        st.sidebar.error("Enter owner username.")
    else:
        user_row = st.session_state["staff_df"][
            (st.session_state["staff_df"]["Username"] == owner_user_input) &
            (st.session_state["staff_df"]["Role"] == "Owner")
        ]
        if user_row.empty:
            st.sidebar.error("Owner username not found.")
        else:
            stored_pw = user_row.iloc[0]["Password"]
            pw_str = "" if pd.isna(stored_pw) else str(stored_pw)
            # encode and check
            try:
                if bcrypt.checkpw(owner_pw_input.encode(), pw_str.encode()):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = owner_user_input
                    st.session_state["role"] = "Owner"
                    st.sidebar.success(f"Welcome Owner: {owner_user_input}")
                else:
                    st.sidebar.error("Invalid Owner password.")
            except Exception:
                st.sidebar.error("Password check failed. Contact admin.")

st.sidebar.header("🔐 Staff Login")
staff_user_input = st.sidebar.text_input("Staff Username", key="staff_user")
staff_pw_input = st.sidebar.text_input("Staff Password", type="password", key="staff_pw")
if st.sidebar.button("Staff Login"):
    if staff_user_input.strip() == "":
        st.sidebar.error("Enter staff username.")
    else:
        user_row = st.session_state["staff_df"][
            (st.session_state["staff_df"]["Username"] == staff_user_input) &
            (st.session_state["staff_df"]["Role"] != "Owner")
        ]
        if user_row.empty:
            st.sidebar.error("Staff username not found.")
        else:
            stored_pw = user_row.iloc[0]["Password"]
            pw_str = "" if pd.isna(stored_pw) else str(stored_pw)
            try:
                if bcrypt.checkpw(staff_pw_input.encode(), pw_str.encode()):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = staff_user_input
                    st.session_state["role"] = user_row.iloc[0]["Role"]
                    st.sidebar.success(f"Welcome Staff: {staff_user_input}")
                else:
                    st.sidebar.error("Invalid Staff password.")
            except Exception:
                st.sidebar.error("Password check failed. Contact admin.")

# ---------- AFTER LOGIN ----------
if st.session_state.get("logged_in", False):
    user = st.session_state.get("username", "")
    role = st.session_state.get("role", "")

    # Membership expiry alerts
    st.markdown("### ⚠️ Membership Expiry Alerts")
    today = datetime.now(TIMEZONE).date()
    try:
        expiring = st.session_state["members_df"][
            pd.to_datetime(st.session_state["members_df"]["End_Date"], errors="coerce").dt.date.between(today, today + timedelta(days=5))
        ]
    except Exception:
        expiring = pd.DataFrame()
    if not expiring.empty:
        for _, row in expiring.iterrows():
            endd = row["End_Date"]
            end_str = endd.date() if not pd.isna(endd) else "Unknown"
            st.warning(f"Member **{row['Name']}** membership ends on **{end_str}**")
    else:
        st.info("No memberships nearing expiry.")

    # Tabs
    tabs = st.tabs(["🏋️ Add Member", "📋 View Members", "👥 Staff (Owner Only)"])

    # Add / Update Member
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
                    # find by exact name; you can change to case-insensitive if desired
                    idx = st.session_state["members_df"][st.session_state["members_df"]["Name"] == name].index
                    now_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
                    if not idx.empty:
                        # Update existing member
                        st.session_state["members_df"].loc[idx, ["Membership_Type","Start_Date","End_Date","Amount","Last_Updated"]] = [
                            membership_type, pd.to_datetime(start_date), pd.to_datetime(end_date), float(amount), now_str
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
                            "Added_On": now_str,
                            "Last_Updated": now_str
                        }])
                        st.session_state["members_df"] = pd.concat([st.session_state["members_df"], new_entry], ignore_index=True)
                        st.success(f"Member **{name}** added successfully!")

                    st.session_state["members_df"] = clean_members_df(st.session_state["members_df"])
                    save_excel(st.session_state["members_df"], MEMBER_FILE)

    # View Members
    with tabs[1]:
        st.subheader("Your Added Members")
        df_to_show = st.session_state["members_df"]
        if role != "Owner":
            df_to_show = df_to_show[df_to_show["Added_By"] == user]
        st.dataframe(df_to_show, use_container_width=True)

    # Staff management (owner only)
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
                        hashed_pw = bcrypt.hashpw(staff_password.encode(), bcrypt.gensalt()).decode()
                        new_row = pd.DataFrame([{
                            "Username": new_staff,
                            "Password": hashed_pw,
                            "Role": staff_role,
                            "Added_On": datetime.now(TIMEZONE)
                        }])
                        st.session_state["staff_df"] = pd.concat([st.session_state["staff_df"], new_row], ignore_index=True)
                        st.session_state["staff_df"] = clean_staff_df(st.session_state["staff_df"])
                        save_excel(st.session_state["staff_df"], STAFF_FILE)
                        st.success(f"Staff **{new_staff}** added successfully!")

            # show staff without passwords
            display_staff = st.session_state["staff_df"].copy()
            if "Password" in display_staff.columns:
                display_staff = display_staff.drop(columns=["Password"])
            st.dataframe(display_staff, use_container_width=True)
        else:
            st.info("You don’t have access to this section.")

else:
    st.info("👈 Please log in using the sidebar to continue.")
