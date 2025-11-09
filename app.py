import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
import pytz
import os

# -----------------------------
# CONFIGURATION
# -----------------------------
EXCEL_FILE = "members.xlsx"
INDIAN_TZ = pytz.timezone("Asia/Kolkata")

USER_CREDENTIALS = {
    "vineeth": {"password": "panda@2006", "role": "Owner"},
    "staff": {"password": "staff@123", "role": "Staff"}
}

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def validate_phone(phone: str) -> bool:
    """Ensure phone has 10+ digits and is numeric."""
    return phone.isdigit() and len(phone) >= 10

def calculate_expiry_date(start_date: datetime, duration_option: str) -> datetime:
    """Calculate expiry date accurately using DateOffset."""
    durations = {"1 Month": 1, "3 Months": 3, "6 Months": 6, "1 Year": 12}
    months = durations.get(duration_option, 1)
    return start_date + DateOffset(months=months)

def load_members():
    """Load member records from Excel safely."""
    dtypes = {"Member_Name": str, "Phone_Number": str, "Duration": str}
    date_cols = ["Join_Date", "Expiry_Date"]
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE, dtype=dtypes, parse_dates=date_cols)
        except Exception as e:
            st.error(f"Error loading file. Starting fresh. ({e})")
            df = pd.DataFrame(columns=list(dtypes.keys()) + date_cols)
    else:
        df = pd.DataFrame(columns=list(dtypes.keys()) + date_cols)
    return df

def save_members(df):
    """Save DataFrame to Excel (overwrite)."""
    df.to_excel(EXCEL_FILE, index=False)

def get_expiring_members(df):
    """Return expiring soon (≤7 days) and expired members."""
    today = datetime.now(INDIAN_TZ).date()
    df["Expiry_Date"] = pd.to_datetime(df["Expiry_Date"], errors="coerce").dt.date

    expired = df[df["Expiry_Date"].notna() & (df["Expiry_Date"] < today)].copy()
    expiring_soon = df[
        df["Expiry_Date"].notna() &
        (df["Expiry_Date"] >= today) &
        ((df["Expiry_Date"] - today).apply(lambda x: x.days) <= 7)
    ].copy()

    return expiring_soon, expired

# -----------------------------
# MEMBER MANAGEMENT
# -----------------------------
def add_member(df):
    st.subheader("➕ Add New Member")
    name = st.text_input("Member Name", key="add_name")
    phone = st.text_input("Phone Number", key="add_phone")
    duration = st.selectbox("Membership Duration", ["1 Month", "3 Months", "6 Months", "1 Year"], key="add_duration")

    if st.button("Add Member", key="submit_add"):
        if not name or not phone:
            st.warning("Please fill all fields.")
            return df
        if not validate_phone(phone):
            st.warning("Phone number must be at least 10 digits and numeric.")
            return df

        now = datetime.now(INDIAN_TZ)
        join_date = now.strftime("%Y-%m-%d %H:%M:%S")
        expiry_date = calculate_expiry_date(now, duration)

        new_entry = pd.DataFrame([{
            "Member_Name": name,
            "Phone_Number": phone,
            "Join_Date": join_date,
            "Expiry_Date": expiry_date.date(),
            "Duration": duration
        }])

        df = pd.concat([df, new_entry], ignore_index=True)
        save_members(df)
        st.success(f"✅ {name} added successfully! Expires on {expiry_date.date()}")
    return df

def edit_member(df):
    st.subheader("✏️ Renew / Edit Member")
    if df.empty:
        st.info("No members found.")
        return df

    df["Display"] = (
        df["Member_Name"] + 
        " (Ph: " + df["Phone_Number"].astype(str) + 
        " | Exp: " + pd.to_datetime(df["Expiry_Date"]).dt.strftime("%Y-%m-%d") + ")"
    )

    selected = st.selectbox("Select Member", df["Display"], key="edit_select")
    row = df[df["Display"] == selected].iloc[0]
    idx = df[df["Display"] == selected].index[0]

    st.markdown(f"**Current Expiry:** `{pd.to_datetime(row['Expiry_Date']).strftime('%Y-%m-%d')}`")
    st.markdown("---")

    new_name = st.text_input("Edit Name", value=row["Member_Name"], key="edit_name")
    new_phone = st.text_input("Edit Phone", value=row["Phone_Number"], key="edit_phone")
    duration_options = ["1 Month", "3 Months", "6 Months", "1 Year"]
    new_duration = st.selectbox("Renew Duration", duration_options,
                                index=duration_options.index(row["Duration"]), key="edit_duration")

    if st.button("Update / Renew", key="submit_edit"):
        if not new_name or not new_phone:
            st.warning("All fields required.")
            return df
        if not validate_phone(new_phone):
            st.warning("Phone number must be numeric & 10+ digits.")
            return df

        now = datetime.now(INDIAN_TZ)
        new_expiry = calculate_expiry_date(now, new_duration)

        df.at[idx, "Member_Name"] = new_name
        df.at[idx, "Phone_Number"] = new_phone
        df.at[idx, "Duration"] = new_duration
        df.at[idx, "Expiry_Date"] = new_expiry.date()

        save_members(df)
        st.success(f"✅ {new_name}'s membership renewed till {new_expiry.date()}")

    df.drop(columns=["Display"], inplace=True, errors="ignore")
    return df

# -----------------------------
# MAIN APP
# -----------------------------
def main():
    st.set_page_config(page_title="Gym Management", layout="wide")
    st.title("🏋️ Gym Membership Management System")

    # --- LOGIN ---
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.role = None

    if not st.session_state.logged_in:
        username = st.text_input("Username").strip().lower()
        password = st.text_input("Password", type="password").strip()

        if st.button("Login"):
            user = USER_CREDENTIALS.get(username)
            if user and user["password"] == password:
                st.session_state.logged_in = True
                st.session_state.role = user["role"]
                st.rerun()
            else:
                st.error("❌ Invalid credentials.")
        return

    st.sidebar.success(f"👤 Logged in as: **{st.session_state.role}**")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- LOAD DATA & REMINDERS ---
    members_df = load_members()
    expiring_soon, expired = get_expiring_members(members_df)

    with st.container(border=True):
        st.markdown("### 🔔 Membership Reminders")

        if not expired.empty:
            st.error("🚨 EXPIRED MEMBERS")
            st.dataframe(expired[["Member_Name", "Phone_Number", "Expiry_Date"]]
                         .sort_values("Expiry_Date"), use_container_width=True, hide_index=True)

        if not expiring_soon.empty:
            st.warning("⚠️ EXPIRING WITHIN 7 DAYS")
            st.dataframe(expiring_soon[["Member_Name", "Phone_Number", "Expiry_Date"]]
                         .sort_values("Expiry_Date"), use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- ADD / EDIT ---
    col1, col2 = st.columns(2)
    with col1:
        members_df = add_member(members_df)
    with col2:
        if st.session_state.role == "Owner":
            members_df = edit_member(members_df)
        else:
            st.info("Only **Owner** can renew or edit.")

    # --- FULL LIST ---
    st.markdown("---")
    st.subheader(f"📋 Members (Active: {len(members_df) - len(expired)} / Total: {len(members_df)})")

    display_df = members_df.copy()
    if "Join_Date" in display_df.columns:
        display_df["Join_Date"] = pd.to_datetime(display_df["Join_Date"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M").fillna("")
    if "Expiry_Date" in display_df.columns:
        display_df["Expiry_Date"] = pd.to_datetime(display_df["Expiry_Date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")

    st.dataframe(display_df, use_container_width=True, hide_index=True)

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    main()
