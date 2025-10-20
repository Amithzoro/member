import streamlit as st
import pandas as pd
import datetime
import pytz
import hashlib
import os

# ---------------- CONFIG ----------------
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "gym_data.xlsx"

OWNER_USERNAME = "vineeth"
OWNER_PASSWORD = "panda@2006"
STAFF_CREDENTIALS = {"staff1": "staff123"}

# ---------------- UTILS ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_ist_time():
    return datetime.datetime.now(IST)

# ---------------- DATABASE ----------------
def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE, sheet_name='Members')
            if not df.empty:
                df['Join Time'] = pd.to_datetime(df['Join Time'])
                df['Expiry Time'] = pd.to_datetime(df['Expiry Time'])
            else:
                df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Time','Expiry Time'])
            return df
        except:
            pass
    df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Time','Expiry Time'])
    save_data(df)
    return df

def save_data(df):
    with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Members', index=False)

# ---------------- LOGIN ----------------
def login():
    st.title("Gym Membership System")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
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
def member_management(df):
    st.header("Member Management")
    
    # Add member section (staff & owner)
    with st.expander("Add Member"):
        next_id = int(df['ID'].max()+1) if not df.empty else 1
        name = st.text_input("Full Name", key="add_name")
        phone = st.text_input("Phone", key="add_phone")
        mtype = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'], key="add_type")
        join_time = st.datetime_input("Join Time", get_ist_time(), key="add_join")
        if mtype=='Monthly':
            expiry_time = join_time + datetime.timedelta(days=30)
        elif mtype=='Quarterly':
            expiry_time = join_time + datetime.timedelta(days=90)
        else:
            expiry_time = join_time + datetime.timedelta(days=365)
        
        if st.button("Add Member"):
            if not name or not phone:
                st.error("All fields required")
            else:
                new_member = pd.DataFrame([{
                    'ID': next_id,
                    'Name': name,
                    'Phone': phone,
                    'Membership Type': mtype,
                    'Join Time': join_time,
                    'Expiry Time': expiry_time
                }])
                df = pd.concat([df, new_member], ignore_index=True)
                save_data(df)
                st.success(f"Added {name} (ID:{next_id})")
    
    # Edit member section (only owner)
    if st.session_state['role']=='owner' and not df.empty:
        st.subheader("Edit Members")
        member_ids = df['ID'].tolist()
        edit_id = st.selectbox("Select Member ID to edit", member_ids, key="edit_id")
        member_row = df[df['ID']==edit_id]
        if not member_row.empty:
            edit_name = st.text_input("Edit Name", member_row.iloc[0]['Name'], key="edit_name")
            edit_phone = st.text_input("Edit Phone", member_row.iloc[0]['Phone'], key="edit_phone")
            edit_mtype = st.selectbox("Edit Membership Type", ['Monthly','Quarterly','Yearly'], member_row.iloc[0]['Membership Type'], key="edit_type")
            edit_join = st.datetime_input("Edit Join Time", member_row.iloc[0]['Join Time'], key="edit_join")
            if edit_mtype=='Monthly':
                edit_expiry = edit_join + datetime.timedelta(days=30)
            elif edit_mtype=='Quarterly':
                edit_expiry = edit_join + datetime.timedelta(days=90)
            else:
                edit_expiry = edit_join + datetime.timedelta(days=365)
            if st.button("Update Member"):
                df.loc[df['ID']==edit_id,'Name'] = edit_name
                df.loc[df['ID']==edit_id,'Phone'] = edit_phone
                df.loc[df['ID']==edit_id,'Membership Type'] = edit_mtype
                df.loc[df['ID']==edit_id,'Join Time'] = edit_join
                df.loc[df['ID']==edit_id,'Expiry Time'] = edit_expiry
                save_data(df)
                st.success("Member updated")
    
    # Show all members
    st.subheader("All Members")
    if not df.empty:
        st.dataframe(df.sort_values('ID'))
    else:
        st.info("No members yet.")
    
    return df

# ---------------- REMINDERS POPUP ----------------
def reminders_popup(df):
    if df.empty:
        return
    now = get_ist_time()
    
    # Ensure datetime columns exist
    for col in ['Join Time','Expiry Time']:
        if col not in df.columns:
            df[col] = pd.NaT
    
    df['Expiry Date'] = df['Expiry Time'].dt.date
    df['Days Left'] = (df['Expiry Date'] - now.date()).apply(lambda x: x.days if pd.notnull(x) else None)
    
    expired = df[df['Days Left'] < 0]
    soon = df[(df['Days Left'] >=0) & (df['Days Left'] <=30)]
    
    if not expired.empty:
        st.warning("⚠️ Some memberships have **expired!**")
        st.dataframe(expired[['ID','Name','Phone','Membership Type','Expiry Time','Days Left']])
    if not soon.empty:
        st.info("📅 Memberships expiring within 30 days")
        st.dataframe(soon[['ID','Name','Phone','Membership Type','Expiry Time','Days Left']])

# ---------------- MAIN ----------------
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    if st.session_state['logged_in']:
        sidebar()
        if 'members_df' not in st.session_state:
            st.session_state['members_df'] = load_data()
        
        reminders_popup(st.session_state['members_df'])
        
        page = st.sidebar.radio("Go to", ["Members"])
        if page=="Members":
            st.session_state['members_df'] = member_management(st.session_state['members_df'])
    else:
        login()

# ---------------- RUN ----------------
if __name__=="__main__":
    main()
