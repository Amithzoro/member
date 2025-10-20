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
def member_management(df):
    st.header("Member Management")

    # Add Member
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
                    'Expiry Date': expiry
                }])
                df = pd.concat([df, new_member], ignore_index=True)
                save_data(df)
                st.success(f"Added {name} (ID:{next_id})")

    # Edit Member (Owner only)
    if st.session_state['role'] == 'owner':
        st.subheader("Edit Member")
        member_id = st.number_input("Enter Member ID to Edit", min_value=1, step=1, key="edit_id")
        member = df[df['ID']==member_id]
        if not member.empty:
            edit_name = st.text_input("Full Name", member['Name'].values[0], key=f"edit_name_{member_id}")
            edit_phone = st.text_input("Phone", member['Phone'].values[0], key=f"edit_phone_{member_id}")
            edit_type = st.selectbox(
                "Membership Type",
                ['Monthly','Quarterly','Yearly'],
                index=['Monthly','Quarterly','Yearly'].index(member['Membership Type'].values[0]),
                key=f"edit_type_{member_id}"
            )
            join_date = pd.to_datetime(member['Join Date'].values[0])
            edit_join = st.date_input("Join Date", join_date.date(), key=f"edit_join_{member_id}")

            # Compute expiry
            if edit_type=='Monthly':
                edit_expiry = edit_join + datetime.timedelta(days=30)
            elif edit_type=='Quarterly':
                edit_expiry = edit_join + datetime.timedelta(days=90)
            else:
                edit_expiry = edit_join + datetime.timedelta(days=365)

            if st.button("Save Changes", key=f"save_edit_{member_id}"):
                idx = df.index[df['ID']==member_id][0]
                df.at[idx,'Name'] = edit_name
                df.at[idx,'Phone'] = edit_phone
                df.at[idx,'Membership Type'] = edit_type
                df.at[idx,'Join Date'] = pd.Timestamp(edit_join)
                df.at[idx,'Expiry Date'] = pd.Timestamp(edit_expiry)
                save_data(df)
                st.success(f"Member ID {member_id} updated successfully")
        else:
            st.info("Enter a valid Member ID to edit")

    st.subheader("All Members")
    if not df.empty:
        st.dataframe(df.sort_values('ID'))
    else:
        st.info("No members yet.")
    return df

# ---------------- REMINDERS ----------------
def reminders_popup(df):
    st.header("Membership Reminders")
    today = get_ist_time().date()
    df_copy = df.copy()
    df_copy['Days Left'] = (df_copy['Expiry Date'].dt.date - today).apply(lambda x: x.days if pd.notnull(x) else None)

    expired = df_copy[df_copy['Days Left'] < 0]
    soon = df_copy[(df_copy['Days Left'] >=0) & (df_copy['Days Left'] <=30)]

    if not expired.empty:
        st.warning("Expired Memberships!")
        st.dataframe(expired[['ID','Name','Expiry Date','Days Left']])
    if not soon.empty:
        st.info("Memberships expiring soon (<=30 days)")
        st.dataframe(soon[['ID','Name','Expiry Date','Days Left']])
    if expired.empty and soon.empty:
        st.success("No memberships expiring soon.")

# ---------------- MAIN ----------------
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'members_df' not in st.session_state:
        st.session_state['members_df'] = load_data()

    if st.session_state['logged_in']:
        sidebar()
        page = st.sidebar.radio("Go to", ["Members", "Reminders"])
        if page=="Members":
            st.session_state['members_df'] = member_management(st.session_state['members_df'])
        elif page=="Reminders":
            reminders_popup(st.session_state['members_df'])
    else:
        login()

if __name__ == "__main__":
    main()
