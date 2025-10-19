import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os
import calendar

# ========== SETTINGS ==========
TIMEZONE = pytz.timezone("Asia/Kolkata")
EXCEL_FILE = "gym_data.xlsx"

# ========== INITIAL DATA CREATION ==========
def load_data():
    if not os.path.exists(EXCEL_FILE):
        users_df = pd.DataFrame({
            "Username": ["owner", "staff1"],
            "Password": ["owner123", "staff123"],
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

        # Ensure required columns exist (safety net)
        for col in ["Full_Name", "Phone", "Membership_Type", "Join_Date", "Expiry_Date", "Added_By"]:
            if col not in members_df.columns:
                members_df[col] = ""

    return users_df, members_df

def save_data(users_df, members_df):
    users_df = users_df.astype(str)
    members_df = members_df.astype(str)
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        members_df.to_excel(writer, sheet_name="Members", index=False)

    # Save monthly backup
    month_name = calendar.month_name[datetime.now(TIMEZONE).month]
    backup_file = f"gym_data_{month_name[:3]}.xlsx"
    with pd.ExcelWriter(backup_file, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        members_df.to_excel(writer, sheet_name="Members", index=False)

# ========== LOAD DATA ==========
users_df, members_df = load_data()

# ========== LOGIN ==========
st.title("🏋️ Gym Membership Management")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    user = users_df[(users_df["Username"] == username) & (users_df["Password"] == password)]

    if user.empty:
        st.error("❌ Invalid credentials!")
    else:
        role = user.iloc[0]["Role"]
        st.success(f"✅ Logged in as {role}")

        # --- Members Section ---
        st.header("👥 Member List")

        # Convert expiry column safely
        members_df["Expiry_Date"] = pd.to_datetime(members_df["Expiry_Date"], errors="coerce")

        # --- Reminder Section ---
        if not members_df.empty:
            soon_expiring = members_df[members_df["Expiry_Date"] <= datetime.now(TIMEZONE) + timedelta(days=7)]
            if not soon_expiring.empty:
                st.sidebar.warning("⚠️ Memberships Expiring Soon:")
                for _, row in soon_expiring.iterrows():
                    st.sidebar.write(f"📅 {row['Full_Name']} - expires on {row['Expiry_Date'].strftime('%d-%b-%Y')}")

        st.dataframe(members_df)

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
                else:
                    join_date = datetime.now(TIMEZONE)
                    if membership_type == "Monthly":
                        expiry_date = join_date + timedelta(days=30)
                    elif membership_type == "Quarterly":
                        expiry_date = join_date + timedelta(days=90)
                    else:
                        expiry_date = join_date + timedelta(days=365)

                    new_row = pd.DataFrame([{
                        "Full_Name": full_name,
                        "Phone": phone,
                        "Membership_Type": membership_type,
                        "Join_Date": join_date.strftime("%Y-%m-%d"),
                        "Expiry_Date": expiry_date.strftime("%Y-%m-%d"),
                        "Added_By": role
                    }])

                    members_df = pd.concat([members_df, new_row], ignore_index=True)
                    save_data(users_df, members_df)
                    st.success(f"✅ Member '{full_name}' added successfully!")

        # --- Edit/Delete only for Owner ---
        if role == "Owner":
            st.subheader("✏️ Edit / Delete Members")

            selected_member = st.selectbox("Select Member", members_df["Full_Name"].tolist())

            edit_col1, edit_col2 = st.columns(2)
            with edit_col1:
                if st.button("🗑 Delete Member"):
                    members_df = members_df[members_df["Full_Name"] != selected_member]
                    save_data(users_df, members_df)
                    st.warning(f"🗑 Member '{selected_member}' deleted!")

            with edit_col2:
                new_type = st.selectbox("Change Membership Type", ["Monthly", "Quarterly", "Yearly"], key="edit_type")
                if st.button("💾 Update Type"):
                    members_df.loc[members_df["Full_Name"] == selected_member, "Membership_Type"] = new_type
                    st.success(f"🔁 Updated '{selected_member}' to {new_type}")
                    save_data(users_df, members_df)
