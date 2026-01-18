import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from io import BytesIO
import requests
import json

# --- 1. CONNECTION & UTILITY ENGINE ---
def get_gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def parse_roster_matrix(matrix, team_names):
    league_data = {}
    if not matrix: return league_data
    header_row = matrix[0]
    for col_idx, cell_value in enumerate(header_row):
        team_name = str(cell_value).strip()
        if team_name in team_names:
            league_data[team_name] = []
            for row in matrix[1:]:
                if col_idx < len(row):
                    p_name = str(row[col_idx]).strip()
                    if p_name and not p_name.endswith(':'):
                        league_data[team_name].append(p_name)
    return league_data

def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rosters')
    return output.getvalue()

SHEET_ID = "1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A"

# --- 2. MASTER LEAGUE DATA ---
def get_initial_league():
    return {
        "Witness Protection (Me)": {}, "Bobbys Squad": {}, "Arm Barn Heros": {}, 
        "Guti Gang": {}, "Happy": {}, "Hit it Hard Hit it Far": {}, 
        "ManBearPuig": {}, "Milwaukee Beers": {}, "Seiya Later": {}, "Special Eds": {}
    }

# --- 3. PAGE CONFIG ---
st.set_page_config(page_title="Executive GM Terminal", layout="wide")
st.title("🧠 Dynasty GM Suite: Executive Terminal")

# --- 4. MAIN APP LOGIC ---
try:
    init_data = get_initial_league()
    team_list = list(init_data.keys())
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws = sh.get_worksheet(0)
    roster_ws = sh.get_worksheet(1)

    permanent_history = history_ws.col_values(1)
    raw_roster_matrix = roster_ws.get_all_values()
    parsed_rosters = parse_roster_matrix(raw_roster_matrix, team_list)

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    flash_models = [m for m in available_models if 'flash' in m]
    model = genai.GenerativeModel(flash_models[0] if flash_models else 'gemini-1.5-pro')

    def call_openrouter(model_id, persona, prompt):
        try:
            r = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}", "HTTP-Referer": "https://streamlit.io"},
                data=json.dumps({"model": model_id, "messages": [{"role": "system", "content": persona}, {"role": "user", "content": prompt}]}),
                timeout=30
            )
            return r.json()['choices'][0]['message']['content'] if r.status_code == 200 else f"Error {r.status_code}"
        except: return "Connection Timeout."

    def get_multi_ai_opinions(user_query, task_type="Trade"):
        directive = """
        STRATEGY: Hybrid Retool (30/70 split).
        EVALUATION PROTOCOL: Analyze from BOTH sides.
        1. OUR GAIN: Does it help our 2027 window?
        2. THEIR GAIN: Why would they say yes? If no one wins but us, flag as 'Unrealistic'.
        3. LIVE DATA: Cross-reference Jan 2026 ZiPS and Dynasty Rankings.
        """
        with st.spinner("📡 Scanning Jan 2026 Projections & Rankings..."):
            search_query = f"Provide 2026 ZiPS, Dynasty Tiers, and latest news for: {user_query}."
            live_intel = call_openrouter("perplexity/sonar", "League Arbitrator.", search_query)
        
        briefing = f"ROSTERS: {json.dumps(parsed_rosters)}\nINTEL: {live_intel}\nINPUT: {user_query}\nGOAL: {directive}"
        
        return {
            'Perplexity': live_intel,
            'Gemini': model.generate_content(f"Analyze from both sides. Provide a 'Fairness Score' (1-100). {briefing}").text,
            'ChatGPT': call_openrouter("openai/gpt-4o", "Market Expert. Focus on trade equity.", briefing),
            'Claude': call_openrouter("anthropic/claude-3.5-sonnet", "Strategy Architect. Focus on roster fit.", briefing)
        }

    # --- 5. UI TABS ---
    tabs = st.tabs(["🔁 Terminal", "🔥 Trade Analysis", "🔍 Trade Finder", "📋 Ledger", "🎯 Priority", "🕵️‍♂️ Scouting", "💎 Sleepers", "📜 History"])

    # --- TAB 1: TWO-SIDED ANALYSIS ---
    with tabs[1]:
        st.subheader("⚖️ Two-Sided Trade Arbitrator")
        trade_q = st.chat_input("Enter trade: (e.g., 'My Fried for his Skenes')")
        if trade_q:
            results = get_multi_ai_opinions(trade_q)
            with st.expander("📡 Live Field Report", expanded=True): st.write(results['Perplexity'])
            st.divider()
            c1, c2, c3 = st.columns(3)
            with c1: st.info("🟢 Gemini (Fairness)"); st.write(results['Gemini'])
            with c2: st.info("🔵 GPT-4o (Value)"); st.write(results['ChatGPT'])
            with c3: st.info("🟠 Claude (Fit)"); st.write(results['Claude'])

    # --- TAB 2: TRADE FINDER ---
    with tabs[2]:
        st.subheader("🔍 Automated Trade Finder")
        col1, col2 = st.columns(2)
        with col1:
            target_need = st.selectbox("I am looking for:", ["Elite Prospects (<23)", "Impact Youth (23-25)", "Draft Capital", "2026 Pitching"])
        with col2:
            offering = st.text_input("I am willing to offer:", placeholder="e.g. Max Fried, veterans, 2026 picks")
        
        if st.button("Scour League for Partners"):
            finder_prompt = f"LEAGUE_ROSTERS: {json.dumps(parsed_rosters)}\nNEED: {target_need}\nOFFER: {offering}\nTASK: Identify 3 realistic trade partners. Explain why it makes sense for THEM based on their current roster depth."
            results = get_multi_ai_opinions(finder_prompt, "Trade Finder")
            st.markdown(results['Gemini'])

    # (Other tabs remain as previously configured)
    with tabs[0]:
        st.subheader("Transaction Terminal")
        # ... (Terminal logic from previous version)

except Exception as e:
    st.error(f"Executive System Offline: {e}")
