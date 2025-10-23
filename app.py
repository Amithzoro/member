import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# ==================================================
# CONFIGURATION
# ==================================================
EXCEL_FILE = "members.xlsx"

# ==================================================
# LOAD OR CREATE DATA
# ==================================================
try:
    df = pd.read_excel(EXCEL_FILE)
except FileNotFoundError:
    df = pd.DataFrame({
        "Username": ["vineeth", "staff1", "member1"],
        "Password": ["panda@2006", "staff@123", "mem@123"],
        "Role": ["Owner", "Staff", "Member"],
        "Join_Date": [datetime.now().strftime("%Y-%m-%d")]*3,
        "Expiry_Date": [
            (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        ]
    })
    df.to_excel(EXCEL_FILE, index=False)

# ==================================================
# LOGIN SYSTEM
# ==================================================
st.title("🏋️ GYM MEMBERSHIP & STAFF SYSTEM")

# Keep login state
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

# ---------------- LOGIN PAGE ----------------
if st.session_state.logged_in_user is None:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = df[
            (df["Username"].astype(str).str.lower() == username.lower()) &
            (df["Password"].astype(str) == password)
        ]

        if not user.empty:
            st.session_state.logged_in_user = user.iloc[0].to_dict()
            st.success(f"✅ Login successful! Welcome, {username}")
            st.rerun()
        else:
            st.error("❌ Invalid username or password.")

# ---------------- MAIN DASHBOARD ----------------
else:
    user = st.session_state.logged_in_user
    st.sidebar.success(f"👋 Logged in as: {user['Username']} ({user['Role']})")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in_user = None
        st.rerun()

    role = user.get("Role", "Member")

    # ==================================================
    # OWNER DASHBOARD
    # ==================================================
    if role.lower() == "owner":
        st.header("👑 Owner Dashboard")
        st.dataframe(df[["Username", "Role", "Join_Date", "Expiry_Date"]])

        st.subheader("➕ Add New User")
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        new_role = st.selectbox("Select Role", ["Member", "Staff"])

        if st.button("Add User"):
            if new_username and new_password:
                if new_username.lower() in df["Username"].astype(str).str.lower().values:
                    st.warning("⚠️ Username already exists.")
                else:
                    new_entry = {
                        "Username": new_username,
                        "Password": new_password,
                        "Role": new_role,
                        "Join_Date": datetime.now().strftime("%Y-%m-%d"),
                        "Expiry_Date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                    }
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                    df.to_excel(EXCEL_FILE, index=False)
                    st.success(f"✅ {new_role} '{new_username}' added successfully!")
                    st.rerun()
            else:
                st.warning("⚠️ Please enter all fields.")

        # Show soon-to-expire members
        st.subheader("⏳ Memberships Expiring Soon")
        df["Expiry_Date"] = pd.to_datetime(df["Expiry_Date"], errors='coerce')
        soon_expiring = df[(df["Role"] == "Member") & (df["Expiry_Date"] <= datetime.now() + timedelta(days=7))]
        if not soon_expiring.empty:
            st.warning("⚠️ The following memberships will expire soon:")
            st.dataframe(soon_expiring[["Username", "Expiry_Date"]])
        else:
            st.info("✅ No memberships expiring soon.")

    # ==================================================
    # STAFF DASHBOARD
    # ==================================================
    elif role.lower() == "staff":
        st.header("👨‍🔧 Staff Dashboard")

        # Staff can view all members, not owners
        members_df = df[df["Role"] == "Member"]
        st.dataframe(members_df[["Username", "Join_Date", "Expiry_Date"]])

        st.subheader("➕ Add New Member")
        new_username = st.text_input("Member Username")
        new_password = st.text_input("Member Password", type="password")

        if st.button("Add Member"):
            if new_username and new_password:
                if new_username.lower() in df["Username"].astype(str).str.lower().values:
                    st.warning("⚠️ Username already exists.")
                else:
                    new_entry = {
                        "Username": new_username,
                        "Password": new_password,
                        "Role": "Member",
                        "Join_Date": datetime.now().strftime("%Y-%m-%d"),
                        "Expiry_Date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                    }
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                    df.to_excel(EXCEL_FILE, index=False)
                    st.success(f"✅ Member '{new_username}' added successfully!")
                    st.rerun()
            else:
                st.warning("⚠️ Please fill in both fields.")

        # Warn about expiry
        st.subheader("⚠️ Expiring Members")
        df["Expiry_Date"] = pd.to_datetime(df["Expiry_Date"], errors='coerce')
        soon_expiring = members_df[members_df["Expiry_Date"] <= datetime.now() + timedelta(days=7)]
        if not soon_expiring.empty:
            st.warning("These members will expire soon:")
            st.dataframe(soon_expiring[["Username", "Expiry_Date"]])
        else:
            st.info("✅ No expiring memberships this week.")

    # ==================================================
    # MEMBER DASHBOARD
    # ==================================================
    else:
        st.header(f"💪 Welcome, {user['Username']}!")
        st.write(f"**Join Date:** {user['Join_Date']}")
        st.write(f"**Expiry Date:** {user['Expiry_Date']}")

        expiry = pd.to_datetime(user["Expiry_Date"], errors='coerce')
        days_left = (expiry - datetime.now()).days if pd.notna(expiry) else 0

        if days_left <= 0:
            st.error("❌ Your membership has expired. Please renew soon.")
        elif days_left <= 7:
            st.warning(f"⚠️ Your membership expires in {days_left} days.")
        else:
            st.success(f"✅ Your membership is active for {days_left} more days.")
