# app.py
import streamlit as st
import pandas as pd
import datetime
import json
import requests
from typing import List, Dict, Any

# --- Page config ---
st.set_page_config(page_title="AI Productivity Brain", page_icon="🚀", layout="wide")

# --- Helpers ---
def parse_tasks(raw_text: str) -> List[Dict[str,Any]]:
    tasks=[]
    for line in raw_text.splitlines():
        line=line.strip()
        if not line: continue
        parts=[p.strip() for p in line.split("|")]
        task=parts[0]
        est=int(parts[1]) if len(parts)>1 and parts[1].isdigit() else None
        due=parts[2] if len(parts)>2 and parts[2] else None
        ctx=parts[3] if len(parts)>3 else ""
        tasks.append({"task":task,"est_min":est,"due":due,"context":ctx})
    return tasks

def tasks_to_text(tasks: List[Dict[str,Any]]) -> str:
    lines=[]
    for t in tasks:
        p=[t["task"]]
        if t.get("est_min"): p.append(str(t["est_min"]))
        if t.get("due"): p.append(t["due"])
        if t.get("context"): p.append(t["context"])
        lines.append(" | ".join(p))
    return "\n".join(lines)

# --- HuggingFace Inference wrapper (safe) ---
def hf_generate(prompt: str, model: str="google/flan-t5-small", max_tokens: int=256, timeout:int=60) -> str:
    """
    Call HuggingFace Inference API. Expects secret HF_TOKEN in Streamlit Secrets (recommended)
    or environment variable HF_TOKEN.
    """
    hf_token = None
    # priority: streamlit secrets, then environment
    try:
        hf_token = st.secrets["HF_TOKEN"]
    except Exception:
        import os
        hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("HuggingFace token not found. Add HF_TOKEN to Streamlit Secrets or set HF_TOKEN env var.")

    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "return_full_text": False}}
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"HuggingFace API error {resp.status_code}: {resp.text}")
    data = resp.json()
    # Safe extraction
    if isinstance(data, list) and isinstance(data[0], dict):
        # common HF output: [{"generated_text": "..."}]
        if "generated_text" in data[0]:
            return data[0]["generated_text"]
    if isinstance(data, dict) and "generated_text" in data:
        return data["generated_text"]
    return json.dumps(data)

# --- AI feature wrappers with fallbacks ---
def ai_prioritize(tasks: List[Dict[str,Any]], work_style: str, day_start:str, day_end:str, tone:str) -> List[Dict[str,Any]]:
    system = "You are a professional, friendly, motivational productivity coach. Respond concisely."
    prompt = f"""{system}
Work style: {work_style}
Work hours: {day_start} - {day_end}
Tone: {tone}

Tasks (one per line: task | estimated_minutes | due_date | context):
{tasks_to_text(tasks)}

Return ONLY a JSON array of objects with keys:
task, est_min, due, priority_score (0-100), quadrant (Do now|Schedule|Delegate|Eliminate), suggested_time, reason
"""
    try:
        out = hf_generate(prompt, model="google/flan-t5-small", max_tokens=512)
        # try to extract JSON array from model output
        s = out.find("[")
        e = out.rfind("]")
        if s!=-1 and e!=-1:
            return json.loads(out[s:e+1])
        return json.loads(out)
    except Exception as ex:
        # fallback deterministic prioritization
        fallback=[]
        for i,t in enumerate(tasks):
            fallback.append({
                "task": t["task"],
                "est_min": t.get("est_min") or 30,
                "due": t.get("due"),
                "priority_score": max(100 - i*10, 10),
                "quadrant": "Do now" if i < 2 else "Schedule",
                "suggested_time": None,
                "reason": "Fallback priority (deterministic)"
            })
        return fallback

def ai_daily_plan(prioritized: List[Dict[str,Any]], date_str: str, day_start:str, day_end:str, focus_minutes:int) -> Dict[str,Any]:
    system = "Create a realistic time-blocked schedule for the day."
    prompt = f"""{system}
Date: {date_str}
Work hours: {day_start} - {day_end}
Focus block: {focus_minutes} minutes
Tasks JSON: {json.dumps(prioritized)}

Return ONLY valid JSON: {{ "date": "{date_str}", "schedule":[ {{ "start":"HH:MM","end":"HH:MM","task":"...","notes":"..." }} ] }}
"""
    try:
        out = hf_generate(prompt, model="google/flan-t5-small", max_tokens=512)
        s = out.find("{")
        e = out.rfind("}")
        if s!=-1 and e!=-1:
            return json.loads(out[s:e+1])
        return json.loads(out)
    except Exception:
        # fallback greedy schedule
        schedule=[]
        start_dt = datetime.datetime.strptime(f"{date_str} {day_start}", "%Y-%m-%d %H:%M")
        for t in prioritized:
            est = t.get("est_min") or 30
            end_dt = start_dt + datetime.timedelta(minutes=est)
            schedule.append({"start": start_dt.strftime("%H:%M"), "end": end_dt.strftime("%H:%M"), "task": t["task"], "notes": t.get("reason","")})
            start_dt = end_dt + datetime.timedelta(minutes=10)
            if start_dt.time() > datetime.datetime.strptime(day_end, "%H:%M").time():
                break
        return {"date": date_str, "schedule": schedule}

def ai_nudges(user_profile: str, tone: str) -> List[str]:
    prompt = f"You are a short motivational coach. User profile: {user_profile}. Tone: {tone}. Provide 3 short nudges (1-2 sentences each)."
    try:
        out = hf_generate(prompt, model="google/flan-t5-small", max_tokens=200)
        # split lines and pick top 3
        lines = [l.strip(" -•0123456789.") for l in out.splitlines() if l.strip()]
        if len(lines) >= 3:
            return lines[:3]
        return [out]
    except Exception:
        return ["Keep going — take one focused step now.","Small consistent progress compounds.","Finish the highest-impact task first."]

# --- UI ---
def main():
    st.title("🚀 AI Productivity Brain")
    st.write("Professional · Friendly · Motivational — turn tasks into prioritized action plans.")

    # Sidebar settings
    with st.sidebar:
        st.header("Settings")
        work_style = st.selectbox("Work style", ["Deep-focus","Sprints (Pomodoro)","Balanced"])
        day_start = st.time_input("Day start", datetime.time(9,0))
        day_end = st.time_input("Day end", datetime.time(17,0))
        focus_minutes = st.slider("Focus block (minutes)", 25, 120, 50)
        user_profile = st.text_area("Short user profile (for nudges)", "Software developer, morning person, tight deadlines.", height=100)
        tone = st.selectbox("Tone", ["professional","friendly","motivational"])
        st.markdown("---")
        st.write("Tip: Add your HF token in Streamlit Secrets as HF_TOKEN.")

    col1, col2 = st.columns([2,1])

    with col1:
        st.subheader("Enter tasks (one per line)")
        st.markdown("Format: `task | minutes | due (YYYY-MM-DD) | context (optional)`")
        sample = ("Finish client proposal | 90 | 2025-11-25 | high value\n"
                  "Fix payment bug | 60 | 2025-11-23 | urgent\n"
                  "Write blog post | 120 | 2025-12-01 | marketing\n"
                  "Prepare slides | 150 | 2025-11-29 | investor")
        raw = st.text_area("Tasks", value=sample, height=240)

        if st.button("Analyze & Prioritize"):
            tasks = parse_tasks(raw)
            if not tasks:
                st.warning("Enter some tasks first.")
            else:
                with st.spinner("Prioritizing..."):
                    prioritized = ai_prioritize(tasks, work_style, day_start.strftime("%H:%M"), day_end.strftime("%H:%M"), tone)
                st.session_state["prioritized"] = prioritized
                df = pd.DataFrame(prioritized)
                st.subheader("Prioritized Tasks")
                st.dataframe(df[["task","priority_score","quadrant","est_min","due","suggested_time","reason"]].fillna(""))

        if st.button("Generate Today's Plan"):
            if "prioritized" not in st.session_state:
                st.warning("Prioritize tasks first.")
            else:
                today = datetime.date.today().isoformat()
                with st.spinner("Creating daily plan..."):
                    plan = ai_daily_plan(st.session_state["prioritized"], today, day_start.strftime("%H:%M"), day_end.strftime("%H:%M"), focus_minutes)
                st.session_state["plan"] = plan
                st.success("Plan generated for " + plan.get("date","today"))
                for b in plan.get("schedule",[]):
                    st.write(f"**{b['start']} - {b['end']}** — {b['task']}")
                    if b.get("notes"):
                        st.caption(b.get("notes"))

    with col2:
        st.subheader("Quick tools")
        if "prioritized" in st.session_state:
            dfp = pd.DataFrame(st.session_state["prioritized"])
            st.download_button("Download prioritized (CSV)", dfp.to_csv(index=False), file_name="prioritized.csv")
        if "plan" in st.session_state:
            st.download_button("Download plan (JSON)", json.dumps(st.session_state["plan"], indent=2), file_name="today_plan.json")

        st.markdown("---")
        st.subheader("Motivation")
        if st.button("Get Motivational Nudges"):
            with st.spinner("Generating nudges..."):
                nudges = ai_nudges(user_profile, tone)
            for n in nudges:
                st.write("•", n)

    st.markdown("---")
    st.caption("Tip: Store your HuggingFace token in Streamlit Secrets as HF_TOKEN. If you don't want to use HF API, the app falls back to deterministic behavior.")

if __name__ == "__main__":
    main()
