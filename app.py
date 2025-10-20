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
OWNER_PASSWORD = "panda@2006"  # plaintext
STAFF_CREDENTIALS = {"staff1": "staff123"}  # optional initial staff

# ---------------- UTILS ----------------
def get_ist_time():
    return datetime.datetime.now(IST)

# ---------------- DATABASE ----------------
def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE, sheet_name='Members')
            if not df.empty:
                df['Join Date'] = pd.to_datetime(df['Join Date'], errors='coerce')
                df['Expiry Date'] = pd.to_datetime(df['Expiry Date'], errors='coerce')
            else:
                df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Date','Expiry Date','Last CheckIn'])
            return df
        except:
            pass
    df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Date','Expiry Date','Last CheckIn'])
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

    if st.session_state['role'] in ['owner','staff']:
        with st.expander("Add Member"):
            next_id = int(df['ID'].max()+1) if not df.empty else 1
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
            if st.button("Add Member", key="add_btn"):
                if not name or not phone:
                    st.error("All fields required")
                else:
                    new_member = pd.DataFrame([{
                        'ID': next_id,
                        'Name': name,
                        'Phone': phone,
                        'Membership Type': mtype,
                        'Join Date': join,
                        'Expiry Date': expiry,
                        'Last CheckIn': pd.NaT
                    }])
                    df = pd.concat([df, new_member], ignore_index=True)
                    save_data(df)
                    st.success(f"Added {name} (ID:{next_id})")

    if st.session_state['role']=='owner' and not df.empty:
        with st.expander("Edit Member"):
            member_id = st.number_input("Enter Member ID to Edit", min_value=1, step=1, key="edit_id")
            member = df[df['ID']==member_id]
            if not member.empty:
                member_index = member.index[0]

                name_edit = st.text_input("Name", member['Name'].values[0], key=f"name_{member_id}")
                phone_edit = st.text_input("Phone", member['Phone'].values[0], key=f"phone_{member_id}")
                mtype_edit = st.selectbox(
                    "Membership Type", 
                    ['Monthly','Quarterly','Yearly'], 
                    index=['Monthly','Quarterly','Yearly'].index(member['Membership Type'].values[0]),
                    key=f"type_{member_id}"
                )

                # Handle Join Date safely
                join_val = member['Join Date'].values[0]
                if pd.isnull(join_val):
                    join_val = get_ist_time().date()
                else:
                    join_val = join_val.date()
                join_edit = st.date_input("Join Date", join_val, key=f"join_{member_id}")

                # Handle Expiry Date safely
                expiry_val = member['Expiry Date'].values[0]
                if pd.isnull(expiry_val):
                    if mtype_edit=='Monthly':
                        expiry_val = join_edit + datetime.timedelta(days=30)
                    elif mtype_edit=='Quarterly':
                        expiry_val = join_edit + datetime.timedelta(days=90)
                    else:
                        expiry_val = join_edit + datetime.timedelta(days=365)
                else:
                    expiry_val = expiry_val.date()
                expiry_edit = st.date_input("Expiry Date", expiry_val, key=f"expiry_{member_id}")

                if st.button("Save Changes", key=f"save_{member_id}"):
                    df.at[member_index,'Name'] = name_edit
                    df.at[member_index,'Phone'] = phone_edit
                    df.at[member_index,'Membership Type'] = mtype_edit
                    df.at[member_index,'Join Date'] = join_edit
                    df.at[member_index,'Expiry Date'] = expiry_edit
                    save_data(df)
                    st.success(f"Member ID {member_id} updated!")

    st.subheader("All Members")
    if not df.empty:
        st.dataframe(df.sort_values('ID'))
    else:
        st.info("No members yet.")
    return df

# ---------------- REMINDERS ----------------
def reminders_popup(df):
    now = get_ist_time()
    df = df.copy()
    df['Join Date'] = pd.to_datetime(df['Join Date'], errors='coerce')
    df['Expiry Date'] = pd.to_datetime(df['Expiry Date'], errors='coerce')
    df['Days Left'] = (df['Expiry Date'] - now).dt.days
    expired = df[df['Days Left'] < 0]
    expiring_soon = df[(df['Days Left'] >= 0) & (df['Days Left'] <= 30)]
    if not expired.empty:
        st.warning(f"{len(expired)} members have expired memberships!")
    if not expiring_soon.empty:
        st.info(f"{len(expiring_soon)} members expiring within 30 days.")

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
        st.session_state['members_df'] = member_management(st.session_state['members_df'])
    else:
        login()

# ---------------- RUN ----------------
main()
