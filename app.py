import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import os

# --- INITIALIZATION & MEMORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "trade_log" not in st.session_state:
    # Load permanent memory from a file
    if os.path.exists("trade_history.json"):
        with open("trade_history.json", "r") as f:
            st.session_state.trade_log = json.load(f)
    else:
        st.session_state.trade_log = []

# --- CONFIG AI ENGINE ---
# Set up Gemini to handle the reasoning
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# --- UI LAYOUT ---
st.set_page_config(page_title="Dynasty GM: Deep Assistant", layout="wide")
st.title("🧠 Professional GM Reasoning Engine")

# SIDEBAR: Permanent League Knowledge
with st.sidebar:
    st.header("📜 League Transaction Log")
    for idx, trade in enumerate(st.session_state.trade_log):
        st.info(f"Trade {idx+1}: {trade}")
    
    if st.button("Clear Log"):
        st.session_state.trade_log = []
        if os.path.exists("trade_history.json"): os.remove("trade_history.json")
        st.rerun()

# --- CHAT INTERFACE ---
# Display historical messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Query Input
if prompt := st.chat_input("Ask about a trade, or report a league move..."):
    # 1. Display user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Reasoning Logic
    # We provide the AI with your roster and history for context
    context = f"My Team: Witness Protection (Core: Acuna, Strider, Crews, Made, Emerson). " \
              f"League History: {st.session_state.trade_log}. " \
              f"User Question: {prompt}"
    
    with st.spinner("Assistant is reasoning..."):
        response = model.generate_content(context)
        ai_response = response.text

    # 3. Detect if a trade happened and save it
    if "traded" in prompt.lower() or "deal" in prompt.lower():
        st.session_state.trade_log.append(prompt)
        with open("trade_history.json", "w") as f:
            json.dump(st.session_state.trade_log, f)

    # 4. Display AI response
    with st.chat_message("assistant"):
        st.markdown(ai_response)
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
