import streamlit as st
import pandas as pd
from datetime import datetime

# Excel file name (you can change this)
EXCEL_FILE = "members.xlsx"

# --- Load or create Excel file ---
try:
    df = pd.read_excel(EXCEL_FILE)
except FileNotFoundError:
    # If file not found, create a sample one with your login
    df = pd.DataFrame({
        "Username": ["vineeth"],
        "Password": ["panda@2006"],
        "Role": ["Owner"]  # optional: Owner / Member
    })
    df.to_excel(EXCEL_FILE, index=False)

# --- Login Section ---
st.title("🏋️ Gym Membership System Login")

st.markdown("Enter your username and password to continue.")
username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if username.strip() == "" or password.strip() == "":
        st.warning("⚠️ Please enter both username and password.")
    else:
        # Check credentials in Excel
        user = df[
            (df["Username"].astype(str).str.lower() == username.lower()) &
            (df["Password"].astype(str) == password)
        ]

        if not user.empty:
            role = user.iloc[0].get("Role", "Member")
            st.success(f"✅ Login successful! Welcome, {username} ({role})")

            # Optional: record login time
            login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.write(f"🕒 Logged in at: {login_time}")
        else:
            st.error("❌ Invalid username or password. Please try again.")
