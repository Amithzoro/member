# membership_app.py
import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.text import MIMEText

# ============================
# CONFIGURATION - EDIT THESE
# ============================
# Admin credentials (change as needed)
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# Owner backup login (enter phone number that admin can use to login if they forget password)
OWNER_PHONE = "7019384280"  # enter without + or with country code if you prefer

# OPTIONAL: Email settings (if you want the app to send emails)
# If you DON'T want emails, leave OWNER_EMAIL blank ("")
OWNER_EMAIL = ""                       # e.g. "youremail@gmail.com"
OWNER_APP_PASSWORD = ""                # Gmail app password (16 chars) if using Gmail SMTP

# File where members are stored
FILE_PATH = "membership.xlsx"

# timezone for join/expiry
TIMEZONE = pytz.timezone("Asia/Kolkata")

# Membership plan durations in days
PLAN_DURATIONS = {
    "1 Month": 30,
    "3 Months": 90,
    "6 Months": 180,
    "12 Months (1 Year)": 365
}

# ============================
# SESSION STATE INIT
# ============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=[
        "Name", "Email", "Phone", "Plan", "Join Date", "Expiry Date", "Password", "Status"
    ])

# ============================
# DATA HANDLING
# ============================
def load_data():
    try:
        df = pd.read_excel(FILE_PATH)
        # ensure columns exist
        for c in ["Name", "Email", "Phone", "Plan", "Join Date", "Expiry Date", "Password", "Status"]:
            if c not in df.columns:
                df[c] = ""
        st.session_state.df = df
    except FileNotFoundError:
        st.session_state.df = pd.DataFrame(columns=[
            "Name", "Email", "Phone", "Plan", "Join Date", "Expiry Date", "Password", "Status"
        ])

def save_data(df):
    df.to_excel(FILE_PATH, index=False)
    st.session_state.df = df
    st.success("💾 Data saved to membership.xlsx")

# ============================
# EMAIL (optional)
# ============================
def send_email_if_configured(to_email, subject, body):
    """Send email only if OWNER_EMAIL and OWNER_APP_PASSWORD are configured."""
    if not OWNER_EMAIL or not OWNER_APP_PASSWORD:
        # email not configured; skip silently
        return False, "Email not configured"
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = OWNER_EMAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(OWNER_EMAIL, OWNER_APP_PASSWORD)
            server.send_message(msg)
        return True, "Email sent"
    except Exception as e:
        return False, str(e)

# ============================
# UTILS: expiry, status, reminders
# ============================
def calculate_expiry(join_datetime_str, plan_label):
    days = PLAN_DURATIONS.get(plan_label, 365)
    join_dt = datetime.strptime(join_datetime_str, "%Y-%m-%d %H:%M:%S")
    expiry_dt = join_dt + timedelta(days=days)
    return expiry_dt.strftime("%Y-%m-%d")

def update_membership_status(df):
    if df.empty:
        return df
    today = datetime.now(TIMEZONE).date()
    # ensure expiry is string fmt yyyy-mm-dd
    def status_of(x):
        try:
            expiry_date = datetime.strptime(str(x), "%Y-%m-%d").date()
            return "Expired" if expiry_date < today else "Active"
        except:
            return "Unknown"
    df["Status"] = df["Expiry Date"].apply(status_of)
    return df

def send_expiry_reminders(df):
    # send reminder emails if configured, for members expiring in 5 days or less (but >0)
    if not OWNER_EMAIL or not OWNER_APP_PASSWORD:
        return
    today = datetime.now(TIMEZONE).date()
    for _, row in df.iterrows():
        try:
            expiry_date = datetime.strptime(str(row["Expiry Date"]), "%Y-%m-%d").date()
            days_left = (expiry_date - today).days
            if 0 < days_left <= 5:
                subject = "Membership Expiry Reminder"
                body = (f"Hello {row['Name']},\n\n"
                        f"Your {row.get('Plan','membership')} will expire on {row['Expiry Date']} ({days_left} day(s) left).\n"
                        f"Please renew to continue enjoying the benefits.\n\nContact owner: {OWNER_PHONE}")
                send_email_if_configured(row["Email"], subject, body)
        except Exception:
            continue

# ============================
# AUTHENTICATION
# ============================
def check_admin_credentials(username, password):
    return username == ADMIN_USER and password == ADMIN_PASSWORD

def login_screen():
    st.header("🔐 Admin Login")
    with st.form("login_form"):
        username = st.text_input("Username or Owner phone")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
        if submitted:
            # owner phone backup login - allow phone either with or without country code
            normalized = username.strip()
            if normalized == OWNER_PHONE or normalized == ("+91" + OWNER_PHONE) or normalized == ("91" + OWNER_PHONE):
                # login via owner phone
                st.session_state.logged_in = True
                load_data()
                st.success("Logged in using owner phone backup ✅")
                st.rerun()
                return
            if check_admin_credentials(username.strip(), password):
                st.session_state.logged_in = True
                load_data()
                st.success("Logged in as admin ✅")
                st.rerun()
                return
            st.error("Invalid credentials")

# ============================
# DASHBOARD / UI
# ============================
def display_dashboard():
    st.subheader("📊 Dashboard")
    df = st.session_state.df.copy()
    df = update_membership_status(df)
    st.session_state.df = df

    total = len(df)
    active = (df["Status"] == "Active").sum() if "Status" in df.columns else 0
    expired = (df["Status"] == "Expired").sum() if "Status" in df.columns else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Members", total)
    c2.metric("Active", int(active))
    c3.metric("Expired", int(expired))

    st.markdown("#### Members")
    if df.empty:
        st.info("No members yet.")
    else:
        st.dataframe(df[["Name","Email","Phone","Plan","Join Date","Expiry Date","Status"]], use_container_width=True)

# ============================
# ADD MEMBER
# ============================
def add_member_ui():
    st.subheader("➕ Add New Member")
    with st.form("add_member_form"):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        plan = st.selectbox("Select Plan", list(PLAN_DURATIONS.keys()))
        password = st.text_input("Password (will be hashed)")
        submitted = st.form_submit_button("Add Member")
        if submitted:
            if not (name and email and phone and password):
                st.warning("Please fill all fields")
                return
            df = st.session_state.df
            if email in df["Email"].values:
                st.error("Member with this email already exists")
                return
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            join_date = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            expiry = calculate_expiry(join_date, plan)
            new = {
                "Name": name,
                "Email": email,
                "Phone": phone,
                "Plan": plan,
                "Join Date": join_date,
                "Expiry Date": expiry,
                "Password": hashed_pw,
                "Status": "Active"
            }
            new_df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
            save_data(new_df)

            # optional welcome email
            if OWNER_EMAIL and OWNER_APP_PASSWORD:
                subject = "Membership Activated"
                body = (f"Hello {name},\n\n"
                        f"Your membership on the {plan} plan is active until {expiry}.\n\n"
                        f"For queries contact owner: {OWNER_PHONE}")
                ok, info = send_email_if_configured(email, subject, body)
                if ok:
                    st.success("Member added and welcome email sent ✅")
                else:
                    st.warning(f"Member added but email failed: {info}")
            else:
                st.success("Member added (email not configured) ✅")

# ============================
# MANAGE MEMBERS
# ============================
def manage_members_ui():
    st.subheader("🛠 Manage Members")
    df = st.session_state.df.copy()
    if df.empty:
        st.info("No members to manage")
        return

    # show editable table without password column
    display_df = df.drop(columns=["Password"], errors="ignore")
    edited = st.data_editor(display_df, use_container_width=True, num_rows="dynamic", key="member_editor")

    if st.button("Save changes"):
        # Merge edited back into st.session_state.df while preserving passwords
        orig = st.session_state.df.copy()
        # We assume indexing lines up; safer approach uses Email as key
        # Let's merge by Email to be robust
        edited_emails = edited["Email"].tolist()
        # Build new_df starting from orig, update fields by email
        for _, row in edited.iterrows():
            email = row["Email"]
            # find index in orig
            idx = orig.index[orig["Email"] == email]
            if len(idx) > 0:
                i = idx[0]
                for col in ["Name","Phone","Plan","Join Date","Expiry Date","Status"]:
                    if col in row:
                        orig.at[i, col] = row[col]
            else:
                # new row added in editor (not recommended) -> append
                new_row = {c: row.get(c, "") for c in orig.columns}
                orig = pd.concat([orig, pd.DataFrame([new_row])], ignore_index=True)
        save_data(orig)
        st.success("Changes saved")
        st.experimental_rerun()

    st.markdown("---")
    st.subheader("🗑 Delete Member")
    emails = df["Email"].tolist()
    if emails:
        to_delete = st.selectbox("Select email to delete", emails)
        if st.button("Delete selected member"):
            df2 = df[df["Email"] != to_delete]
            save_data(df2)
            st.success(f"Deleted {to_delete}")
            st.experimental_rerun()

# ============================
# MAIN
# ============================
st.set_page_config(page_title="Membership Portal", page_icon="🛡️", layout="wide")
st.title("🛡️ Membership Management Portal")
st.caption("Plans: 1 Month, 3 Months, 6 Months, 12 Months. Optional email notifications.")

if not st.session_state.logged_in:
    login_screen()
else:
    # load data once for safety
    load_data()
    # update statuses and optionally send reminders
    st.session_state.df = update_membership_status(st.session_state.df)
    # send reminders only if email configured
    if OWNER_EMAIL and OWNER_APP_PASSWORD:
        send_expiry_reminders(st.session_state.df)

    st.sidebar.markdown(f"**Owner contact:** {OWNER_PHONE}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Add Member", "🛠 Manage Members"])
    with tab1:
        display_dashboard()
    with tab2:
        add_member_ui()
    with tab3:
        manage_members_ui()
