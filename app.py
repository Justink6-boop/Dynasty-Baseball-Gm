import streamlit as st
import google.generativeai as genai

# --- 1. THE LEAGUE KNOWLEDGE BASE ---
# This acts as the 'Brain' the AI references before answering
LEAGUE_INTEL = """
TEAM ROSTERS:
- [span_6](start_span)Team Witness Protection (User): Catchers: J.T. Realmuto, Dillon Dingler. Infield: Yandy Diaz (1B), Jake Cronenworth (2B), Ke'Bryan Hayes (3B), Ceddanne Rafaela (SS/OF). Outfield: Ronald Acuna Jr, Dylan Crews, JJ Bleday. Pitchers: Dylan Cease, Max Fried, Spencer Strider.[span_6](end_span)
- Bobbys Squad: Catchers: Will Smith. Infield: Bobby Witt Jr (SS), Gunnar Henderson (SS), Pete Alonso (1B), Josh Naylor (1B). [span_7](start_span)Outfield: Jasson Dominguez, Luis Robert Jr.[span_7](end_span)
- Arm Barn Heros: Catchers: Adley Rutschman. Infield: Trea Turner (SS), Marcus Semien (2B), Royce Lewis (3B). [span_8](start_span)Outfield: Aaron Judge, Fernando Tatis Jr, Corbin Carroll.[span_8](end_span)
- Happy: Catchers: Francisco Alvarez. Infield: Jose Ramirez (3B), Corey Seager (SS), Freddie Freeman (1B). [span_9](start_span)Outfield: Juan Soto, Julio Rodriguez, Jackson Merrill.[span_9](end_span)
- Guti Gang: Catchers: Cal Raleigh. Infield: Mookie Betts (SS), Francisco Lindor (SS), Ketel Marte (2B). [span_10](start_span)Outfield: James Wood, Cody Bellinger.[span_10](end_span)

LINEUP RULES: 
[span_11](start_span)Must start 2 Catchers, 1B, 2B, 3B, SS, Corner Infield (CI), Middle Infield (MI), 3 OF, 2 UTIL.[span_11](end_span)
STRATEGY: User is in a 'Hard Youth Pivot' targeting a 2026-2028 winning window.
"""

# --- 2. AI CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    
    st.set_page_config(page_title="Dynasty Executive Assistant", layout="wide")
    st.title("🧠 Dynasty Executive Assistant GM")

    # Initialize Session Memory
    if "messages" not in st.session_state: st.session_state.messages = []
    if "trades" not in st.session_state: st.session_state.trades = []

    # SIDEBAR: Trade Logger (Memory)
    with st.sidebar:
        st.header("📝 League Transaction Log")
        st.caption("Tell the AI who moved where to update the brain.")
        new_trade = st.text_input("Log a move:", placeholder="e.g. Bobbys Squad traded Witt Jr for Skenes")
        if st.button("Update League History"):
            st.session_state.trades.append(new_trade)
            st.success("Trade recorded in memory!")
        
        st.subheader("Current Session History")
        for t in st.session_state.trades: st.caption(f"✅ {t}")

    # 3. CHAT INTERFACE
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Propose a trade or ask for strategy advice..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        
        # Combine everything for the AI's thought process
        trade_history = "\n".join(st.session_state.trades)
        full_context = f"{LEAGUE_INTEL}\n\nRECENT TRADES LOGGED:\n{trade_history}\n\nQUESTION: {prompt}"
        
        with st.spinner("Analyzing league depth and roster impact..."):
            response = model.generate_content(full_context)
            ai_text = response.text
            
            st.session_state.messages.append({"role": "assistant", "content": ai_text})
            st.chat_message("assistant").markdown(ai_text)

except Exception as e:
    st.error(f"System Error: {e}")
