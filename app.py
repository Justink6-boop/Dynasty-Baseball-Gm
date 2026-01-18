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

# --- 3. AI ENGINES (GEN & VISION) ---
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

def organize_roster_ai(player_list):
    """Uses AI to sort a raw list of players into positional categories."""
    model = get_active_model()
    prompt = f"""
    You are a Fantasy Baseball Clerk. 
    Here is a list of players: {player_list}
    
    TASK:
    1. Identify the primary position for each player.
    2. Group them into two strict lists: 'HITTERS:' and 'PITCHERS:'.
    3. Within Hitters, sort by field position (C, 1B, 2B, 3B, SS, OF, DH).
    4. Within Pitchers, sort by (SP, RP).
    
    OUTPUT FORMAT:
    Return a single Python list of strings. 
    Use the exact headers 'HITTERS:' and 'PITCHERS:' (with the colon).
    """
    try:
        response = model.generate_content(prompt).text
        match = re.search(r"(\[.*\])", response, re.DOTALL)
        if match: return eval(match.group(1))
        return None
    except: return None

def smart_correct_vision(vision_data, full_league_data):
    """Cross-references AI vision results against the official ledger."""
    t_a = vision_data.get("team_a")
    t_b = vision_data.get("team_b")
    if t_a not in full_league_data or t_b not in full_league_data: return vision_data

    roster_a = [p['name'].lower().strip() for p in full_league_data[t_a]]
    roster_b = [p['name'].lower().strip() for p in full_league_data[t_b]]
    final_players_a = []
    final_players_b = []
    
    all_found = vision_data.get("players_a", []) + vision_data.get("players_b", [])
    for player in all_found:
        p_clean = player.lower().strip()
        match_a = difflib.get_close_matches(p_clean, roster_a, n=1, cutoff=0.6)
        match_b = difflib.get_close_matches(p_clean, roster_b, n=1, cutoff=0.6)
        
        if match_a: final_players_a.append(player)
        elif match_b: final_players_b.append(player)
        else:
            if player in vision_data.get("players_a", []): final_players_a.append(player)
            else: final_players_b.append(player)

    return {"team_a": t_a, "players_a": final_players_a, "team_b": t_b, "players_b": final_players_b}

# --- 4. LOGIC & PARSING ---
def parse_horizontal_rosters(matrix):
    """Maps Row 1 Headers to Columns."""
    league_map = {}
    if not matrix: return league_map
    headers = [str(cell).strip() for cell in matrix[0]]
    for t in TEAM_NAMES: league_map[t] = []

    for col_idx, header_val in enumerate(headers):
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

def parse_trade_screenshot(image_file, team_names):
    """Uses Gemini Vision to read trade screenshots."""
    model = get_active_model()
    img = Image.open(image_file)
    prompt = f"""
    Analyze this fantasy baseball trade screenshot.
    CRITICAL: Expand abbreviations (e.g. "Z. Neto" -> "Zach Neto").
    1. Identify the two teams. Match to: {team_names}
    2. Extract the players.
    Output valid Python dict: {{"team_a": "...", "players_a": [], "team_b": "...", "players_b": []}}
    """
    with st.spinner("👀 Vision Processing..."):
        try:
            res = model.generate_content([prompt, img]).text
            clean = res.replace("```python", "").replace("```", "").replace("json", "").strip()
            return ast.literal_eval(clean)
        except: return None

def execute_hard_swap(matrix, team_a, players_a, team_b, players_b):
    """Moves players between columns mathematically."""
    headers = [str(c).strip() for c in matrix[0]]
    try:
        match_a = difflib.get_close_matches(team_a, headers, n=1, cutoff=0.8)[0]
        col_a_idx = headers.index(match_a)
        match_b = difflib.get_close_matches(team_b, headers, n=1, cutoff=0.8)[0]
        col_b_idx = headers.index(match_b)
    except: return None, "Column not found."

    def get_col_data(col_idx): return [row[col_idx] if col_idx < len(row) else "" for row in matrix]
    col_a_data = get_col_data(col_a_idx); col_b_data = get_col_data(col_b_idx)
    names_moving_a = [p['name'] for p in players_a]; names_moving_b = [p['name'] for p in players_b]

    new_col_a = [col_a_data[0]] + [x for x in col_a_data[1:] if x not in names_moving_a and x != ""]
    new_col_b = [col_b_data[0]] + [x for x in col_b_data[1:] if x not in names_moving_b and x != ""]
    for p in names_moving_b: new_col_a.append(p)
    for p in names_moving_a: new_col_b.append(p)

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

def cleanup_trade_block(sh, players_traded):
    """Removes traded players from 'Trade Block' worksheet."""
    try:
        block_ws = sh.worksheet("Trade Block")
        block_names = block_ws.col_values(2) 
        removed_count = 0
        for p_name in players_traded:
            matches = difflib.get_close_matches(p_name, block_names, n=1, cutoff=0.9)
            if matches:
                cell = block_ws.find(matches[0])
                if cell:
                    block_ws.delete_rows(cell.row)
                    removed_count += 1
                    block_names = block_ws.col_values(2)
        return f"Cleaned {removed_count} from Block."
    except: return "No Block found."

def get_fuzzy_matches(input_names, team_players):
    """Aggressive Matcher."""
    results = []
    if not team_players: return [None]
    
    ledger_map = {p['name'].strip().lower(): p for p in team_players}
    ledger_names_clean = list(ledger_map.keys())
    raw_list = [n.strip() for n in input_names.split(",") if n.strip()]
    
    for name in raw_list:
        clean_input = name.strip().lower()
        match_found = None
        if clean_input in ledger_map: match_found = ledger_map[clean_input]['name']
        if not match_found:
            matches = difflib.get_close_matches(clean_input, ledger_names_clean, n=1, cutoff=0.5)
            if matches: match_found = ledger_map[matches[0]]['name']
        if not match_found and "." in clean_input:
            parts = clean_input.split(".")
            if len(parts) >= 2:
                first_init = parts[0].strip(); last_seg = parts[1].strip()
                for real_name in ledger_names_clean:
                    if last_seg in real_name and real_name.startswith(first_init):
                        match_found = ledger_map[real_name]['name']; break
        if match_found:
            match_obj = next((p for p in team_players if p['name'] == match_found), None)
            if match_obj: results.append(match_obj)
            else: results.append({"name": f"❌ '{name}' Error", "row": -1})
        else: results.append({"name": f"❌ '{name}' Not Found", "row": -1})
    return results

# --- 5. IMPACT ANALYTICS & SAVE ENGINE ---
def run_gm_analysis(query, league_data, task="Trade"):
    mandate = "REALISM GATE: Elite Youth > Aging Vets. Scout ALL 4 Ais."
    with st.spinner(f"📡 War Room: {task} Protocol..."):
        search = call_openrouter("perplexity/sonar", "Lead Sabermetrician.", f"Jan 2026 ZiPS and values for: {query}")
    brief = f"ROSTERS: {league_data}\nINTEL: {search}\nQUERY: {query}\nMANDATE: {mandate}"
    return {
        "Research": search,
        "Gemini": get_active_model().generate_content(f"Lead GM Verdict. {brief}").text,
        "GPT": call_openrouter("openai/gpt-4o", "Market Expert.", brief),
        "Claude": call_openrouter("anthropic/claude-3.5-sonnet", "Strategist.", brief)
    }

def analyze_and_save_block(image_files, user_roster, sh):
    """
    1. Extracts players.
    2. Calculates SCORING IMPACT (Pct Increase).
    3. Calculates OUTLOOK SHIFT (Rebuilder -> Contender).
    4. Saves to 'Trade Block' Google Sheet.
    """
    model = get_active_model()
    prompt = f"""
    You are an Expert Dynasty GM. 
    MY ROSTER (Analyze Deeply): {user_roster}
    MY GOAL: Win in 2027 (Retooling).
    SCORING SYSTEM: Standard Fantasy Points (H2H).
    
    TASK:
    1. Extract ALL players from the images. Expand abbreviations.
    2. For EACH player, perform a "Gap Analysis" against my current roster:
       - 'Impact_Pct': Estimate the % increase in my weekly team scoring if I swap my current starter for this player. (e.g. "+5.2%")
       - 'Outlook_Shift': How does this specific player change my team's trajectory? (e.g. "Fringe -> Contender" or "No Change").
       - 'Verdict': PURSUE or PASS.
       - 'Analysis': Brief reasoning citing ZiPS/Dynasty Rank.
    
    OUTPUT FORMAT:
    Return ONLY a JSON list of dictionaries.
    Example:
    [
      {{"Team": "Guti Gang", "Player": "Zach Neto", "Position": "SS", "Grade": "A", "Verdict": "PURSUE", "Impact_Pct": "+4.1%", "Outlook_Shift": "Accelerator", "Analysis": "Upgrade over current SS."}},
      ...
    ]
    """
    
    content = [prompt]
    for img_file in image_files: content.append(Image.open(img_file))
        
    with st.spinner(f"👀 Calculating Scoring Projections & Saving..."):
        try:
            response = model.generate_content(content).text
            clean_json = response.replace("```json", "").replace("```", "").strip()
            match = re.search(r"(\[.*\])", clean_json, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                try:
                    block_ws = sh.worksheet("Trade Block")
                except:
                    block_ws = sh.add_worksheet("Trade Block", 1000, 10)
                    # HEADER ROW with New Analytics Columns
                    block_ws.append_row(["Team", "Player", "Position", "Grade", "Verdict", "Impact %", "Outlook Shift", "Analysis", "Timestamp"])
                
                timestamp = time.strftime("%Y-%m-%d %H:%M")
                rows_to_add = []
                for entry in data:
                    rows_to_add.append([
                        entry.get("Team", "Unknown"),
                        entry.get("Player", "Unknown"),
                        entry.get("Position", "?"),
                        entry.get("Grade", "N/A"),
                        entry.get("Verdict", "N/A"),
                        entry.get("Impact_Pct", "0%"),      # NEW
                        entry.get("Outlook_Shift", "-"),    # NEW
                        entry.get("Analysis", ""),
                        timestamp
                    ])
                block_ws.append_rows(rows_to_add)
                return data 
            else: return None
        except Exception as e:
            st.error(f"Analysis Failed: {e}"); return None

# --- 6. UI DIALOGS ---
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
                    
                    all_names = [p['name'] for p in final_a] + [p['name'] for p in final_b]
                    cleanup_status = cleanup_trade_block(sh, all_names)
                    
                    st.success(f"Success! {cleanup_status}")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e: st.error(f"API Error: {e}")
            else: st.error(f"Swap Failed: {status}")

# --- 7. MAIN APP UI ---
st.set_page_config(page_title="GM Master Terminal", layout="wide", page_icon="🏛️")
st.title("🏛️ Dynasty GM Suite: Master Executive Terminal")

try:
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws = sh.get_worksheet(0) 
    roster_ws = sh.get_worksheet(1) 
    
    if st.sidebar.button("🔄 Force Refresh"): st.cache_data.clear(); st.rerun()
    st.sidebar.divider()
    st.sidebar.header("🛠️ Roster Inspector")
    debug_team = st.sidebar.selectbox("Inspect Team:", ["Select..."] + TEAM_NAMES)
    
    raw_matrix = roster_ws.get_all_values()
    full_league_data = parse_horizontal_rosters(raw_matrix)
    user_roster = full_league_data.get(USER_TEAM, [])
    
    if debug_team != "Select...":
        r = full_league_data.get(debug_team, [])
        st.sidebar.write(f"Found {len(r)} players.")
        st.sidebar.code("\n".join(sorted([p['name'] for p in r])))

    tabs = st.tabs(["🔁 Terminal", "🔥 Analysis", "🔍 Finder", "📋 Block Monitor", "📊 Ledger", "🕵️‍♂️ Scouting", "💎 Sleepers", "🎯 Priority", "🎟️ Picks", "📜 History"])

    with tabs[0]:
        st.subheader("Official Sync Terminal")
        tab_man, tab_vis = st.tabs(["🖐️ Manual Entry", "📸 Screenshot Upload"])
        with tab_man:
            c1, c2 = st.columns(2)
            with c1:
                team_a = st.selectbox("Team A:", TEAM_NAMES, key="man_ta")
                p_a = st.text_area("Giving:", key="man_pa")
            with c2:
                team_b = st.selectbox("Team B:", TEAM_NAMES, key="man_tb")
                p_b = st.text_area("Giving:", key="man_pb")
            if st.button("🔥 Verify Manual Trade"):
                if team_a not in full_league_data or team_b not in full_league_data: st.error("Team not found.")
                else:
                    ma = get_fuzzy_matches(p_a, full_league_data[team_a]) if p_a else []
                    mb = get_fuzzy_matches(p_b, full_league_data[team_b]) if p_b else []
                    if any(x.get('row') == -1 for x in ma + mb if x): st.error("Match failed.")
                    else: verify_trade_dialog(team_a, ma, team_b, mb, roster_ws, history_ws, raw_matrix, sh)

        with tab_vis:
            st.info("📸 AI auto-corrects team mix-ups.")
            up_img = st.file_uploader("Upload Trade Screenshot", type=["jpg","png"])
            if up_img:
                raw_data = parse_trade_screenshot(up_img, TEAM_NAMES)
                if raw_data:
                    data = smart_correct_vision(raw_data, full_league_data)
                    st.success("✅ Parsed & Validated.")
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
                        if any(x.get('row') == -1 for x in ma + mb if x): st.error("Match failed.")
                        else: verify_trade_dialog(v_ta, ma, v_tb, mb, roster_ws, history_ws, raw_matrix, sh)

    with tabs[1]:
        q = st.chat_input("Analyze trade...")
        if q:
            res = run_gm_analysis(q, json.dumps(full_league_data))
            st.write(res["Research"])
            c1, c2 = st.columns(2)
            with c1: st.info("Verdict"); st.write(res["Gemini"])
            with c2: st.info("Strategy"); st.write(res["Claude"])

    with tabs[2]:
        c1, c2 = st.columns(2)
        with c1: target = st.selectbox("I need:", ["Prospects", "2026 SP", "Draft Capital"])
        with c2: offer = st.text_input("Offering:")
        if st.button("Scour League"):
            st.write(run_gm_analysis(f"Get {target} for {offer}", json.dumps(full_league_data), "Finder")["Gemini"])

    with tabs[3]:
        st.subheader("📋 Living Trade Block")
        try:
            block_ws = sh.worksheet("Trade Block")
            block_records = block_ws.get_all_records()
            if block_records:
                st.success(f"📂 Database: {len(block_records)} Active Players")
                df_block = pd.DataFrame(block_records)
                st.dataframe(df_block, use_container_width=True)
            else: st.info("Database Empty.")
        except: st.warning("Sheet not ready.")
        
        st.divider()
        st.subheader("📸 Add New Intel")
        up_files = st.file_uploader("Upload Block Screenshots", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if up_files and st.button("Calculate Projections & Save"):
            new_data = analyze_and_save_block(up_files, json.dumps(user_roster), sh)
            if new_data:
                st.success(f"✅ Analytics Saved! Refreshing...")
                time.sleep(2); st.rerun()

    with tabs[4]:
        st.subheader("📊 Roster Matrix")
        if raw_matrix and len(raw_matrix) > 0:
            with st.expander("✨ Roster Architect", expanded=False):
                col_single, col_bulk = st.columns(2)
                with col_single:
                    target_team = st.selectbox("Single Team:", TEAM_NAMES, key="sort_single")
                    if st.button(f"Organize {target_team}"):
                        headers = [str(c).strip() for c in raw_matrix[0]]
                        try:
                            col_idx = headers.index(target_team)
                            curr = [row[col_idx] for row in raw_matrix[1:] if col_idx < len(row) and row[col_idx].strip()]
                            sorted_list = organize_roster_ai(curr)
                            if sorted_list:
                                for r in range(1, len(raw_matrix)):
                                    if col_idx < len(raw_matrix[r]): raw_matrix[r][col_idx] = ""
                                while len(raw_matrix) < len(sorted_list) + 1:
                                    raw_matrix.append([""] * len(raw_matrix[0]))
                                for i, item in enumerate(sorted_list):
                                    raw_matrix[i+1][col_idx] = item
                                roster_ws.clear(); roster_ws.update(raw_matrix)
                                st.success(f"✅ Organized!"); time.sleep(1); st.rerun()
                        except: st.error("Failed.")
                with col_bulk:
                    if st.button("🚀 Organize ENTIRE League"):
                        headers = [str(c).strip() for c in raw_matrix[0]]
                        prog = st.progress(0)
                        valid_cols = [(idx, h) for idx, h in enumerate(headers) if h in TEAM_NAMES]
                        for i, (col_idx, team_name) in enumerate(valid_cols):
                            curr = [row[col_idx] for row in raw_matrix[1:] if col_idx < len(row) and row[col_idx].strip()]
                            s_list = organize_roster_ai(curr)
                            if s_list:
                                for r in range(1, len(raw_matrix)):
                                    if col_idx < len(raw_matrix[r]): raw_matrix[r][col_idx] = ""
                                while len(raw_matrix) < len(s_list) + 1:
                                    raw_matrix.append([""] * len(raw_matrix[0]))
                                for k, item in enumerate(s_list):
                                    raw_matrix[k+1][col_idx] = item
                            prog.progress((i+1)/len(valid_cols))
                        roster_ws.clear(); roster_ws.update(raw_matrix)
                        st.success("✅ League Organized!"); time.sleep(2); st.rerun()

            df = pd.DataFrame(raw_matrix[1:], columns=raw_matrix[0])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else: st.warning("⚠️ No data.")

    # (Tabs 5-9 kept same as previous correct version)
    with tabs[5]:
        scout_p = st.text_input("Scout Player:", key="scout_q")
        if scout_p:
            res = run_gm_analysis(f"Full scouting report for {scout_p}", json.dumps(full_league_data), "Scouting")
            c1, c2 = st.columns(2)
            with c1: st.info("Gemini"); st.write(res["Gemini"])
            with c2: st.info("Consensus"); st.write(res["GPT"])

    with tabs[6]:
        if st.button("Identify Breakouts"):
            res = run_gm_analysis("Identify 5 players with elite 2026 ZiPS but low Dynasty ECR rankings.", json.dumps(full_league_data), "Sleepers")
            st.write(res["Gemini"]); st.write(res["Claude"])

    with tabs[7]:
        if st.button("Generate Targets"):
            res = run_gm_analysis("Who are the top 5 targets I should move for now?", json.dumps(full_league_data), "Priority")
            st.write(res["Gemini"])

    with tabs[8]:
        if st.button("Evaluate 2026 Class"):
             res = run_gm_analysis("Analyze 2026 MLB Draft Class strength.", "N/A", "Draft")
             st.write(res["Gemini"])

    with tabs[9]:
        for log in history_ws.col_values(1)[::-1]: st.write(f"🔹 {log}")

except Exception as e: st.error(f"System Offline: {e}")
