import streamlit as st
import requests

st.title("AI Productivity Brain – HuggingFace API")

# Load token safely from Streamlit Secrets
HF_TOKEN = st.secrets["HF_TOKEN"]

API_URL = "https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

def analyze_text(text):
    payload = {"inputs": text}
    response = requests.post(API_URL, headers=headers, json=payload)
    try:
        return response.json()
    except:
        return {"error": "Invalid response from API"}

st.subheader("Enter text to analyze sentiment")
user_text = st.text_area("Type something…")

if st.button("Analyze"):
    if user_text.strip() == "":
        st.warning("Please enter text first.")
    else:
        result = analyze_text(user_text)
        st.write("### Result:")
        st.json(result)
