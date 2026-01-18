import streamlit as st
import google.generativeai as genai

# --- 1. SYSTEM LOGIC: THE REASONING ENGINE ---
# We define your league's unique 'Trade Value' parameters
SYSTEM_PROMPT = """
Role: OOTP-Style Executive Assistant GM.
League Rules: 2-C, CI, MI slots. 6x6 scoring (OPS, QS, SVH).
Strategy: Hard Youth Pivot. Primary window 2026-2028.

YOUR TASK:
1. Grade players on a 0-100 scale:
   - CURRENT: Immediate stats for the 2026 season.
   - POTENTIAL: Value in 2027-2028 based on ZiPS/FanGraphs.
2. Trade Simulation:
   - Calculate 'Surplus Value'. A veteran like Marcell Ozuna has high Current but low Potential. 
   - A prospect like Samuel Basallo has massive 2-C Potential.
3. Verdict: Grade trades (A-F) and explain the 'Why' from an OOTP sim perspective.
"""

# --- 2. LEAGUE DATA (Complete Rosters) ---
# Pulled from your PDF to ensure the AI knows every manager's depth
LEAGUE_DB = {
    "Witness Protection (Me)": ["Ronald Acuna Jr.", "Spencer Strider", "Dylan Crews", "Ceddanne Rafaela", "J.T. Realmuto"],
    "Bobbys Squad": ["Bobby Witt Jr.", "Gunnar Henderson", "Pete Alonso", "Will Smith"],
    "Arm Barn Heros": ["Aaron Judge", "Adley Rutschman", "Fernando Tatis Jr.", "Corbin Carroll"],
    "Happy": ["Juan Soto", "Julio Rodriguez", "Paul Skenes", "Jackson Holliday"],
    "Guti Gang": ["Mookie Betts", "Francisco Lindor", "Ketel Marte", "James Wood"]
}

# --- 3. PERSISTENT STATE ---
if "faab" not in st.session_state: st.session_state.faab = 200.00
if "history" not in st.session_state: st.session_state.history = []
if "messages" not in st.session_state: st.session_state.messages = []

# --- 4. CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    
    st.set_page_config(page_title="Executive Assistant GM", layout="wide")
    st.title("🧠 Dynasty Assistant GM: Reasoning Engine")

    # SIDEBAR: FAAB & Trade Log
    with st.sidebar:
        st.header(f"💰 FAAB: ${st.session_state.faab:.2f}")
        st.subheader("📢 Log Transaction")
        move = st.text_input("Report move:", placeholder="e.g. Happy claimed Walcott")
        if st.button("Update Brain"):
            st.session_state.history.append(move)
            st.success("Roster updated.")

    # 5. THE INTERFACE
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Ask: 'Grade a trade of Acuna for Skenes and a CI prospect'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        
        # Combine rosters, history, and the system logic
        moves_str = "\n".join(st.session_state.history)
        context = f"{SYSTEM_PROMPT}\nROSTERS: {LEAGUE_DB}\nMOVES: {moves_str}\nUSER: {prompt}"
        
        with st.spinner("Simulating trade outcomes..."):
            response = model.generate_content(context)
            ai_text = response.text
            st.session_state.messages.append({"role": "assistant", "content": ai_text})
            st.chat_message("assistant").markdown(ai_text)

except Exception as e:
    st.error(f"Engine Offline: {e}")
