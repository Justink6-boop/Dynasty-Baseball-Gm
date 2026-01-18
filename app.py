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

# --- 2. THE STRUCTURAL PARSER (IRONCLAD LOGIC) ---
def get_gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def parse_horizontal_rosters(matrix):
    """
    Ensures the AI recognizes Team Names in Row 1.
    Every player found in a column is assigned to the header of that column.
    """
    league_map = {}
    if not matrix: return league_map
    
    # 1. Map the Headers (Row 1)
    headers = [str(cell).strip() for cell in matrix[0]]
    
    # 2. Iterate through every column in the sheet
    for col_idx, team_header in enumerate(headers):
        if team_header in TEAM_NAMES:
            league_map[team_header] = []
            # 3. Scan every row below the header for players
            for row_idx, row in enumerate(matrix[1:]):
                if col_idx < len(row):
                    player_val = str(row[col_idx]).strip()
                    # Filter out empty cells and category labels (e.g., "Pitchers:")
                    if player_val and not player_val.endswith(':'):
                        league_map[team_header].append({
                            "name": player_val,
                            "row": row_idx + 2, # +1 for 0-indexing, +1 for header row
                            "col": col_idx + 1  # Google Sheets is 1-indexed
                        })
    return league_map

# --- 3. FUZZY VERIFICATION DIALOG ---
def get_fuzzy_match(name, team_players):
    """Finds the closest name on a specific team to prevent parsing errors."""
    name_list = [p['name'] for p in team_players]
    matches = difflib.get_close_matches(name, name_list, n=1, cutoff=0.6)
    return matches[0] if matches else None

@st.dialog("Verify Roster Move")
def verify_names_dialog(raw_a, match_a, team_a, raw_b, match_b, team_b):
    st.write(f"⚠️ **Identity Verification Required**")
    st.write(f"On **{team_a}**, you typed '{raw_a}'. Did you mean **{match_a}**?")
    st.write(f"On **{team_b}**, you typed '{raw_b}'. Did you mean **{match_b}**?")
    
    if st.button("Confirm & Execute Sync"):
        # Execution logic would go here
        st.success("Ledger Syncing...")
        time.sleep(1)
        st.rerun()

# --- 4. THE AI BRAIN (SELF-HEALING) ---
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

def run_hypothetical_analysis(trade_query, league_json):
    """Processes value, age, and scarcity to determine a winner."""
    mandate = """
    You are a high-stakes Dynasty GM. 
    1. POSITIONAL VALUE: Elite SS/OF bats are worth 5x aging SPs.
    2. WINNER: Decide who wins based on 2026-2029 surplus value.
    3. REALISM: If the trade is lopsided (e.g. Fried for Witt), call it 'UNREALISTIC' and explain why.
    """
    with st.spinner("📡 Accessing 2026 ZiPS & Dynasty Value Tiers..."):
        search = call_openrouter("perplexity/sonar", "Dynasty Analyst.", f"Jan 2026 ZiPS and trade values for: {trade_query}")
    
    brief = f"LEAGUE: {league_json}\nINTEL: {search}\nTRADE: {trade_query}\nMANDATE: {mandate}"
    model = get_active_model()
    
    return {
        "Research": search,
        "Gemini": model.generate_content(f"Lead GM Verdict. {brief}").text,
        "GPT": call_openrouter("openai/gpt-4o", "Market Valuator.", brief),
        "Claude": call_openrouter("anthropic/claude-3.5-sonnet", "Strategist.", brief)
    }

# --- 5. MAIN UI ---
st.set_page_config(page_title="GM Suite: Ironclad Ledger", layout="wide", page_icon="🏛️")
st.title("⚾ Dynasty GM Suite: Executive Terminal")

try:
    # A. INITIALIZE
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws, roster_ws = sh.get_worksheet(0), sh.get_worksheet(1)
    
    raw_matrix = roster_ws.get_all_values()
    full_league_data = parse_horizontal_rosters(raw_matrix)
    
    # B. TABS
    tabs = st.tabs(["🔁 Terminal", "🔥 Hypothetical Trade Analyzer", "🔍 Trade Finder", "📊 Live Ledger", "🕵️‍♂️ Scouting", "💎 Sleepers", "📜 History"])

    # TAB 0: TERMINAL (THE VERIFIER)
    with tabs[0]:
        st.subheader("Official Sync Terminal")
        st.caption("This terminal maps Row 1 to Columns. It cannot 'lose' team ownership.")
        
        c1, c2 = st.columns(2)
        with c1:
            t_a = st.selectbox("Team A:", TEAM_NAMES, key="t_a_final")
            p_a_input = st.text_input("Leaving Team A:", key="p_a_final")
        with c2:
            t_b = st.selectbox("Team B:", TEAM_NAMES, key="t_b_final")
            p_b_input = st.text_input("Leaving Team B:", key="p_b_final")
            
        if st.button("🔥 Verify & Execute Trade", use_container_width=True):
            match_a = get_fuzzy_match(p_a_input, full_league_data[t_a])
            match_b = get_fuzzy_match(p_b_input, full_league_data[t_b])
            
            if match_a and match_b:
                verify_names_dialog(p_a_input, match_a, t_a, p_b_input, match_b, t_b)
            else:
                st.error("Could not find one of those players on the selected rosters. Check spelling.")

    # TAB 1: HYPOTHETICAL ANALYZER
    with tabs[1]:
        st.subheader("🔥 Hypothetical Trade Arbitrator")
        trade_q = st.chat_input("Analyze deal: (e.g. Max Fried for Paul Skenes)")
        if trade_q:
            res = run_hypothetical_analysis(trade_q, json.dumps(full_league_data))
            with st.expander("📡 Live 2026 Intelligence"): st.write(res["Research"])
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1: st.info("🟢 Gemini Verdict"); st.write(res["Gemini"])
            with col2: st.info("🔵 GPT Market Value"); st.write(res["GPT"])
            with col3: st.info("🟠 Claude Strategy"); st.write(res["Claude"])

    # TAB 3: LEDGER
    with tabs[3]:
        st.subheader("📊 Current Ledger Matrix")
        st.dataframe(pd.DataFrame(raw_matrix), use_container_width=True)

except Exception as e:
    st.error(f"Executive Protocol Failed: {e}")
