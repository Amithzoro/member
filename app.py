import streamlit as st
import pandas as pd
import pytz
import bcrypt
from twilio.rest import Client
from datetime import datetime
import time 

# --- Configuration and Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])

FILE_PATH = "membership.xlsx"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# --- Secrets Loading ---
try:
    TWILIO_SID = st.secrets["TWILIO_SID"]
    TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
    TWILIO_FROM = st.secrets["TWILIO_FROM"]
    ADMIN_USER = st.secrets.get("ADMIN_USER", "admin")
    ADMIN_PASSWORD_HASH = st.secrets["ADMIN_PASSWORD_HASH"] 
except KeyError as e:
    st.error(f"Configuration Error: Missing secret key: {e}. Please ensure Twilio and Admin keys are defined in .streamlit/secrets.toml.")
    st.stop()

# ✅ Initialize Twilio client
client = Client(TWILIO_SID, TWILIO_AUTH)

# --- Data Persistence Functions ---

@st.cache_data(show_spinner="Loading membership data...")
def load_data():
    """Loads member data from Excel or initializes an empty DataFrame."""
    try:
        df = pd.read_excel(FILE_PATH)
        # Ensure critical columns exist and are of the right type
        if 'Password' not in df.columns: df['Password'] = ''
        if 'Join Date' not in df.columns: df['Join Date'] = ''
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"])

def save_data(df):
    """Saves the DataFrame back to the Excel file."""
    try:
        df.to_excel(FILE_PATH, index=False)
        st.session_state.df = df # Update session state after successful save
        # Clear the cache so the next load pulls fresh data
        load_data.clear() 
        st.success("💾 Data saved successfully!")
    except Exception as e:
        st.error(f"Error saving data to Excel: {e}")

# --- Utility & Authentication ---

def send_whatsapp_confirmation(name, phone):
    """Sends a WhatsApp welcome message using Twilio."""
    try:
        client.messages.create(
            body=f"Hello {name}, welcome to our exclusive membership program! Your registration is complete.",
            from_=TWILIO_FROM,
            to=f"whatsapp:{phone}"
        )
        st.toast("WhatsApp welcome message sent!", icon="✅")
    except Exception as e:
        st.warning(f"Failed to send WhatsApp message. Ensure '{phone}' is a valid WhatsApp contact. Error: {e}")

def check_admin_login(username, password):
    """Checks credentials against the stored hash in secrets."""
    if username != ADMIN_USER:
        return False
    
    try:
        # Check the plain text password against the hashed password from secrets
        return bcrypt.checkpw(password.encode('utf-8'), ADMIN_PASSWORD_HASH.encode('utf-8'))
    except ValueError:
        st.error("Authentication Error: Invalid password hash configuration.")
        return False

def login_form():
    """Renders the login form."""
    st.markdown("### 🔒 Administrator Login")
    with st.form("admin_login"):
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        submitted = st.form_submit_button("Log In", use_container_width=True)

        if submitted:
            with st.spinner("Verifying credentials..."):
                time.sleep(0.5) 
                if check_admin_login(username, password):
                    st.session_state.logged_in = True
                    # Load data into session state right after login
                    st.session_state.df = load_data() 
                    st.success("Login successful! Welcome, Administrator.")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            
def logout():
    """Logs the admin out."""
    st.session_state.logged_in = False
    # Clear data in session state on logout
    st.session_state.df = pd.DataFrame(columns=["Name", "Email", "Phone", "Join Date", "Password"]) 
    st.toast("Logged out successfully.", icon="👋")
    st.rerun()

# --- Core Feature Sections ---

def display_dashboard(df):
    """Displays key metrics."""
    st.subheader("📊 Membership Dashboard")
    total_members = len(df)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Active Members", total_members)
    
    if total_members > 0:
        # Find the latest join date
        latest_join = df["Join Date"].max()
        # Format date for display if it's a string (as saved)
        display_date = latest_join.split(' ')[0] if isinstance(latest_join, str) and latest_join else "N/A"
        col2.metric("Latest Join Date", display_date)
    else:
        col2.metric("Latest Join Date", "N/A")
    
    col3.metric("Unique Phone Contacts", df['Phone'].nunique())
    st.divider()

def add_member_section():
    """Section for adding new members."""
    st.subheader("➕ Register New Member")
    
    with st.form("add_member_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", max_chars=50)
            email = st.text_input("Email", help="Email is the unique identifier.")
        with col2:
            phone = st.text_input("Phone (e.g., +919876543210)", help="Required for WhatsApp communication.")
            password = st.text_input("Initial Password", type="password")

        add_button = st.form_submit_button("Add Member", use_container_width=True, type="primary")

        if add_button:
            df = st.session_state.df
            if name and email and phone and password:
                # Check for duplicate email
                if df['Email'].str.lower().eq(email.lower()).any():
                    st.warning(f"Member with email '{email}' already exists!")
                else:
                    try:
                        # Hash Password
                        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        
                        new_member = {
                            "Name": name,
                            "Email": email,
                            "Phone": phone,
                            "Join Date": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
                            "Password": hashed_pw,
                        }

                        # Add new member and save
                        new_df = pd.concat([df, pd.DataFrame([new_member])], ignore_index=True)
                        save_data(new_df)
                        send_whatsapp_confirmation(name, phone)
                        # Clear form inputs using keys (optional, but good practice)
                        st.session_state["add_member_form_key"] = datetime.now()
                        st.rerun() 
                    except Exception as e:
                        st.error(f"An error occurred during addition: {e}")
            else:
                st.warning("Please fill all required fields!")

def manage_members_section():
    """Section for viewing, editing, and deleting members."""
    st.subheader("📝 Edit & Delete Members")

    df_display = st.session_state.df.copy()
    
    # 1. Prepare data for editing: drop sensitive/non-editable columns
    df_editable = df_display.drop(columns=['Password', 'Join Date'], errors='ignore')
    
    st.info("Edit 'Name' and 'Phone' directly in the table below. Use the **Apply Changes** button to save.")
    
    # Use st.data_editor for interactive editing
    edited_df = st.data_editor(
        df_editable,
        use_container_width=True,
        key="member_editor",
        num_rows="dynamic", # Allows admin to add rows (though adding via form is safer)
        column_config={
            "Email": st.column_config.TextColumn("Email", disabled=True, help="Email is the unique identifier and cannot be edited."),
        }
    )

    if st.button("Apply Changes", type="primary", help="Save any modifications made in the table above."):
        original_df = st.session_state.df.copy()
        
        # Merge changes back, preserving original columns (Password, Join Date)
        if len(edited_df) > len(original_df):
            st.warning("Adding new rows directly in the editor is not recommended. Use the 'New Registration' tab.")
            
        # Re-index the edited_df to match the original index for updating existing rows
        edited_df_indexed = edited_df.set_index(original_df.index[:len(edited_df)])
        
        # Update existing rows based on the editor changes
        for index, row in edited_df_indexed.iterrows():
             if index in original_df.index:
                original_df.loc[index, 'Name'] = row['Name']
                original_df.loc[index, 'Phone'] = row['Phone']

        # Handle row deletion (if admin manually deleted a row in the editor)
        # This is basic and assumes rows are deleted from the end or middle randomly.
        # A more robust solution is the dedicated delete form below.
        if len(edited_df) < len(original_df):
            deleted_indices = original_df.index.difference(edited_df_indexed.index)
            if not deleted_indices.empty:
                 original_df = original_df.drop(deleted_indices)
                 st.info(f"Detected and applied deletion of {len(deleted_indices)} row(s).")

        save_data(original_df)
        st.rerun()


    st.markdown("---")
    st.markdown("##### 🗑️ Dedicated Member Deletion")
    
    # Deletion form
    df = st.session_state.df
    member_options = df['Email'].tolist()
    
    if not member_options:
        st.info("No members to delete.")
    else:
        member_to_delete = st.selectbox("Select Member Email to Delete", member_options, key="delete_select")
        
        if st.button(f"Confirm Permanently Delete: {member_to_delete}", type="danger"):
            # Filter out the row where the Email matches
            df_after_delete = df[df['Email'] != member_to_delete]
            
            if len(df_after_delete) < len(df):
                save_data(df_after_delete)
                st.success(f"Member with email **{member_to_delete}** has been deleted.")
                st.rerun()
            else:
                st.warning("Member not found or deletion failed.")


# --- Application Entry Point ---

st.title("🛡️ Secure Membership Management Portal")
st.markdown("Manage registrations, track members, and communicate via WhatsApp.")

if not st.session_state.logged_in:
    # Check if data needs to be loaded when the app first starts (before login, for a clean state)
    if st.session_state.df.empty and len(st.session_state.df.columns) <= 1:
        st.session_state.df = load_data()
        
    login_form()
else:
    # Ensure the latest data is always in session state when logged in
    if st.session_state.df.empty or len(st.session_state.df.columns) <= 1:
        st.session_state.df = load_data()
    
    st.sidebar.button("Logout", on_click=logout, type="secondary", use_container_width=True)
    st.sidebar.success(f"Logged in as {ADMIN_USER}")

    df = st.session_state.df # Use session state DF for all operations
    
    display_dashboard(df)

    # Tabs for organization
    tab_add, tab_manage = st.tabs(["New Registration", "Edit & Delete"])

    with tab_add:
        add_member_section()

    with tab_manage:
        manage_members_section()
