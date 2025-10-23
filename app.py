import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

EXCEL_FILE = "members.xlsx"

# --- Load data ---
try:
    df = pd.read_excel(EXCEL_FILE)
except FileNotFoundError:
    df = pd.DataFrame({
        "Username": ["vineeth"],
        "Password": ["panda@2006"],
        "Role": ["Owner"],
        "Join_Date": [datetime.now().strftime("%Y-%m-%d")],
        "Expiry_Date": [(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")]
    })
    df.to_excel(EXCEL_FILE, index=False)

# --- Login section ---
st.title("🏋️ Gym Membership System")

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

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
            st.experimental_rerun()
        else:
            st.error("❌ Invalid username or password.")
else:
    user = st.session_state.logged_in_user
    st.sidebar.success(f"Logged in as {user['Username']} ({user['Role']})")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in_user = None
        st.experimental_rerun()

    role = user.get("Role", "Member")

    # --- OWNER VIEW ---
    if role.lower() == "owner":
        st.header("📋 Member Management")

        st.dataframe(df[["Username", "Role", "Join_Date", "Expiry_Date"]])

        st.subheader("➕ Add New Member")
        new_username = st.text_input("New member username")
        new_password = st.text_input("New member password", type="password")

        if st.button("Add Member"):
            if new_username and new_password:
                new_entry = {
                    "Username": new_username,
                    "Password": new_password,
                    "Role": "Member",
                    "Join_Date": datetime.now().strftime("%Y-%m-%d"),
                    "Expiry_Date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                }
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                df.to_excel(EXCEL_FILE, index=False)
                st.success(f"✅ Member '{new_username}' added!")
                st.experimental_rerun()
            else:
                st.warning("Please enter both username and password.")
    
    # --- MEMBER VIEW ---
    else:
        st.header(f"👋 Welcome {user['Username']}!")
        st.write(f"**Join Date:** {user['Join_Date']}")
        st.write(f"**Expiry Date:** {user['Expiry_Date']}")

        days_left = (pd.to_datetime(user["Expiry_Date"]) - datetime.now()).days
        if days_left <= 0:
            st.error("❌ Your membership has expired. Please renew.")
        elif days_left <= 7:
            st.warning(f"⚠️ Your membership expires in {days_left} days.")
        else:
            st.success(f"✅ Your membership is active for {days_left} more days.")
