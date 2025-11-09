import streamlit as st
import pandas as pd
from datetime import datetime, time
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
    """Simple check for 10+ digits and numeric content."""
    return phone.isdigit() and len(phone) >= 10

def calculate_expiry_date(start_date: datetime, duration_option: str) -> datetime:
    """Accurately calculate expiry date based on duration using DateOffset."""
    if duration_option == "1 Month":
        return start_date + DateOffset(months=1)
    elif duration_option == "3 Months":
        return start_date + DateOffset(months=3)
    elif duration_option == "6 Months":
        return start_date + DateOffset(months=6)
    else: # 1 Year
        return start_date + DateOffset(years=1)

def load_members():
    """Load members from Excel or create empty DataFrame."""
    dtypes = {"Member_Name": str, "Phone_Number": str, "Duration": str}
    date_cols = ["Join_Date", "Expiry_Date"]
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE, dtype=dtypes, parse_dates=date_cols)
        except Exception as e:
            st.error(f"Error loading members file. Starting new. ({e})")
            df = pd.DataFrame(columns=list(dtypes.keys()) + date_cols)
    else:
        df = pd.DataFrame(columns=list(dtypes.keys()) + date_cols)
    return df

def save_members(df):
    """Save DataFrame to Excel safely."""
    df.to_excel(EXCEL_FILE, index=False)

def get_expiring_members(df):
    """Get expiring soon (≤7 days) and expired members."""
    today = datetime.now(INDIAN_TZ).date()
    df["Expiry_Date"] = pd.to_datetime(df["Expiry_Date"], errors="coerce").dt.date

    # Members whose expiration date is in the past
    expired_mask = (df["Expiry_Date"].notna()) & (df["Expiry_Date"] < today)
    
    # Members expiring today or in the next 7 days
    expiring_mask = (
        (df["Expiry_Date"].notna()) &
        (df["Expiry_Date"] >= today) &
        ((df["Expiry_Date"] - today).apply(lambda x: x.days) <= 7)
    )

    expired = df[expired_mask].copy()
    expiring_soon = df[expiring_mask].copy()
    return expiring_soon, expired

# -----------------------------
# MEMBER MANAGEMENT
# -----------------------------
def add_member(df):
    st.subheader("➕ Add New Member")
    name = st.text_input("Member Name", key="add_name")
    phone = st.text_input("Phone Number", key="add_phone")
    duration = st.selectbox("Membership Duration", ["1 Month", "3 Months", "6 Months", "1 Year"], key="add_duration")
    
    # --- NEW: Date Input for Join Date ---
    join_date_input = st.date_input("Join Date", value=datetime.now(INDIAN_TZ).date(), key="add_join_date")

    if st.button("Add Member", key="submit_add"):
        if not name or not phone:
            st.warning("Please fill all fields.")
            return df
        if not validate_phone(phone):
            st.warning("Phone number must be at least 10 digits and numeric.")
            return df

        # Convert date input to timezone-aware datetime for calculation
        join_datetime = INDIAN_TZ.localize(datetime.combine(join_date_input, time(0,0,0))) 
        
        join_date_str = join_datetime.strftime("%Y-%m-%d %H:%M:%S")
        expiry_date = calculate_expiry_date(join_datetime, duration) # Calculate expiry based on the chosen join date

        new_entry = pd.DataFrame([{
            "Member_Name": name,
            "Phone_Number": phone,
            "Join_Date": join_date_str, 
            "Expiry_Date": expiry_date.date(),
            "Duration": duration
        }])

        df = pd.concat([df, new_entry], ignore_index=True)
        save_members(df)
        st.success(f"✅ **{name}** added! Joined: **{join_date_input}**, Expires: **{expiry_date.date()}**")
    return df

def edit_member(df):
    st.subheader("✏️ Renew / Edit Member")
    if df.empty:
        st.info("No members to edit.")
        return df

    # Create enhanced Display column for clear identification
    df["Display"] = (
        df["Member_Name"] + 
        " (Ph: " + df["Phone_Number"].astype(str) + 
        " | Exp: " + pd.to_datetime(df["Expiry_Date"]).dt.strftime("%Y-%m-%d") + ")"
    )

    selected = st.selectbox("Select Member", df["Display"], key="edit_select")
    row = df[df["Display"] == selected].iloc[0]
    idx = df[df["Display"] == selected].index[0]

    st.markdown(f"**Current Expiry:** **`{pd.to_datetime(row['Expiry_Date']).strftime('%Y-%m-%d')}`**")
    st.markdown("---")

    new_name = st.text_input("Edit Name", value=row["Member_Name"], key="edit_name")
    new_phone = st.text_input("Edit Phone", value=row["Phone_Number"], key="edit_phone")

    current_duration_index = ["1 Month", "3 Months", "6 Months", "1 Year"].index(row["Duration"])
    new_duration = st.selectbox("Renew Duration", ["1 Month", "3 Months", "6 Months", "1 Year"],
                                 index=current_duration_index, key="edit_duration")

    # --- NEW: Date Input for Renewal Date ---
    renewal_date_input = st.date_input("Renewal/Update Date (Membership starts from this date)", 
                                       value=datetime.now(INDIAN_TZ).date(), 
                                       key="edit_renewal_date")

    if st.button("Update / Renew", key="submit_edit"):
        if not new_name or not new_phone:
            st.warning("All fields required.")
            return df
        if not validate_phone(new_phone):
            st.warning("Phone number must be at least 10 digits and numeric.")
            return df

        # Convert date input to timezone-aware datetime for calculation
        renewal_datetime = INDIAN_TZ.localize(datetime.combine(renewal_date_input, time(0,0,0)))
        
        # Calculate new expiry date based on the chosen renewal date
        expiry_date = calculate_expiry_date(renewal_datetime, new_duration)

        # Update details
        df.at[idx, "Member_Name"] = new_name
        df.at[idx, "Phone_Number"] = new_phone
        df.at[idx, "Duration"] = new_duration
        df.at[idx, "Expiry_Date"] = expiry_date.date()

        save_members(df)
        st.success(f"✅ **{new_name}'s** membership renewed on **{renewal_date_input}** till **{expiry_date.date()}**")

    # Drop the temporary display column
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
                st.error("❌ Invalid credentials. Please check username or password.")
        return

    # --- SIDEBAR & LOGOUT ---
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
            st.error("🚨 **EXPIRED MEMBERS** - Action Required!")
            st.dataframe(
                expired[["Member_Name", "Phone_Number", "Expiry_Date"]].sort_values("Expiry_Date"), 
                use_container_width=True, 
                hide_index=True
            )

        if not expiring_soon.empty:
            st.warning("⚠️ **Expiring Within 7 Days** - Send Reminder!")
            st.dataframe(
                expiring_soon[["Member_Name", "Phone_Number", "Expiry_Date"]].sort_values("Expiry_Date"), 
                use_container_width=True, 
                hide_index=True
            )

    st.markdown("---")

    # --- ADD / EDIT ---
    col1, col2 = st.columns(2)
    with col1:
        members_df = add_member(members_df)
    with col2:
        if st.session_state.role == "Owner":
            members_df = edit_member(members_df)
        else:
            st.info("Edit/Renewal available only to the **Owner** role.")

    # --- FULL LIST ---
    st.markdown("---")
    st.subheader(f"📋 Member List (Active: **{len(members_df) - len(expired)}** / Total: {len(members_df)})")

    # Prepare DataFrame for clean display formatting
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
