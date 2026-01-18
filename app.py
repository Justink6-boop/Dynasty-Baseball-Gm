import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from io import BytesIO
import requests
import json
import time

# --- 1. GLOBAL MASTER CONFIGURATION ---
SHEET_ID = "1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A"
TEAM_NAMES = [
    "Witness Protection (Me)", "Bobbys Squad", "Arm Barn Heros", 
    "Guti Gang", "Happy", "Hit it Hard Hit it Far", 
    "ManBearPuig", "Milwaukee Beers", "Seiya Later", "Special Eds"
]

# --- 2. CORE UTILITY ENGINE ---
def get_gspread_client():
    """Secure connection to Google Sheets via Service Account."""
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def parse_horizontal_rosters(matrix, team_names):
    """
    Parses horizontal ledger (Team names in Row 1).
    Maps players to their respective columns.
    """
    league_map = {}
    if not matrix: return league_map
    # Standardize headers from Row 1
    headers = [str(cell).strip() for cell in matrix[0]]
    for col_idx, team in enumerate(headers):
        if team in team_names:
            # Collect all non-empty values below the header, skipping category labels
            players = []
            for row in matrix[1:]:
                if col_idx < len(row):
                    val = str(row[col_idx]).strip()
                    if val and not val.endswith(':'):
                        players.append(val)
            league_map[team] = players
    return league_map

def convert_to_excel(df):
    """Utility for binary download of Excel files."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- 3. THE AI BRAIN (SELF-HEALING & MULTI-AGENT) ---
def get_active_model():
    """Finds the latest available Gemini model to prevent 404/version errors."""
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prefer flash for speed, 2.0 or 1.5
        flash_models = [m for m in models if 'flash' in m]
        flash_models.sort(reverse=True)
        return genai.GenerativeModel(flash_models[0])
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

def call_openrouter(model_id, persona, prompt):
    """Generic wrapper for OpenRouter (GPT, Claude, Perplexity)."""
    try:
        r = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
                "HTTP-Referer": "https://streamlit.io",
                "X-Title": "Dynasty GM Master Suite"
            },
            data=json.dumps({"model": model_id, "messages": [
                {"role": "system", "content": persona},
                {"role": "user", "content": prompt}
            ]}),
            timeout=30
        )
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
        return f"Model Error: {r.status_code}"
    except Exception as e:
        return f"Connection Error: {e}"

# --- 4. MASTER ANALYSIS LOGIC (THE REALISM GATE) ---
def run_gm_analysis(query, league_data, task="Trade"):
    """
    Stage 1: Live Intelligence (Perplexity)
    Stage 2: Sabermetric Verdict (Gemini + Realism Gate)
    Stage 3: Market/Strategy Consensus (GPT/Claude)
    """
    mandate = """
    CRITICAL REALISM PROTOCOL:
    - You are an elite, high-stakes Dynasty GM.
    - POSITIONAL SCARCITY: 5-tool SS/OF (Witt, Gunnar, Acuna) are worth 4x-5x an aging SP (Fried, Cole).
    - AGE CURVES: A 24-year-old superstar is nearly 'untradeable'. 
    - VERDICT: If a trade is lopsided (e.g. Fried for Witt), call it 'DELUSIONAL' and explain the massive value gap.
    - WINNER: Identify who wins based on 2026-2029 projected surplus value.
    """
    
    with st.spinner("📡 Scouting 2026 ZiPS, FanGraphs, and Market Value..."):
        search_prompt = f"Analyze Jan 2026 trade value, ZiPS, and news for: {query}. Focus on surplus value."
        live_intel = call_openrouter("perplexity/sonar", "Lead Sabermetrician.", search_prompt)

    brief = f"ROSTERS: {league_data}\nINTEL: {live_intel}\nINPUT: {query}\nMANDATE: {mandate}"
    
    return {
        "Research": live_intel,
        "Gemini": get_active_model().generate_content(f"Lead GM Verdict. Task: {task}. {brief}").text,
        "GPT": call_openrouter("openai/gpt-4o", "Market Valuator. Be brutally realistic about trade equity.", brief),
        "Claude": call_openrouter("anthropic/claude-3.5-sonnet", "Strategy Architect. Focus on championship windows.", brief)
    }

# --- 5. UI INITIALIZATION ---
st.set_page_config(page_title="GM Suite Master", layout="wide", page_icon="🏛️")
st.title("⚾ Dynasty GM Suite: Master Executive Terminal")

try:
    # A. CONNECT TO GOOGLE
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws = sh.get_worksheet(0)
    roster_ws = sh.get_worksheet(1)
    
    # B. PULL & PARSE DATA
    raw_matrix = roster_ws.get_all_values()
    parsed_league = parse_horizontal_rosters(raw_matrix, TEAM_NAMES)
    
    # C. UI TABS
    tabs = st.tabs([
        "🔁 Transaction Terminal", 
        "🔥 Hypothetical Trade Analyzer", 
        "🔍 Automated Trade Finder", 
        "📋 Live Ledger", 
        "🕵️‍♂️ Pro Scouting", 
        "💎 Sleeper Cell", 
        "📜 History Log"
    ])

    # --- TAB 0: TRANSACTION TERMINAL ---
    with tabs[0]:
        st.subheader("Official League Transaction Terminal")
        st.caption("Updates the Horizontal Ledger (Row 1 Team Headers)")
        
        mode = st.radio("Action:", ["Trade", "Add/Drop"], horizontal=True, key="mode_sel")
        
        if mode == "Trade":
            col1, col2 = st.columns(2)
            with col1:
                t_a = st.selectbox("Team A (Selling):", TEAM_NAMES, key="t_a_sel")
                p_a = st.text_area("Leaving Team A:", placeholder="Player 1, Player 2", key="p_a_sel")
            with col2:
                t_b = st.selectbox("Team B (Buying):", TEAM_NAMES, key="t_b_sel")
                p_b = st.text_area("Leaving Team B:", placeholder="Player 1, Player 2", key="p_b_sel")
            
            if st.button("🔥 Execute Official Sync", use_container_width=True):
                with st.spinner("Processing Horizontal Data Re-structure..."):
                    # Use Gemini to handle the complex list-of-lists reordering
                    logic_prompt = f"Matrix: {raw_matrix}. Action: Trade {p_a} from {t_a} to {t_b}. Trade {p_b} from {t_b} to {t_a}. Return ONLY a Python list of lists."
                    res = get_active_model().generate_content(logic_prompt).text
                    clean_res = res.replace("```python", "").replace("```", "").strip()
                    try:
                        new_matrix = eval(clean_res)
                        roster_ws.clear()
                        roster_ws.update(new_matrix)
                        history_ws.append_row([f"TRADE: {t_a} ↔️ {t_b} | {p_a} for {p_b}"])
                        st.success("Ledger Updated!")
                        time.sleep(1)
                        st.rerun()
                    except: st.error("Parsing Error. Check player names against ledger.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                t_target = st.selectbox("Select Team:", TEAM_NAMES, key="t_target_sel")
                action = st.selectbox("Action:", ["Add", "Drop"], key="act_sel")
            with c2:
                player_target = st.text_input("Player Name:", key="p_target_sel")
            
            if st.button("Submit Waiver Transaction", use_container_width=True):
                logic_prompt = f"Matrix: {raw_matrix}. Action: {action} {player_target} to/from {t_target}. Return ONLY Python list of lists."
                res = get_active_model().generate_content(logic_prompt).text
                clean_res = res.replace("```python", "").replace("```", "").strip()
                try:
                    new_matrix = eval(clean_res)
                    roster_ws.clear()
                    roster_ws.update(new_matrix)
                    history_ws.append_row([f"{action.upper()}: {player_target} ({t_target})"])
                    st.success("Waiver Action Logged!")
                    time.sleep(1)
                    st.rerun()
                except: st.error("Error updating waiver move.")

    # --- TAB 1: HYPOTHETICAL TRADE ANALYZER ---
    with tabs[1]:
        st.subheader("🔥 Hypothetical Trade Arbitrator")
        st.caption("Analyzing via Positional Value & 2026-2029 Age Curves")
        trade_q = st.chat_input("Enter Trade: (e.g. My Fried for his Skenes)")
        if trade_q:
            results = run_gm_analysis(trade_q, json.dumps(parsed_league))
            with st.expander("📡 Live Market Intel (ZiPS & Rankings)", expanded=True):
                st.write(results["Research"])
            st.divider()
            c1, c2, c3 = st.columns(3)
            with c1: st.info("🟢 Lead Scout (Verdict)"); st.write(results["Gemini"])
            with c2: st.info("🔵 Market Reality Check"); st.write(results["GPT"])
            with c3: st.info("🟠 Strategy Architect"); st.write(results["Claude"])

    # --- TAB 2: AUTOMATED TRADE FINDER ---
    with tabs[2]:
        st.subheader("🔍 Automated Win-Win Partner Finder")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            find_need = st.selectbox("I need:", ["Elite Prospects (<23)", "Impact Youth (23-25)", "2026 Pitching", "Draft Capital"])
        with f_col2:
            find_offer = st.text_input("I am shopping:", placeholder="e.g. Max Fried, veterans")
        
        if st.button("Scour League for Win-Win Deals", use_container_width=True):
            finder_res = run_gm_analysis(f"Find trades to get {find_need} by offering {find_offer}", json.dumps(parsed_league), task="Trade Finder")
            st.markdown(finder_res["Gemini"])

    # --- TAB 3: LIVE LEDGER ---
    with tabs[3]:
        st.subheader("📊 Roster Matrix (Live View)")
        df_ledger = pd.DataFrame(raw_matrix)
        st.dataframe(df_ledger, use_container_width=True)
        st.download_button("📥 Export to Excel", convert_to_excel(df_ledger), "Dynasty_Rosters.xlsx")

    # --- TAB 4: PRO SCOUTING ---
    with tabs[4]:
        st.subheader("🕵️‍♂️ Deep-Dive Scouting Report")
        scout_p = st.text_input("Enter Player for Live Analytics Dive:")
        if scout_p:
            scout_res = run_gm_analysis(f"Full scouting report for {scout_p}", json.dumps(parsed_league), task="Scouting")
            st.write(scout_res["Gemini"])

    # --- TAB 5: SLEEPER CELL ---
    with tabs[5]:
        st.subheader("💎 2026 Market Inefficiencies")
        if st.button("Identify Undervalued Breakouts"):
            sleeper_res = run_gm_analysis("5 players with elite 2026 ZiPS but low Dynasty ECR rankings.", json.dumps(parsed_league), task="Sleepers")
            st.write(sleeper_res["Gemini"])

    # --- TAB 6: HISTORY LOG ---
    with tabs[6]:
        st.subheader("📜 Transaction Archive")
        logs = history_ws.col_values(1)[::-1]
        for log in logs:
            st.write(f"🔹 {log}")

except Exception as e:
    st.error(f"Executive Protocol Failed: {e}")
