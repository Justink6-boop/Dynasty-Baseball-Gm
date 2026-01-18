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
    """Parses data where Team Names are in Row 1 and players are in columns below."""
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
    # A. INITIALIZE DATA
    init_data = get_initial_league()
    team_list = list(init_data.keys())
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws = sh.get_worksheet(0)
    roster_ws = sh.get_worksheet(1)

    permanent_history = history_ws.col_values(1)
    raw_roster_matrix = roster_ws.get_all_values()
    parsed_rosters = parse_roster_matrix(raw_roster_matrix, team_list)

    # B. AI CONFIGURATION
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    flash_models = [m for m in available_models if 'flash' in m]
    model = genai.GenerativeModel(flash_models[0] if flash_models else 'gemini-1.5-pro')

    # C. WAR ROOM LOGIC
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
        directive = "MISSION: 30% 2026 win-now / 70% 2027-29 peak. Hybrid Retool Strategy."
        with st.spinner("📡 Scanning Jan 2026 ZiPS & Rankings..."):
            search_query = f"Search latest Jan 2026 ZiPS, Statcast, and Dynasty Rankings for: {user_query}."
            live_intel = call_openrouter("perplexity/sonar", "Lead Researcher.", search_query)
        briefing = f"ROSTERS: {json.dumps(parsed_rosters)}\nINTEL: {live_intel}\nINPUT: {user_query}\nGOAL: {directive}"
        return {
            'Perplexity': live_intel,
            'Gemini': model.generate_content(f"Lead Scout. Task: {task_type}. Briefing: {briefing}").text,
            'ChatGPT': call_openrouter("openai/gpt-4o", "Market Analyst.", briefing),
            'Claude': call_openrouter("anthropic/claude-3.5-sonnet", "Window Strategist.", briefing)
        }

    # --- 5. UI TABS ---
    with st.sidebar:
        st.header(f"💰 FAAB: ${st.session_state.get('faab', 200.00):.2f}")
        spent = st.number_input("Log Spending:", min_value=0.0)
        if st.button("Update Budget"): st.session_state.faab = st.session_state.get('faab', 200.00) - spent

    tabs = st.tabs(["🔁 Transaction Terminal", "🔥 Trade Analysis", "📋 Live Ledger", "🎯 Priority Candidates", "🕵️‍♂️ Full Scouting", "💎 Sleeper Cell", "📜 History Log"])

    # --- TAB 0: TRANSACTION TERMINAL ---
    with tabs[0]:
        st.subheader("Official League Transaction Terminal")
        trans_type = st.radio("Action:", ["Trade", "Waiver/Drop"], horizontal=True)
        if trans_type == "Trade":
            col1, col2 = st.columns(2)
            with col1:
                team_a = st.selectbox("From Team:", team_list, key="ta_t")
                p_out = st.text_area("Leaving Team A:", key="po_t")
            with col2:
                team_b = st.selectbox("To Team:", team_list, key="tb_t")
                p_in = st.text_area("Leaving Team B:", key="pi_t")
            if st.button("Execute Trade"):
                with st.spinner("Updating Horizontal Ledger..."):
                    prompt = f"DATA: {raw_roster_matrix}\nMove {p_out} from {team_a} to {team_b}, and {p_in} from {team_b} to {team_a}. Return ONLY a Python list of lists representing the updated horizontal sheet."
                    res = model.generate_content(prompt).text
                    clean = res.replace("```python", "").replace("```", "").strip()
                    try:
                        new_list = eval(clean); roster_ws.clear(); roster_ws.update(new_list)
                        history_ws.append_row([f"TRADE: {team_a} ↔️ {team_b}"]); st.success("Trade Synced!"); st.rerun()
                    except: st.error("Sync Error. Check your player names.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                t_team = st.selectbox("Team:", team_list, key="wt_t"); act = st.selectbox("Action:", ["Add", "Drop"], key="wa_t")
            with col2: p_name = st.text_input("Player Name:", key="wp_t")
            if st.button("Submit Move"):
                prompt = f"DATA: {raw_roster_matrix}\n{act} {p_name} to/from {t_team}. Return ONLY Python list of lists."
                res = model.generate_content(prompt).text
                clean = res.replace("```python", "").replace("```", "").strip()
                try:
                    new_list = eval(clean); roster_ws.clear(); roster_ws.update(new_list)
                    history_ws.append_row([f"{act.upper()}: {p_name} ({t_team})"]); st.rerun()
                except: st.error("Update Error.")

    # --- TAB 1: TRADE ANALYSIS ---
    with tabs[1]:
        st.subheader("🚀 War Room: Live 2026 Intelligence")
        trade_q = st.chat_input("Analyze Fried for Skenes...")
        if trade_q:
            results = get_multi_ai_opinions(trade_q)
            with st.expander("📡 Live Field Report", expanded=True): st.write(results['Perplexity'])
            st.divider()
            c1, c2, c3 = st.columns(3)
            with c1: st.info("🟢 Gemini"); st.write(results['Gemini'])
            with c2: st.info("🔵 GPT-4o"); st.write(results['ChatGPT'])
            with c3: st.info("🟠 Claude"); st.write(results['Claude'])

    # --- TAB 2: LEDGER ---
    with tabs[2]:
        st.download_button("📥 Excel Download", convert_df_to_excel(pd.DataFrame(raw_roster_matrix)), "Rosters.xlsx")
        st.dataframe(pd.DataFrame(raw_roster_matrix), use_container_width=True)

    # --- TAB 3: PRIORITY CANDIDATES ---
    with tabs[3]:
        if st.button("Identify Trade Targets"):
            results = get_multi_ai_opinions("Who are the top 3 young under-25 players on rival rosters we should target for a hybrid retool?", "Strategy")
            st.write(results['Gemini'])

    # --- TAB 4: SCOUTING ---
    with tabs[4]:
        sn = st.text_input("Scout Player (Live 2026 Data):")
        if sn:
            results = get_multi_ai_opinions(f"Full scouting report for {sn}", "Scouting")
            st.write(results['Gemini'])

    # --- TAB 5: SLEEPER CELL ---
    with tabs[5]:
        if st.button("Find Undervalued Sleepers"):
            results = get_multi_ai_opinions("Find 3 sleeper candidates with elite 2026 ZiPS projections currently undervalued.", "Sleepers")
            st.write(results['Gemini'])

    # --- TAB 6: HISTORY ---
    with tabs[6]:
        for entry in permanent_history[::-1]: st.write(f"✅ {entry}")

except Exception as e:
    st.error(f"Executive System Offline: {e}")
