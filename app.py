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

# ---------------- UTILITIES ----------------
def get_ist_time():
    return datetime.datetime.now(IST)

def format_time(dt):
    return dt.strftime("%Y-%m-%d %I:%M:%S %p")

# ---------------- DATABASE ----------------
def load_data():
    """Load data and fix missing columns if needed"""
    cols = ['ID', 'Name', 'Phone', 'Membership Type', 'Join Time', 'Expiry Time']
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            for c in cols:
                if c not in df.columns:
                    df[c] = None
            df = df[cols]  # reorder
            if not df.empty:
                if 'Join Time' in df.columns:
                    df['Join Time'] = pd.to_datetime(df['Join Time'], errors='coerce')
                if 'Expiry Time' in df.columns:
                    df['Expiry Time'] = pd.to_datetime(df['Expiry Time'], errors='coerce')
            return df
        except Exception as e:
            st.warning(f"Error reading file: {e}")
    return pd.DataFrame(columns=cols)

def save_data(df):
    with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

# ---------------- LOGIN ----------------
def login_page():
    st.title("🏋️ Gym Membership System")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == OWNER_USERNAME and password == OWNER_PASSWORD:
            st.session_state.update({'logged_in': True, 'role': 'owner', 'user': username})
            st.rerun()
        elif username in STAFF_CREDENTIALS and password == STAFF_CREDENTIALS[username]:
            st.session_state.update({'logged_in': True, 'role': 'staff', 'user': username})
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

# ---------------- SIDEBAR ----------------
def sidebar():
    st.sidebar.title(f"👤 {st.session_state['user']}")
    st.sidebar.write(f"**Role:** {st.session_state['role'].capitalize()}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

# ---------------- MEMBER MANAGEMENT ----------------
def member_management(df):
    st.header("👥 Member Management")
    role = st.session_state['role']

    # Add members (both can)
    with st.expander("➕ Add New Member"):
        next_id = int(df['ID'].max() + 1) if not df.empty else 1
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
                st.error("⚠️ Please fill all fields")
            else:
                new = pd.DataFrame([{
                    'ID': next_id,
                    'Name': name,
                    'Phone': phone,
                    'Membership Type': mtype,
                    'Join Time': join_time,
                    'Expiry Time': expiry_time
                }])
                df = pd.concat([df, new], ignore_index=True)
                save_data(df)
                st.success(f"✅ Added {name}")
                st.rerun()

    st.subheader("📋 Members List")
    if not df.empty:
        df_display = df.copy()
        df_display['Join Time'] = df_display['Join Time'].apply(lambda x: format_time(x) if pd.notnull(x) else "")
        df_display['Expiry Time'] = df_display['Expiry Time'].apply(lambda x: format_time(x) if pd.notnull(x) else "")
        st.dataframe(df_display.sort_values('ID'))

        if role == 'owner':
            st.markdown("### ✏️ Edit / Delete Member")
            ids = df['ID'].dropna().astype(int).tolist()
            if ids:
                selected_id = st.number_input("Enter Member ID", min_value=min(ids), step=1)
                if selected_id in df['ID'].values:
                    row = df.loc[df['ID'] == selected_id].iloc[0]
                    new_name = st.text_input("Edit Name", row['Name'])
                    new_phone = st.text_input("Edit Phone", row['Phone'])
                    new_type = st.selectbox("Edit Type", ['Monthly', 'Quarterly', 'Yearly'], 
                                            index=['Monthly','Quarterly','Yearly'].index(row['Membership Type']))

                    if st.button("Update"):
                        df.loc[df['ID']==selected_id, ['Name','Phone','Membership Type']] = [new_name,new_phone,new_type]
                        save_data(df)
                        st.success("✅ Updated successfully")
                        st.rerun()

                    if st.button("Delete"):
                        df = df[df['ID'] != selected_id]
                        save_data(df)
                        st.success("🗑️ Deleted successfully")
                        st.rerun()
            else:
                st.info("No members to edit")
    else:
        st.info("No members yet.")
    return df

# ---------------- REMINDERS ----------------
def reminders_popup(df):
    if df.empty or 'Expiry Time' not in df.columns:
        return
    now = get_ist_time()
    df['Days Left'] = (df['Expiry Time'].dt.date - now.date()).apply(lambda x: x.days if pd.notnull(x) else None)
    expired = df[df['Days Left'] < 0]
    soon = df[(df['Days Left'] >= 0) & (df['Days Left'] <= 7)]

    if not expired.empty:
        st.warning("⚠️ Some memberships have **expired!**")
        st.dataframe(expired[['ID','Name','Phone','Membership Type','Expiry Time','Days Left']])
    if not soon.empty:
        st.info("📅 Memberships expiring within 7 days")
        st.dataframe(soon[['ID','Name','Phone','Membership Type','Expiry Time','Days Left']])

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
        st.session_state['members_df'] = member_management(st.session_state['members_df'])
    else:
        login_page()

if __name__ == "__main__":
    main()
