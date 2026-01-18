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

# --- 2. THE IRONCLAD HORIZONTAL PARSER ---
def get_gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def parse_horizontal_rosters(matrix):
    """
    Strict Column-Mapping Logic:
    Ensures Row 1 is treated as Team Headers and columns below are locked to that team.
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
                    # Filter out empty cells and structural labels
                    if player_val and not player_val.endswith(':'):
                        league_map[team_header].append({
                            "name": player_val,
                            "row": row_idx + 2, # Account for 1-based indexing and Header row
                            "col": col_idx + 1
                        })
    return league_map

# --- 3. FUZZY IDENTITY & VALIDATION ENGINE ---
def get_fuzzy_matches(input_names, team_players):
    """Checks a comma-separated list of names against the ledger."""
    results = []
    ledger_names = [p['name'] for p in team_players]
    
    raw_list = [n.strip() for n in input_names.split(",") if n.strip()]
    for name in raw_list:
        matches = difflib.get_close_matches(name, ledger_names, n=1, cutoff=0.6)
        if matches:
            # Find the full coordinate object
            match_obj = next(p for p in team_players if p['name'] == matches[0])
            results.append(match_obj)
        else:
            results.append(None)
    return results

@st.dialog("Verify Roster Sync")
def verify_trade_dialog(team_a, final_a, team_b, final_b, roster_ws, history_ws, raw_matrix):
    st.warning("⚖️ **Identity Verification Required**")
    st.write("The system has identified these players for the move:")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**From {team_a}:**")
        for p in final_a: st.write(f"- {p['name']} (Col {p['col']})")
    with col2:
        st.write(f"**From {team_b}:**")
        for p in final_b: st.write(f"- {p['name']} (Col {p['col']})")
        
    st.divider()
    if st.button("🔥 Confirm & Push to Google Sheets", use_container_width=True):
        with st.spinner("Re-writing Ledger Columns..."):
            # EXECUTION LOGIC: Targeted Coordinate Update
            # 1. Prepare names for the history log
            names_a = ", ".join([p['name'] for p in final_a])
            names_b = ", ".join([p['name'] for p in final_b])

            # 2. Use Gemini to calculate the new matrix (Ironclad method)
            # This ensures Row 1 headers and Column alignment never shift
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
                new_matrix = eval(clean_res)
                roster_ws.clear()
                roster_ws.update(new_matrix)
                history_ws.append_row([f"TRADE: {team_a} ↔️ {team_b} | {names_a} for {names_b}"])
                st.success("Ledger Synchronized!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Sync Error: {e}")

# --- 4. THE AI BRAIN (MULTI-AGENT & REALISM GATE) ---
def get_active_model():
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

def run_hypothetical_war_room(trade_query, league_data):
    """Analyzes the trade from a Sabermetric and Strategy perspective."""
    mandate = """
    REALISM GATE: 
    - 2026 ZiPS & Age Curves are absolute.
    - Elite young assets (Witt, Gunnar) are worth 5x aging SPs (Fried).
    - If a trade is delusional (e.g. Fried for Witt), label it 'UNREALISTIC' and explain why.
    - Analyze ALL players in the trade simultaneously.
    """
    with st.spinner("📡 Scouting 2026 ZiPS, FanGraphs, and Tiers..."):
        search = call_openrouter("perplexity/sonar", "Dynasty Analyst.", f"Jan 2026 ZiPS and Dynasty rankings for: {trade_query}")
    
    brief = f"LEAGUE: {league_data}\nINTEL: {search}\nTRADE: {trade_query}\nMANDATE: {mandate}"
    model = get_active_model()
    
    return {
        "Research": search,
        "Gemini": model.generate_content(f"Lead GM Verdict. Decide who wins. {brief}").text,
        "GPT": call_openrouter("openai/gpt-4o", "Market Valuator. Focus on surplus value.", brief),
        "Claude": call_openrouter("anthropic/claude-3.5-sonnet", "Strategist. Focus on window alignment.", brief)
    }

# --- 5. MAIN UI INTERFACE ---
st.set_page_config(page_title="GM Master Terminal", layout="wide", page_icon="🏛️")
st.title("🏛️ Dynasty GM Suite: Master Executive Terminal")

try:
    # A. CONNECT & PULL
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws, roster_ws = sh.get_worksheet(0), sh.get_worksheet(1)
    
    raw_matrix = roster_ws.get_all_values()
    full_league_data = parse_horizontal_rosters(raw_matrix)
    model = get_active_model()

    # B. THE 8-TAB COMMAND CENTER
    tabs = st.tabs(["🔁 Terminal", "🔥 Analysis", "🔍 Finder", "📊 Ledger", "🕵️‍♂️ Scouting", "💎 Sleepers", "🎯 Priority", "📜 History"])

    # --- TAB 0: TERMINAL (MULTI-PLAYER ENABLED) ---
    with tabs[0]:
        st.subheader("Official Sync Terminal")
        st.caption("Multi-player trades enabled. Separate names with commas.")
        
        c1, c2 = st.columns(2)
        with c1:
            team_a = st.selectbox("Team A (Owner):", TEAM_NAMES, key="t_a_final")
            p_a_input = st.text_area("Leaving Team A (e.g. Max Fried, Max Muncy):", key="p_a_final")
        with c2:
            team_b = st.selectbox("Team B (Counterparty):", TEAM_NAMES, key="t_b_final")
            p_b_input = st.text_area("Leaving Team B (e.g. Paul Skenes):", key="p_b_final")
            
        if st.button("🔥 Verify & Execute Multi-Player Trade", use_container_width=True):
            match_a = get_fuzzy_matches(p_a_input, full_league_data[team_a])
            match_b = get_fuzzy_matches(p_b_input, full_league_data[team_b])
            
            if None in match_a or None in match_b:
                st.error("One or more players not found. Check spelling or commas.")
            else:
                verify_trade_dialog(team_a, match_a, team_b, match_b, roster_ws, history_ws)

    # --- TAB 1: HYPOTHETICAL TRADE ANALYZER ---
    with tabs[1]:
        st.subheader("🔥 Hypothetical Trade Arbitrator")
        trade_input = st.chat_input("Analyze deal: (e.g. My Fried for his Skenes)")
        if trade_input:
            res = run_hypothetical_war_room(trade_input, json.dumps(full_league_data))
            with st.expander("📡 Live 2026 Intelligence Briefing", expanded=True): st.write(res["Research"])
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1: st.info("🟢 Gemini Verdict"); st.write(res["Gemini"])
            with col2: st.info("🔵 GPT Market Value"); st.write(res["GPT"])
            with col3: st.info("🟠 Claude Strategy"); st.write(res["Claude"])

    # --- TAB 2: TRADE FINDER ---
    with tabs[2]:
        st.subheader("🔍 Automated Win-Win Partner Finder")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            find_target = st.selectbox("I need:", ["Elite Prospects (<23)", "2026 Production", "Draft Capital"])
        with f_col2:
            find_offer = st.text_input("I am shopping:", placeholder="e.g. Max Fried")
        if st.button("Scour League for Partners", use_container_width=True):
            results = run_hypothetical_war_room(f"Find trades to get {find_target} by giving up {find_offer}", json.dumps(full_league_data))
            st.markdown(results["Gemini"])

    # --- TAB 3: LIVE LEDGER ---
    with tabs[3]:
        st.subheader("📊 Roster Matrix")
        df_display = pd.DataFrame(raw_matrix)
        st.dataframe(df_display, use_container_width=True)
        st.download_button("📥 Export to Excel", convert_df_to_excel(df_display), "League_Ledger.xlsx")

    # --- TAB 4: PRO SCOUTING ---
    with tabs[4]:
        st.subheader("🕵️‍♂️ Deep-Dive Scouting Report")
        scout_p = st.text_input("Scout Player (Live News/ZiPS):", key="scout_q")
        if scout_p:
            scout_res = run_hypothetical_war_room(f"Full scouting report for {scout_p}", json.dumps(full_league_data))
            st.write(scout_res["Gemini"])

    # --- TAB 5: SLEEPERS ---
    with tabs[5]:
        st.subheader("💎 2026 Market Inefficiencies")
        if st.button("Identify Undervalued Breakouts"):
            sleeper_res = run_hypothetical_war_room("Identify 5 players with elite 2026 ZiPS but low Dynasty ECR rankings.", json.dumps(full_league_data))
            st.write(sleeper_res["Gemini"])

    # --- TAB 6: PRIORITY TARGETS ---
    with tabs[6]:
        st.subheader("🎯 Retool Priority Board")
        if st.button("Generate Priority Target List"):
            priority_res = run_hypothetical_war_room("Based on my retool strategy, who are the top 5 targets in the league I should move for now?", json.dumps(full_league_data))
            st.write(priority_res["Gemini"])

    # --- TAB 7: HISTORY ---
    with tabs[7]:
        st.subheader("📜 History Log")
        for log in history_ws.col_values(1)[::-1]: st.write(f"🔹 {log}")

except Exception as e:
    st.error(f"Executive Protocol Failed: {e}")
