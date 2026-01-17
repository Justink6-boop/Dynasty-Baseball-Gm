import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. CONFIGURATION & ROSTER RULES ---
# Custom Lineup Requirements: 2 C, 1B, 2B, 3B, SS, CI, MI, 3+ OF, UTIL
LINEUP_RULES = """
Lineup Slots: 2 Catchers, 1B, 2B, 3B, SS, Corner Infielder (1B/3B), 
Middle Infielder (2B/SS), 3 Outfielders, 2 Utility.
"""

# --- 2. THE LEAGUE BRAIN (From your PDF) ---
# This dictionary now acts as the 'Source of Truth' for the AI
league_db = {
    "Team Witness Protection": ["Ronald Acuna Jr.", "Spencer Strider", "Dylan Crews", "Jesus Made", "Colt Emerson", "J.T. Realmuto", "Dillon Dingler"],
    "Bobbys Squad": ["Bobby Witt Jr.", "Gunnar Henderson", "Pete Alonso", "Josh Naylor", "Chase Burns"],
    "Happy": ["Juan Soto", "Julio Rodriguez", "Paul Skenes", "Jackson Holliday", "Ethan Salas"]
}

# --- 3. AI REASONING SETUP ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error("API Key missing. Add GEMINI_API_KEY to Streamlit Secrets.")

# --- 4. APP UI ---
st.set_page_config(page_title="Dynasty Executive Assistant", layout="wide")
st.title("🧠 Dynasty Executive Assistant GM")

# Sidebar: Transaction History
if "trades" not in st.session_state: st.session_state.trades = []
with st.sidebar:
    st.header("📝 League Transaction Log")
    new_move = st.text_input("Report a move (e.g., 'Happy traded Soto to Guti Gang')")
    if st.button("Log Transaction"):
        st.session_state.trades.append(new_move)
    for t in st.session_state.trades: st.caption(f"✅ {t}")

# MAIN INTERFACE: Trade Grader & Reasoner
st.subheader("Trade Evaluation & Strategy Reasoning")
trade_query = st.text_area("Describe a potential trade or ask a strategy question:", 
                          placeholder="Example: Should I trade J.T. Realmuto for a 1st rounder and a young CI?")

if st.button("Analyze Trade"):
    # The 'Professional GM' Prompt
    full_prompt = f"""
    You are a Pro Dynasty GM. 
    League Rules: {LINEUP_RULES}. 
    My Team (Witness Protection): {league_db['Team Witness Protection']}.
    Recent League Moves: {st.session_state.trades}.
    User Question: {trade_query}
    
    INSTRUCTIONS:
    1. Grade the trade (A-F).
    2. Analyze the 'Positional Scarcity' (we must start 2 Catchers and a CI/MI).
    3. Determine if it fits our 'Youth Pivot' strategy.
    4. Provide a 'Verdict' on whether to accept, decline, or counter.
    """
    
    with st.spinner("Reasoning through roster impact..."):
        try:
            response = model.generate_content(full_prompt)
            st.markdown("---")
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Error connecting to reasoning engine: {e}")
