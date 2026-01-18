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
import re

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
    """Generates the binary Excel file for download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def parse_horizontal_rosters(matrix):
    """
    Maps the spreadsheet. 
    Row 1 = Team Headers. 
    Columns below = Players.
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
                    # We accept everything that isn't empty or a category label
                    if player_val and not player_val.endswith(':'):
                        league_map[team_header].append({
                            "name": player_val,
                            "row": row_idx + 2, # +2 for Header and 0-index
                            "col": col_idx + 1  # 1-based index for GSpread
                        })
    return league_map

# --- 3. THE DETERMINISTIC SWAP ENGINE (NO AI INVOLVED) ---
def execute_hard_swap(matrix, team_a, players_a, team_b, players_b):
    """
    Mathematically moves players between columns without AI hallucination.
    """
    # 1. Find Column Indices for both teams
    headers = [str(c).strip() for c in matrix[0]]
    try:
        col_a_idx = headers.index(team_a)
        col_b_idx = headers.index(team_b)
    except ValueError:
        return None, "Team Name not found in Header Row."

    # 2. Extract current full rosters (preserving headers and labels)
    # We will rebuild the columns entirely to avoid holes
    
    # Helper to get column data safe
    def get_col_data(col_idx):
        return [row[col_idx] if col_idx < len(row) else "" for row in matrix]

    col_a_data = get_col_data(col_a_idx)
    col_b_data = get_col_data(col_b_idx)

    # 3. Filter out the moving players from source columns
    names_moving_a = [p['name'] for p in players_a]
    names_moving_b = [p['name'] for p in players_b]

    # Rebuild A: Keep header (row 0), keep non-moving players
    new_col_a = [col_a_data[0]] + [
        x for x in col_a_data[1:] 
        if x not in names_moving_a and x != ""
    ]
    
    # Rebuild B: Keep header, keep non-moving players
    new_col_b = [col_b_data[0]] + [
        x for x in col_b_data[1:] 
        if x not in names_moving_b and x != ""
    ]

    # 4. Swap! Add incoming players to the bottom
    # (Append B's players to A, and A's players to B)
    for p in names_moving_b: new_col_a.append(p)
    for p in names_moving_a: new_col_b.append(p)

    # 5. Write back to Matrix (Pad with empty strings if needed)
    # Find max depth of sheet
    max_len = max(len(matrix), len(new_col_a), len(new_col_b))
    
    # Extend matrix rows if columns got longer
    while len(matrix) < max_len:
        matrix.append([""] * len(matrix[0]))

    # Update the specific columns in the matrix
    for r in range(max_len):
        # Update A
        if r < len(new_col_a):
            # Ensure row is long enough
            while len(matrix[r]) <= col_a_idx: matrix[r].append("")
            matrix[r][col_a_idx] = new_col_a[r]
        else:
             if len(matrix[r]) > col_a_idx: matrix[r][col_a_idx] = ""

        # Update B
        if r < len(new_col_b):
            while len(matrix[r]) <= col_b_idx: matrix[r].append("")
            matrix[r][col_b_idx] = new_col_b[r]
        else:
             if len(matrix[r]) > col_b_idx: matrix[r][col_b_idx] = ""

    return matrix, "Success"

# --- 4. FUZZY VALIDATION & DIALOGS ---
def get_fuzzy_matches(input_names, team_players):
    results = []
    # Create a clean list of just names for matching
    ledger_names = [p['name'] for p in team_players]
    
    raw_list = [n.strip() for n in input_names.split(",") if n.strip()]
    for name in raw_list:
        matches = difflib.get_close_matches(name, ledger_names, n=1, cutoff=0.6)
        if matches:
            # Retrieve the full player object (dict)
            match_obj = next(p for p in team_players if p['name'] == matches[0])
            results.append(match_obj)
        else:
            results.append(None)
    return results

@st.dialog("Verify Roster Sync")
def verify_trade_dialog(team_a, final_a, team_b, final_b, roster_ws, history_ws, raw_matrix):
    st.warning("⚖️ **Identity Verification Required**")
    st.caption("Confirming coordinates for Real-Time Execution.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**From {team_a}:**")
        for p in final_a: st.write(f"- {p['name']}")
    with c2:
        st.write(f"**From {team_b}:**")
        for p in final_b: st.write(f"- {p['name']}")

    if st.button("🔥 Confirm & Push to Google Sheets", use_container_width=True):
        with st.spinner("Calculating Deterministic Swap..."):
            # EXECUTE THE HARD SWAP
            new_matrix, status = execute_hard_swap(raw_matrix, team_a, final_a, team_b, final_b)
            
            if status == "Success":
                try:
                    # Update Google Sheets
                    roster_ws.clear()
                    roster_ws.update(new_matrix)
                    
                    # Log History
                    names_a = ", ".join([p['name'] for p in final_a])
                    names_b = ", ".join([p['name'] for p in final_b])
                    history_ws.append_row([f"TRADE: {team_a} ↔️ {team_b} | {names_a} for {names_b}"])
                    
                    st.success("Ledger Synchronized! Refreshing...")
                    time.sleep(1)
                    st.rerun() # REAL TIME REFRESH
                except Exception as e:
                    st.error(f"API Error: {e}")
            else:
                st.error(f"Swap Failed: {status}")

# --- 5. AI ENGINE (SELF-HEALING) ---
def get_active_model():
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in models if 'flash' in m]
        flash_models.sort(reverse=True)
        return genai.GenerativeModel(flash_models[0])
    except: return genai.GenerativeModel('gemini-1.5-flash')

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
    mandate = """
    REALISM GATE: 
    - Elite Youth (Witt/Gunnar) > Aging Veterans (Fried/Cole). 
    - If trade is lopsided, call it 'UNREALISTIC'.
    - If unrealistic, provide 3 SPECIFIC alternative trades.
    - Scout ALL 4 Ais.
    """
    with st.spinner("📡 Accessing Global Baseball Database..."):
        search = call_openrouter("perplexity/sonar", "Lead Sabermetrician.", f"Jan 2026 ZiPS and values for: {query}")
    
    brief = f"ROSTERS: {league_data}\nINTEL: {search}\nQUERY: {query}\nMANDATE: {mandate}"
    
    return {
        "Research": search,
        "Gemini": get_active_model().generate_content(f"Lead GM Verdict. {brief}").text,
        "GPT": call_openrouter("openai/gpt-4o", "Market Expert.", brief),
        "Claude": call_openrouter("anthropic/claude-3.5-sonnet", "Strategist.", brief)
    }

# --- 6. MAIN APP UI ---
st.set_page_config(page_title="GM Master Terminal", layout="wide", page_icon="🏛️")
st.title("🏛️ Dynasty GM Suite: Master Executive Terminal")

try:
    # A. CONNECT & FETCH
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws, roster_ws = sh.get_worksheet(0), sh.get_worksheet(1)
    
    # FETCH DATA ONCE
    raw_matrix = roster_ws.get_all_values()
    full_league_data = parse_horizontal_rosters(raw_matrix)
    model = get_active_model()

    # B. TABS
    tabs = st.tabs([
        "🔁 Terminal", 
        "🔥 Analysis", 
        "🔍 Finder", 
        "📊 Ledger", 
        "🕵️‍♂️ Scouting", 
        "💎 Sleepers", 
        "🎯 Priority", 
        "🎟️ Picks", 
        "📜 History"
    ])

    # --- TAB 0: TERMINAL ---
    with tabs[0]:
        st.subheader("Official Sync Terminal")
        st.caption("Real-Time Execution Engine Active.")
        c1, c2 = st.columns(2)
        with c1:
            team_a = st.selectbox("Team A (Owner):", TEAM_NAMES, key="t_a_final")
            p_a_input = st.text_area("Leaving Team A (Separate with commas):", key="p_a_final")
        with c2:
            team_b = st.selectbox("Team B (Counterparty):", TEAM_NAMES, key="t_b_final")
            p_b_input = st.text_area("Leaving Team B (Separate with commas):", key="p_b_final")
            
        if st.button("🔥 Verify & Execute Trade", use_container_width=True):
            match_a = get_fuzzy_matches(p_a_input, full_league_data[team_a])
            match_b = get_fuzzy_matches(p_b_input, full_league_data[team_b])
            
            if None in match_a or None in match_b:
                st.error("Error: Player name not found. Please check spelling.")
            else:
                verify_trade_dialog(team_a, match_a, team_b, match_b, roster_ws, history_ws, raw_matrix)

    # --- TAB 1: ANALYSIS ---
    with tabs[1]:
        st.subheader("🔥 Hypothetical Trade Arbitrator")
        trade_q = st.chat_input("Analyze deal...")
        if trade_q:
            res = run_gm_analysis(trade_q, json.dumps(full_league_data))
            with st.expander("📡 Live Intelligence Brief", expanded=True): st.write(res["Research"])
            c1, c2, c3 = st.columns(3)
            with c1: st.info("🟢 Gemini Verdict"); st.write(res["Gemini"])
            with c2: st.info("🔵 GPT Value"); st.write(res["GPT"])
            with c3: st.info("🟠 Claude Strategy"); st.write(res["Claude"])

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
            with st.expander("Strategic Alternatives (Claude)"): st.write(res["Claude"])

    # --- TAB 3: LEDGER ---
    with tabs[3]:
        st.subheader("📊 Roster Matrix (Live)")
        df_display = pd.DataFrame(raw_matrix)
        st.dataframe(df_display, use_container_width=True)
        # Convert df uses the utility function defined at top
        st.download_button("📥 Export Excel", convert_df_to_excel(df_display), "Rosters.xlsx")

    # --- TAB 4: SCOUTING ---
    with tabs[4]:
        st.subheader("🕵️‍♂️ Deep-Dive Scouting Report")
        scout_p = st.text_input("Scout Player:", key="scout_q")
        if scout_p:
            scout_res = run_gm_analysis(f"Full scouting report for {scout_p}", json.dumps(full_league_data), "Scouting")
            c1, c2 = st.columns(2)
            with c1: st.info("Gemini Analysis"); st.write(scout_res["Gemini"])
            with c2: st.info("Market Consensus"); st.write(scout_res["GPT"])

    # --- TAB 5: SLEEPERS ---
    with tabs[5]:
        st.subheader("💎 2026 Market Inefficiencies")
        if st.button("Identify Undervalued Breakouts"):
            sleeper_res = run_gm_analysis("Identify 5 players with elite 2026 ZiPS but low Dynasty ECR rankings.", json.dumps(full_league_data), "Sleepers")
            st.write(sleeper_res["Gemini"])
            st.write(sleeper_res["Claude"])

    # --- TAB 6: PRIORITY ---
    with tabs[6]:
        st.subheader("🎯 Retool Priority Board")
        if st.button("Generate Priority Target List"):
            res = run_gm_analysis("Who are the top 5 targets I should move for now?", json.dumps(full_league_data), "Priority")
            st.write(res["Gemini"])

    # --- TAB 7: PICKS ---
    with tabs[7]:
        st.subheader("🎟️ Draft Asset Tracker")
        if st.button("Evaluate 2026 Class"):
             res = run_gm_analysis("Analyze 2026 MLB Draft Class strength.", "N/A", "Draft")
             st.write(res["Gemini"])

    # --- TAB 8: HISTORY ---
    with tabs[8]:
        st.subheader("📜 History Log")
        for log in history_ws.col_values(1)[::-1]: st.write(f"🔹 {log}")

except Exception as e:
    st.error(f"Executive Protocol Failed: {e}")
