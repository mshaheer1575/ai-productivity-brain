import streamlit as st
import pandas as pd
import requests
import datetime

# ---------------- Page Setup ----------------
st.set_page_config(page_title="AI Productivity Brain", page_icon="🚀")
st.title("🚀 AI Productivity Brain")
st.write("Professional, friendly, motivational AI assistant for tasks and planning.")

# ---------------- HuggingFace API Setup ----------------
API_URL = "https://api-inference.huggingface.co/models/bigscience/bloomz-560m"

# Option 1: Direct token (replace with your token)
# API_TOKEN = "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"

# Option 2 (Safer): Use Streamlit secrets
# st.secrets.toml file: HF_TOKEN = "your_token"
# API_TOKEN = st.secrets["HF_TOKEN"]

# For simplicity here, we'll use direct token:
API_TOKEN = "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"

headers = {"Authorization": f"Bearer {API_TOKEN}"}

def call_hf_api(prompt):
    payload = {"inputs": prompt}
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        try:
            return response.json()[0]["generated_text"]
        except:
            return "Error parsing API response."
    else:
        return f"API Error: {response.status_code}"

# ---------------- Input Tasks ----------------
raw_tasks = st.text_area(
    "Enter your tasks (format: task | minutes | due-date | context)",
    height=200,
    placeholder="""
Write report | 60 | 2025-11-25 | urgent
Design homepage | 45 | 2025-11-28 | creative
Email clients | 20 | 2025-11-22 | communication
"""
)

# ---------------- Analyze & Prioritize ----------------
if st.button("Analyze & Prioritize"):
    tasks = [line for line in raw_tasks.splitlines() if line.strip()]
    if not tasks:
        st.warning("Please enter some tasks first!")
    else:
        prompt = "Prioritize these tasks by urgency and importance:\n" + "\n".join(tasks)
        result = call_hf_api(prompt)
        st.subheader("📌 AI Prioritized Tasks")
        st.text(result)

# ---------------- Motivational Nudge ----------------
if st.button("Motivational Nudge"):
    prompt = "Give 3 short motivational nudges for productivity."
    nudges = call_hf_api(prompt)
    st.subheader("🔥 Motivation")
    st.text(nudges)

# ---------------- Optional: Display today's date ----------------
st.sidebar.header("Settings")
st.sidebar.write("Today:", datetime.date.today().isoformat())
