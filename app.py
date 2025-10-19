import streamlit as st
import pandas as pd
import datetime
import pytz
import json
import hashlib
import os

# --- Configuration & Constants ---
OWNER_USERNAME = "vineeth"
OWNER_PASSWORD_HASH = hashlib.sha256("panda@2006".encode()).hexdigest()
DB_FILE = "membership_data.xlsx"
CRED_FILE = "staff_credentials.json"
IST = pytz.timezone('Asia/Kolkata')

# --- Utility Functions ---

def hash_password(password):
    """Hashes a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def get_ist_time():
    """Returns the current IST datetime."""
    return datetime.datetime.now(IST)

# --- Staff Credentials Persistence ---

def load_staff_credentials():
    if os.path.exists(CRED_FILE):
        try:
            with open(CRED_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error("Error loading staff credentials. Resetting to empty.")
            return {}
    return {}

def save_staff_credentials(creds):
    with open(CRED_FILE, 'w') as f:
        json.dump(creds, f, indent=4)

# --- Database Persistence ---

def load_database():
    try:
        member_df = pd.read_excel(DB_FILE, sheet_name='Members')
        if not member_df.empty:
            member_df['Join Date'] = pd.to_datetime(member_df['Join Date']).dt.date
            member_df['Expiry Date'] = pd.to_datetime(member_df['Expiry Date']).dt.date
            member_df['ID'] = member_df['ID'].astype(int)
        log_df = pd.read_excel(DB_FILE, sheet_name='CheckIns')
        if not log_df.empty:
            log_df['CheckIn Time_dt'] = pd.to_datetime(log_df['CheckIn Time'].str.replace(' IST',''))
        return member_df, log_df
    except FileNotFoundError:
        member_df = pd.DataFrame(columns=['ID', 'Name', 'Phone', 'Membership Type', 'Join Date', 'Expiry Date'])
        log_df = pd.DataFrame(columns=['ID', 'Name', 'CheckIn Time', 'Staff User'])
        return member_df, log_df
    except ValueError:
        st.error("Database file is corrupted or sheets missing. Starting fresh.")
        member_df = pd.DataFrame(columns=['ID', 'Name', 'Phone', 'Membership Type', 'Join Date', 'Expiry Date'])
        log_df = pd.DataFrame(columns=['ID', 'Name', 'CheckIn Time', 'Staff User'])
        return member_df, log_df

def save_database(member_df, log_df):
    try:
        with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
            member_df.to_excel(writer, sheet_name='Members', index=False)
            log_df.drop(columns=['CheckIn Time_dt'], errors='ignore').to_excel(writer, sheet_name='CheckIns', index=False)
    except Exception as e:
        st.error(f"Error saving database: {e}")

# --- Core Logic ---

def record_entry(member_id, member_df, log_df, staff_user):
    member = member_df[member_df['ID'] == member_id]
    if member.empty:
        st.error(f"Member ID {member_id} not found.")
        return False, log_df
    member_name = member['Name'].iloc[0]
    expiry_date = member['Expiry Date'].iloc[0]
    today = get_ist_time().date()
    if expiry_date < today:
        st.error(f"Membership expired for {member_name} (Expiry: {expiry_date})")
        return False, log_df
    checkin_time = get_ist_time().strftime('%Y-%m-%d %H:%M:%S IST')
    new_entry = pd.DataFrame([{
        'ID': member_id,
        'Name': member_name,
        'CheckIn Time': checkin_time,
        'Staff User': staff_user,
        'CheckIn Time_dt': pd.to_datetime(get_ist_time())
    }])
    log_df = pd.concat([log_df, new_entry], ignore_index=True)
    st.success(f"✅ Entry Recorded: {member_name} at {checkin_time}")
    days_until_expiry = (expiry_date - today).days
    if days_until_expiry <= 7:
        st.warning(f"⚠️ Reminder: {member_name}'s membership expires in {days_until_expiry} days.")
    return True, log_df

# --- Staff Registration/Login ---

def staff_registration():
    st.subheader("Staff Registration")
    new_username = st.text_input("New Staff Username")
    new_password = st.text_input("New Staff Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    if st.button("Register Staff"):
        if not new_username or not new_password:
            st.error("Fields cannot be empty.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        elif new_username == OWNER_USERNAME:
            st.error("Reserved username.")
        else:
            creds = load_staff_credentials()
            if new_username in creds:
                st.error("Username exists.")
            else:
                creds[new_username] = hash_password(new_password)
                save_staff_credentials(creds)
                st.success(f"Staff '{new_username}' registered successfully.")

def login_page():
    st.image("https://placehold.co/600x150/1F3D78/ffffff?text=GYM+MEMBERSHIP+APP", use_column_width=True)
    st.title("Member Check-In & Management")
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == OWNER_USERNAME and hash_password(password) == OWNER_PASSWORD_HASH:
            st.session_state['logged_in'] = True
            st.session_state['user'] = OWNER_USERNAME
            st.session_state['role'] = 'owner'
            st.rerun()
        else:
            creds = load_staff_credentials()
            if username in creds and hash_password(password) == creds[username]:
                st.session_state['logged_in'] = True
                st.session_state['user'] = username
                st.session_state['role'] = 'staff'
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.markdown("---")
    st.info("Staff: Register if you haven't yet.")
    if st.button("Register New Staff Account"):
        st.session_state['show_register'] = True
    if st.session_state.get('show_register'):
        staff_registration()

# --- Sidebar ---

def sidebar_menu():
    st.sidebar.title("Welcome")
    st.sidebar.markdown(f"**User:** {st.session_state.get('user', 'Guest')}")
    st.sidebar.markdown(f"**Role:** _{st.session_state.get('role', 'N/A')}_")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
    st.sidebar.markdown("---")
    st.sidebar.header("Navigation")

# --- Pages ---

def page_check_in(member_df, log_df):
    st.header("Member Check-In")
    st.markdown(f"Current IST: `{get_ist_time().strftime('%Y-%m-%d %H:%M:%S IST')}`")
    member_id_input = st.number_input("Enter Member ID:", min_value=1, step=1, key="check_in_id")
    if st.button("Record Entry", use_column_width=True):
        if member_id_input:
            success, new_log_df = record_entry(member_id_input, member_df, log_df, st.session_state['user'])
            if success:
                st.session_state['log_df'] = new_log_df
                save_database(member_df, new_log_df)
    st.markdown("---")
    st.subheader("Recent Check-Ins")
    if not log_df.empty:
        df_disp = log_df.sort_values('CheckIn Time_dt', ascending=False).head(10)
        st.dataframe(df_disp[['ID','Name','CheckIn Time','Staff User']], use_container_width=True, hide_index=True)
    else:
        st.info("No check-in entries yet.")

def add_member_form(member_df):
    with st.expander("➕ Add New Member"):
        with st.form("add_member_form", clear_on_submit=True):
            next_id = int(member_df['ID'].max() + 1) if not member_df.empty else 1
            st.text_input("Member ID (Auto-Generated)", value=str(next_id), disabled=True)
            name = st.text_input("Full Name *")
            phone = st.text_input("Phone Number *")
            m_type = st.selectbox("Membership Type *", ['Monthly', 'Quarterly', 'Annual', 'Trial'])
            join_date = st.date_input("Join Date *", value=get_ist_time().date())
            expiry_date = st.date_input("Expiry Date *", value=join_date + datetime.timedelta(days=30))
            submitted = st.form_submit_button("Register Member")
            if submitted:
                if not name or not phone:
                    st.error("Fill all required fields (*).")
                elif expiry_date <= join_date:
                    st.error("Expiry must be after Join Date.")
                else:
                    new_member = pd.DataFrame([{
                        'ID': next_id,
                        'Name': name,
                        'Phone': phone,
                        'Membership Type': m_type,
                        'Join Date': join_date,
                        'Expiry Date': expiry_date
                    }])
                    new_member['ID'] = new_member['ID'].astype(int)
                    member_df = pd.concat([member_df, new_member], ignore_index=True)
                    st.session_state['member_df'] = member_df
                    st.success(f"Member **{name}** registered with ID: **{next_id}**")
                    st.rerun()
    return member_df

def page_member_management(member_df):
    st.header("Member Management")
    if st.session_state['role'] == 'owner':
        member_df = add_member_form(member_df)
    else:
        st.info("Staff can only view members.")
    st.markdown("---")
    st.subheader("Active Members List")
    if not member_df.empty:
        st.dataframe(member_df.sort_values('ID'), use_container_width=True, hide_index=True)
    else:
        st.info("No members registered yet.")
    return member_df

def page_reminders(member_df):
    st.header("Membership Reminders")
    if st.session_state['role'] != 'owner':
        st.warning("You do not have permission to view reminders.")
        return
    today = get_ist_time().date()
    df_temp = member_df.copy()
    df_temp['Days Until Expiry'] = (df_temp['Expiry Date'] - today).apply(lambda x: x.days)
    expiring_soon = df_temp[(df_temp['Days Until Expiry'] <= 30) & (df_temp['Days Until Expiry'] >= 0)]
    expired = df_temp[df_temp['Days Until Expiry'] < 0]
    st.subheader("🚨 Expired Memberships")
    if not expired.empty:
        st.dataframe(expired.style.applymap(lambda x: 'color: red', subset=['Expiry Date']), use_container_width=True)
    else:
        st.info("🎉 No expired memberships!")
    st.subheader("⏳ Expiring Within 30 Days")
    if not expiring_soon.empty:
        st.dataframe(expiring_soon.sort_values('Days Until Expiry'), use_container_width=True)
    else:
        st.info("Everyone is good for at least 30 days!")

# --- Main App ---

def main_app():
    sidebar_menu()
    if 'member_df' not in st.session_state or 'log_df' not in st.session_state:
        st.session_state['member_df'], st.session_state['log_df'] = load_database()
    member_df = st.session_state['member_df']
    log_df = st.session_state['log_df']
    page_options = {"Check-In / Entry": page_check_in, "Member Management": page_member_management}
    if st.session_state['role'] == 'owner':
        page_options["Membership Reminders"] = page_reminders
    selected_page = st.sidebar.radio("Go to", list(page_options.keys()))
    st.title(selected_page)
    st.markdown("---")
    if selected_page == "Check-In / Entry":
        page_options[selected_page](member_df, log_df)
    elif selected_page == "Member Management":
        st.session_state['member_df'] = page_options[selected_page](member_df)
        save_database(st.session_state['member_df'], st.session_state['log_df'])
    elif selected_page == "Membership Reminders":
        page_options[selected_page](member_df)

# --- App Execution ---

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'show_register' not in st.session_state:
        st.session_state['show_register'] = False
    if not os.path.exists(CRED_FILE):
        save_staff_credentials({})
    if st.session_state['logged_in']:
        main_app()
    else:
        hash_password("panda@2006")
        login_page()
