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
STAFF_CREDENTIALS = {"staff1": "staff123"}  # initial staff

# ---------------- UTILS ----------------
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
    # Add member (staff & owner)
    with st.expander("Add Member"):
        next_id = int(members_df['ID'].max()+1) if not members_df.empty else 1
        name = st.text_input("Full Name", key="add_name")
        phone = st.text_input("Phone", key="add_phone")
        mtype = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'], key="add_type")
        join = st.date_input("Join Date", get_ist_time().date(), key="add_join")
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
                    'Join Date': pd.Timestamp(join),
                    'Expiry Date': pd.Timestamp(expiry)
                }])
                members_df = pd.concat([members_df, new_member], ignore_index=True)
                save_data(members_df)
                st.success(f"Added {name} (ID:{next_id})")
    
    # Edit member (owner only)
    if st.session_state['role'] == 'owner':
        st.subheader("Edit Member")
        member_id = st.number_input("Enter Member ID to Edit", min_value=1, step=1, key="edit_id")
        if st.button("Load Member"):
            member = members_df[members_df['ID']==member_id]
            if member.empty:
                st.error("Member not found")
            else:
                edit_name = st.text_input("Full Name", member['Name'].values[0], key=f"edit_name_{member_id}")
                edit_phone = st.text_input("Phone", member['Phone'].values[0], key=f"edit_phone_{member_id}")
                edit_type = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'], 
                                         index=['Monthly','Quarterly','Yearly'].index(member['Membership Type'].values[0]),
                                         key=f"edit_type_{member_id}")
                edit_join = st.date_input("Join Date", member['Join Date'].values[0].date(), key=f"edit_join_{member_id}")
                if edit_type=='Monthly':
                    edit_expiry = edit_join + datetime.timedelta(days=30)
                elif edit_type=='Quarterly':
                    edit_expiry = edit_join + datetime.timedelta(days=90)
                else:
                    edit_expiry = edit_join + datetime.timedelta(days=365)
                if st.button("Save Changes", key=f"save_edit_{member_id}"):
                    idx = members_df.index[members_df['ID']==member_id][0]
                    members_df.at[idx,'Name'] = edit_name
                    members_df.at[idx,'Phone'] = edit_phone
                    members_df.at[idx,'Membership Type'] = edit_type
                    members_df.at[idx,'Join Date'] = pd.Timestamp(edit_join)
                    members_df.at[idx,'Expiry Date'] = pd.Timestamp(edit_expiry)
                    save_data(members_df)
                    st.success("Member updated successfully")

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
    now_ts = pd.Timestamp(get_ist_time().date())
    df = members_df.copy()
    df['Days Left'] = (df['Expiry Date'] - now_ts).dt.days
    expiring = df[(df['Days Left'] >=0) & (df['Days Left'] <=30)]
    if not expiring.empty:
        st.warning(
            f"Members expiring within 30 days:\n"
            f"{expiring[['ID','Name','Expiry Date','Days Left']].to_string(index=False)}"
        )

# ---------------- MAIN ----------------
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if st.session_state['logged_in']:
        sidebar()
        if 'members_df' not in st.session_state:
            st.session_state['members_df'] = load_data()
        reminders_popup(st.session_state['members_df'])
        st.session_state['members_df'] = member_management(st.session_state['members_df'])
    else:
        login()

if __name__ == "__main__":
    main()
