import streamlit as st
import pandas as pd
import datetime
import pytz
import os

# ---------------- CONFIG ----------------
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "gym_data.xlsx"

OWNER_USERNAME = "owner"
OWNER_PASSWORD = "owner123"  # Change as needed
STAFF_CREDENTIALS = {"staff1": "staff123"}  # initial staff

# ---------------- UTILS ----------------
def get_ist_time():
    return datetime.datetime.now(IST)

# ---------------- DATABASE ----------------
def load_data():
    if os.path.exists(DB_FILE):
        try:
            members_df = pd.read_excel(DB_FILE, sheet_name='Members')
            log_df = pd.read_excel(DB_FILE, sheet_name='CheckInLog')
        except:
            members_df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Date','Expiry Date'])
            log_df = pd.DataFrame(columns=['ID','Name','CheckIn Time','Staff User'])
    else:
        members_df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Date','Expiry Date'])
        log_df = pd.DataFrame(columns=['ID','Name','CheckIn Time','Staff User'])
        save_data(members_df, log_df)
    return members_df, log_df

def save_data(members_df, log_df):
    with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
        members_df.to_excel(writer, sheet_name='Members', index=False)
        log_df.to_excel(writer, sheet_name='CheckInLog', index=False)

# ---------------- LOGIN ----------------
def login():
    st.title("Gym Membership System")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login", key="login_btn"):
        if username == OWNER_USERNAME and password == OWNER_PASSWORD:
            st.session_state['logged_in'] = True
            st.session_state['role'] = 'owner'
            st.session_state['user'] = OWNER_USERNAME
            st.experimental_rerun()
        elif username in STAFF_CREDENTIALS and password == STAFF_CREDENTIALS[username]:
            st.session_state['logged_in'] = True
            st.session_state['role'] = 'staff'
            st.session_state['user'] = username
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

# ---------------- SIDEBAR ----------------
def sidebar():
    st.sidebar.title(f"User: {st.session_state['user']}")
    st.sidebar.markdown(f"Role: {st.session_state['role']}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()

# ---------------- MEMBER MANAGEMENT ----------------
def member_management(members_df, log_df):
    st.header("Member Management")
    
    # --- Add Member ---
    with st.expander("Add Member"):
        next_id = int(members_df['ID'].max()+1) if not members_df.empty else 1
        name = st.text_input("Full Name", key=f"add_name_{next_id}")
        phone = st.text_input("Phone", key=f"add_phone_{next_id}")
        mtype = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'], key=f"add_type_{next_id}")
        join = st.date_input("Join Date", get_ist_time().date(), key=f"add_join_{next_id}")
        if mtype=='Monthly':
            expiry = join + datetime.timedelta(days=30)
        elif mtype=='Quarterly':
            expiry = join + datetime.timedelta(days=90)
        else:
            expiry = join + datetime.timedelta(days=365)
        if st.button("Add Member", key=f"add_member_btn_{next_id}"):
            if not name or not phone:
                st.error("All fields are required")
            else:
                new_member = pd.DataFrame([{
                    'ID': next_id,
                    'Name': name,
                    'Phone': phone,
                    'Membership Type': mtype,
                    'Join Date': join,
                    'Expiry Date': expiry
                }])
                members_df = pd.concat([members_df, new_member], ignore_index=True)
                save_data(members_df, log_df)
                st.success(f"Added {name} (ID:{next_id})")
    
    # --- Edit Member (Owner Only) ---
    if st.session_state['role'] == 'owner':
        with st.expander("Edit Member"):
            edit_id = st.number_input("Enter Member ID to Edit", min_value=1, step=1, key="edit_id")
            member = members_df[members_df['ID']==edit_id]
            if not member.empty:
                name_edit = st.text_input("Full Name", member['Name'].values[0], key=f"edit_name_{edit_id}")
                phone_edit = st.text_input("Phone", member['Phone'].values[0], key=f"edit_phone_{edit_id}")
                mtype_edit = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'], index=['Monthly','Quarterly','Yearly'].index(member['Membership Type'].values[0]), key=f"edit_type_{edit_id}")
                join_edit = st.date_input("Join Date", member['Join Date'].values[0], key=f"edit_join_{edit_id}")
                if mtype_edit=='Monthly':
                    expiry_edit = join_edit + datetime.timedelta(days=30)
                elif mtype_edit=='Quarterly':
                    expiry_edit = join_edit + datetime.timedelta(days=90)
                else:
                    expiry_edit = join_edit + datetime.timedelta(days=365)
                if st.button("Update Member", key=f"update_member_{edit_id}"):
                    members_df.loc[members_df['ID']==edit_id, ['Name','Phone','Membership Type','Join Date','Expiry Date']] = \
                        [name_edit, phone_edit, mtype_edit, join_edit, expiry_edit]
                    save_data(members_df, log_df)
                    st.success(f"Updated Member ID {edit_id}")
            else:
                st.info("Member not found")
    
    # --- Display Members ---
    st.subheader("All Members")
    if not members_df.empty:
        st.dataframe(members_df.sort_values('ID'))
    else:
        st.info("No members yet.")
    
    return members_df, log_df

# ---------------- REMINDERS ----------------
def reminders_popup(members_df):
    st.header("Membership Reminders")
    today = get_ist_time().date()
    if 'Expiry Date' not in members_df.columns:
        st.info("No members data yet")
        return
    df = members_df.copy()
    df['Days Left'] = (df['Expiry Date'] - today).apply(lambda x: x.days)
    
    expired = df[df['Days Left'] < 0]
    if not expired.empty:
        st.warning(f"Expired Members: {', '.join(expired['Name'].tolist())}")
    
    soon = df[(df['Days Left']>=0) & (df['Days Left']<=30)]
    if not soon.empty:
        st.info(f"Members expiring in 30 days: {', '.join(soon['Name'].tolist())}")

# ---------------- CHECK-IN ----------------
def check_in(members_df, log_df):
    st.header("Member Check-In")
    member_id = st.number_input("Enter Member ID", min_value=1, step=1, key="checkin_id")
    staff_user = st.session_state['user']
    if st.button("Check In", key="checkin_btn"):
        member = members_df[members_df['ID']==member_id]
        if member.empty:
            st.error("Member not found")
        else:
            checkin_time = get_ist_time()
            new_log = pd.DataFrame([{
                'ID': member_id,
                'Name': member['Name'].values[0],
                'CheckIn Time': checkin_time,
                'Staff User': staff_user
            }])
            log_df = pd.concat([log_df, new_log], ignore_index=True)
            save_data(members_df, log_df)
            st.success(f"{member['Name'].values[0]} checked in at {checkin_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Display last 10 check-ins
    if not log_df.empty:
        st.subheader("Last 10 Check-Ins")
        st.dataframe(log_df.sort_values('CheckIn Time', ascending=False).head(10))
    
    return log_df

# ---------------- MAIN ----------------
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    if st.session_state['logged_in']:
        sidebar()
        if 'members_df' not in st.session_state or 'log_df' not in st.session_state:
            st.session_state['members_df'], st.session_state['log_df'] = load_data()
        
        reminders_popup(st.session_state['members_df'])
        
        page = st.sidebar.radio("Go to", ["Members","Check-In"])
        if page=="Members":
            st.session_state['members_df'], st.session_state['log_df'] = member_management(
                st.session_state['members_df'], st.session_state['log_df'])
        elif page=="Check-In":
            st.session_state['log_df'] = check_in(
                st.session_state['members_df'], st.session_state['log_df'])
    else:
        login()

if __name__=="__main__":
    main()
