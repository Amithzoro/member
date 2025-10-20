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
STAFF_CREDENTIALS = {"staff1": "staff123"}

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

    # Initialize session_state keys
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['role'] = None
        st.session_state['user'] = None

    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")
    
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

    # Add Member Section
    with st.expander("Add Member"):
        next_id = int(df['ID'].max() + 1) if not df.empty else 1
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
                    'Join Date': join,
                    'Expiry Date': expiry
                }])
                df = pd.concat([df, new_member], ignore_index=True)
                save_data(df)
                st.success(f"Added {name} (ID:{next_id})")

    # Edit Member Section (Owner only)
    if st.session_state['role'] == 'owner':
        with st.expander("Edit Member"):
            member_id = st.number_input("Enter Member ID to Edit", min_value=1, step=1, key="edit_id")
            member = df[df['ID'] == member_id]
            if not member.empty:
                name_edit = st.text_input("Full Name", member['Name'].values[0], key=f"edit_name_{member_id}")
                phone_edit = st.text_input("Phone", member['Phone'].values[0], key=f"edit_phone_{member_id}")
                mtype_edit = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'],
                                          index=['Monthly','Quarterly','Yearly'].index(member['Membership Type'].values[0]),
                                          key=f"edit_type_{member_id}")
                join_edit = st.date_input("Join Date", member['Join Date'].values[0].date(), key=f"edit_join_{member_id}")
                if mtype_edit=='Monthly':
                    expiry_edit = join_edit + datetime.timedelta(days=30)
                elif mtype_edit=='Quarterly':
                    expiry_edit = join_edit + datetime.timedelta(days=90)
                else:
                    expiry_edit = join_edit + datetime.timedelta(days=365)
                if st.button("Update Member", key=f"update_{member_id}"):
                    idx = df.index[df['ID']==member_id][0]
                    df.at[idx,'Name'] = name_edit
                    df.at[idx,'Phone'] = phone_edit
                    df.at[idx,'Membership Type'] = mtype_edit
                    df.at[idx,'Join Date'] = join_edit
                    df.at[idx,'Expiry Date'] = expiry_edit
                    save_data(df)
                    st.success(f"Updated Member ID {member_id}")

    # Display Members
    st.subheader("All Members")
    if not df.empty:
        st.dataframe(df.sort_values('ID'))
    else:
        st.info("No members yet.")

    return df

# ---------------- REMINDERS ----------------
def reminders_popup(df):
    st.header("Membership Reminders")
    now = get_ist_time()
    df_copy = df.copy()
    df_copy['Days Left'] = (df_copy['Expiry Date'].dt.date - now.date()).apply(lambda x: x.days if pd.notnull(x) else None)

    expired = df_copy[df_copy['Days Left'] < 0]
    soon = df_copy[(df_copy['Days Left']>=0) & (df_copy['Days Left']<=30)]

    if not expired.empty:
        st.warning("Expired Members:")
        st.dataframe(expired)
    if not soon.empty:
        st.info("Members expiring in 30 days:")
        st.dataframe(soon)

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
