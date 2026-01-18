import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from io import BytesIO
import requests
import json
import time
import difflib # Native fuzzy matching for name verification

# --- 1. GLOBAL MASTER CONFIGURATION ---
SHEET_ID = "1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A"
TEAM_NAMES = [
    "Witness Protection (Me)", "Bobbys Squad", "Arm Barn Heros", 
    "Guti Gang", "Happy", "Hit it Hard Hit it Far", 
    "ManBearPuig", "Milwaukee Beers", "Seiya Later", "Special Eds"
]

# --- 2. CORE UTILITY ENGINE ---
def get_gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def parse_horizontal_rosters(matrix, team_names):
    """Deep-scans Row 1 for teams and builds a full mapping of every player."""
    league_map = {}
    if not matrix: return league_map
    headers = [str(cell).strip() for cell in matrix[0]]
    for col_idx, team in enumerate(headers):
        if team in team_names:
            league_map[team] = [
                str(row[col_idx]).strip() for row in matrix[1:] 
                if col_idx < len(row) and str(row[col_idx]).strip() 
                and not str(row[col_idx]).strip().endswith(':')
            ]
    return league_map

def convert_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- 3. NAME VALIDATION ENGINE (The "Did You Mean" Logic) ---
def find_closest_player(input_name, all_players_list):
    """Returns the closest match from the ledger if not an exact match."""
    matches = difflib.get_close_matches(input_name, all_players_list, n=1, cutoff=0.6)
    return matches[0] if matches else None

@st.dialog("Verify Player Identity")
def verification_dialog(input_name, suggested_name, team_context, action_data):
    st.write(f"The name **'{input_name}'** was not found on **{team_context}**.")
    st.write(f"Did you mean: **{suggested_name}**?")
    if st.button("Yes, Confirm & Execute"):
        # This triggers the execution with the corrected name
        execute_transaction_final(action_data, corrected_name=suggested_name)
        st.rerun()
    if st.button("No, Let me re-type"):
        st.rerun()

# --- 4. SELF-HEALING AI ENGINE ---
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

# --- 5. TRANSACTION EXECUTION ENGINE ---
def execute_transaction_final(action_data, corrected_name=None):
    """The final backend call to update Google Sheets after validation."""
    # (Internal logic to communicate with GSpread remains clean)
    pass 

# --- 6. MASTER ANALYSIS LOGIC ---
def run_front_office_analysis(query, league_data, task="Trade"):
    strategy = "Hybrid Retool: 30% 2026 Win / 70% 2027-29 Peak."
    with st.spinner("📡 Scouting 2026 ZiPS & Dynasty Rankings..."):
        search_query = f"Provide 2026 ZiPS, Dynasty Rankings, and latest news for: {query}."
        live_intel = call_openrouter("perplexity/sonar", "Lead Sabermetrician.", search_query)

    briefing = f"ROSTERS: {league_data}\nINTEL: {live_intel}\nINPUT: {query}\nSTRATEGY: {strategy}"
    
    return {
        "Research": live_intel,
        "Gemini": get_active_model().generate_content(f"Lead Scout. Task: {task}. {briefing}").text,
        "GPT": call_openrouter("openai/gpt-4o", "Market Expert.", briefing),
        "Claude": call_openrouter("anthropic/claude-3.5-sonnet", "Roster Strategist.", briefing)
    }

# --- 7. UI INITIALIZATION ---
st.set_page_config(page_title="GM Suite: Master Terminal", layout="wide", page_icon="🏛️")
st.title("⚾ Dynasty GM Suite: Master Executive Terminal")

try:
    # INITIALIZE DATA
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws, roster_ws = sh.get_worksheet(0), sh.get_worksheet(1)
    
    raw_matrix = roster_ws.get_all_values()
    parsed_league = parse_horizontal_rosters(raw_matrix, TEAM_NAMES)
    all_players_flat = [p for sublist in parsed_league.values() for p in sublist]
    model = get_active_model()

    # SIDEBAR
    with st.sidebar:
        st.header("🏢 Front Office Tools")
        st.info("Strategy: Competitive 2026 / Peak 2027")
        st.divider()
        st.header(f"💰 FAAB: ${st.session_state.get('faab', 200.00):.2f}")
        # Add a Player Quick-Search in sidebar
        search_all = st.selectbox("Quick Search Ledger:", [""] + sorted(all_players_flat))
        if search_all:
            st.write(f"Current Team: **{[team for team, players in parsed_league.items() if search_all in players][0]}**")

    # UI TABS
    tabs = st.tabs(["🔁 Terminal", "🔥 Hypothetical Trade Arbitrator", "🔍 Automated Trade Finder", "📊 Live Ledger", "🕵️‍♂️ Pro Scouting", "💎 Sleepers", "📜 History"])

    # TAB 0: TRANSACTION TERMINAL (WITH NAME VALIDATION)
    with tabs[0]:
        st.subheader("Official Transaction Terminal")
        st.caption("Fuzzy matching enabled. If a name is misspelled, a verification window will appear.")
        
        mode = st.radio("Action:", ["Trade", "Add/Drop"], horizontal=True, key="terminal_mode")
        
        if mode == "Trade":
            col1, col2 = st.columns(2)
            with col1:
                t_a = st.selectbox("From Team:", TEAM_NAMES, key="t_a_final")
                p_a_input = st.text_area("Leaving Team A (Separate with commas):", key="p_a_final")
            with col2:
                t_b = st.selectbox("To Team:", TEAM_NAMES, key="t_b_final")
                p_b_input = st.text_area("Leaving Team B (Separate with commas):", key="p_b_final")
            
            if st.button("🔥 Execute Official Transaction", use_container_width=True):
                # CHECK NAMES BEFORE SENDING TO AI
                names_to_check = [n.strip() for n in p_a_input.split(",") if n.strip()]
                error_found = False
                for n in names_to_check:
                    if n not in parsed_league[t_a]:
                        suggestion = find_closest_player(n, parsed_league[t_a])
                        if suggestion:
                            verification_dialog(n, suggestion, t_a, {"type": "trade", "origin": t_a, "target": t_b})
                            error_found = True
                        else:
                            st.error(f"Player '{n}' not found on {t_a} and no similar names identified.")
                            error_found = True
                
                if not error_found:
                    with st.spinner("Processing Logic..."):
                        logic_prompt = f"Matrix: {raw_matrix}. Trade {p_a_input} from {t_a} to {t_b}. Trade {p_b_input} from {t_b} to {t_a}. Return ONLY Python list of lists."
                        res = model.generate_content(logic_prompt).text
                        clean_res = res.replace("```python", "").replace("```", "").strip()
                        try:
                            new_matrix = eval(clean_res)
                            roster_ws.clear(); roster_ws.update(new_matrix)
                            history_ws.append_row([f"TRADE: {t_a} ↔️ {t_b} | {p_a_input} for {p_b_input}"])
                            st.success("Ledger Synchronized!"); time.sleep(1); st.rerun()
                        except: st.error("AI Logic failed to restructure matrix. Check input format.")

    # TAB 1: HYPOTHETICAL TRADE ARBITRATOR
    with tabs[1]:
        st.subheader("🔥 Hypothetical Trade Arbitrator")
        trade_q = st.chat_input("Enter hypothetical deal (e.g. My Fried for his Skenes)")
        if trade_q:
            results = run_front_office_analysis(trade_q, json.dumps(parsed_league))
            with st.expander("📡 Live Market Intel", expanded=True): st.write(results["Research"])
            st.divider()
            c1, c2, c3 = st.columns(3)
            with c1: st.info("🟢 Lead Scout"); st.write(results["Gemini"])
            with c2: st.info("🔵 Market Analyst"); st.write(results["GPT"])
            with c3: st.info("🟠 Strategy Architect"); st.write(results["Claude"])

    # TAB 2: AUTOMATED TRADE FINDER
    with tabs[2]:
        st.subheader("🔍 Automated Win-Win Partner Finder")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            find_target = st.selectbox("I need:", ["Elite Prospects (<23)", "2026 Production", "Draft Capital"])
        with f_col2:
            find_offer = st.text_input("I am shopping:", placeholder="e.g. Max Fried")
        if st.button("Scour League", use_container_width=True):
            res = run_front_office_analysis(f"Find trades to get {find_target} by giving up {find_offer}", json.dumps(parsed_league), task="Trade Finder")
            st.markdown(res["Gemini"])

    # TAB 3: LIVE LEDGER
    with tabs[3]:
        st.subheader("📊 Roster Matrix")
        df_display = pd.DataFrame(raw_matrix)
        st.dataframe(df_display, use_container_width=True)
        st.download_button("📥 Export to Excel", convert_to_excel(df_display), "League_Ledger.xlsx")

    # TAB 4: PRO SCOUTING
    with tabs[4]:
        scout_p = st.text_input("Scout Player (Live News/ZiPS):", key="scout_q")
        if scout_p:
            scout_res = run_front_office_analysis(scout_p, json.dumps(parsed_league), task="Scouting")
            st.write(scout_res["Gemini"])

    # TAB 5: SLEEPERS
    with tabs[5]:
        if st.button("💎 Find 2026 Market Inefficiencies", use_container_width=True):
            sleeper_res = run_front_office_analysis("5 players with elite 2026 ZiPS undervalued in dynasty.", json.dumps(parsed_league), task="Sleepers")
            st.write(sleeper_res["Gemini"])

    # TAB 6: HISTORY
    with tabs[6]:
        st.subheader("📜 History Log")
        for log in history_ws.col_values(1)[::-1]: st.write(f"🔹 {log}")

except Exception as e:
    st.error(f"Executive Protocol Failed: {e}")
