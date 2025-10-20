import streamlit as st
import pandas as pd
import datetime
import pytz
import os

# ---------------- CONFIG ----------------
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "gym_data.xlsx"

OWNER_USERNAME = "vineeth"
OWNER_PASSWORD = "panda@2006"
STAFF_CREDENTIALS = {"staff1": "staff123"}  # initial staff login

# ---------------- UTILS ----------------
def get_ist_time():
    return datetime.datetime.now(IST)

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE, sheet_name='Members')
            if not df.empty:
                df['Join Date'] = pd.to_datetime(df['Join Date'])
                df['Expiry Date'] = pd.to_datetime(df['Expiry Date'])
            else:
                df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Date','Expiry Date'])
            return df
        except:
            pass
    df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Date','Expiry Date'])
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
def member_management(members_df):
    st.header("Member Management")
    
    # --- Add Member ---
    with st.expander("Add Member"):
        next_id = int(members_df['ID'].max()+1) if not members_df.empty else 1
        name = st.text_input("Full Name", key="add_name")
        phone = st.text_input("Phone", key="add_phone")
        mtype = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'], key="add_mtype")
        join = st.date_input("Join Date", get_ist_time().date(), key="add_join")
        
        # calculate expiry
        if mtype=='Monthly':
            expiry = join + datetime.timedelta(days=30)
        elif mtype=='Quarterly':
            expiry = join + datetime.timedelta(days=90)
        else:
            expiry = join + datetime.timedelta(days=365)
        
        if st.button("Add Member", key="add_member_btn"):
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
    
    # --- Edit Member (Owner Only) ---
    if st.session_state['role'] == 'owner' and not members_df.empty:
        st.subheader("Edit Member")
        member_id_input = st.number_input("Enter Member ID to Edit", min_value=1, step=1, key="edit_member_id")
        
        if member_id_input in members_df['ID'].values:
            member = members_df.loc[members_df['ID'] == member_id_input].iloc[0]
            name_edit = st.text_input("Full Name", member['Name'], key=f"edit_name_{member_id_input}")
            phone_edit = st.text_input("Phone", member['Phone'], key=f"edit_phone_{member_id_input}")
            mtype_edit = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'],
                                      index=['Monthly','Quarterly','Yearly'].index(member['Membership Type']),
                                      key=f"edit_mtype_{member_id_input}")
            join_edit = st.date_input("Join Date", member['Join Date'].date(), key=f"edit_join_{member_id_input}")
            
            # calculate expiry
            if mtype_edit == 'Monthly':
                expiry_edit = join_edit + datetime.timedelta(days=30)
            elif mtype_edit == 'Quarterly':
                expiry_edit = join_edit + datetime.timedelta(days=90)
            else:
                expiry_edit = join_edit + datetime.timedelta(days=365)
            
            if st.button("Save Changes", key=f"save_{member_id_input}"):
                members_df.loc[members_df['ID'] == member_id_input, ['Name','Phone','Membership Type','Join Date','Expiry Date']] = [
                    name_edit, phone_edit, mtype_edit, join_edit, expiry_edit
                ]
                save_data(members_df)
                st.success(f"Member ID {member_id_input} updated successfully!")
        else:
            st.info("Enter a valid Member ID to edit.")
    
    # --- Display Members ---
    st.subheader("All Members")
    if not members_df.empty:
        st.dataframe(members_df.sort_values('ID'))
    else:
        st.info("No members yet.")
    
    return members_df

# ---------------- REMINDERS ----------------
def reminders_popup(members_df):
    st.header("Membership Reminders")
    today = get_ist_time().date()
    df = members_df.copy()
    df['Days Left'] = (df['Expiry Date'].dt.date - today).apply(lambda x: x.days)
    
    # Expired
    expired = df[df['Days Left'] < 0]
    if not expired.empty:
        st.warning("Expired Memberships:")
        st.dataframe(expired)
    
    # Expiring Soon
    soon = df[(df['Days Left'] >=0) & (df['Days Left'] <=30)]
    if not soon.empty:
        st.info("Memberships Expiring in 30 Days:")
        st.dataframe(soon)

# ---------------- MAIN ----------------
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        sidebar()
        if 'members_df' not in st.session_state:
            st.session_state['members_df'] = load_data()
        
        # Show reminders to both staff and owner
        reminders_popup(st.session_state['members_df'])
        
        st.session_state['members_df'] = member_management(st.session_state['members_df'])
    else:
        login()

main()
