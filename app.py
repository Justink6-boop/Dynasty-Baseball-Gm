import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from io import BytesIO
import requests
import json
import time
import difflib

# --- 1. GLOBAL MASTER CONFIGURATION ---
SHEET_ID = "1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A"
TEAM_NAMES = [
    "Witness Protection (Me)", "Bobbys Squad", "Arm Barn Heros", 
    "Guti Gang", "Happy", "Hit it Hard Hit it Far", 
    "ManBearPuig", "Milwaukee Beers", "Seiya Later", "Special Eds"
]

# --- 2. CORE UTILITY ENGINE ---
def get_gspread_client():
    """Secure connection to Google Sheets."""
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def convert_df_to_excel(df):
    """Utility for binary download of Excel files."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def parse_horizontal_rosters(matrix):
    """
    Ironclad Horizontal Parser:
    Maps Row 1 as Team Headers and locks every column to that specific team.
    """
    league_map = {}
    if not matrix: return league_map
    headers = [str(cell).strip() for cell in matrix[0]]
    for col_idx, team_header in enumerate(headers):
        if team_header in TEAM_NAMES:
            league_map[team_header] = []
            for row_idx, row in enumerate(matrix[1:]):
                if col_idx < len(row):
                    player_val = str(row[col_idx]).strip()
                    if player_val and not player_val.endswith(':'):
                        league_map[team_header].append({
                            "name": player_val,
                            "row": row_idx + 2,
                            "col": col_idx + 1
                        })
    return league_map

# --- 3. FUZZY IDENTITY & VALIDATION ENGINE ---
def get_fuzzy_matches(input_names, team_players):
    """Validates comma-separated names against the ledger for a specific team."""
    results = []
    ledger_names = [p['name'] for p in team_players]
    raw_list = [n.strip() for n in input_names.split(",") if n.strip()]
    for name in raw_list:
        matches = difflib.get_close_matches(name, ledger_names, n=1, cutoff=0.6)
        if matches:
            match_obj = next(p for p in team_players if p['name'] == matches[0])
            results.append(match_obj)
        else:
            results.append(None)
    return results

@st.dialog("Verify Roster Sync")
def verify_trade_dialog(team_a, final_a, team_b, final_b, roster_ws, history_ws, raw_matrix):
    """The safety-net popup for identity verification and coordinate swapping."""
    st.warning("⚖️ **Identity Verification Required**")
    st.write("The system has identified these players for the move:")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**From {team_a}:**")
        for p in final_a: st.write(f"- {p['name']}")
    with col2:
        st.write(f"**From {team_b}:**")
        for p in final_b: st.write(f"- {p['name']}")
        
    st.divider()
    if st.button("🔥 Confirm & Push to Google Sheets", use_container_width=True):
        with st.spinner("Executing Coordinate Swap..."):
            names_a = ", ".join([p['name'] for p in final_a])
            names_b = ", ".join([p['name'] for p in final_b])
            
            # Ironclad logic prompt for AI-assisted matrix restructuring
            model = get_active_model()
            logic_prompt = f"""
            MATRIX: {raw_matrix}
            TASK: Swap {names_a} from {team_a}'s column to the bottom of {team_b}'s column. 
            Swap {names_b} from {team_b}'s column to the bottom of {team_a}'s column.
            Maintain horizontal structure. Return ONLY a Python list of lists.
            """
            res = model.generate_content(logic_prompt).text
            clean_res = res.replace("```python", "").replace("```", "").strip()
            try:
                new_m = eval(clean_res)
                roster_ws.clear()
                roster_ws.update(new_m)
                history_ws.append_row([f"TRADE: {team_a} ↔️ {team_b} | {names_a} for {names_b}"])
                st.success("Ledger Synchronized!")
                time.sleep(1)
                st.rerun()
            except:
                st.error("Matrix Structure Error. Please verify the AI output format.")

# --- 4. THE AI BRAIN (SELF-HEALING & MULTI-AGENT) ---
def get_active_model():
    """Prevents 404 errors by dynamically finding the active Flash model."""
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in models if 'flash' in m]
        flash_models.sort(reverse=True)
        return genai.GenerativeModel(flash_models[0])
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

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

def run_gm_analysis(query, league_data, task="Trade"):
    """
    Hypothetical Trade Arbitrator:
    Determines winners based on 2026 ZiPS, age, and scarcity.
    Uses the Realism Gate to block 'Witt-for-Fried' level delusions.
    """
    mandate = """
    REALISM PROTOCOL: 
    - Elite cornerstone youth (Witt, Gunnar, Elly) > aging SPs (Fried).
    - If a trade is lopsided, call it 'UNREALISTIC' and explain why.
    - Identify the winner and suggest necessary sweeteners.
    """
    with st.spinner("📡 Scouting live 2026 ZiPS, FanGraphs, and Tiers..."):
        search = call_openrouter("perplexity/sonar", "Lead Sabermetrician.", f"Jan 2026 ZiPS and dynasty trade value for: {query}")
    
    brief = f"LEAGUE: {league_data}\nINTEL: {search}\nQUERY: {query}\nMANDATE: {mandate}"
    return {
        "Research": search,
        "Gemini": get_active_model().generate_content(f"Lead GM Verdict. {brief}").text,
        "GPT": call_openrouter("openai/gpt-4o", "Market Expert.", brief),
        "Claude": call_openrouter("anthropic/claude-3.5-sonnet", "Strategist.", brief)
    }

# --- 5. MAIN UI INTERFACE ---
st.set_page_config(page_title="GM Master Terminal", layout="wide", page_icon="🏛️")
st.title("🏛️ Dynasty GM Suite: Master Executive Terminal")

try:
    # A. INITIALIZE DATA & CONNECTIONS
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws, roster_ws = sh.get_worksheet(0), sh.get_worksheet(1)
    
    raw_matrix = roster_ws.get_all_values()
    full_league_data = parse_horizontal_rosters(raw_matrix)
    model = get_active_model()

    # B. THE 8-TAB COMMAND CENTER
    tabs = st.tabs(["🔁 Terminal", "🔥 Analysis", "🔍 Finder", "📊 Ledger", "🕵️‍♂️ Scouting", "💎 Sleepers", "🎯 Priority", "📜 History"])

    # --- TAB 0: TERMINAL ---
    with tabs[0]:
        st.subheader("Official Sync Terminal")
        st.caption("Multi-player trades enabled. Names in columns under Row 1 Headers.")
        c1, c2 = st.columns(2)
        with c1:
            team_a = st.selectbox("Team A (Owner):", TEAM_NAMES, key="t_a_final")
            p_a_input = st.text_area("Leaving Team A (Separate with commas):", key="p_a_final")
        with c2:
            team_b = st.selectbox("Team B (Counterparty):", TEAM_NAMES, key="t_b_final")
            p_b_input = st.text_area("Leaving Team B (Separate with commas):", key="p_b_final")
            
        if st.button("🔥 Verify & Execute Multi-Player Trade", use_container_width=True):
            match_a = get_fuzzy_matches(p_a_input, full_league_data[team_a])
            match_b = get_fuzzy_matches(p_b_input, full_league_data[team_b])
            
            if None in match_a or None in match_b:
                st.error("Player name not found on the specified roster. Check spelling.")
            else:
                verify_trade_dialog(team_a, match_a, team_b, match_b, roster_ws, history_ws, raw_matrix)

    # --- TAB 1: ANALYSIS ---
    with tabs[1]:
        st.subheader("🔥 Hypothetical Trade Arbitrator")
        trade_q = st.chat_input("Analyze deal: (e.g. My Fried for his Skenes)")
        if trade_q:
            res = run_gm_analysis(trade_q, json.dumps(full_league_data))
            with st.expander("📡 Live 2026 Intelligence", expanded=True): st.write(res["Research"])
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1: st.info("🟢 Gemini Verdict"); st.write(res["Gemini"])
            with col2: st.info("🔵 GPT Value"); st.write(res["GPT"])
            with col3: st.info("🟠 Claude Strategy"); st.write(res["Claude"])

    # --- TAB 2: FINDER ---
    with tabs[2]:
        st.subheader("🔍 Automated Win-Win Partner Finder")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            find_target = st.selectbox("I need:", ["Elite Prospects (<23)", "2026 Production", "Draft Capital"])
        with f_col2:
            find_offer = st.text_input("I am shopping:", placeholder="e.g. Max Fried")
        if st.button("Scour League", use_container_width=True):
            res = run_gm_analysis(f"Find trades to get {find_target} by giving up {find_offer}", json.dumps(full_league_data), "Finder")
            st.markdown(res["Gemini"])

    # --- TAB 3: LEDGER ---
    with tabs[3]:
        st.subheader("📊 Roster Matrix")
        df_display = pd.DataFrame(raw_matrix)
        st.dataframe(df_display, use_container_width=True)
        st.download_button("📥 Export Excel", convert_df_to_excel(df_display), "Rosters.xlsx")

    # --- TAB 4: SCOUTING ---
    with tabs[4]:
        st.subheader("🕵️‍♂️ Deep-Dive Scouting Report")
        scout_p = st.text_input("Scout Player (Live Projections):", key="scout_q")
        if scout_p:
            scout_res = run_gm_analysis(f"Full scouting report for {scout_p}", json.dumps(full_league_data), "Scouting")
            st.write(scout_res["Gemini"])

    # --- TAB 5: SLEEPERS ---
    with tabs[5]:
        st.subheader("💎 2026 Market Inefficiencies")
        if st.button("Identify Undervalued Breakouts"):
            sleeper_res = run_gm_analysis("Identify 5 players with elite 2026 ZiPS currently undervalued in dynasty.", json.dumps(full_league_data), "Sleepers")
            st.write(sleeper_res["Gemini"])

    # --- TAB 6: PRIORITY ---
    with tabs[6]:
        st.subheader("🎯 Retool Priority Board")
        if st.button("Generate Priority Target List"):
            priority_res = run_gm_analysis("Based on my retool strategy, who are the top 5 targets in the league I should move for now?", json.dumps(full_league_data), "Priority")
            st.write(priority_res["Gemini"])

    # --- TAB 7: HISTORY ---
    with tabs[7]:
        st.subheader("📜 History Log")
        for log in history_ws.col_values(1)[::-1]: st.write(f"🔹 {log}")

except Exception as e:
    st.error(f"Executive Protocol Failed: {e}")

