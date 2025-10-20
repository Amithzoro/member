import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import os

# ----------------- CONFIG -----------------
OWNER_USERNAME = "vineeth"
OWNER_PASSWORD = "panda@2006"  # store hashed ideally

DATA_FILE = "members.xlsx"

# ----------------- HELPERS -----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_excel(DATA_FILE, engine='openpyxl')
        # Convert date columns to datetime
        for col in ['Join Date', 'Expiry Date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df
    else:
        return pd.DataFrame(columns=['ID', 'Name', 'Membership Type', 'Join Date', 'Expiry Date', 'Phone'])

def save_data(df):
    df.to_excel(DATA_FILE, index=False, engine='openpyxl')

def calculate_expiry(join_date, membership_type):
    if membership_type == "Monthly":
        return join_date + pd.DateOffset(months=1)
    elif membership_type == "Quarterly":
        return join_date + pd.DateOffset(months=3)
    elif membership_type == "Yearly":
        return join_date + pd.DateOffset(years=1)
    else:
        return join_date

# ----------------- LOGIN -----------------
def login_page():
    st.title("Gym Membership Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_clicked = st.button("Login")

    if login_clicked:
        if username == OWNER_USERNAME and password == OWNER_PASSWORD:
            st.session_state['logged_in'] = True
            st.session_state['role'] = 'owner'
            st.session_state['user'] = OWNER_USERNAME
            # trigger rerun by toggling a session state
            st.session_state['login_trigger'] = not st.session_state.get('login_trigger', False)
        else:
            st.error("Invalid username or password")

# ----------------- MEMBER MANAGEMENT -----------------
def member_management(df):
    st.header("Manage Members")

    # Add new member
    st.subheader("Add Member")
    with st.form("add_member_form"):
        name = st.text_input("Name")
        membership_type = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'])
        join_date = st.date_input("Join Date", datetime.today())
        phone = st.text_input("Phone Number")
        submitted = st.form_submit_button("Add Member")
        if submitted:
            new_id = 1 if df.empty else df['ID'].max() + 1
            expiry_date = calculate_expiry(pd.Timestamp(join_date), membership_type)
            df.loc[len(df)] = [new_id, name, membership_type, pd.Timestamp(join_date), expiry_date, phone]
            save_data(df)
            st.success("Member added!")

    # Edit member
    st.subheader("Edit Member")
    if not df.empty:
        member_ids = df['ID'].tolist()
        edit_id = st.selectbox("Select Member ID", member_ids)
        member = df[df['ID'] == edit_id].iloc[0]

        name_edit = st.text_input("Name", member['Name'], key=f"name_{edit_id}")
        mtype_edit = st.selectbox("Membership Type", ['Monthly','Quarterly','Yearly'], 
                                  index=['Monthly','Quarterly','Yearly'].index(member['Membership Type']), key=f"type_{edit_id}")
        join_edit = st.date_input("Join Date", member['Join Date'].date() if pd.notnull(member['Join Date']) else datetime.today(), key=f"join_{edit_id}")
        phone_edit = st.text_input("Phone", member['Phone'], key=f"phone_{edit_id}")
        if st.button("Update Member", key=f"update_{edit_id}"):
            df.loc[df['ID'] == edit_id, ['Name','Membership Type','Join Date','Expiry Date','Phone']] = [
                name_edit, mtype_edit, pd.Timestamp(join_edit), calculate_expiry(pd.Timestamp(join_edit), mtype_edit), phone_edit
            ]
            save_data(df)
            st.success("Member updated!")

    # Display members
    if not df.empty:
        st.subheader("All Members")
        st.dataframe(df.sort_values('ID'))

    return df

# ----------------- REMINDERS -----------------
def reminders_popup(df):
    if df.empty:
        return
    now = pd.Timestamp.now()
    df['Days Left'] = (df['Expiry Date'] - now).dt.days
    soon_expiring = df[df['Days Left'] <= 7]
    if not soon_expiring.empty:
        st.warning("Some memberships are expiring soon!")
        st.table(soon_expiring[['ID','Name','Membership Type','Days Left']])

# ----------------- MAIN -----------------
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['login_trigger'] = False

    if not st.session_state['logged_in']:
        login_page()
        return

    df = load_data()
    st.session_state['members_df'] = df
    st.session_state['members_df'] = member_management(st.session_state['members_df'])
    reminders_popup(st.session_state['members_df'])

# ----------------- RUN -----------------
if __name__ == "__main__":
    main()
