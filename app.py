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
STAFF_CREDENTIALS = {"staff1": "staff123", "staff2": "staff456"}

# ---------------- UTILITIES ----------------
def get_ist_time():
    """Return current time in Asia/Kolkata timezone"""
    return datetime.datetime.now(IST)

def format_time(dt):
    """Return formatted time as 12-hour with AM/PM"""
    return dt.strftime("%Y-%m-%d %I:%M:%S %p")

def load_data():
    if os.path.exists(DB_FILE):
        try:
            members_df = pd.read_excel(DB_FILE)
            if not members_df.empty:
                members_df['Join Time'] = pd.to_datetime(members_df['Join Time'])
                members_df['Expiry Time'] = pd.to_datetime(members_df['Expiry Time'])
                return members_df
        except Exception as e:
            st.warning(f"Error loading data: {e}")
    return pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Time','Expiry Time'])

def save_data(members_df):
    with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
        members_df.to_excel(writer, index=False)

# ---------------- LOGIN ----------------
def login_page():
    st.title("🏋️ Gym Membership System")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == OWNER_USERNAME and password == OWNER_PASSWORD:
            st.session_state['logged_in'] = True
            st.session_state['role'] = 'owner'
            st.session_state['user'] = username
            st.experimental_rerun()
        elif username in STAFF_CREDENTIALS and password == STAFF_CREDENTIALS[username]:
            st.session_state['logged_in'] = True
            st.session_state['role'] = 'staff'
            st.session_state['user'] = username
            st.experimental_rerun()
        else:
            st.error("❌ Invalid username or password")

# ---------------- SIDEBAR ----------------
def sidebar():
    st.sidebar.title(f"👤 User: {st.session_state['user']}")
    st.sidebar.markdown(f"**Role:** {st.session_state['role'].capitalize()}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()

# ---------------- MEMBER MANAGEMENT ----------------
def member_management(members_df):
    st.header("👥 Member Management")
    role = st.session_state['role']

    if role in ['owner', 'staff']:
        with st.expander("➕ Add New Member"):
            next_id = int(members_df['ID'].max() + 1) if not members_df.empty else 1
            name = st.text_input("Full Name")
            phone = st.text_input("Phone")
            mtype = st.selectbox("Membership Type", ['Monthly', 'Quarterly', 'Yearly'])
            join_time = get_ist_time()

            if mtype == 'Monthly':
                expiry_time = join_time + datetime.timedelta(days=30)
            elif mtype == 'Quarterly':
                expiry_time = join_time + datetime.timedelta(days=90)
            else:
                expiry_time = join_time + datetime.timedelta(days=365)

            if st.button("Add Member"):
                if not name or not phone:
                    st.error("⚠️ All fields required")
                else:
                    new_member = pd.DataFrame([{
                        'ID': next_id,
                        'Name': name,
                        'Phone': phone,
                        'Membership Type': mtype,
                        'Join Time': join_time,
                        'Expiry Time': expiry_time
                    }])
                    members_df = pd.concat([members_df, new_member], ignore_index=True)
                    save_data(members_df)
                    st.success(f"✅ Added member: {name}")
                    st.experimental_rerun()

    st.subheader("📋 Members List")

    if not members_df.empty:
        df_display = members_df.copy()
        df_display['Join Time'] = df_display['Join Time'].apply(format_time)
        df_display['Expiry Time'] = df_display['Expiry Time'].apply(format_time)
        st.dataframe(df_display.sort_values('ID'))

        if role == 'owner':
            st.markdown("### ✏️ Edit / Delete Member")
            selected_id = st.number_input("Enter Member ID to Edit/Delete", min_value=1, step=1)
            if selected_id in members_df['ID'].values:
                member_row = members_df[members_df['ID'] == selected_id].iloc[0]
                new_name = st.text_input("Edit Name", member_row['Name'])
                new_phone = st.text_input("Edit Phone", member_row['Phone'])
                new_mtype = st.selectbox("Edit Membership Type", 
                                         ['Monthly', 'Quarterly', 'Yearly'], 
                                         index=['Monthly', 'Quarterly', 'Yearly'].index(member_row['Membership Type']))
                new_join = st.date_input("Edit Join Date", member_row['Join Time'].date())
                new_expiry = st.date_input("Edit Expiry Date", member_row['Expiry Time'].date())

                if st.button("Update Member"):
                    members_df.loc[members_df['ID'] == selected_id, 
                                   ['Name','Phone','Membership Type','Join Time','Expiry Time']] = [
                        new_name, new_phone, new_mtype,
                        datetime.datetime.combine(new_join, member_row['Join Time'].time()),
                        datetime.datetime.combine(new_expiry, member_row['Expiry Time'].time())
                    ]
                    save_data(members_df)
                    st.success("✅ Member updated successfully")
                    st.experimental_rerun()

                if st.button("Delete Member"):
                    members_df = members_df[members_df['ID'] != selected_id]
                    save_data(members_df)
                    st.success("🗑️ Member deleted successfully")
                    st.experimental_rerun()
            else:
                st.info("Enter a valid Member ID")
    else:
        st.info("No members yet.")

    return members_df

# ---------------- REMINDERS ----------------
def reminders_popup(members_df):
    if members_df.empty:
        return

    now = get_ist_time()
    members_df['Days Left'] = (members_df['Expiry Time'].dt.date - now.date()).apply(lambda x: x.days)

    expiring_soon = members_df[members_df['Days Left'].between(0, 7)]
    expired = members_df[members_df['Days Left'] < 0]

    if not expired.empty:
        st.warning("⚠️ Some memberships have **expired!**")
        st.dataframe(expired[['ID','Name','Phone','Membership Type','Expiry Time','Days Left']])

    if not expiring_soon.empty:
        st.info("📅 Memberships expiring **within 7 days**:")
        st.dataframe(expiring_soon[['ID','Name','Phone','Membership Type','Expiry Time','Days Left']])

# ---------------- MAIN ----------------
def main():
    st.set_page_config("Gym System", layout="wide")

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        sidebar()
        if 'members_df' not in st.session_state:
            st.session_state['members_df'] = load_data()

        reminders_popup(st.session_state['members_df'])

        page = st.sidebar.radio("Go to", ["Members"])
        if page == "Members":
            st.session_state['members_df'] = member_management(st.session_state['members_df'])
    else:
        login_page()

if __name__ == "__main__":
    main()
