import streamlit as st
import pandas as pd
import datetime
import json

st.set_page_config(page_title="AI Productivity Brain", page_icon="🚀")

st.title("🚀 AI Productivity Brain")
st.write("Your professional, friendly, motivational AI assistant for tasks and planning.")

# --- Sample Tasks Input ---
raw_tasks = st.text_area("Enter your tasks (format: task | minutes | due-date | context)", height=200, placeholder="""
Write report | 60 | 2025-11-25 | urgent
Design homepage | 45 | 2025-11-28 | creative
Email clients | 20 | 2025-11-22 | communication
""")

# --- Dummy AI Prioritize Function ---
def ai_prioritize(tasks):
    prioritized = []
    for i, t in enumerate(tasks):
        prioritized.append({
            "task": t.split("|")[0].strip(),
            "est_min": int(t.split("|")[1].strip()) if len(t.split("|"))>1 else 30,
            "priority_score": 50 + i*10,
            "quadrant": "Do now" if i%2==0 else "Schedule",
            "reason": "Sample AI reasoning"
        })
    return prioritized

# --- Parse tasks and show prioritized ---
if st.button("Analyze & Prioritize"):
    tasks = [line for line in raw_tasks.splitlines() if line.strip()]
    if not tasks:
        st.warning("Enter some tasks first.")
    else:
        prioritized = ai_prioritize(tasks)
        df = pd.DataFrame(prioritized)
        st.subheader("📌 Prioritized Tasks")
        st.dataframe(df)

# --- Motivational Nudge ---
if st.button("Motivational Nudge"):
    nudges = [
        "Keep going — small steps lead to big results!",
        "Stay consistent and focused.",
        "Every task completed is progress!"
    ]
    st.subheader("🔥 Motivational Nudges")
    for n in nudges:
        st.write("•", n)
