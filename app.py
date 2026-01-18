import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# --- 1. CONNECTION ENGINE ---
def get_gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

SHEET_ID = "1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A" 

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="Executive Assistant GM", layout="wide")
st.title("🧠 Dynasty GM Engine: Full Executive Suite")

if "faab" not in st.session_state: st.session_state.faab = 200.00

try:
    # DATA CONNECTION
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws = sh.get_worksheet(0)
    roster_ws = sh.get_worksheet(1) 

    permanent_history = history_ws.col_values(1)
    raw_rosters = roster_ws.get_all_values()

    # AI SETUP
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    flash_models = [m for m in available_models if 'flash' in m]
    model = genai.GenerativeModel(flash_models[0] if flash_models else 'gemini-1.5-flash')

    # SHARED AI FUNCTION
    def get_gm_advice(category, user_input=""):
        context = f"""
        LIVE_ROSTERS: {raw_rosters}
        TRADE_HISTORY: {permanent_history}
        SCORING: 6x6 (OPS, QS, SVH)
        GOAL: Dynasty Rebuild / Youth Pivot (2026-2028 Window)
        CATEGORY: {category}
        """
        full_query = f"{context}\nQuery: {user_input if user_input else 'Provide a strategic report based on this category.'}"
        return model.generate_content(full_query).text

    # 3. SIDEBAR TRANSACTIONS
    with st.sidebar:
        st.header(f"💰 FAAB: ${st.session_state.faab:.2f}")
        spent = st.number_input("Log Spent:", min_value=0.0)
        if st.button("Update Budget"): st.session_state.faab -= spent

        st.divider()
        st.subheader("📢 Log Transaction")
        move = st.text_input("Trade/Claim:", placeholder="e.g. 'Fried for Skenes'")
        if st.button("Update Live Database"):
            with st.spinner("Rewriting League Data..."):
                update_prompt = f"CURRENT_DATA: {raw_rosters}\nMOVE: {move}\nTASK: Update the list of lists. Return ONLY the Python list."
                response = model.generate_content(update_prompt)
                try:
                    new_roster_list = eval(response.text.strip())
                    roster_ws.clear()
                    roster_ws.update(new_roster_list)
                    history_ws.append_row([move])
                    st.success("Database Synced!")
                    st.rerun()
                except: st.error("AI Format Error. Try again.")

    # 4. EXECUTIVE TABS
    tabs = st.tabs([
        "🔥 Trade Analysis", 
        "📋 Live Ledger", 
        "🎯 Priority Candidates", 
        "🕵️‍♂️ Full Scouting", 
        "💸 FAAB & Strategy"
    ])

    with tabs[0]:
        st.subheader("OOTP-Style Trade Consultant")
        trade_q = st.chat_input("Grade a trade or ask for a suggestion...")
        if trade_q:
            st.markdown(get_gm_advice("Trade Negotiation & Grading", trade_q))

    with tabs[1]:
        st.subheader("Current League Database")
        st.dataframe(pd.DataFrame(raw_rosters), use_container_width=True)
        st.subheader("Recent Activity")
        for trade in permanent_history[-5:]: # Show last 5
            st.write(f"✅ {trade}")

    with tabs[2]:
        st.subheader("Priority Targets (Trade & Free Agency)")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Identify Trade Targets"):
                st.markdown(get_gm_advice("Priority Trade Candidates"))
        with col2:
            if st.button("Identify Priority Free Agents"):
                st.markdown(get_gm_advice("Free Agent Priority List"))

    with tabs[3]:
        st.subheader("Deep Scouting Hub")
        player_q = st.text_input("Enter player name for fit analysis:")
        if player_q:
            st.markdown(get_gm_advice("Player Fit & Scouting Report", player_q))

    with tabs[4]:
        st.subheader("Financial & Long-Term Strategy")
        if st.button("Generate Strategy Report"):
            st.markdown(get_gm_advice("FAAB Allocation & 3-Year Plan"))

except Exception as e:
    st.error(f"System Error: {e}")
