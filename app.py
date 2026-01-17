import streamlit as st
import google.generativeai as genai

# --- 1. SYSTEM RULES (Your 2-C, CI, MI logic) ---
ROSTER_CONTEXT = """
You are a Pro Dynasty GM. 
Rules: 2-Catcher league, CI and MI slots required. 
Strategy: Youth Pivot (2026-2028 window).
"""

# --- 2. THE CONNECTION ---
try:
    # Ensure the key is pulled from Secrets
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    
    # FIXED: Using the full model path to prevent 404 errors
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    
    st.title("🧠 Dynasty Reasoning Engine")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])

    if prompt := st.chat_input("Ask a strategy question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        # Deep Reasoning
        response = model.generate_content(f"{ROSTER_CONTEXT}\nUser: {prompt}")
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.chat_message("assistant").write(response.text)

except Exception as e:
    st.error(f"Reasoning Engine Offline: {e}")