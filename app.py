import streamlit as st
import pandas as pd
import datetime
import pytz
import os

# ---------------- CONFIG ----------------
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "gym_data.xlsx"

OWNER_USERNAME = "vineeth"
OWNER_PASSWORD = "panda@2006"  # plaintext
STAFF_CREDENTIALS = {"staff1": "staff123"}

# ---------------- UTILS ----------------
def get_ist_time():
    return datetime.datetime.now(IST)

def load_data():
    if os.path.exists(DB_FILE):
        try:
            members_df = pd.read_excel(DB_FILE, sheet_name='Members')
            logs_df = pd.read_excel(DB_FILE, sheet_name='Logs')
            # Convert dates to datetime
            for col in ['Join Date', 'Expiry Date']:
                if col in members_df.columns:
                    members_df[col] = pd.to_datetime(members_df[col], errors='coerce')
            if 'CheckIn Time' in logs_df.columns:
                logs_df['CheckIn Time'] = pd.to_datetime(logs_df['CheckIn Time'], errors='coerce')
            return members_df, logs_df
        except:
            pass
    # Empty DataFrames if file missing
    members_df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Date','Expiry Date'])
    logs_df = pd.DataFrame(columns=['Member ID','Name','CheckIn Time','Staff User'])
    save_data(members_df, logs_df)
    return members_df, logs_df

def save_data(members_df, logs_df=None):
    with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
        members_df.to_excel(writer, sheet_name='Members', index=False)
        if logs_df is not None:
            logs_df.to_excel(writer, sheet_name='Logs', index=False)

# ---------------- LOGIN ----------------
def login():
    st.title("Gym Membership System")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")
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
def member_management(members_df):
    st.header("Member Management")

    # ---------------- ADD MEMBER ----------------
    with st.expander("Add Member"):
        next_id = int(members_df['ID'].max() + 1) if not members_df.empty else 1
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

    # ---------------- EDIT MEMBER ----------------
    if st.session_state['role'] == 'owner':
        with st.expander("Edit Member"):
            member_id = st.number_input("Enter Member ID to Edit", min_value=1, step=1, key="edit_id")
            if st.button("Load Member", key="load_edit"):
                member = members_df[members_df['ID']==member_id]
                if member.empty:
                    st.error("Member ID not found")
                else:
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
                    if st.button("Update Member", key=f"update_member_{member_id}"):
                        members_df.loc[members_df['ID']==member_id, ['Name','Phone','Membership Type','Join Date','Expiry Date']] = \
                            [name_edit, phone_edit, mtype_edit, join_edit, expiry_edit]
                        save_data(members_df)
                        st.success(f"Member ID {member_id} updated")

    # ---------------- DISPLAY ----------------
    st.subheader("All Members")
    if not members_df.empty:
        df_display = members_df.copy()
        for col in ['Join Date','Expiry Date']:
            df_display[col] = pd.to_datetime(df_display[col], errors='coerce')
            df_display[col] = df_display[col].where(df_display[col].notnull(), None)
        st.dataframe(df_display.sort_values('ID'))
    else:
        st.info("No members yet.")

    return members_df

# ---------------- REMINDERS ----------------
def reminders_popup(members_df):
    if members_df.empty:
        return
    now = get_ist_time()
    df = members_df.copy()
    df['Join Date'] = pd.to_datetime(df['Join Date'], errors='coerce')
    df['Expiry Date'] = pd.to_datetime(df['Expiry Date'], errors='coerce')
    df['Days Left'] = (df['Expiry Date'] - now.date()).apply(lambda x: x.days if pd.notnull(x) else None)
    expired = df[df['Days Left'] < 0]
    soon = df[(df['Days Left']>=0) & (df['Days Left']<=30)]
    if not expired.empty:
        st.warning("⚠️ Some memberships have expired!")
        st.dataframe(expired[['ID','Name','Expiry Date','Days Left']])
    if not soon.empty:
        st.info("ℹ️ Some memberships are expiring soon (within 30 days).")
        st.dataframe(soon[['ID','Name','Expiry Date','Days Left']])

# ---------------- MAIN ----------------
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'members_df' not in st.session_state:
        st.session_state['members_df'], st.session_state['logs_df'] = load_data()

    if st.session_state['logged_in']:
        sidebar()
        reminders_popup(st.session_state['members_df'])
        page = st.sidebar.radio("Go to", ["Members"])
        if page=="Members":
            st.session_state['members_df'] = member_management(st.session_state['members_df'])
    else:
        login()

if __name__ == "__main__":
    main()
