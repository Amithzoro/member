import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, timedelta
from twilio.rest import Client
import random
import string

# ---------------- OWNER DETAILS ----------------
OWNER_EMAIL = "owner@gmail.com"   # owner login email
OWNER_PASSWORD = "owner123"       # owner login password
OWNER_PHONE = "7019384280"        # owner number for SMS reference

# ---------------- TWILIO CONFIG ----------------
TWILIO_SID = "your_twilio_sid_here"
TWILIO_AUTH = "your_twilio_auth_token_here"
TWILIO_PHONE = "+14155238886"  # Your Twilio verified number (SMS enabled)

# ---------------- SESSION STORAGE ----------------
if "users" not in st.session_state:
    st.session_state.users = {
        OWNER_EMAIL: {
            "password": bcrypt.hashpw(OWNER_PASSWORD.encode(), bcrypt.gensalt()),
            "role": "owner"
        }
    }

if "members" not in st.session_state:
    st.session_state.members = []

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = None


# ---------------- UTILITIES ----------------
def send_sms(number, message):
    """Send SMS using Twilio"""
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        client.messages.create(
            from_=TWILIO_PHONE,
            body=message,
            to=f"+91{number}"
        )
        st.success(f"📩 SMS sent successfully to {number}")
    except Exception as e:
        st.warning(f"Failed to send SMS: {e}")


def generate_password(length=8):
    """Generate random password for staff"""
    import random, string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


# ---------------- LOGIN ----------------
def login():
    st.title("🏋️ Gym Membership Portal")
    email = st.text_input("Enter your login email")
    password = st.text_input("Enter your password", type="password")

    if st.button("Login"):
        if email in st.session_state.users:
            hashed_pw = st.session_state.users[email]["password"]
            if bcrypt.checkpw(password.encode(), hashed_pw):
                st.session_state.logged_in = True
                st.session_state.role = st.session_state.users[email]["role"]
                st.success(f"Welcome {st.session_state.role.capitalize()} 👋")
                st.rerun()
            else:
                st.error("❌ Invalid password")
        else:
            st.error("❌ No account found for this email")


# ---------------- OWNER DASHBOARD ----------------
def owner_dashboard():
    st.sidebar.write("Role: Owner")
    st.title("👑 Owner Dashboard")

    # --- Add Staff ---
    st.subheader("Add Staff Member")
    new_email = st.text_input("Staff Email")
    if st.button("Add Staff"):
        if new_email in st.session_state.users:
            st.warning("Staff already exists!")
        else:
            pw = generate_password()
            st.session_state.users[new_email] = {
                "password": bcrypt.hashpw(pw.encode(), bcrypt.gensalt()),
                "role": "staff"
            }
            st.success(f"✅ Staff added successfully. Temporary password: {pw}")

    st.divider()

    # --- Manage Members ---
    st.subheader("📋 Manage Members")
    if st.session_state.members:
        df = pd.DataFrame(st.session_state.members)
        st.dataframe(df, use_container_width=True)

        # --- Send Expiry SMS ---
        member_names = [m["name"] for m in st.session_state.members]
        selected = st.selectbox("Select member to send expiry SMS", member_names)

        if st.button("Send Expiry SMS"):
            member = next((m for m in st.session_state.members if m["name"] == selected), None)
            if member:
                send_sms(
                    member["phone"],
                    f"Dear {member['name']}, your gym membership for {member['plan']} "
                    f"expires on {member['expiry']}. Please renew soon! – {OWNER_PHONE}"
                )

        # --- Delete Member ---
        del_member = st.selectbox("Select member to delete", member_names, key="del")
        if st.button("Delete Member"):
            member = next((m for m in st.session_state.members if m["name"] == del_member), None)
            if member:
                send_sms(
                    member["phone"],
                    f"Dear {member['name']}, your membership has been cancelled. Contact {OWNER_PHONE} for details."
                )
                st.session_state.members = [m for m in st.session_state.members if m["name"] != del_member]
                st.success("Member deleted and notified.")
                st.rerun()
    else:
        st.info("No members yet.")


# ---------------- STAFF DASHBOARD ----------------
def staff_dashboard():
    st.sidebar.write("Role: Staff")
    st.title("👥 Staff Dashboard")

    # --- Add Member ---
    st.subheader("Add New Member")
    name = st.text_input("Member Name")
    phone = st.text_input("Phone Number (10 digits)")
    plan = st.selectbox("Select Plan", ["1 Month", "3 Months", "6 Months", "1 Year"])

    if st.button("Add Member"):
        if name and phone:
            today = datetime.now()
            if plan == "1 Month":
                expiry = today + timedelta(days=30)
            elif plan == "3 Months":
                expiry = today + timedelta(days=90)
            elif plan == "6 Months":
                expiry = today + timedelta(days=180)
            else:
                expiry = today + timedelta(days=365)

            member_data = {
                "name": name,
                "phone": phone,
                "plan": plan,
                "expiry": expiry.strftime("%Y-%m-%d")
            }
            st.session_state.members.append(member_data)

            send_sms(
                phone,
                f"Hi {name}! Your gym membership ({plan}) is now active till {expiry.strftime('%Y-%m-%d')}. 💪"
            )
            st.success("Member added and SMS sent successfully!")
        else:
            st.warning("Please enter all details.")

    st.divider()

    # --- Send Reminder ---
    if st.session_state.members:
        member_names = [m["name"] for m in st.session_state.members]
        selected = st.selectbox("Select member to send reminder", member_names)
        if st.button("Send Reminder SMS"):
            member = next((m for m in st.session_state.members if m["name"] == selected), None)
            if member:
                send_sms(
                    member["phone"],
                    f"Hello {member['name']}, this is a reminder that your {member['plan']} membership "
                    f"expires on {member['expiry']}. Contact us for renewal! 💪"
                )
    else:
        st.info("No members available.")


# ---------------- MAIN APP ----------------
def main():
    if not st.session_state.logged_in:
        login()
    else:
        if st.session_state.role == "owner":
            owner_dashboard()
        elif st.session_state.role == "staff":
            staff_dashboard()
        else:
            st.error("Unknown role!")

        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()


if __name__ == "__main__":
    main()
