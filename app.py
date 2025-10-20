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
            members_df = pd.read_excel(DB_FILE, sheet_name='Members')
            if not members_df.empty:
                members_df['Join Date'] = pd.to_datetime(members_df['Join Date'])
                members_df['Expiry Date'] = pd.to_datetime(members_df['Expiry Date'])
            else:
                members_df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Date','Expiry Date'])
            return members_df
        except:
            pass
    members_df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Date','Expiry Date'])
    save_data(members_df)
    return members_df

def save_data(members_df):
    with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
        members_df.to_excel(writer, sheet_name='Members', index=False)

# ---------------- LOGIN ----------------
def login():
    st.title("Gym Membership System")
    st.session_state.setdefault('logged_in', False)
    st.session_state.setdefault('role', None)
    st.session_state.setdefault('user', None)

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
def member_management(members_df):
    st.header("Member Management")
    
    # Add member (both owner and staff)
    with st.expander("Add Member"):
        next_id = int(members_df['ID'].max() + 1) if not members_df.empty else 1
        name = st.text_input("Full Name")
        phone = st.text_input("Phone")
        mtype = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'])
        join = st.date_input("Join Date", get_ist_time().date())
        if mtype=='Monthly':
            expiry = join + datetime.timedelta(days=30)
        elif mtype=='Quarterly':
            expiry = join + datetime.timedelta(days=90)
        else:
            expiry = join + datetime.timedelta(days=365)
        if st.button("Add Member"):
            if not name or not phone:
                st.error("All fields required")
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
                save_data(members_df)
                st.success(f"Added {name} (ID:{next_id})")

    # Edit member (only owner)
    if st.session_state['role'] == 'owner' and not members_df.empty:
        st.subheader("Edit Member")
        member_id = st.number_input("Enter Member ID to Edit", min_value=1, step=1)
        if st.button("Load Member"):
            if member_id in members_df['ID'].values:
                member = members_df.loc[members_df['ID']==member_id].iloc[0]
                name_edit = st.text_input("Full Name", member['Name'])
                phone_edit = st.text_input("Phone", member['Phone'])
                mtype_edit = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'], index=['Monthly','Quarterly','Yearly'].index(member['Membership Type']))
                join_edit = st.date_input("Join Date", member['Join Date'].date())
                if mtype_edit=='Monthly':
                    expiry_edit = join_edit + datetime.timedelta(days=30)
                elif mtype_edit=='Quarterly':
                    expiry_edit = join_edit + datetime.timedelta(days=90)
                else:
                    expiry_edit = join_edit + datetime.timedelta(days=365)
                if st.button("Save Changes"):
                    members_df.loc[members_df['ID']==member_id, ['Name','Phone','Membership Type','Join Date','Expiry Date']] = [name_edit, phone_edit, mtype_edit, join_edit, expiry_edit]
                    save_data(members_df)
                    st.success(f"Member ID {member_id} updated successfully!")
            else:
                st.warning("Member ID not found")

    st.subheader("All Members")
    if not members_df.empty:
        st.dataframe(members_df.sort_values('ID'))
    else:
        st.info("No members yet.")
    
    return members_df

# ---------------- REMINDERS ----------------
def reminders_popup(members_df):
    if members_df.empty:
        return
    now = get_ist_time()
    df = members_df.copy()
    df['Days Left'] = (df['Expiry Date'].dt.date - now.date()).apply(lambda x: x.days)
    expiring_soon = df[df['Days Left'] <= 7]
    if not expiring_soon.empty:
        st.warning("⚠️ Memberships expiring soon or expired!")
        st.dataframe(expiring_soon[['ID','Name','Expiry Date','Days Left']])

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

if __name__ == "__main__":
    main()
