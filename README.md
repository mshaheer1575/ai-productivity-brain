# AI Productivity Brain

**AI Productivity Brain** is a web-based app that helps you prioritize tasks, create daily plans, and get motivational nudges using AI.

---

## How to Use

1. Open the app in your browser.
2. In the **Tasks** section, enter your tasks, one per line, using this format:  

Example:
Finish client proposal | 90 | 2025-11-25 | high value
Fix payment bug | 60 | 2025-11-23 | urgent
Write blog post | 120 | 2025-12-01 | marketing

3. Click **Analyze & Prioritize** to see tasks sorted by urgency and importance.
4. Click **Generate Today's Plan** to create a realistic daily schedule.
5. Click **Get Motivational Nudges** to receive 3 short AI-powered motivational messages.
6. You can download the prioritized tasks (CSV) and daily plan (JSON) for later use.

---

## API Used

- **HuggingFace Inference API**
- Model: `google/flan-t5-small`
- Purpose: AI task prioritization, daily plan generation, motivational nudges

---
## Notes

- Make sure to **add your HuggingFace token** in Streamlit Secrets:  
Key: `HF_TOKEN`  
Value: `hf_your_token_here`  
- If the token is missing or invalid, the app will show an error and stop.  
- App works offline/fallback deterministically if API fails.
