import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

EXCEL_FILE = "members.xlsx"

# --- Load or create file safely ---
required_cols = ["Username", "Password", "Role", "Join_Date", "Expiry_Date"]

try:
    df = pd.read_excel(EXCEL_FILE)

    # Add any missing columns automatically
    for col in required_cols:
        if col not in df.columns:
            if col in ["Join_Date", "Expiry_Date"]:
                df[col] = datetime.now().strftime("%Y-%m-%d")
            elif col == "Role":
                df[col] = "Member"
            else:
                df[col] = ""
    df.to_excel(EXCEL_FILE, index=False)

except FileNotFoundError:
    # If file not found, create new with defaults
    df = pd.DataFrame({
        "Username": ["vineeth", "staff1", "member1"],
        "Password": ["panda@2006", "staff@123", "mem@123"],
        "Role": ["Owner", "Staff", "Member"],
        "Join_Date": [datetime.now().strftime("%Y-%m-%d")] * 3,
        "Expiry_Date": [
            (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        ]
    })
    df.to_excel(EXCEL_FILE, index=False)
