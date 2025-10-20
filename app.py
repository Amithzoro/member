import streamlit as st
import pandas as pd
import datetime
import pytz
import os

# ---------------- CONFIG ----------------
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "gym_data.xlsx"

OWNER_USERNAME = "vineeth"
OWNER_PASSWORD = "panda@2006"  # plaintext for simplicity
STAFF_CREDENTIALS = {"staff1": "staff123"}  # Add more if needed

# ---------------- UTILITIES ----------------
def get_ist_time():
    return datetime.datetime.now(IST)

# ---------------- DATABASE ----------------
def load_data():
    if os.path.exists(DB_FILE):
        try:
            members_df = pd.read_excel(DB_FILE, sheet_name='Members')
            if not members_df.empty:
                members_df['Join Date'] = pd.to_datetime(members_df['Join Date']).dt.date
                members_df['Expiry Date'] = pd.to_datetime(members_df['Expiry Date']).dt.date
            else:
                members_df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Date','Expiry Date'])
            return members_df
        except Exception as e:
            st.warning(f"Error loading data: {e}")
    # if file missing or error
    members_df = pd.DataFrame(columns=['ID','Name','Phone','Membership Type','Join Date','Expiry Date'])
    save_data(members_df)
    return members_df

def save_data(members_df):
    with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
        members_df.to_excel(writer, sheet_name='Members', index=False)

# ---------------- LOGIN ----------------
def login():
    st.title("🏋️ Gym Membership System")
    st.markdown("### Please log in")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Owner login
        if username == OWNER_USERNAME and password == OWNER_PASSWORD:
            st.session_state['logged_in'] = True
            st.session_state['role'] = 'owner'
            st.session_state['user'] = OWNER_USERNAME
            st.rerun()
        # Staff login
        elif username in STAFF_CREDENTIALS and password == STAFF_CREDENTIALS[username]:
            st.session_state['logged_in'] = True
            st.session_state['role'] = 'staff'
            st.session_state['user'] = username
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

# ---------------- SIDEBAR ----------------
def sidebar():
    st.sidebar.title("🏠 Dashboard")
    st.sidebar.markdown(f"**User:** {st.session_state['user']}")
    st.sidebar.markdown(f"**Role:** {st.session_state['role'].capitalize()}")

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

# ---------------- MEMBER MANAGEMENT ----------------
def member_management(members_df):
    st.header("👥 Member Management")

    # Only owner can add new members
    if st.session_state['role'] == 'owner':
        with st.expander("➕ Add New Member"):
            next_id = int(members_df['ID'].max() + 1) if not members_df.empty else 1
            name = st.text_input("Full Name")
            phone = st.text_input("Phone")
            mtype = st.selectbox("Membership Type", ['Monthly', 'Quarterly', 'Yearly'])
            join = st.date_input("Join Date", get_ist_time().date())

            # Calculate expiry date
            if mtype == 'Monthly':
                expiry = join + datetime.timedelta(days=30)
            elif mtype == 'Quarterly':
                expiry = join + datetime.timedelta(days=90)
            else:
                expiry = join + datetime.timedelta(days=365)

            if st.button("Add Member"):
                if not name or not phone:
                    st.error("⚠️ All fields are required.")
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
                    st.success(f"✅ Member added: {name} (ID: {next_id})")

    st.subheader("📋 All Members")
    if not members_df.empty:
        st.dataframe(members_df.sort_values('ID'), use_container_width=True)
    else:
        st.info("No members found.")
    return members_df

# ---------------- REMINDERS ----------------
def reminders(members_df):
    st.header("⏰ Membership Reminders")

    if st.session_state['role'] != 'owner':
        st.warning("Only the owner can view reminders.")
        return

    today = get_ist_time().date()
    df = members_df.copy()
    df['Days Left'] = (df['Expiry Date'] - today).apply(lambda x: x.days)

    # Expired members
    st.subheader("❌ Expired Members")
    expired = df[df['Days Left'] < 0]
    if not expired.empty:
        st.dataframe(expired[['ID','Name','Phone','Membership Type','Expiry Date','Days Left']], use_container_width=True)
    else:
        st.info("✅ No expired memberships.")

    # Soon to expire
    st.subheader("⚠️ Expiring Within 30 Days")
    soon = df[(df['Days Left'] >= 0) & (df['Days Left'] <= 30)]
    if not soon.empty:
        st.dataframe(soon[['ID','Name','Phone','Membership Type','Expiry Date','Days Left']], use_container_width=True)
    else:
        st.info("🎉 No members expiring soon.")

# ---------------- MAIN ----------------
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        sidebar()
        if 'members_df' not in st.session_state:
            st.session_state['members_df'] = load_data()

        page = st.sidebar.radio("Navigate", ["Members"] + (["Reminders"] if st.session_state['role'] == 'owner' else []))

        if page == "Members":
            st.session_state['members_df'] = member_management(st.session_state['members_df'])
        elif page == "Reminders":
            reminders(st.session_state['members_df'])
    else:
        login()

if __name__ == "__main__":
    main()
