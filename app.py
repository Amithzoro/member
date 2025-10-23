import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# ✅ Safe writable path for Streamlit Cloud
EXCEL_FILE = "/mount/data/members.xlsx"
os.makedirs("/mount/data", exist_ok=True)

# --- Required columns ---
required_cols = ["Member_Name", "Join_Date", "Expiry_Date", "Amount"]

# --- Load or create Excel file ---
if os.path.exists(EXCEL_FILE):
    members_df = pd.read_excel(EXCEL_FILE)
    for col in required_cols:
        if col not in members_df.columns:
            members_df[col] = ""
else:
    members_df = pd.DataFrame(columns=required_cols)
    members_df.to_excel(EXCEL_FILE, index=False)

# --- Login credentials ---
USERS = {
    "vineeth": {"password": "panda@2006", "role": "Owner"},
    "staff1": {"password": "staff@123", "role": "Staff"},
}

# --- Session setup ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None

# --- Login Page ---
st.title("🏋️ Gym Membership Management System")

if not st.session_state.logged_in:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.role = USERS[username]["role"]
            st.session_state.username = username
            st.success(f"✅ Welcome, {username}! You are logged in as {st.session_state.role}.")
            st.rerun()
        else:
            st.error("❌ Invalid username or password!")

else:
    role = st.session_state.role
    st.sidebar.success(f"Logged in as: {role}")
    st.sidebar.button("🚪 Logout", on_click=lambda: [st.session_state.clear(), st.rerun()])

    # --- Expiry reminder ---
    if not members_df.empty and "Expiry_Date" in members_df.columns:
        try:
            members_df["Expiry_Date"] = pd.to_datetime(members_df["Expiry_Date"], errors="coerce")
            soon_expiring = members_df[
                (members_df["Expiry_Date"].notnull()) &
                (members_df["Expiry_Date"] - pd.Timestamp.now() <= pd.Timedelta(days=7))
            ]
            if not soon_expiring.empty:
                st.warning("⚠️ Members expiring within 7 days:")
                st.dataframe(soon_expiring[["Member_Name", "Expiry_Date", "Amount"]])
        except Exception as e:
            st.info("ℹ️ Some expiry dates may be invalid or missing.")

    # --- Dashboard ---
    st.header(f"{role} Dashboard")

    # --- View Members ---
    st.subheader("👥 Member List")
    if members_df.empty:
        st.info("No members found yet.")
    else:
        st.dataframe(members_df)

    # --- Add Member (Owner & Staff) ---
    st.subheader("➕ Add New Member")
    member_name = st.text_input("Member Name")
    amount = st.number_input("Amount Paid", min_value=0)
    expiry_date = st.date_input("Expiry Date", value=datetime.now() + timedelta(days=30))

    if st.button("Add Member"):
        if member_name:
            new_row = {
                "Member_Name": member_name,
                "Join_Date": datetime.now().strftime("%Y-%m-%d"),
                "Expiry_Date": expiry_date.strftime("%Y-%m-%d"),
                "Amount": amount,
            }
            members_df = pd.concat([members_df, pd.DataFrame([new_row])], ignore_index=True)
            members_df.to_excel(EXCEL_FILE, index=False)
            st.success(f"✅ Member '{member_name}' added successfully!")
            st.rerun()
        else:
            st.warning("⚠️ Please enter a member name.")

    # --- Edit/Delete Members (Owner Only) ---
    if role == "Owner":
        st.subheader("✏️ Edit or Delete Member")
        if not members_df.empty:
            selected_member = st.selectbox("Select Member", members_df["Member_Name"])
            row = members_df[members_df["Member_Name"] == selected_member].iloc[0]

            new_name = st.text_input("Edit Name", row["Member_Name"])
            new_amount = st.number_input("Edit Amount", value=float(row["Amount"]))
            new_expiry = st.date_input(
                "Edit Expiry Date",
                row["Expiry_Date"] if not pd.isna(row["Expiry_Date"]) else datetime.now() + timedelta(days=30)
            )

            if st.button("💾 Save Changes"):
                members_df.loc[members_df["Member_Name"] == selected_member, ["Member_Name", "Amount", "Expiry_Date"]] = [
                    new_name,
                    new_amount,
                    new_expiry.strftime("%Y-%m-%d"),
                ]
                members_df.to_excel(EXCEL_FILE, index=False)
                st.success(f"✅ Updated '{selected_member}' successfully!")
                st.rerun()

            if st.button("🗑 Delete Member"):
                members_df = members_df[members_df["Member_Name"] != selected_member]
                members_df.to_excel(EXCEL_FILE, index=False)
                st.warning(f"❌ Deleted member '{selected_member}'")
                st.rerun()

    # --- Staff can update amount only ---
    if role == "Staff":
        st.subheader("💰 Update Member Amount")
        if not members_df.empty:
            selected_member = st.selectbox("Select Member to Update", members_df["Member_Name"])
            new_amount = st.number_input("Enter New Amount", min_value=0)
            if st.button("Update Amount"):
                members_df.loc[members_df["Member_Name"] == selected_member, "Amount"] = new_amount
                members_df.to_excel(EXCEL_FILE, index=False)
                st.success(f"✅ Updated amount for {selected_member}")
                st.rerun()
