import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

EXCEL_FILE = "members.xlsx"

# --- Load or create the members file safely ---
required_cols = ["Username", "Password", "Role", "Join_Date", "Expiry_Date"]

try:
    df = pd.read_excel(EXCEL_FILE)

    # Add missing columns automatically
    for col in required_cols:
        if col not in df.columns:
            if col in ["Join_Date", "Expiry_Date"]:
                df[col] = datetime.now().strftime("%Y-%m-%d")
            elif col == "Role":
                df[col] = "Member"
            else:
                df[col] = ""
    df.to_excel(EXCEL_FILE, index=False)

except FileNotFoundError:
    # Create a fresh file with default accounts
    df = pd.DataFrame({
        "Username": ["vineeth", "staff1", "member1"],
        "Password": ["panda@2006", "staff@123", "mem@123"],
        "Role": ["Owner", "Staff", "Member"],
        "Join_Date": [datetime.now().strftime("%Y-%m-%d")] * 3,
        "Expiry_Date": [
            (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        ]
    })
    df.to_excel(EXCEL_FILE, index=False)

# --- Login system ---
st.title("🏋️ Gym Membership System")

username = st.text_input("Username")
password = st.text_input("Password", type="password")
login_btn = st.button("Login")

if login_btn:
    user = df[(df["Username"] == username) & (df["Password"] == password)]

    if not user.empty:
        role = user.iloc[0]["Role"]
        st.success(f"✅ Login successful! Welcome, {username} ({role})")

        login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.info(f"🕒 Logged in at: {login_time}")

        # --- Owner Section ---
        if role == "Owner":
            st.subheader("👑 Owner Dashboard")
            st.dataframe(df[["Username", "Role", "Join_Date", "Expiry_Date"]])

            st.markdown("### ➕ Add New Member or Staff")
            new_username = st.text_input("New Username")
            new_password = st.text_input("New Password")
            new_role = st.selectbox("Role", ["Member", "Staff"])

            if st.button("Add User"):
                if new_username and new_password:
                    new_entry = {
                        "Username": new_username,
                        "Password": new_password,
                        "Role": new_role,
                        "Join_Date": datetime.now().strftime("%Y-%m-%d"),
                        "Expiry_Date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                    }
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                    df.to_excel(EXCEL_FILE, index=False)
                    st.success(f"✅ {new_role} '{new_username}' added successfully!")
                    st.rerun()
                else:
                    st.warning("Please enter both username and password.")

        # --- Staff Section ---
        elif role == "Staff":
            st.subheader("🧾 Staff Dashboard")
            st.dataframe(df[["Username", "Role", "Join_Date", "Expiry_Date"]])

        # --- Member Section ---
        else:
            st.subheader("💪 Member Dashboard")
            info = user.iloc[0]
            st.write(f"**Join Date:** {info['Join_Date']}")
            st.write(f"**Expiry Date:** {info['Expiry_Date']}")

            expiry = datetime.strptime(str(info["Expiry_Date"]), "%Y-%m-%d")
            remaining_days = (expiry - datetime.now()).days
            if remaining_days <= 7:
                st.warning(f"⚠️ Your membership expires in {remaining_days} days!")
            else:
                st.success(f"✅ {remaining_days} days remaining on your membership.")

    else:
        st.error("❌ Invalid username or password!")
