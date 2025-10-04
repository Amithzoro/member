import streamlit as st
import pandas as pd
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Membership Tracker", layout="wide")

# --- Custom CSS ---
st.markdown("""
<style>
    .stSelectbox, .stNumberInput, .stTextInput {
        background-color: #111827 !important;
        color: white !important;
        border-radius: 8px !important;
    }
    .stButton button {
        background-color: #2563eb;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        padding: 0.5em 1em;
        transition: 0.3s;
    }
    .stButton button:hover {
        background-color: #1e40af;
    }
</style>
""", unsafe_allow_html=True)

st.title("💪 Membership & Client Tracker")

# --- Payment modes ---
payment_modes = ["Cash", "UPI", "Card", "Net Banking", "Wallet"]

# --- Load or initialize data ---
def load_data():
    try:
        return pd.read_csv("memberships.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            "Date", "Time", "Client Name", "Phone Number",
            "Membership Type", "Amount", "Payment Mode", "Notes"
        ])

df = load_data()

# --- Entry Form ---
st.subheader("➕ Add New Member / Payment Entry")

col1, col2 = st.columns(2)
with col1:
    client_name = st.text_input("Client Name")
    phone_number = st.text_input("Phone Number (10 digits)")
    membership_type = st.selectbox(
        "Membership Type",
        ["Monthly", "Quarterly", "Half-Yearly", "Yearly", "One-Time Session", "Other"]
    )

with col2:
    amount = st.number_input("Amount (₹)", min_value=0.0, step=0.01)
    payment_mode = st.selectbox("Payment Mode", payment_modes)
    notes = st.text_input("Notes (optional)")

# --- Add Entry ---
if st.button("💾 Add Entry"):
    if not client_name.strip():
        st.error("⚠️ Please enter the client name before saving.")
    elif not phone_number.strip().isdigit() or len(phone_number.strip()) != 10:
        st.error("⚠️ Please enter a valid 10-digit phone number.")
    else:
        now = datetime.now()  # Get real current time every time button is pressed
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%I:%M:%S %p")  # 12-hour format with AM/PM

        new_entry = {
            "Date": current_date,
            "Time": current_time,
            "Client Name": client_name.strip().title(),
            "Phone Number": phone_number.strip(),
            "Membership Type": membership_type,
            "Amount": amount,
            "Payment Mode": payment_mode,
            "Notes": notes
        }

        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv("memberships.csv", index=False)
        st.success(f"✅ Entry added for {client_name.strip().title()} at {current_time}!")

# --- Display and Summary ---
st.subheader("📊 Membership Summary")

if not df.empty:
    st.dataframe(df, use_container_width=True)

    total = df["Amount"].sum()
    st.markdown(f"### 💸 Total Income: ₹{total:.2f}")

    chart_data = df.groupby("Membership Type")["Amount"].sum().sort_values(ascending=False)
    st.bar_chart(chart_data)
else:
    st.info("No entries recorded yet. Start by adding a new member!")
