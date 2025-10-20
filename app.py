import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# ---------- Constants ----------
OWNER_USERNAME = "vineeth"
OWNER_PASSWORD = "panda@2006"

MEMBER_FILE = "members.xlsx"

# ---------- Initialize session ----------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'role' not in st.session_state:
    st.session_state.role = None
if 'members_df' not in st.session_state:
    try:
        st.session_state.members_df = pd.read_excel(MEMBER_FILE)
    except:
        st.session_state.members_df = pd.DataFrame(columns=[
            'ID', 'Name', 'Join Date', 'Expiry Date', 'Membership Type'
        ])

# ---------- Utility Functions ----------
def save_members():
    st.session_state.members_df.to_excel(MEMBER_FILE, index=False)

def login_page():
    st.title("Gym Membership Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == OWNER_USERNAME and password == OWNER_PASSWORD:
            st.session_state.logged_in = True
            st.session_state.role = "owner"
            st.experimental_rerun()
        else:
            st.error("Invalid username or password!")

def add_member():
    st.subheader("Add Member")
    name = st.text_input("Name")
    membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Yearly"])
    join_date = st.date_input("Join Date", datetime.now())
    expiry_date = st.date_input("Expiry Date", datetime.now() + timedelta(days=30))
    
    if st.button("Add Member"):
        df = st.session_state.members_df
        new_id = 1 if df.empty else df['ID'].max() + 1
        df.loc[len(df)] = [new_id, name, join_date, expiry_date, membership_type]
        save_members()
        st.success(f"Member {name} added!")

def edit_member():
    st.subheader("Edit Member")
    df = st.session_state.members_df
    if df.empty:
        st.info("No members to edit.")
        return
    
    member_id = st.number_input("Enter Member ID to Edit", min_value=1, step=1)
    member = df[df['ID'] == member_id]
    
    if member.empty:
        st.warning("Member ID not found.")
        return
    
    member_index = member.index[0]
    name = st.text_input("Name", member.at[member_index, 'Name'])
    membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Yearly"],
                                   index=["Monthly", "Quarterly", "Yearly"].index(member.at[member_index, 'Membership Type']))
    join_date = st.date_input("Join Date", pd.to_datetime(member.at[member_index, 'Join Date']).date())
    expiry_date = st.date_input("Expiry Date", pd.to_datetime(member.at[member_index, 'Expiry Date']).date())
    
    if st.button("Update Member"):
        df.at[member_index, 'Name'] = name
        df.at[member_index, 'Membership Type'] = membership_type
        df.at[member_index, 'Join Date'] = join_date
        df.at[member_index, 'Expiry Date'] = expiry_date
        save_members()
        st.success(f"Member {name} updated!")

def show_members():
    st.subheader("All Members")
    df = st.session_state.members_df
    if not df.empty:
        st.dataframe(df.sort_values('ID'))
    else:
        st.info("No members found.")

def reminders_popup():
    st.subheader("Membership Expiry Reminders")
    df = st.session_state.members_df.copy()
    if df.empty:
        st.info("No members to show.")
        return
    now = pd.Timestamp.now()
    df['Days Left'] = (pd.to_datetime(df['Expiry Date']) - now).dt.days
    expiring_soon = df[df['Days Left'] <= 7]
    if not expiring_soon.empty:
        st.warning("These memberships are expiring within 7 days:")
        st.table(expiring_soon[['ID','Name','Expiry Date','Days Left']])
    else:
        st.success("No memberships expiring within 7 days.")

# ---------- Main ----------
def main():
    if not st.session_state.logged_in:
        login_page()
        return
    
    st.title("Gym Membership Management")
    menu = ["Add Member", "Edit Member", "Show Members", "Reminders"]
    choice = st.sidebar.selectbox("Menu", menu)
    
    if choice == "Add Member":
        add_member()
    elif choice == "Edit Member":
        edit_member()
    elif choice == "Show Members":
        show_members()
    elif choice == "Reminders":
        reminders_popup()

if __name__ == "__main__":
    main()
