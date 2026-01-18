import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from io import BytesIO
from PIL import Image
import requests
import json
import time
import difflib
import re
import ast

# --- 1. GLOBAL MASTER CONFIGURATION ---
SHEET_ID = "1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A"
USER_TEAM = "Witness Protection (Me)" 
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
    """Generates binary Excel file."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def clean_ai_matrix(raw_response):
    """Parses AI matrix response to ensure rectangularity."""
    try:
        match = re.search(r"(\[[\s\n]*\[.*\][\s\n]*\])", raw_response, re.DOTALL)
        if not match: return None
        matrix = eval(match.group(1))
        if isinstance(matrix, list) and len(matrix) > 0:
            max_cols = max(len(row) for row in matrix)
            for row in matrix:
                while len(row) < max_cols: row.append("")
            return matrix
        return None
    except: return None

def parse_horizontal_rosters(matrix):
    """Maps Row 1 Headers to Columns with Fuzzy Matching."""
    league_map = {}
    if not matrix: return league_map
    
    headers = [str(cell).strip() for cell in matrix[0]]
    # Pre-fill map
    for t in TEAM_NAMES: league_map[t] = []

    for col_idx, header_val in enumerate(headers):
        # Fuzzy match header against known TEAM_NAMES
        match = difflib.get_close_matches(header_val, TEAM_NAMES, n=1, cutoff=0.9)
        if match:
            team_key = match[0]
            for row_idx, row in enumerate(matrix[1:]):
                if col_idx < len(row):
                    player_val = str(row[col_idx]).strip()
                    if player_val and not player_val.endswith(':'):
                        league_map[team_key].append({
                            "name": player_val,
                            "row": row_idx + 2, 
                            "col": col_idx + 1
                        })
    return league_map

# --- 3. DETERMINISTIC SWAP ENGINE ---
def execute_hard_swap(matrix, team_a, players_a, team_b, players_b):
    """Moves players between columns mathematically (No AI)."""
    headers = [str(c).strip() for c in matrix[0]]
    
    try:
        match_a = difflib.get_close_matches(team_a, headers, n=1, cutoff=0.8)[0]
        col_a_idx = headers.index(match_a)
        
        match_b = difflib.get_close_matches(team_b, headers, n=1, cutoff=0.8)[0]
        col_b_idx = headers.index(match_b)
    except IndexError:
        return None, f"Column not found for {team_a} or {team_b}"

    def get_col_data(col_idx):
        return [row[col_idx] if col_idx < len(row) else "" for row in matrix]

    col_a_data = get_col_data(col_a_idx)
    col_b_data = get_col_data(col_b_idx)

    names_moving_a = [p['name'] for p in players_a]
    names_moving_b = [p['name'] for p in players_b]

    # Rebuild columns
    new_col_a = [col_a_data[0]] + [x for x in col_a_data[1:] if x not in names_moving_a and x != ""]
    new_col_b = [col_b_data[0]] + [x for x in col_b_data[1:] if x not in names_moving_b and x != ""]

    # Swap
    for p in names_moving_b: new_col_a.append(p)
    for p in names_moving_a: new_col_b.append(p)

    # Resize Matrix
    max_len = max(len(matrix), len(new_col_a), len(new_col_b))
    while len(matrix) < max_len: matrix.append([""] * len(matrix[0]))

    for r in range(max_len):
        if r < len(new_col_a):
            while len(matrix[r]) <= col_a_idx: matrix[r].append("")
            matrix[r][col_a_idx] = new_col_a[r]
        else:
             if len(matrix[r]) > col_a_idx: matrix[r][col_a_idx] = ""

        if r < len(new_col_b):
            while len(matrix[r]) <= col_b_idx: matrix[r].append("")
            matrix[r][col_b_idx] = new_col_b[r]
        else:
             if len(matrix[r]) > col_b_idx: matrix[r][col_b_idx] = ""

    return matrix, "Success"

# --- 4. CLEANUP PROTOCOL ---
def cleanup_trade_block(sh, players_traded):
    """Removes traded players from 'Trade Block' worksheet."""
    try:
        block_ws = sh.worksheet("Trade Block")
        block_names = block_ws.col_values(1)
        removed_count = 0
        for p_name in players_traded:
            matches = difflib.get_close_matches(p_name, block_names, n=1, cutoff=0.9)
            if matches:
                cell = block_ws.find(matches[0])
                if cell:
                    block_ws.delete_rows(cell.row)
                    removed_count += 1
                    block_names = block_ws.col_values(1) # Refresh
        return f"Cleaned {removed_count} from Block."
    except: return "No Block found."

# --- 5. AI & VISION ENGINE ---
def get_active_model():
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in models if '1.5' in m or '2.0' in m]
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

def parse_trade_screenshot(image_file, team_names):
    """Uses Gemini Vision to read trade screenshots."""
    model = get_active_model()
    img = Image.open(image_file)
    prompt = f"""
    Analyze this fantasy trade screenshot.
    Extract the two teams and players involved.
    Match teams to: {team_names}
    Output valid Python dict:
    {{
        "team_a": "Team Name",
        "players_a": ["Player 1", "Player 2"],
        "team_b": "Team Name",
        "players_b": ["Player 3"]
    }}
    """
    with st.spinner("👀 Vision Processing..."):
        try:
            res = model.generate_content([prompt, img]).text
            clean = res.replace("```python", "").replace("```", "").replace("json", "").strip()
            return ast.literal_eval(clean)
        except Exception as e: return None

# --- 6. ANALYSIS FUNCTIONS ---
def run_gm_analysis(query, league_data, task="Trade"):
    mandate = """
    REALISM GATE: Elite Youth > Aging Vets.
    If unrealistic, provide 3 SPECIFIC alternatives.
    """
    with st.spinner(f"📡 War Room: {task} Protocol..."):
        search = call_openrouter("perplexity/sonar", "Lead Sabermetrician.", f"Jan 2026 ZiPS and values for: {query}")
    brief = f"ROSTERS: {league_data}\nINTEL: {search}\nQUERY: {query}\nMANDATE: {mandate}"
    return {
        "Research": search,
        "Gemini": get_active_model().generate_content(f"Lead GM Verdict. {brief}").text,
        "GPT": call_openrouter("openai/gpt-4o", "Market Expert.", brief),
        "Claude": call_openrouter("anthropic/claude-3.5-sonnet", "Strategist.", brief)
    }

def analyze_trade_block_text(block_text, user_roster):
    prompt = f"Trade Block Audit. ROSTER: {user_roster}. BLOCK: {block_text}. Grade fits (A-F)."
    with st.spinner("Analyzing Matches..."):
        return call_openrouter("anthropic/claude-3.5-sonnet", "Assistant GM.", prompt)

def analyze_trade_block_image(image_file, user_roster):
    model = get_active_model()
    img = Image.open(image_file)
    prompt = f"Extract names. Compare to MY ROSTER: {user_roster}. Grade fit (A-F)."
    with st.spinner("👀 Scanning Block..."):
        return model.generate_content([prompt, img]).text

# --- 7. VERIFICATION DIALOG ---
@st.dialog("Verify Roster Sync")
def verify_trade_dialog(team_a, final_a, team_b, final_b, roster_ws, history_ws, raw_matrix, sh):
    st.warning("⚖️ **Identity Verification Required**")
    
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**From {team_a}:**")
        for p in final_a: st.write(f"- {p['name']}")
    with c2:
        st.write(f"**From {team_b}:**")
        for p in final_b: st.write(f"- {p['name']}")

    if st.button("🔥 Confirm & Push to Google Sheets", use_container_width=True):
        with st.spinner("Executing Swap & Cleaning Trade Block..."):
            new_matrix, status = execute_hard_swap(raw_matrix, team_a, final_a, team_b, final_b)
            if status == "Success":
                try:
                    roster_ws.clear()
                    roster_ws.update(new_matrix)
                    names_a = ", ".join([p['name'] for p in final_a])
                    names_b = ", ".join([p['name'] for p in final_b])
                    history_ws.append_row([f"TRADE: {team_a} ↔️ {team_b} | {names_a} for {names_b}"])
                    
                    # Cleanup
                    all_names = [p['name'] for p in final_a] + [p['name'] for p in final_b]
                    cleanup_status = cleanup_trade_block(sh, all_names)
                    
                    st.success(f"Success! {cleanup_status}")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e: st.error(f"API Error: {e}")
            else: st.error(f"Swap Failed: {status}")

# --- 8. FUZZY MATCH HELPERS ---
def get_fuzzy_matches(input_names, team_players):
    results = []
    if not team_players: return [None]
    ledger_names = [p['name'] for p in team_players]
    raw_list = [n.strip() for n in input_names.split(",") if n.strip()]
    for name in raw_list:
        matches = difflib.get_close_matches(name, ledger_names, n=1, cutoff=0.6)
        if matches:
            match_obj = next(p for p in team_players if p['name'] == matches[0])
            results.append(match_obj)
        else: results.append(None)
    return results

# --- 9. MAIN APP UI ---
st.set_page_config(page_title="GM Master Terminal", layout="wide", page_icon="🏛️")
st.title("🏛️ Dynasty GM Suite: Master Executive Terminal")

try:
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws, roster_ws = sh.get_worksheet(0), sh.get_worksheet(1)
    
    # Force Reload Button in Sidebar
    if st.sidebar.button("🔄 Force Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    try:
        block_ws = sh.worksheet("Trade Block")
        block_data = block_ws.col_values(1)
    except: block_data = []

    raw_matrix = roster_ws.get_all_values()
    full_league_data = parse_horizontal_rosters(raw_matrix)
    user_roster = full_league_data.get(USER_TEAM, [])
    model = get_active_model()

    tabs = st.tabs(["🔁 Terminal", "🔥 Analysis", "🔍 Finder", "📋 Block Monitor", "📊 Ledger", "🕵️‍♂️ Scouting", "💎 Sleepers", "🎯 Priority", "🎟️ Picks", "📜 History"])

    # TAB 0: TERMINAL
    with tabs[0]:
        st.subheader("Official Sync Terminal")
        tab_man, tab_vis = st.tabs(["🖐️ Manual Entry", "📸 Screenshot Upload"])
        
        # MANUAL
        with tab_man:
            c1, c2 = st.columns(2)
            with c1:
                team_a = st.selectbox("Team A:", TEAM_NAMES, key="man_ta")
                p_a = st.text_area("Giving:", key="man_pa")
            with c2:
                team_b = st.selectbox("Team B:", TEAM_NAMES, key="man_tb")
                p_b = st.text_area("Giving:", key="man_pb")
            if st.button("🔥 Verify Manual Trade"):
                ma = get_fuzzy_matches(p_a, full_league_data[team_a]) if p_a else []
                mb = get_fuzzy_matches(p_b, full_league_data[team_b]) if p_b else []
                if None in ma or None in mb: st.error("Player not found.")
                else: verify_trade_dialog(team_a, ma, team_b, mb, roster_ws, history_ws, raw_matrix, sh)

        # VISION
        with tab_vis:
            up_img = st.file_uploader("Upload Trade Screenshot", type=["jpg","png"])
            if up_img:
                data = parse_trade_screenshot(up_img, TEAM_NAMES)
                if data:
                    st.info("✅ Parsed. Verify details below:")
                    c1, c2 = st.columns(2)
                    with c1:
                        try: idx_a = TEAM_NAMES.index(data.get("team_a"))
                        except: idx_a = 0
                        v_ta = st.selectbox("Team A:", TEAM_NAMES, index=idx_a, key="v_ta")
                        v_pa = st.text_area("Players A:", value=", ".join(data.get("players_a", [])), key="v_pa")
                    with c2:
                        try: idx_b = TEAM_NAMES.index(data.get("team_b"))
                        except: idx_b = 0
                        v_tb = st.selectbox("Team B:", TEAM_NAMES, index=idx_b, key="v_tb")
                        v_pb = st.text_area("Players B:", value=", ".join(data.get("players_b", [])), key="v_pb")
                    
                    if st.button("🔥 Verify Vision Trade"):
                        ma = get_fuzzy_matches(v_pa, full_league_data[v_ta])
                        mb = get_fuzzy_matches(v_pb, full_league_data[v_tb])
                        if None in ma or None in mb: st.error("Player match failed. Check text.")
                        else: verify_trade_dialog(v_ta, ma, v_tb, mb, roster_ws, history_ws, raw_matrix, sh)

    # TAB 1: ANALYSIS
    with tabs[1]:
        q = st.chat_input("Analyze trade...")
        if q:
            res = run_gm_analysis(q, json.dumps(full_league_data))
            st.write(res["Research"])
            c1, c2 = st.columns(2)
            with c1: st.info("Verdict"); st.write(res["Gemini"])
            with c2: st.info("Strategy"); st.write(res["Claude"])

    # TAB 2: FINDER
    with tabs[2]:
        c1, c2 = st.columns(2)
        with c1: target = st.selectbox("I need:", ["Prospects", "2026 SP", "Draft Capital"])
        with c2: offer = st.text_input("Offering:")
        if st.button("Scour League"):
            st.write(run_gm_analysis(f"Get {target} for {offer}", json.dumps(full_league_data), "Finder")["Gemini"])

    # TAB 3: BLOCK MONITOR
    with tabs[3]:
        st.subheader("📋 Trade Block Evaluator")
        if block_data:
            st.success(f"✅ Synced {len(block_data)} players.")
            if st.button("Analyze Synced Block"):
                st.write(analyze_trade_block_text(", ".join(block_data), json.dumps(user_roster)))
        
        up_file = st.file_uploader("📸 Upload Block Screenshot", type=["jpg", "png"])
        if up_file and st.button("Analyze Image"):
            st.write(analyze_trade_block_image(up_file, json.dumps(user_roster)))

    # TAB 4: LEDGER (FIXED)
    with tabs[4]:
        st.subheader("📊 Roster Matrix")
        # Ensure raw_matrix has content before creating DataFrame
        if raw_matrix and len(raw_matrix) > 0:
            # FIX: Use first row as headers, rest as data
            headers = raw_matrix[0]
            data = raw_matrix[1:]
            df = pd.DataFrame(data, columns=headers)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("📥 Export Excel", convert_df_to_excel(df), "Rosters.xlsx")
        else:
            st.warning("⚠️ No data found in the roster sheet.")

    # TAB 5: SCOUTING
    with tabs[5]:
        scout_p = st.text_input("Scout Player:", key="scout_q")
        if scout_p:
            scout_res = run_gm_analysis(f"Full scouting report for {scout_p}", json.dumps(full_league_data), "Scouting")
            c1, c2 = st.columns(2)
            with c1: st.info("Gemini Analysis"); st.write(scout_res["Gemini"])
            with c2: st.info("Market Consensus"); st.write(scout_res["GPT"])

    # TAB 6: SLEEPERS
    with tabs[6]:
        if st.button("Identify Undervalued Breakouts"):
            sleeper_res = run_gm_analysis("Identify 5 players with elite 2026 ZiPS but low Dynasty ECR rankings.", json.dumps(full_league_data), "Sleepers")
            st.write(sleeper_res["Gemini"])
            st.write(sleeper_res["Claude"])

    # TAB 7: PRIORITY
    with tabs[7]:
        if st.button("Generate Priority Target List"):
            res = run_gm_analysis("Who are the top 5 targets I should move for now?", json.dumps(full_league_data), "Priority")
            st.write(res["Gemini"])

    # TAB 8: PICKS
    with tabs[8]:
        if st.button("Evaluate 2026 Class"):
             res = run_gm_analysis("Analyze 2026 MLB Draft Class strength.", "N/A", "Draft")
             st.write(res["Gemini"])

    # TAB 9: HISTORY
    with tabs[9]:
        for log in history_ws.col_values(1)[::-1]: st.write(f"🔹 {log}")

except Exception as e: st.error(f"System Offline: {e}")
