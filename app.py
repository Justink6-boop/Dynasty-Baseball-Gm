import streamlit as st
import google.generativeai as genai

# --- 1. SYSTEM BRAIN: FYPD, SCORING, & OOTP LOGIC ---
SYSTEM_PROMPT = """
Role: OOTP-Style Executive Assistant GM. Window: 2026-2028.
Scoring (6x6): HR, RBI, R, SB, AVG, OPS | QS, BAA, ERA, SVH, K/9, WHIP.
Roster Rules: 2-C, 1B, 2B, 3B, SS, CI, MI, 3 OF, 2 UTIL.

VALUATION RULES:
- Grade players 0-100 on CURRENT (2026) and POTENTIAL (2027-2028).
- FYPD Pick Valuation: 1.01-1.03 (85-95), 1.04-1.08 (70-84), Late 1st (55-69).
- Trade Grading: Use 'Surplus Value' logic. Picks are 'Currency'. 
- Scouting: Monitor top 2026 names like Tatsuya Imai, Eli Willits, and Roch Cholowsky.
"""

# --- 2. INITIAL LEAGUE DATA (From PDF) ---
INITIAL_ROSTERS = {
    "Witness Protection (Me)": ["Ronald Acuna Jr.", "Dylan Crews", "2026 Pick 1.02"],
    "Bobbys Squad": ["Bobby Witt Jr.", "Gunnar Henderson", "2026 Pick 1.05"],
    "Arm Barn Heros": ["Aaron Judge", "Adley Rutschman", "2026 Pick 2.01"],
    "Guti Gang": ["Mookie Betts", "Francisco Lindor", "James Wood"],
    "Happy": ["Juan Soto", "Julio Rodriguez", "Jackson Merrill", "Ethan Salas"]
}

# --- 3. PERSISTENT MEMORY ---
if "faab" not in st.session_state: st.session_state.faab = 200.00
if "league_rosters" not in st.session_state: st.session_state.league_rosters = INITIAL_ROSTERS
if "history" not in st.session_state: st.session_state.history = []
if "messages" not in st.session_state: st.session_state.messages = []

# --- 4. THE CONNECTION (No-Error Auto-Scanner) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # This scanner prevents 404 errors by picking an available model
    available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    target = 'models/gemini-2.0-flash' if 'models/gemini-2.0-flash' in str(available) else available[0]
    model = genai.GenerativeModel(target)
    
    st.set_page_config(page_title="Executive Assistant GM", layout="wide")
    st.title("🧠 Dynasty Assistant: FYPD & Trade Logic")

    # SIDEBAR: FAAB & Pick Tracker
    with st.sidebar:
        st.header(f"💰 FAAB: ${st.session_state.faab:.2f}")
        bid = st.number_input("Deduct FAAB:", min_value=0.0, step=1.0)
        if st.button("Update Cash"):
            st.session_state.faab -= bid
            st.rerun()

        st.divider()
        st.subheader("📢 Update League Memory")
        move = st.text_input("e.g. 'Bobbys Squad traded 1.05 for Fried'")
        if st.button("Commit Change"):
            st.session_state.history.append(move)
            st.success("Roster state updated!")

    # 5. THE INTERFACE
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Analyze a trade or FYPD pick..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        
        # Combine everything for the Assistant
        moves_log = "\n".join(st.session_state.history)
        full_context = f"{SYSTEM_PROMPT}\nROSTERS: {st.session_state.league_rosters}\nMOVES: {moves_log}\nUSER: {prompt}"
        
        with st.spinner("Analyzing surplus value and draft equity..."):
            response = model.generate_content(full_context)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.chat_message("assistant").markdown(response.text)

except Exception as e:
    st.error(f"Reasoning Engine Offline: {e}")
