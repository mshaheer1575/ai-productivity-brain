# app.py
import streamlit as st
import pandas as pd
import datetime
import json
import requests
from typing import List, Dict, Any

st.set_page_config(page_title="AI Productivity Brain", page_icon="🚀", layout="wide")

# ----------------- Helpers -----------------
def parse_tasks(raw_text: str) -> List[Dict[str,Any]]:
    tasks = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        task = parts[0]
        est = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        due = parts[2] if len(parts) > 2 and parts[2] else None
        ctx = parts[3] if len(parts) > 3 else ""
        tasks.append({"task": task, "est_min": est, "due": due, "context": ctx})
    return tasks

def tasks_to_lines(tasks: List[Dict[str,Any]]) -> str:
    lines=[]
    for t in tasks:
        parts=[t["task"]]
        if t.get("est_min"): parts.append(str(t["est_min"]))
        if t.get("due"): parts.append(t["due"])
        if t.get("context"): parts.append(t["context"])
        lines.append(" | ".join(parts))
    return "\n".join(lines)

# ----------------- HuggingFace API call -----------------
def call_hf_model(prompt: str, model: str="google/flan-t5-small", max_new_tokens: int=256, timeout: int=30) -> str:
    """
    Call HuggingFace Inference API. Expects HF token in Streamlit secrets as HF_TOKEN.
    Returns generated text or raises Exception.
    """
    try:
        hf_token = st.secrets["HF_TOKEN"]
    except Exception as e:
        raise RuntimeError("HF_TOKEN not found in Streamlit secrets. Add it in app settings.") from e

    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": max_new_tokens}}
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"HuggingFace API error {resp.status_code}: {resp.text}")
    data = resp.json()
    # Some HF endpoints return [{'generated_text': '...'}] or [{'generated_text': '...','warnings':...}]
    # or a dict. We try safe extraction:
    if isinstance(data, list) and "generated_text" in data[0]:
        return data[0]["generated_text"]
    if isinstance(data, dict) and "generated_text" in data:
        return data["generated_text"]
    # Last fallback: stringify
    return json.dumps(data)

# ----------------- AI wrappers with fallback -----------------
def ai_prioritize(tasks: List[Dict[str,Any]], work_style: str, day_start: str, day_end: str, tone: str) -> List[Dict[str,Any]]:
    """
    Ask the model to return JSON array of objects:
    {task, est_min, due, priority_score (0-100), quadrant, suggested_time, reason}
    """
    system = ("You are a professional, friendly, motivational productivity coach. "
              "Provide concise, business-aware prioritization.")
    tasks_text = tasks_to_lines(tasks)
    prompt = f"""{system}

Work style: {work_style}
Work hours: {day_start} - {day_end}
Tone: {tone}

Tasks (one per line: task | estimated_minutes | due_date | context):
{tasks_text}

Return ONLY valid JSON: an array of objects with keys:
task, est_min, due, priority_score, quadrant (Do now|Schedule|Delegate|Eliminate), suggested_time, reason
"""
    try:
        out = call_hf_model(prompt, max_new_tokens=512)
        # try extract JSON substring if model adds commentary
        start = out.find("[")
        end = out.rfind("]")
        if start != -1 and end != -1:
            j = out[start:end+1]
            return json.loads(j)
        return json.loads(out)
    except Exception as e:
        # fallback heuristic: simple scoring
        fallback=[]
        for i,t in enumerate(tasks):
            fallback.append({
                "task": t["task"],
                "est_min": t.get("est_min") or 30,
                "due": t.get("due"),
                "priority_score": max(100 - i*10, 10),
                "quadrant": "Do now" if i<2 else "Schedule",
                "suggested_time": None,
                "reason": "Fallback: default priority"
            })
        return fallback

def ai_daily_plan(prioritized: List[Dict[str,Any]], date_str: str, day_start: str, day_end: str, focus_minutes:int) -> Dict[str,Any]:
    system = "You are a time-blocking assistant creating a practical day schedule."
    prompt = f"""{system}
Date: {date_str}
Work hours: {day_start} - {day_end}
Preferred focus block: {focus_minutes} minutes

Tasks (JSON array): {json.dumps(prioritized)}

Return ONLY valid JSON:
{{ "date": "{date_str}", "schedule": [ {{ "start": "HH:MM", "end": "HH:MM", "task":"...", "notes":"..." }} ] }}
"""
    try:
        out = call_hf_model(prompt, max_new_tokens=512)
        start = out.find("{")
        end = out.rfind("}")
        if start!=-1 and end!=-1:
            j = out[start:end+1]
            return json.loads(j)
        return json.loads(out)
    except Exception:
        # greedy fallback schedule
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
    system = "You are a short motivational coach with business insight."
    prompt = f"{system}\nUser profile: {user_profile}\nTone: {tone}\nProvide 3 short motivational nudges (1-2 sentences each)."
    try:
        out = call_hf_model(prompt, max_new_tokens=200)
        # try split into lines
        lines = [l.strip("-•0123456789. ") for l in out.splitlines() if l.strip()]
        if len(lines) >= 3:
            return lines[:3]
        return [out]
    except Exception:
        return ["Keep going — take one focused step now.", "Small wins compound into big gains.", "Focus and finish the most impactful task first."]

# ----------------- UI -----------------
def main():
    st.title("🚀 AI Productivity Brain")
    st.write("Professional · Friendly · Motivational — turns tasks into prioritized plans.")

    with st.sidebar:
        st.header("Settings")
        work_style = st.selectbox("Work style", ["Deep-focus (long blocks)","Sprints (Pomodoro)","Balanced"])
        day_start = st.time_input("Day start", datetime.time(9,0))
        day_end = st.time_input("Day end", datetime.time(17,0))
        focus_minutes = st.slider("Focus block minutes", 25, 120, 50)
        user_profile = st.text_area("Short user profile (for personalized nudges)", "Software developer, morning person, tight deadlines.", height=100)
        tone = st.selectbox("Tone", ["professional","friendly","motivational"])
        st.markdown("---")
        st.write("Demo tips: Paste 6 tasks, click Analyze → Generate Plan → Nudges.")

    col1, col2 = st.columns([2,1])

    with col1:
        st.subheader("Enter tasks (one per line)")
        st.markdown("Format: `task | est_minutes | due_date(YYYY-MM-DD) | context` (context optional)")
        sample = ("Finish client proposal | 90 | 2025-11-25 | high value\n"
                  "Fix payment bug | 60 | 2025-11-23 | urgent\n"
                  "Write blog post | 120 | 2025-12-01 | marketing\n"
                  "Prepare slides | 150 | 2025-11-29 | investor")
        raw = st.text_area("Tasks", value=sample, height=220)

        if st.button("Analyze & Prioritize"):
            tasks = parse_tasks(raw)
            if not tasks:
                st.warning("Please enter tasks first.")
            else:
                with st.spinner("Asking the AI to prioritize..."):
                    prioritized = ai_prioritize(tasks, work_style, day_start.strftime("%H:%M"), day_end.strftime("%H:%M"), tone)
                st.success("Prioritization complete.")
                st.session_state["prioritized"] = prioritized
                df = pd.DataFrame(prioritized)
                st.subheader("Prioritized tasks")
                st.dataframe(df[["task","priority_score","quadrant","est_min","due","suggested_time","reason"]].fillna(""))

                # show simple stats
                quads = df["quadrant"].value_counts().to_dict()
                st.markdown("**Eisenhower matrix counts**")
                st.write(quads)

        if st.button("Generate Today's Plan"):
            if "prioritized" not in st.session_state:
                st.warning("Generate prioritization first.")
            else:
                today = datetime.date.today().isoformat()
                with st.spinner("Creating time-blocked plan..."):
                    plan = ai_daily_plan(st.session_state["prioritized"], today, day_start.strftime("%H:%M"), day_end.strftime("%H:%M"), focus_minutes)
                st.session_state["plan"] = plan
                st.success("Plan generated for " + plan.get("date","today"))
                for item in plan.get("schedule", []):
                    st.write(f"**{item['start']} - {item['end']}** — {item['task']}")
                    if item.get("notes"):
                        st.caption(item.get("notes"))

    with col2:
        st.subheader("Quick Tools")
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
    st.caption("Tip: For Streamlit deployment, store your HuggingFace token in Streamlit Secrets as HF_TOKEN.")

if __name__ == "__main__":
    main()
