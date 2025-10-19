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

# --- Utility Functions for Hashing and Time ---

def hash_password(password):
    """Hashes a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def get_ist_time():
    """Returns the current time in IST (Indian Standard Time)."""
    return datetime.datetime.now(IST)

# --- Persistence Functions (Staff Credentials) ---

def load_staff_credentials():
    """Loads staff credentials from JSON file."""
    if os.path.exists(CRED_FILE):
        try:
            with open(CRED_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error("Error loading staff credentials file. Initializing an empty dictionary.")
            return {}
    return {}

def save_staff_credentials(creds):
    """Saves staff credentials to JSON file."""
    with open(CRED_FILE, 'w') as f:
        json.dump(creds, f, indent=4)

# --- Persistence Functions (Membership & Log Data) ---

def load_database():
    """Loads member data and check-in logs from Excel."""
    try:
        # Load the Members sheet
        member_df = pd.read_excel(DB_FILE, sheet_name='Members')
        member_df['Expiry Date'] = pd.to_datetime(member_df['Expiry Date']).dt.date
        
        # Load the CheckIns sheet
        log_df = pd.read_excel(DB_FILE, sheet_name='CheckIns')
        
        return member_df, log_df
    except FileNotFoundError:
        # Initialize new DataFrames if file doesn't exist
        member_df = pd.DataFrame(columns=['ID', 'Name', 'Phone', 'Membership Type', 'Join Date', 'Expiry Date'])
        member_df['ID'] = member_df['ID'].astype(int)
        member_df['Join Date'] = pd.to_datetime(member_df['Join Date']).dt.date
        member_df['Expiry Date'] = pd.to_datetime(member_df['Expiry Date']).dt.date
        
        log_df = pd.DataFrame(columns=['ID', 'Name', 'CheckIn Time', 'Staff User'])
        return member_df, log_df
    except ValueError:
        st.error("Error reading one or more sheets from the database file. Please check the structure of 'membership_data.xlsx'.")
        # Initialize new if error occurs
        member_df = pd.DataFrame(columns=['ID', 'Name', 'Phone', 'Membership Type', 'Join Date', 'Expiry Date'])
        log_df = pd.DataFrame(columns=['ID', 'Name', 'CheckIn Time', 'Staff User'])
        return member_df, log_df


def save_database(member_df, log_df):
    """Saves both DataFrames back to the Excel file using separate sheets."""
    try:
        with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
            # Save Members to one sheet
            member_df.to_excel(writer, sheet_name='Members', index=False)
            # Save Check-in Logs to another sheet
            log_df.to_excel(writer, sheet_name='CheckIns', index=False)
        st.success(f"Data saved successfully to {DB_FILE}!")
    except Exception as e:
        st.error(f"Error saving data to Excel: {e}")

# --- Core Logic Functions ---

def record_entry(member_id, member_df, log_df, staff_user):
    """Records a member check-in with IST time and updates log."""
    
    # 1. Check if Member ID exists
    member = member_df[member_df['ID'] == member_id]
    if member.empty:
        st.error(f"Error: Member ID {member_id} not found.")
        return False, log_df

    member_name = member['Name'].iloc[0]
    
    # 2. Check Expiry
    expiry_date = member['Expiry Date'].iloc[0]
    today = get_ist_time().date()
    
    if expiry_date < today:
        st.error(f"MEMBERSHIP EXPIRED! Member {member_name} (ID: {member_id}) expired on {expiry_date}.")
        return False, log_df
    
    # 3. Record Entry
    checkin_time = get_ist_time().strftime('%Y-%m-%d %H:%M:%S IST')
    
    new_entry = pd.DataFrame([{
        'ID': member_id, 
        'Name': member_name, 
        'CheckIn Time': checkin_time, 
        'Staff User': staff_user
    }])
    
    log_df = pd.concat([log_df, new_entry], ignore_index=True)
    st.success(f"✅ Entry Recorded: **{member_name} (ID: {member_id})** at {checkin_time}")
    
    # 4. Expiry Reminder Check (Optional check at entry)
    days_until_expiry = (expiry_date - today).days
    if days_until_expiry <= 7:
        st.warning(f"⚠️ Reminder: {member_name}'s membership expires in {days_until_expiry} days on {expiry_date}.")

    return True, log_df

# --- Streamlit UI Components ---

def staff_registration():
    """Allows a staff member to register their credentials."""
    st.subheader("Staff Registration")
    
    new_username = st.text_input("New Staff Username")
    new_password = st.text_input("New Staff Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register Staff"):
        if not new_username or not new_password:
            st.error("Username and Password cannot be empty.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        elif new_username == OWNER_USERNAME:
            st.error("This username is reserved for the owner.")
        else:
            creds = load_staff_credentials()
            if new_username in creds:
                st.error("Username already exists. Please choose another one.")
            else:
                creds[new_username] = hash_password(new_password)
                save_staff_credentials(creds)
                st.success(f"Staff member '{new_username}' registered successfully! You can now log in.")

def login_page():
    """Handles the owner and staff login interface."""
    st.image("https://placehold.co/600x150/1F3D78/ffffff?text=GYM+MEMBERSHIP+APP", use_column_width=True)
    st.title("Member Check-In & Management System")
    st.subheader("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Check Owner Login
        if username == OWNER_USERNAME and hash_password(password) == OWNER_PASSWORD_HASH:
            st.session_state['logged_in'] = True
            st.session_state['user'] = OWNER_USERNAME
            st.session_state['role'] = 'owner'
            st.rerun()
            
        # Check Staff Login
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
    st.info("Staff members: If you haven't registered, click below.")
    if st.button("Register New Staff Account"):
        st.session_state['show_register'] = True

    if st.session_state.get('show_register'):
        staff_registration()

def sidebar_menu():
    """Renders the sidebar with current user info and logout."""
    st.sidebar.title("Welcome")
    st.sidebar.markdown(f"**User:** {st.session_state.get('user', 'Guest')}")
    st.sidebar.markdown(f"**Role:** _{st.session_state.get('role', 'N/A')}_")
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("Navigation")

# --- Main Application Pages ---

def page_check_in(member_df, log_df):
    """Page for member check-ins."""
    st.header("Member Check-In")
    st.markdown(f"Current IST: `{get_ist_time().strftime('%Y-%m-%d %H:%M:%S IST')}`")
    
    member_id_input = st.number_input("Enter Member ID:", min_value=1, step=1, key="check_in_id")

    if st.button("Record Entry", use_column_width=True, type="primary"):
        if member_id_input:
            success, new_log_df = record_entry(member_id_input, member_df, log_df, st.session_state['user'])
            
            # Save the updated log file
            if success:
                st.session_state['log_df'] = new_log_df
                save_database(member_df, new_log_df)
        else:
            st.warning("Please enter a valid Member ID.")

    st.markdown("---")
    st.subheader("Recent Check-Ins")
    if not log_df.empty:
        # Show the last 10 check-ins, newest first
        st.dataframe(
            log_df.sort_values(by='CheckIn Time', ascending=False).head(10), 
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No check-in entries yet.")

def page_member_management(member_df):
    """Page for adding and viewing members."""
    st.header("Member Management")

    if st.session_state['role'] == 'owner':
        member_df = add_member_form(member_df)
    else:
        st.info("Staff can only view members.")

    st.markdown("---")
    st.subheader("Active Members List")
    
    if not member_df.empty:
        df_display = member_df.sort_values(by='ID')
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No members registered yet.")
        
    return member_df

def add_member_form(member_df):
    """Form to add a new member (Owner only)."""
    with st.expander("➕ Add New Member"):
        with st.form("add_member_form", clear_on_submit=True):
            st.markdown("##### New Member Details")
            
            # Auto-generate next ID
            next_id = member_df['ID'].max() + 1 if not member_df.empty else 1
            st.text_input("Member ID (Auto-Generated)", value=str(next_id), disabled=True)
            
            name = st.text_input("Full Name *")
            phone = st.text_input("Phone Number *")
            m_type = st.selectbox("Membership Type *", ['Monthly', 'Quarterly', 'Annual', 'Trial'])
            join_date = st.date_input("Join Date *", value=get_ist_time().date())
            expiry_date = st.date_input("Expiry Date *", value=join_date + datetime.timedelta(days=30))
            
            submitted = st.form_submit_button("Register Member")
            
            if submitted:
                if not name or not phone:
                    st.error("Please fill in all required fields (*).")
                elif expiry_date <= join_date:
                     st.error("Expiry Date must be after Join Date.")
                else:
                    new_member = pd.DataFrame([{
                        'ID': next_id,
                        'Name': name,
                        'Phone': phone,
                        'Membership Type': m_type,
                        'Join Date': join_date,
                        'Expiry Date': expiry_date
                    }])
                    
                    # Convert column types to match existing DataFrame structure before concat
                    new_member['ID'] = new_member['ID'].astype(int)
                    
                    member_df = pd.concat([member_df, new_member], ignore_index=True)
                    st.session_state['member_df'] = member_df # Update state
                    st.success(f"Member **{name}** registered with ID: **{next_id}**")
                    st.rerun() # Rerun to refresh the data display

    return member_df

def page_reminders(member_df):
    """Page for showing membership expiry reminders (Owner only)."""
    st.header("Membership Reminders")
    
    if st.session_state['role'] != 'owner':
        st.warning("You do not have permission to view reminders.")
        return

    today = get_ist_time().date()
    
    # Calculate days until expiry
    df_temp = member_df.copy()
    df_temp['Days Until Expiry'] = (df_temp['Expiry Date'] - today).apply(lambda x: x.days)
    
    # Filter for memberships expiring within 30 days or already expired
    expiring_soon = df_temp[
        (df_temp['Days Until Expiry'] <= 30) & (df_temp['Days Until Expiry'] >= 0)
    ].sort_values(by='Days Until Expiry')

    expired = df_temp[
        df_temp['Days Until Expiry'] < 0
    ].sort_values(by='Days Until Expiry', ascending=False)
    
    st.subheader("🚨 Expired Memberships")
    if not expired.empty:
        st.dataframe(expired[['ID', 'Name', 'Phone', 'Expiry Date', 'Days Until Expiry']], use_container_width=True, hide_index=True)
    else:
        st.info("🎉 No expired memberships!")

    st.subheader("⏳ Expiring Within 30 Days")
    if not expiring_soon.empty:
        st.dataframe(expiring_soon[['ID', 'Name', 'Phone', 'Expiry Date', 'Days Until Expiry']], use_container_width=True, hide_index=True)
    else:
        st.info("Everyone is good for at least 30 days!")

def main_app():
    """The main application interface after successful login."""
    
    sidebar_menu()

    # Load data once and store in session state
    if 'member_df' not in st.session_state or 'log_df' not in st.session_state:
        st.session_state['member_df'], st.session_state['log_df'] = load_database()

    # Get data from state
    member_df = st.session_state['member_df']
    log_df = st.session_state['log_df']
    
    # Sidebar selection
    page_options = {
        "Check-In / Entry": page_check_in,
        "Member Management": page_member_management,
    }
    
    if st.session_state['role'] == 'owner':
        page_options["Membership Reminders"] = page_reminders

    selected_page = st.sidebar.radio("Go to", list(page_options.keys()))

    st.title(selected_page)
    st.markdown("---")

    # Render selected page
    if selected_page == "Check-In / Entry":
        page_options[selected_page](member_df, log_df)
    elif selected_page == "Member Management":
        st.session_state['member_df'] = page_options[selected_page](member_df)
        save_database(st.session_state['member_df'], st.session_state['log_df']) # Save after member update
    elif selected_page == "Membership Reminders":
        page_options[selected_page](member_df)


# --- Main Application Execution ---

if __name__ == "__main__":
    
    # Initialize session state variables
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'show_register' not in st.session_state:
        st.session_state['show_register'] = False

    # Check for staff credentials file and create if necessary to ensure smooth startup
    if not os.path.exists(CRED_FILE):
        save_staff_credentials({}) # Create empty JSON file

    # App flow control
    if st.session_state['logged_in']:
        main_app()
    else:
        # Load the owner hash once to ensure file integrity check on startup
        hash_password("panda@2006") # Just to make sure the hashing function is called

        login_page()

    # --- Data Saving Hook (Ensures data is saved on app rerun/exit) ---
    # NOTE: In a real environment, Streamlit runs continuously. Saving logic is placed 
    # within the functions that modify the data, but this is a final fallback check.
    if st.session_state.get('member_df') is not None and st.session_state.get('log_df') is not None:
        pass # Actual saving happens inside management functions for better control
