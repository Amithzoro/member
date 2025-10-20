import streamlit as st
import pandas as pd
import datetime
import pytz
import hashlib
import os
import json

# ---------------- CONFIG ----------------
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "gym_data.xlsx"
CRED_FILE = "staff_credentials.json"

# Owner credentials (you can change). We'll compare hashes at login.
OWNER_USERNAME = "vineeth"
OWNER_PASSWORD = "panda@2006"  # kept for convenience; hashed at runtime
OWNER_PASSWORD_HASH = hashlib.sha256(OWNER_PASSWORD.encode()).hexdigest()

# Optional initial staff (plaintext is only used to initialize the creds file once)
INITIAL_STAFF = {"staff1": "staff123"}

# ---------------- HELPERS ----------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_ist_time() -> datetime.datetime:
    return datetime.datetime.now(IST)

# ---------------- CREDENTIALS (persistent) ----------------
def load_staff_credentials() -> dict:
    if os.path.exists(CRED_FILE):
        try:
            with open(CRED_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    # initialize with INITIAL_STAFF (hashed) if file doesn't exist
    creds = {}
    for u, p in INITIAL_STAFF.items():
        creds[u] = hash_password(p)
    save_staff_credentials(creds)
    return creds

def save_staff_credentials(creds: dict):
    with open(CRED_FILE, 'w') as f:
        json.dump(creds, f, indent=2)

# ---------------- DATABASE ----------------
def load_database():
    """
    Returns (members_df, log_df). Ensures expected columns exist and types are correct.
    """
    # default empty structures
    members_cols = ['ID','Name','Phone','Membership Type','Join Date','Expiry Date']
    logs_cols = ['ID','Name','CheckIn Time','Staff User','CheckIn Time_dt']

    if os.path.exists(DB_FILE):
        try:
            members_df = pd.read_excel(DB_FILE, sheet_name='Members')
            logs_df = pd.read_excel(DB_FILE, sheet_name='CheckIns')
            # Ensure columns
            members_df = members_df.reindex(columns=members_cols)
            logs_df = logs_df.reindex(columns=[c for c in logs_df.columns if c in logs_cols] + [c for c in logs_cols if c not in logs_df.columns])
            # types
            if not members_df.empty:
                # If ID non-numeric, coerce then drop NaN
                members_df['ID'] = pd.to_numeric(members_df['ID'], errors='coerce').fillna(0).astype(int)
                members_df['Join Date'] = pd.to_datetime(members_df['Join Date'], errors='coerce').dt.date
                members_df['Expiry Date'] = pd.to_datetime(members_df['Expiry Date'], errors='coerce').dt.date
            else:
                members_df = pd.DataFrame(columns=members_cols)

            if not logs_df.empty:
                if 'CheckIn Time_dt' not in logs_df.columns or logs_df['CheckIn Time_dt'].isna().all():
                    # create from string if present
                    if 'CheckIn Time' in logs_df.columns:
                        try:
                            logs_df['CheckIn Time_dt'] = pd.to_datetime(logs_df['CheckIn Time'].astype(str).str.replace(' IST',''), errors='coerce')
                        except Exception:
                            logs_df['CheckIn Time_dt'] = pd.NaT
                    else:
                        logs_df['CheckIn Time_dt'] = pd.NaT
            else:
                logs_df = pd.DataFrame(columns=logs_cols)

            return members_df, logs_df
        except Exception:
            # fall through to create new
            pass

    # Create empty file if missing
    members_df = pd.DataFrame(columns=members_cols)
    logs_df = pd.DataFrame(columns=logs_cols)
    save_database(members_df, logs_df)
    return members_df, logs_df

def save_database(members_df: pd.DataFrame, logs_df: pd.DataFrame):
    # drop in-memory helper col
    to_save_logs = logs_df.copy()
    if 'CheckIn Time_dt' in to_save_logs.columns:
        to_save_logs = to_save_logs.drop(columns=['CheckIn Time_dt'])
    with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
        members_df.to_excel(writer, sheet_name='Members', index=False)
        to_save_logs.to_excel(writer, sheet_name='CheckIns', index=False)

# ---------------- UI: Auth ----------------
def login_page():
    st.title("Gym Membership System")
    st.subheader("Login")

    login_col1, login_col2 = st.columns([2,1])
    with login_col1:
        username = st.text_input("Username", key="login_username")
    with login_col2:
        password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", key="login_button"):
        # owner check
        if username == OWNER_USERNAME and hash_password(password) == OWNER_PASSWORD_HASH:
            st.session_state['logged_in'] = True
            st.session_state['role'] = 'owner'
            st.session_state['user'] = OWNER_USERNAME
            st.experimental_rerun()
        else:
            creds = load_staff_credentials()
            if username in creds and hash_password(password) == creds[username]:
                st.session_state['logged_in'] = True
                st.session_state['role'] = 'staff'
                st.session_state['user'] = username
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

    st.markdown("---")
    st.info("If you're a staff and not registered yet, owner can add you or use registration below.")
    if st.button("Show Staff Registration", key="show_reg"):
        st.session_state['show_register'] = True

    if st.session_state.get('show_register'):
        staff_registration()

def staff_registration():
    st.subheader("Register Staff Account")
    u_col, p_col = st.columns(2)
    with u_col:
        new_user = st.text_input("New Username", key="reg_new_user")
    with p_col:
        new_pass = st.text_input("New Password", type="password", key="reg_new_pass")
    confirm = st.text_input("Confirm Password", type="password", key="reg_confirm_pass")

    if st.button("Register", key="reg_submit"):
        if not new_user or not new_pass:
            st.error("Username and password are required")
        elif new_pass != confirm:
            st.error("Passwords do not match")
        elif new_user == OWNER_USERNAME:
            st.error("That username is reserved")
        else:
            creds = load_staff_credentials()
            if new_user in creds:
                st.error("Username already exists")
            else:
                creds[new_user] = hash_password(new_pass)
                save_staff_credentials(creds)
                st.success(f"Staff '{new_user}' registered")
                st.session_state['show_register'] = False

# ---------------- UI: Sidebar ----------------
def show_sidebar():
    st.sidebar.title(f"User: {st.session_state.get('user','Guest')}")
    st.sidebar.markdown(f"Role: **{st.session_state.get('role','N/A')}**")
    if st.sidebar.button("Logout", key="sidebar_logout"):
        st.session_state.clear()
        st.experimental_rerun()

# ---------------- MEMBER MANAGEMENT ----------------
def member_management_page(members_df, logs_df):
    st.header("Member Management")

    # Add Member (both owner & staff allowed per request)
    with st.expander("➕ Add Member"):
        # robust next ID
        if 'ID' in members_df.columns and not members_df['ID'].dropna().empty:
            try:
                next_id = int(members_df['ID'].max()) + 1
            except Exception:
                next_id = 1
        else:
            next_id = 1

        st.markdown(f"**Next ID:** {next_id}")
        name = st.text_input("Full Name", key="m_name")
        phone = st.text_input("Phone", key="m_phone")
        mtype = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly','Trial'], key="m_type")
        join = st.date_input("Join Date", get_ist_time().date(), key="m_join")
        # compute expiry defaults
        if mtype == 'Monthly':
            expiry_default = join + datetime.timedelta(days=30)
        elif mtype == 'Quarterly':
            expiry_default = join + datetime.timedelta(days=90)
        elif mtype == 'Yearly':
            expiry_default = join + datetime.timedelta(days=365)
        else:
            expiry_default = join + datetime.timedelta(days=7)  # trial

        expiry = st.date_input("Expiry Date", expiry_default, key="m_expiry")

        if st.button("Add Member", key="m_add"):
            if not name.strip() or not phone.strip():
                st.error("Name and phone are required.")
            elif expiry <= join:
                st.error("Expiry must be after join date.")
            else:
                new = pd.DataFrame([{
                    'ID': next_id,
                    'Name': name.strip(),
                    'Phone': phone.strip(),
                    'Membership Type': mtype,
                    'Join Date': join,
                    'Expiry Date': expiry
                }])
                members_df = pd.concat([members_df, new], ignore_index=True)
                save_database(members_df, logs_df)
                st.success(f"Added member {name} (ID {next_id})")
                # clear inputs by rerunning
                st.experimental_rerun()

    st.subheader("All Members")
    if not members_df.empty:
        st.dataframe(members_df.sort_values('ID'))
    else:
        st.info("No members yet.")
    return members_df, logs_df

# ---------------- CHECK-IN PAGE ----------------
def check_in_page(members_df, logs_df):
    st.header("Member Check-In")
    st.write("Current IST:", get_ist_time().strftime("%Y-%m-%d %H:%M:%S IST"))

    # ensure ID column numeric
    if 'ID' in members_df.columns and not members_df.empty:
        try:
            members_df['ID'] = members_df['ID'].astype(int)
        except Exception:
            members_df['ID'] = pd.to_numeric(members_df['ID'], errors='coerce').fillna(0).astype(int)

    member_id = st.number_input("Member ID", min_value=1, step=1, key="check_id")
    if st.button("Record Check-In", key="check_btn"):
        if members_df.empty:
            st.error("No members available. Add members first.")
        else:
            # cast
            mid = int(member_id)
            member_row = members_df[members_df['ID'] == mid]
            if member_row.empty:
                st.error(f"Member ID {mid} not found.")
            else:
                name = member_row['Name'].iloc[0]
                expiry = member_row['Expiry Date'].iloc[0]
                today = get_ist_time().date()
                if pd.isnull(expiry):
                    st.error("Member expiry date missing.")
                elif expiry < today:
                    st.error(f"Membership expired on {expiry} for {name}.")
                else:
                    ts = get_ist_time()
                    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S IST")
                    new_log = pd.DataFrame([{
                        'ID': mid,
                        'Name': name,
                        'CheckIn Time': ts_str,
                        'Staff User': st.session_state.get('user','unknown'),
                        'CheckIn Time_dt': ts
                    }])
                    logs_df = pd.concat([logs_df, new_log], ignore_index=True)
                    save_database(members_df, logs_df)
                    st.success(f"Check-in recorded: {name} at {ts_str}")
                    st.experimental_rerun()

    st.subheader("Recent Check-ins")
    if not logs_df.empty:
        if 'CheckIn Time_dt' not in logs_df.columns:
            logs_df['CheckIn Time_dt'] = pd.to_datetime(logs_df['CheckIn Time'].astype(str).str.replace(' IST',''), errors='coerce')
        disp = logs_df.sort_values('CheckIn Time_dt', ascending=False).head(10)
        st.dataframe(disp[['ID','Name','CheckIn Time','Staff User']])
    else:
        st.info("No check-ins yet.")

    return members_df, logs_df

# ---------------- REMINDERS ----------------
def reminders_page(members_df, logs_df):
    st.header("Membership Reminders (Owner Only)")
    if st.session_state.get('role') != 'owner':
        st.warning("Only owner can view reminders.")
        return members_df, logs_df

    today = get_ist_time().date()
    df = members_df.copy()
    df['Days Left'] = (df['Expiry Date'] - today).apply(lambda x: x.days if pd.notnull(x) else None)

    st.subheader("Expired Members")
    expired = df[df['Days Left'] < 0]
    if not expired.empty:
        st.dataframe(expired[['ID','Name','Phone','Expiry Date','Days Left']])
    else:
        st.info("No expired memberships.")

    st.subheader("Expiring Within 30 Days")
    soon = df[(df['Days Left'] >= 0) & (df['Days Left'] <= 30)]
    if not soon.empty:
        st.dataframe(soon[['ID','Name','Phone','Expiry Date','Days Left']])
    else:
        st.info("No memberships expiring within 30 days.")

    return members_df, logs_df

# ---------------- MAIN ----------------
def main():
    # initialize session flags
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'show_register' not in st.session_state:
        st.session_state['show_register'] = False

    if not st.session_state['logged_in']:
        login_page()
        return

    # logged in
    show_sidebar()

    # load DB if not loaded yet in session
    if 'members_df' not in st.session_state or 'logs_df' not in st.session_state:
        members_df, logs_df = load_database()
        st.session_state['members_df'] = members_df
        st.session_state['logs_df'] = logs_df

    members_df = st.session_state['members_df']
    logs_df = st.session_state['logs_df']

    # menu
    menu = ["Members", "Check-In"]
    if st.session_state.get('role') == 'owner':
        menu.append("Reminders")

    choice = st.sidebar.radio("Go to", menu, key="main_menu")

    if choice == "Members":
        members_df, logs_df = member_management_page(members_df, logs_df)
    elif choice == "Check-In":
        members_df, logs_df = check_in_page(members_df, logs_df)
    elif choice == "Reminders":
        members_df, logs_df = reminders_page(members_df, logs_df)

    # push back to session
    st.session_state['members_df'] = members_df
    st.session_state['logs_df'] = logs_df

if __name__ == "__main__":
    main()
