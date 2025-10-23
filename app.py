import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz
import os

# --- IST Timezone ---
IST = pytz.timezone("Asia/Kolkata")

# --- Ensure data folder exists ---
os.makedirs("data", exist_ok=True)
EXCEL_FILE = "data/members.xlsx"

# --- Required columns ---
required_cols = ["Member_Name", "Start_Date", "Expiry_Date", "Amount", "Month", "Year", "Duration"]

# --- Load or create members Excel file ---
try:
    members_df = pd.read_excel(EXCEL_FILE)
    for col in required_cols:
        if col not in members_df.columns:
            members_df[col] = ""
except FileNotFoundError:
    members_df = pd.DataFrame(columns=required_cols)
    members_df.to_excel(EXCEL_FILE, index=False)

# --- Login credentials ---
USERS = {
    "vineeth": {"password": "panda@2006", "role": "Owner"},
    "staff1": {"password": "staff@123", "role": "Staff"},
}

# --- Session state ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None

# --- Login Page ---
st.title("🏋️ Gym Membership Management System (IST)")

if not st.session_state.logged_in:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.role = USERS[username]["role"]
            st.session_state.username = username
            st.success(f"✅ Welcome, {username}! Role: {st.session_state.role}")
            st.rerun()
        else:
            st.error("❌ Invalid username or password!")

# --- Dashboard after login ---
if st.session_state.logged_in:
    role = st.session_state.role
    username = st.session_state.username

    st.sidebar.success(f"Logged in as: {role}")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

    now_ist = datetime.now(IST)

    # --- Expiry reminders in IST ---
    if not members_df.empty:
        # Convert Expiry_Date to IST-aware datetime
        members_df["Expiry_Date_IST"] = pd.to_datetime(members_df["Expiry_Date"], errors="coerce").dt.tz_localize(
            'Asia/Kolkata', ambiguous='NaT', nonexistent='shift_forward'
        )

        soon_expiring = members_df[
            (members_df["Expiry_Date_IST"].notnull()) &
            ((members_df["Expiry_Date_IST"] - now_ist) <= pd.Timedelta(days=7))
        ]
        if not soon_expiring.empty:
            st.warning("⚠️ Members expiring within 7 days (IST):")
            st.dataframe(soon_expiring[["Member_Name", "Start_Date", "Expiry_Date", "Amount", "Month", "Year", "Duration"]])

    st.header(f"{role} Dashboard")

    # --- View Members ---
    st.subheader("👥 Member List")
    if members_df.empty:
        st.info("No members found yet.")
    else:
        st.dataframe(members_df)

    # --- Membership Duration Options ---
    duration_map = {
        "Monthly": 1,
        "Quarterly": 3,
        "Half-Yearly": 6,
        "Yearly": 12
    }

    # --- Add Member (Owner & Staff) ---
    st.subheader("➕ Add New Member")
    member_name = st.text_input("Member Name")
    amount = st.number_input("Amount Paid", min_value=0)
    start_date = st.date_input("Membership Start Date", value=now_ist.date())
    duration_option = st.selectbox("Membership Duration", list(duration_map.keys()))

    # Calculate expiry based on duration
    expiry_date = start_date + relativedelta(months=duration_map[duration_option])
    month = start_date.strftime("%B")
    year = start_date.year
    st.write(f"✅ Expiry Date will be set to: {expiry_date.strftime('%Y-%m-%d')} (Month: {month}, Year: {year})")

    if st.button("Add Member"):
        if member_name:
            new_row = {
                "Member_Name": member_name,
                "Start_Date": start_date.strftime("%Y-%m-%d"),
                "Expiry_Date": expiry_date.strftime("%Y-%m-%d"),
                "Amount": amount,
                "Month": month,
                "Year": year,
                "Duration": duration_option
            }
            members_df = pd.concat([members_df, pd.DataFrame([new_row])], ignore_index=True)

            # --- Save Excel safely ---
            save_df = members_df.copy()
            if "Expiry_Date_IST" in save_df.columns:
                save_df = save_df.drop(columns=["Expiry_Date_IST"])
            for col in ["Start_Date", "Expiry_Date"]:
                if col in save_df.columns:
                    save_df[col] = pd.to_datetime(save_df[col], errors="coerce").dt.tz_localize(None)
            save_df.to_excel(EXCEL_FILE, index=False)

            st.success(f"✅ Member '{member_name}' added successfully!")
            st.rerun()
        else:
            st.warning("⚠️ Please enter a member name.")

    # --- Edit/Delete Members (Owner Only) ---
    if role == "Owner" and not members_df.empty:
        st.subheader("✏️ Edit or Delete Member")
        member_names = members_df["Member_Name"].tolist()
        if member_names:
            selected_member = st.selectbox("Select Member", member_names)
            row = members_df[members_df["Member_Name"] == selected_member].iloc[0]

            new_name = st.text_input("Edit Name", row["Member_Name"])
            new_amount = st.number_input("Edit Amount", value=float(row["Amount"]))
            new_start = st.date_input(
                "Edit Start Date",
                pd.to_datetime(row["Start_Date"]) if not pd.isna(row["Start_Date"]) else now_ist.date()
            )
            duration_option = st.selectbox(
                "Membership Duration",
                list(duration_map.keys()),
                index=list(duration_map.keys()).index(row.get("Duration", "Monthly"))
            )

            # Auto expiry by duration
            auto_expiry = new_start + relativedelta(months=duration_map[duration_option])
            st.write(f"✅ Expiry Date automatically set to: {auto_expiry.strftime('%Y-%m-%d')}")
            new_expiry_override = st.date_input("Override Expiry Date (Optional)", auto_expiry)
            final_expiry = new_expiry_override if new_expiry_override else auto_expiry

            # Month & Year from Start Date
            month = new_start.strftime("%B")
            year = new_start.year

            if st.button("💾 Save Changes"):
                members_df.loc[members_df["Member_Name"] == selected_member, ["Member_Name", "Amount", "Start_Date", "Expiry_Date", "Month", "Year", "Duration"]] = [
                    new_name,
                    new_amount,
                    new_start.strftime("%Y-%m-%d"),
                    final_expiry.strftime("%Y-%m-%d"),
                    month,
                    year,
                    duration_option
                ]

                # --- Save Excel safely ---
                save_df = members_df.copy()
                if "Expiry_Date_IST" in save_df.columns:
                    save_df = save_df.drop(columns=["Expiry_Date_IST"])
                for col in ["Start_Date", "Expiry_Date"]:
                    if col in save_df.columns:
                        save_df[col] = pd.to_datetime(save_df[col], errors="coerce").dt.tz_localize(None)
                save_df.to_excel(EXCEL_FILE, index=False)

                st.success(f"✅ Updated '{selected_member}' successfully!")
                st.rerun()

            if st.button("🗑 Delete Member"):
                members_df = members_df[members_df["Member_Name"] != selected_member]

                # --- Save Excel safely ---
                save_df = members_df.copy()
                if "Expiry_Date_IST" in save_df.columns:
                    save_df = save_df.drop(columns=["Expiry_Date_IST"])
                for col in ["Start_Date", "Expiry_Date"]:
                    if col in save_df.columns:
                        save_df[col] = pd.to_datetime(save_df[col], errors="coerce").dt.tz_localize(None)
                save_df.to_excel(EXCEL_FILE, index=False)

                st.warning(f"❌ Deleted member '{selected_member}'")
                st.rerun()
        else:
            st.info("No members available to edit or delete.")

    # --- Staff can update amount only ---
    if role == "Staff" and not members_df.empty:
        st.subheader("💰 Update Member Amount")
        member_names = members_df["Member_Name"].tolist()
        if member_names:
            selected_member = st.selectbox("Select Member to Update", member_names)
            new_amount = st.number_input("Enter New Amount", min_value=0)
            if st.button("Update Amount"):
                members_df.loc[members_df["Member_Name"] == selected_member, "Amount"] = new_amount

                # --- Save Excel safely ---
                save_df = members_df.copy()
                if "Expiry_Date_IST" in save_df.columns:
                    save_df = save_df.drop(columns=["Expiry_Date_IST"])
                for col in ["Start_Date", "Expiry_Date"]:
                    if col in save_df.columns:
                        save_df[col] = pd.to_datetime(save_df[col], errors="coerce").dt.tz_localize(None)
                save_df.to_excel(EXCEL_FILE, index=False)

                st.success(f"✅ Updated amount for {selected_member}")
                st.rerun()
