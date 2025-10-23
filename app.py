import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

EXCEL_FILE = "members.xlsx"

# --- Load or create the members file safely ---
required_cols = ["Username", "Password", "Role", "Join_Date", "Expiry_Date", "Amount"]

try:
    df = pd.read_excel(EXCEL_FILE)
    for col in required_cols:
        if col not in df.columns:
            if col in ["Join_Date", "Expiry_Date"]:
                df[col] = ""
            elif col == "Amount":
                df[col] = 0
            elif col == "Role":
                df[col] = "Member"
            else:
                df[col] = ""
    df.to_excel(EXCEL_FILE, index=False)
except FileNotFoundError:
    df = pd.DataFrame({
        "Username": ["vineeth", "staff1", "member1"],
        "Password": ["panda@2006", "staff@123", "mem@123"],
        "Role": ["Owner", "Staff", "Member"],
        "Join_Date": [
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
        ],
        "Expiry_Date": [
            (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "",  # staff no expiry
            (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        ],
        "Amount": [0, 0, 0]
    })
    df.to_excel(EXCEL_FILE, index=False)

# --- Login system ---
st.title("🏋️ Gym Management System")

username = st.text_input("Username")
password = st.text_input("Password", type="password")
login_btn = st.button("Login")

if login_btn:
    user = df[(df["Username"] == username) & (df["Password"] == password)]

    if not user.empty:
        role = user.iloc[0]["Role"]
        st.success(f"✅ Login successful! Welcome, {username} ({role})")

        if role == "Owner":
            st.subheader("👑 Owner Dashboard")
            st.dataframe(df[["Username", "Role", "Join_Date", "Expiry_Date", "Amount"]])

            # --- Edit existing users ---
            st.markdown("### ✏️ Edit Member or Staff")
            selected_user = st.selectbox("Select user to edit", df["Username"].unique())
            if selected_user:
                row = df[df["Username"] == selected_user].iloc[0]
                new_role = st.selectbox("Role", ["Member", "Staff", "Owner"], index=["Member", "Staff", "Owner"].index(row["Role"]))
                new_amount = st.number_input("Amount", value=int(row["Amount"]))
                if new_role == "Member":
                    new_expiry = st.date_input("Expiry Date", datetime.strptime(row["Expiry_Date"], "%Y-%m-%d") if row["Expiry_Date"] else datetime.now())
                else:
                    new_expiry = ""

                if st.button("💾 Save Changes"):
                    df.loc[df["Username"] == selected_user, ["Role", "Amount", "Expiry_Date"]] = [new_role, new_amount, new_expiry if new_role == "Member" else ""]
                    df.to_excel(EXCEL_FILE, index=False)
                    st.success("✅ Changes saved successfully!")
                    st.rerun()

            # --- Add new user ---
            st.markdown("### ➕ Add New Member or Staff")
            new_username = st.text_input("New Username")
            new_password = st.text_input("New Password")
            new_role = st.selectbox("New Role", ["Member", "Staff"])
            if st.button("Add User"):
                if new_username and new_password:
                    expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") if new_role == "Member" else ""
                    new_entry = {
                        "Username": new_username,
                        "Password": new_password,
                        "Role": new_role,
                        "Join_Date": datetime.now().strftime("%Y-%m-%d"),
                        "Expiry_Date": expiry,
                        "Amount": 0,
                    }
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                    df.to_excel(EXCEL_FILE, index=False)
                    st.success(f"✅ {new_role} '{new_username}' added successfully!")
                    st.rerun()
                else:
                    st.warning("Please fill all fields.")

        elif role == "Staff":
            st.subheader("🧾 Staff Dashboard")

            st.markdown("### ➕ Add New Member")
            new_username = st.text_input("Member Username")
            new_password = st.text_input("Member Password")
            new_amount = st.number_input("Amount Paid", min_value=0)
            if st.button("Add Member"):
                if new_username and new_password:
                    expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                    new_entry = {
                        "Username": new_username,
                        "Password": new_password,
                        "Role": "Member",
                        "Join_Date": datetime.now().strftime("%Y-%m-%d"),
                        "Expiry_Date": expiry,
                        "Amount": new_amount,
                    }
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                    df.to_excel(EXCEL_FILE, index=False)
                    st.success(f"✅ Member '{new_username}' added successfully!")
                    st.rerun()
                else:
                    st.warning("Please fill all fields.")

            st.markdown("### 💵 Update Member Amount")
            members_only = df[df["Role"] == "Member"]["Username"].tolist()
            member_to_update = st.selectbox("Select Member", members_only)
            new_amount = st.number_input("Enter New Amount", min_value=0)
            if st.button("Update Amount"):
                df.loc[df["Username"] == member_to_update, "Amount"] = new_amount
                df.to_excel(EXCEL_FILE, index=False)
                st.success(f"💰 Amount updated for {member_to_update}")
                st.rerun()

        else:
            st.subheader("💪 Member Dashboard")
            info = user.iloc[0]
            st.write(f"**Join Date:** {info['Join_Date']}")
            st.write(f"**Expiry Date:** {info['Expiry_Date']}")
            st.write(f"**Amount Paid:** ₹{info['Amount']}")

            if info["Expiry_Date"]:
                expiry = datetime.strptime(str(info["Expiry_Date"]), "%Y-%m-%d")
                remaining = (expiry - datetime.now()).days
                if remaining <= 7:
                    st.warning(f"⚠️ Your membership expires in {remaining} days!")
                else:
                    st.success(f"✅ {remaining} days remaining on your membership.")
    else:
        st.error("❌ Invalid username or password!")
