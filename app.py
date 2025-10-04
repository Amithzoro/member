import streamlit as st
import pandas as pd
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Membership Tracker", layout="wide")

# --- Custom CSS for clean dark UI ---
st.markdown("""
<style>
    .stSelectbox, .stNumberInput, .stTextInput, .stDateInput, .stTimeInput {
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

# --- Define payment modes ---
payment_modes = ["Cash", "UPI", "Card", "Net Banking", "Wallet"]

# --- Load or initialize data ---
@st.cache_data
def load_data():
    try:
        return pd.read_csv("memberships.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            "Date", "Time", "Client Name", "Membership Type",
            "Amount", "Payment Mode", "Notes"
        ])

df = load_data()

# --- Membership Entry Form ---
st.subheader("➕ Add New Member / Payment Entry")

col1, col2 = st.columns(2)
with col1:
    date = st.date_input("Date", datetime.now().date())
    time = st.time_input("Time", datetime.now().time().replace(microsecond=0))
    client_name = st.text_input("Client Name")
    membership_type = st.selectbox(
        "Membership Type",
        ["Monthly", "Quarterly", "Half-Yearly", "Yearly", "One-Time Session", "Other"]
    )

with col2:
    amount = st.number_input("Amount (₹)", min_value=0.0, step=0.01)
    payment_mode = st.selectbox("Payment Mode", payment_modes)
    notes = st.text_input("Notes (optional)")

# --- Add Button ---
if st.button("💾 Add Entry"):
    if not client_name.strip():
        st.error("⚠️ Please enter the client name before saving.")
    else:
        new_entry = {
            "Date": date.strftime("%Y-%m-%d"),
            "Time": time.strftime("%H:%M"),
            "Client Name": client_name.strip().title(),
            "Membership Type": membership_type,
            "Amount": amount,
            "Payment Mode": payment_mode,
            "Notes": notes
        }

        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv("memberships.csv", index=False)
        st.success(f"✅ Entry added for {client_name.strip().title()}!")

# --- Display and Summary ---
st.subheader("📊 Membership Summary")

if not df.empty:
    st.dataframe(df, use_container_width=True)

    total = df["Amount"].sum()
    st.markdown(f"### 💸 Total Income: ₹{total:.2f}")

    # --- Chart: Income by Membership Type ---
    chart_data = df.groupby("Membership Type")["Amount"].sum().sort_values(ascending=False)
    st.bar_chart(chart_data)
else:
    st.info("No entries recorded yet. Start by adding a new member!")
