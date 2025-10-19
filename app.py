import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os
import calendar
import time

# ================= SETTINGS =================
TIMEZONE = pytz.timezone("Asia/Kolkata")
EXCEL_FILE = "gym_data.xlsx"

# ================= LOAD DATA =================
def load_data():
    if not os.path.exists(EXCEL_FILE):
        users_df = pd.DataFrame({
            "Username": ["vineeth", "staff1"],
            "Role": ["Owner", "Staff"]
        })
        members_df = pd.DataFrame(columns=[
            "Full_Name", "Phone", "Membership_Type",
            "Join_Date", "Expiry_Date", "Added_By"
        ])
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
            users_df.to_excel(writer, sheet_name="Users", index=False)
            members_df.to_excel(writer, sheet_name="Members", index=False)
    else:
        xls = pd.ExcelFile(EXCEL_FILE)
        users_df = pd.read_excel(xls, "Users")
        members_df = pd.read_excel(xls, "Members")

        for col in ["Full_Name", "Phone", "Membership_Type", "Join_Date", "Expiry_Date", "Added_By"]:
            if col not in members_df.columns:
                members_df[col] = ""

    users_df = users_df.fillna("").astype(str)
    users_df["Username"] = users_df["Username"].str.strip()

    # Convert dates safely
    for col in ["Join_Date", "Expiry_Date"]:
        if col in members_df.columns:
            members_df[col] = pd.to_datetime(members_df[col], errors='coerce')

    return users_df, members_df

# ================= SAVE DATA =================
def save_data(users_df, members_df):
    df_users = users_df.copy()
    df_members = members_df.copy()

    for col in ["Join_Date", "Expiry_Date"]:
        if col in df_members.columns:
            df_members[col] = pd.to_datetime(df_members[col], errors='coerce')
            df_members[col] = df_members[col].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notnull(x) else "")

    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        df_users.to_excel(writer, sheet_name="Users", index=False)
        df_members.to_excel(writer, sheet_name="Members", index=False)

    # Monthly backup
    now = datetime.now(TIMEZONE)
    month_name = calendar.month_name[now.month]
    backup_file = f"gym_data_{month_name[:3]}_{now.day}.xlsx"
    with pd.ExcelWriter(backup_file, engine="openpyxl") as writer:
        df_users.to_excel(writer, sheet_name="Users", index=False)
        df_members.to_excel(writer, sheet_name="Members", index=False)

# ================= LOAD DATA =================
users_df, members_df = load_data()

# ================= SESSION STATE =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

st.title("🏋️ Gym Membership Management")

# --- LOGIN ---
username = st.text_input("Username")
if st.button("Login"):
    uname = str(username).strip()
    user = users_df[users_df["Username"] == uname]
    if user.empty:
        st.error("❌ Invalid username!")
    else:
        st.session_state.logged_in = True
        st.session_state.role = user.iloc[0]["Role"]
        st.success(f"✅ Logged in as {st.session_state.role}")

# ================= MAIN APP =================
if st.session_state.logged_in:
    role = st.session_state.role
    st.subheader(f"Welcome, {role}!")

    # --- Sidebar reminders ---
    reminder_placeholder = st.sidebar.empty()

    def show_expiring_members():
        now = datetime.now(TIMEZONE)
        df = members_df.copy()

        # Ensure Expiry_Date is datetime
        df["Expiry_Date"] = pd.to_datetime(df["Expiry_Date"], errors='coerce')
        df = df[df["Expiry_Date"].notna()]

        # Mask for next 7 days
        mask = df["Expiry_Date"].apply(lambda x: now <= x <= now + timedelta(days=7))
        soon_expiring = df[mask]

        reminder_placeholder.empty()
        if not soon_expiring.empty:
            reminder_placeholder.warning("⚠️ Memberships Expiring Soon (Next 7 Days):")
            for _, row in soon_expiring.iterrows():
                reminder_placeholder.write(
                    f"📅 {row['Full_Name']} - expires on {row['Expiry_Date'].strftime('%d-%b-%Y')}"
                )
        else:
            reminder_placeholder.info("✅ No memberships expiring soon.")

    show_expiring_members()

    # --- Member List ---
    st.header("👥 Member List")
    display_df = members_df.copy()
    for col in ["Join_Date", "Expiry_Date"]:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col], errors='coerce').apply(
                lambda x: x.strftime("%d-%b-%Y") if pd.notnull(x) else "N/A"
            )
    st.dataframe(display_df.reset_index(drop=True))

    # --- Add Member ---
    st.subheader("➕ Add New Member")
    with st.form("add_member_form"):
        full_name = st.text_input("Full Name")
        phone = st.text_input("Phone Number")
        membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Yearly"])
        submit = st.form_submit_button("Add Member")

        if submit:
            if not full_name or not phone:
                st.warning("⚠️ Please fill all fields.")
            elif phone in members_df["Phone"].astype(str).tolist():
                st.warning("⚠️ Member with this phone already exists.")
            else:
                join_date = datetime.now(TIMEZONE)
                if membership_type == "Monthly":
                    expiry_date = join_date + timedelta(days=30)
                elif membership_type == "Quarterly":
                    expiry_date = join_date + timedelta(days=90)
                else:
                    expiry_date = join_date + timedelta(days=365)

                new_row = {
                    "Full_Name": full_name,
                    "Phone": phone,
                    "Membership_Type": membership_type,
                    "Join_Date": join_date,
                    "Expiry_Date": expiry_date,
                    "Added_By": role
                }
                members_df = pd.concat([members_df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(users_df, members_df)
                st.success(f"✅ Member '{full_name}' added successfully!")

    # --- Edit/Delete Members (Owner Only) ---
    if role == "Owner":
        st.subheader("✏️ Edit / Delete Members")
        if not members_df.empty:
            member_names = members_df["Full_Name"].fillna("").tolist()
            selected_member = st.selectbox("Select Member", member_names)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑 Delete Member"):
                    members_df = members_df[members_df["Full_Name"] != selected_member].reset_index(drop=True)
                    save_data(users_df, members_df)
                    st.warning(f"🗑 Member '{selected_member}' deleted!")

            with col2:
                new_type = st.selectbox("Change Membership Type", ["Monthly", "Quarterly", "Yearly"], key="edit_type")
                if st.button("💾 Update Type"):
                    idx = members_df.index[members_df["Full_Name"] == selected_member]
                    if len(idx) > 0:
                        i = idx[0]
                        join_dt = members_df.at[i, "Join_Date"]
                        if pd.isna(join_dt):
                            join_dt = datetime.now(TIMEZONE)
                        if new_type == "Monthly":
                            expiry_date = join_dt + timedelta(days=30)
                        elif new_type == "Quarterly":
                            expiry_date = join_dt + timedelta(days=90)
                        else:
                            expiry_date = join_dt + timedelta(days=365)
                        members_df.at[i, "Membership_Type"] = new_type
                        members_df.at[i, "Expiry_Date"] = expiry_date
                        save_data(users_df, members_df)
                        st.success(f"🔁 Updated '{selected_member}' to {new_type} (expiry recalculated)")
                    else:
                        st.error("Selected member not found.")

    # --- Auto Refresh for 2-minute reminders ---
    st.info("ℹ️ Page auto-refreshes every 2 minutes for membership reminders.")
    time.sleep(120)
    st.experimental_rerun()
