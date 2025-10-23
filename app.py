import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz
import os

# ----------------------- Constants -----------------------
IST = pytz.timezone("Asia/Kolkata")
EXCEL_FILE = "data/members.xlsx"
DURATION_MAP = {"Monthly":1, "Quarterly":3, "Half-Yearly":6, "Yearly":12}

USERS = {
    "vineeth": {"password":"panda@2006", "role":"Owner"},
    "staff1": {"password":"staff@123", "role":"Staff"}
}

REQUIRED_COLUMNS = ["Member_Name", "Start_Date", "Expiry_Date", "Amount", "Month", "Year", "Duration", "Timestamp"]

# ----------------------- Helpers -----------------------
def load_members():
    os.makedirs("data", exist_ok=True)
    try:
        df = pd.read_excel(EXCEL_FILE)
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df
    except FileNotFoundError:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        df.to_excel(EXCEL_FILE, index=False)
        return df

def save_members(df):
    df_copy = df.copy()
    # Convert dates to timezone-naive datetime
    for col in ["Start_Date", "Expiry_Date"]:
        df_copy[col] = pd.to_datetime(df_copy[col], errors="coerce").dt.tz_localize(None)
    try:
        os.makedirs(os.path.dirname(EXCEL_FILE), exist_ok=True)
        df_copy.to_excel(EXCEL_FILE, index=False)
    except Exception as e:
        st.error(f"❌ Failed to save Excel file: {e}")

def get_ist_now():
    return datetime.now(IST)

def add_member(df, name, start_date, duration, amount):
    auto_expiry = start_date + relativedelta(months=DURATION_MAP[duration])
    month = start_date.strftime("%B")
    year = start_date.year
    timestamp = get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = {
        "Member_Name": name,
        "Start_Date": start_date.strftime("%Y-%m-%d"),
        "Expiry_Date": auto_expiry.strftime("%Y-%m-%d"),
        "Amount": amount,
        "Month": month,
        "Year": year,
        "Duration": duration,
        "Timestamp": timestamp
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_members(df)
    return df, auto_expiry

def update_member(df, original_name, new_name, start_date, duration, amount, expiry_override=None):
    auto_expiry = start_date + relativedelta(months=DURATION_MAP[duration])
    final_expiry = expiry_override if expiry_override else auto_expiry
    month = start_date.strftime("%B")
    year = start_date.year
    timestamp = get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
    
    df.loc[df["Member_Name"]==original_name, ["Member_Name","Start_Date","Expiry_Date","Amount","Month","Year","Duration","Timestamp"]] = [
        new_name, start_date.strftime("%Y-%m-%d"), final_expiry.strftime("%Y-%m-%d"),
        amount, month, year, duration, timestamp
    ]
    save_members(df)
    return df

def delete_member(df, member_name):
    df = df[df["Member_Name"] != member_name]
    save_members(df)
    return df

def staff_update_amount(df, member_name, amount):
    df.loc[df["Member_Name"]==member_name, ["Amount","Timestamp"]] = [
        amount, get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
    ]
    save_members(df)
    return df

def get_expiring_members(df, days=7):
    now = get_ist_now()
    expiry_dates = pd.to_datetime(df["Expiry_Date"], errors="coerce").dt.tz_localize(None)
    valid_mask = expiry_dates.notna()
    soon_expire_mask = valid_mask & ((expiry_dates - now) <= pd.Timedelta(days=days))
    soon_expire = df[soon_expire_mask].copy()
    return soon_expire

# ----------------------- Streamlit App -----------------------
def main():
    st.title("🏋️ Gym Membership Management System (IST)")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = None

    # --- Login ---
    if not st.session_state.logged_in:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username in USERS and USERS[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.role = USERS[username]["role"]
                st.session_state.username = username
                st.success(f"✅ Welcome, {username}! Role: {st.session_state.role}")
                st.experimental_rerun()
            else:
                st.error("❌ Invalid username or password!")
        return

    # --- Load members ---
    members_df = load_members()
    role = st.session_state.role

    # --- Sidebar ---
    st.sidebar.success(f"Logged in as: {role}")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.clear()
        st.experimental_rerun()

    # --- Expiry reminder ---
    if not members_df.empty:
        expiring = get_expiring_members(members_df)
        if not expiring.empty:
            st.warning("⚠️ Members expiring within 7 days (IST):")
            st.dataframe(expiring[["Member_Name","Start_Date","Expiry_Date","Amount","Month","Year","Duration","Timestamp"]])

    # --- View Members ---
    st.subheader("👥 Member List")
    if members_df.empty:
        st.info("No members found yet.")
    else:
        st.dataframe(members_df[["Member_Name","Start_Date","Expiry_Date","Amount","Month","Year","Duration","Timestamp"]])

    # --- Add Member (Owner & Staff) ---
    st.subheader("➕ Add New Member")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Member Name", key="add_name")
        amount = st.number_input("Amount Paid", min_value=0, key="add_amount")
    with col2:
        start_date = st.date_input("Membership Start Date", value=get_ist_now().date(), key="add_start")
        duration = st.selectbox("Membership Duration", list(DURATION_MAP.keys()), key="add_duration")
    
    if st.button("Add Member"):
        if name in members_df["Member_Name"].tolist():
            st.warning("Member name already exists!")
        elif amount < 0:
            st.warning("Amount must be >= 0")
        else:
            members_df, auto_expiry = add_member(members_df, name, start_date, duration, amount)
            st.success(f"✅ Member '{name}' added with expiry {auto_expiry.strftime('%Y-%m-%d')}")

    # --- Owner: Edit/Delete Members ---
    if role=="Owner" and not members_df.empty:
        st.subheader("✏️ Edit/Delete Member")
        member_list = members_df["Member_Name"].tolist()
        selected_member = st.selectbox("Select Member", member_list, key="edit_select")
        row = members_df[members_df["Member_Name"]==selected_member].iloc[0]

        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Edit Name", row["Member_Name"], key="edit_name")
            new_amount = st.number_input("Edit Amount", value=float(row["Amount"]), key="edit_amount")
        with col2:
            new_start = st.date_input("Edit Start Date", pd.to_datetime(row["Start_Date"]), key="edit_start")
            duration = st.selectbox("Membership Duration", list(DURATION_MAP.keys()), index=list(DURATION_MAP.keys()).index(row["Duration"]), key="edit_duration")
            auto_expiry = new_start + relativedelta(months=DURATION_MAP[duration])
            expiry_override = st.date_input("Override Expiry Date (Optional)", value=auto_expiry)

        if st.button("💾 Save Changes"):
            members_df = update_member(members_df, selected_member, new_name, new_start, duration, new_amount, expiry_override)
            st.success(f"✅ Member '{new_name}' updated successfully")
            st.experimental_rerun()

        if st.button("🗑 Delete Member"):
            members_df = delete_member(members_df, selected_member)
            st.warning(f"❌ Member '{selected_member}' deleted")
            st.experimental_rerun()

    # --- Staff: Update Amount Only ---
    if role=="Staff" and not members_df.empty:
        st.subheader("💰 Update Member Amount")
        member_list = members_df["Member_Name"].tolist()
        selected_member = st.selectbox("Select Member to Update", member_list, key="staff_select")
        new_amount = st.number_input("Enter New Amount", min_value=0, key="staff_amount")
        if st.button("Update Amount"):
            members_df = staff_update_amount(members_df, selected_member, new_amount)
            st.success(f"✅ Amount updated for {selected_member}")
            st.experimental_rerun()

if __name__ == "__main__":
    main()
