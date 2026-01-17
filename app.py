import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. SETTINGS & ROSTER RULES ---
ROSTER_RULES = """
League Configuration:
- Starting Lineup: 2 Catchers (C), 1B, 2B, 3B, SS, Corner Infield (CI), Middle Infield (MI), 3 OF, 2 UTIL.
- Scoring: [Insert your specific scoring points here for R, HR, RBI, SB, OBP, etc.]
- Strategy: We are in a 'Hard Pivot' to youth. Target windows: 2026-2028.
"""

# --- 2. INITIALIZE AI & MEMORY ---
# Initialize chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Connect to Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # FIXED MODEL NAME: Using 'gemini-1.5-flash' to avoid 404 errors
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error(f"Setup Error: {e}")

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Executive GM Assistant", layout="wide")
st.title("🧠 Dynasty Executive Assistant GM")

# Sidebar: Display Roster Rules for reference
with st.sidebar:
    st.header("📋 Roster Rules")
    st.markdown(ROSTER_RULES)
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# --- 4. THE REASONING INTERFACE ---
# Display existing chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input Box
if prompt := st.chat_input("Ask about a trade, strategy, or roster depth..."):
    # Display user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare the context for the AI
    # We include rules + history so it 'reasons' with context
    context = f"System Rules: {ROSTER_RULES}\n"
    # (Optional: Add your roster from the PDF here too)
    
    with st.spinner("Analyzing league depth and scoring..."):
        try:
            # Generate response
            response = model.generate_content(f"{context}\nUser: {prompt}")
            ai_text = response.text
            
            # Display assistant response
            with st.chat_message("assistant"):
                st.markdown(ai_text)
            st.session_state.messages.append({"role": "assistant", "content": ai_text})
        except Exception as e:
            st.error(f"Error: {e}")
