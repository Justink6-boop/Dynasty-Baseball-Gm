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
import asyncio 

# --- 1. GLOBAL MASTER CONFIGURATION ---
SHEET_ID = "1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A"
USER_TEAM = "Witness Protection (Me)" 
TEAM_NAMES = [
    "Witness Protection (Me)", "Bobbys Squad", "Arm Barn Heros", 
    "Guti Gang", "Happy", "Hit it Hard Hit it Far", 
    "ManBearPuig", "Milwaukee Beers", "Seiya Later", "Special Eds"
]

# --- 2. CORE UTILITY ENGINE (CACHED) ---
def get_gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def flatten_roster_to_df(league_data):
    flat_data = []
    for team, players in league_data.items():
        current_cat = "Unknown"
        for p in players:
            name = p['name']
            if "HITTERS:" in name:
                current_cat = "Hitter"
                continue
            elif "PITCHERS:" in name:
                current_cat = "Pitcher"
                continue
            flat_data.append({"Team": team, "Player": name, "Category": current_cat})
    return pd.DataFrame(flat_data)

# --- 3. AI ENGINES (ASYNC & PARALLEL) ---
def get_active_model():
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in models if '1.5' in m or '2.0' in m]
        flash_models.sort(reverse=True)
        return genai.GenerativeModel(flash_models[0])
    except: return genai.GenerativeModel('gemini-1.5-flash')

async def async_call_openrouter(model_id, persona, prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}", "HTTP-Referer": "https://streamlit.io"}
    data = {"model": model_id, "messages": [{"role": "system", "content": persona}, {"role": "user", "content": prompt}]}
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(None, lambda: requests.post(url, headers=headers, json=data, timeout=30))
        return response.json()['choices'][0]['message']['content'] if response.status_code == 200 else f"Error {response.status_code}"
    except Exception as e: return f"Error: {e}"

async def async_run_gm_analysis(query, league_data, intel_data, task="Trade"):
    """
    UPGRADED WAR ROOM:
    1. Forces live research of Dynasty Rankings/ZiPS.
    2. Implements a 'Trade Value Calculator' mental model.
    """
    
    # 1. RESEARCH PHASE: Aggressively hunt for VALUES, not just stats.
    search_prompt = f"""
    Search for CURRENT Dynasty Baseball Trade Values and 2026 ZiPS Projections for: {query}.
    Find specific rankings (e.g. "Top 10 Dynasty SP" or "Top 50 Prospects").
    Look for "Dynasty League Baseball" or "Fangraphs" trade charts.
    """
    
    with st.spinner(f"📡 War Room: {task} Protocol (Phase 1: Live Value Check)..."):
        # We use Perplexity to get the REAL rankings, preventing hallucinations
        search_res = await async_call_openrouter("perplexity/sonar", "Lead Scout.", search_prompt)
    
    # 2. THE REALISM MANDATE
    mandate = """
    ROLE: You are a Hard-Nosed Dynasty Trade Calculator.
    
    CRITICAL RULES:
    1. **IGNORE NAME VALUE**. Focus ONLY on 3-Year Projection Windows (2026-2028).
    2. **REALISM CHECK**: 
       - If User trades an Aging Vet (e.g. Max Fried) for Elite Youth (e.g. Skenes/Chourio), REJECT IT IMMEDIATELY. Label it "Fleecing/Impossible".
       - Trade Value must be within 15% to be "Fair".
    3. **SOURCES**: Base valuations on Fangraphs Auction Calculator logic and current Dynasty Consensus Rankings.
    
    FORMAT:
    - **Trade Grade**: (0-100 Scale for fairness)
    - **Winner**: (User or Opponent)
    - **Realism**: (Realistic / Lopsided / Fantasy Land)
    - **Analysis**: Use ZiPS/Steamer references.
    """
    
    brief = f"ROSTERS: {league_data}\nINTEL: {intel_data}\nLIVE RANKINGS: {search_res}\nQUERY: {query}\nMANDATE: {mandate}"
    
    # 3. PARALLEL EXECUTION
    with st.spinner("⚔️ Calculating Trade Values (Parallel Processing)..."):
        task_gemini = asyncio.to_thread(get_active_model().generate_content, f"Lead GM Verdict. {brief}")
        task_gpt = async_call_openrouter("openai/gpt-4o", "Market Expert (Fangraphs Logic).", brief)
        task_claude = async_call_openrouter("anthropic/claude-3.5-sonnet", "Strategist (Dynasty Focus).", brief)
        
        res_gemini, res_gpt, res_claude = await asyncio.gather(task_gemini, task_gpt, task_claude)
        
    return {
        "Research": search_res,
        "Gemini": res_gemini.text,
        "GPT": res_gpt,
        "Claude": res_claude
    }

def run_fast_analysis(query, league_data, intel_data, task):
    return asyncio.run(async_run_gm_analysis(query, league_data, intel_data, task))

def organize_roster_ai(player_list):
    """Uses AI to sort players into Hitters/Pitchers."""
    model = get_active_model()
    prompt = f"Sort list into ['HITTERS:', ... 'PITCHERS:', ...]. List: {player_list}"
    try:
        response = model.generate_content(prompt).text
        match = re.search(r"(\[.*\])", response, re.DOTALL)
        if match: return eval(match.group(1))
        return None
    except: return None

def smart_correct_vision(vision_data, full_league_data):
    """Cross-references AI vision results against the official ledger."""
    t_a, t_b = vision_data.get("team_a"), vision_data.get("team_b")
    if t_a not in full_league_data or t_b not in full_league_data: return vision_data

    roster_a = [p['name'].lower().strip() for p in full_league_data[t_a]]
    roster_b = [p['name'].lower().strip() for p in full_league_data[t_b]]
    
    final_a, final_b = [], []
    all_found = vision_data.get("players_a", []) + vision_data.get("players_b", [])
    
    for player in all_found:
        p_clean = player.lower().strip()
        if difflib.get_close_matches(p_clean, roster_a, n=1, cutoff=0.6): final_a.append(player)
        elif difflib.get_close_matches(p_clean, roster_b, n=1, cutoff=0.6): final_b.append(player)
        else:
            if player in vision_data.get("players_a", []): final_a.append(player)
            else: final_b.append(player)

    return {"team_a": t_a, "players_a": final_a, "team_b": t_b, "players_b": final_b}

# --- 4. LOGIC & PARSING ---
def parse_horizontal_rosters(matrix):
    """Maps Row 1 Headers to Columns."""
    league_map = {}
    if not matrix: return league_map
    headers = [str(c).strip() for c in matrix[0]]
    for t in TEAM_NAMES: league_map[t] = []
    for col_idx, header_val in enumerate(headers):
        match = difflib.get_close_matches(header_val, TEAM_NAMES, n=1, cutoff=0.9)
        if match:
            team_key = match[0]
            for row_idx, row in enumerate(matrix[1:]):
                if col_idx < len(row):
                    val = str(row[col_idx]).strip()
                    if val and not val.endswith(':'):
                        league_map[team_key].append({"name": val, "row": row_idx + 2, "col": col_idx + 1})
    return league_map

def parse_trade_screenshot(image_file, team_names):
    """Uses Gemini Vision to read trade screenshots."""
    model = get_active_model()
    img = Image.open(image_file)
    prompt = f"Extract trade details. Expand abbreviations (Z. Neto -> Zach Neto). Match teams: {team_names}. Return JSON dict."
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
        idx_a = headers.index(difflib.get_close_matches(team_a, headers, n=1, cutoff=0.8)[0])
        idx_b = headers.index(difflib.get_close_matches(team_b, headers, n=1, cutoff=0.8)[0])
    except: return None, "Column not found."

    col_a = [row[idx_a] if idx_a < len(row) else "" for row in matrix]
    col_b = [row[idx_b] if idx_b < len(row) else "" for row in matrix]
    
    mov_a = [p['name'] for p in players_a]
    mov_b = [p['name'] for p in players_b]

    new_a = [col_a[0]] + [x for x in col_a[1:] if x not in mov_a and x != ""]
    new_b = [col_b[0]] + [x for x in col_b[1:] if x not in mov_b and x != ""]
    
    new_a.extend(mov_b)
    new_b.extend(mov_a)

    max_len = max(len(matrix), len(new_a), len(new_b))
    while len(matrix) < max_len: matrix.append([""] * len(matrix[0]))

    for r in range(max_len):
        if r < len(new_a): 
            while len(matrix[r]) <= idx_a: matrix[r].append("")
            matrix[r][idx_a] = new_a[r]
        else:
             if len(matrix[r]) > idx_a: matrix[r][idx_a] = ""
        
        if r < len(new_b):
            while len(matrix[r]) <= idx_b: matrix[r].append("")
            matrix[r][idx_b] = new_b[r]
        else:
             if len(matrix[r]) > idx_b: matrix[r][idx_b] = ""

    return matrix, "Success"

def cleanup_trade_block(sh, players_traded):
    """Optimized: Batch cleanup of Trade Block."""
    try:
        block_ws = sh.worksheet("Trade Block")
        all_values = block_ws.get_all_values()
        if not all_values: return "Block empty."
        
        headers = all_values[0]
        data_rows = all_values[1:]
        rows_to_keep = []
        removed = 0
        
        for row in data_rows:
            if len(row) < 2: continue
            # Check match against player name (Col 2)
            if difflib.get_close_matches(row[1], players_traded, n=1, cutoff=0.9):
                removed += 1
            else:
                rows_to_keep.append(row)
        
        if removed > 0:
            block_ws.clear()
            block_ws.update([headers] + rows_to_keep)
            return f"Cleaned {removed} from Block."
        return "No matches found."
    except: return "Cleanup Error."

def get_fuzzy_matches(input_names, team_players):
    """Aggressive Matcher."""
    results = []
    if not team_players: return [None]
    ledger_map = {p['name'].strip().lower(): p for p in team_players}
    raw_list = [n.strip() for n in input_names.split(",") if n.strip()]
    
    for name in raw_list:
        clean = name.strip().lower()
        found = ledger_map.get(clean, {}).get('name')
        if not found:
            m = difflib.get_close_matches(clean, list(ledger_map.keys()), n=1, cutoff=0.5)
            if m: found = ledger_map[m[0]]['name']
        if not found and "." in clean:
            fi, ls = clean.split(".")[0].strip(), clean.split(".")[1].strip()
            for rn in ledger_map.keys():
                if ls in rn and rn.startswith(fi): found = ledger_map[rn]['name']; break
        
        if found: results.append(next((p for p in team_players if p['name'] == found), None))
        else: results.append({"name": f"❌ '{name}' Not Found", "row": -1})
    return results

def analyze_and_save_block(image_files, user_roster, intel_data, sh):
    """Extracts, Grades, and Saves to Trade Block using ZiPS/Fangraphs Criteria."""
    model = get_active_model()
    prompt = f"""
    You are an Expert Dynasty GM. MY ROSTER: {user_roster}. INTEL: {intel_data}. GOAL: Win 2027.
    
    CRITICAL SOURCE REQUIREMENT:
    - Base grades on 2026 ZiPS Projections and Fangraphs Dynasty Rankings.
    - Be HARSH. "A" Grades are reserved for Top 50 Dynasty Assets.
    
    TASK: Analyze screenshots. Return JSON list:
    [{{"Team": "...", "Player": "...", "Position": "...", "Grade": "A-F", "Verdict": "PURSUE/PASS", "Impact_Pct": "+5%", "Outlook_Shift": "...", "Analysis": "..."}}]
    """
    content = [prompt] + [Image.open(f) for f in image_files]
    with st.spinner("👀 Calculating Analytics..."):
        try:
            res = model.generate_content(content).text
            clean = res.replace("```json", "").replace("```", "").strip()
            match = re.search(r"(\[.*\])", clean, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                try: ws = sh.worksheet("Trade Block")
                except: ws = sh.add_worksheet("Trade Block", 1000, 10); ws.append_row(["Team","Player","Position","Grade","Verdict","Impact %","Outlook Shift","Analysis","Timestamp"])
                
                ts = time.strftime("%Y-%m-%d %H:%M")
                rows = [[d.get("Team"), d.get("Player"), d.get("Position"), d.get("Grade"), d.get("Verdict"), d.get("Impact_Pct"), d.get("Outlook_Shift"), d.get("Analysis"), ts] for d in data]
                ws.append_rows(rows)
                return data 
            return None
        except: return None

# --- 6. CACHED DATA LOADER ---
@st.cache_data(ttl=600)
def load_league_data():
    """Cached loader for heavy sheet data."""
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    raw = sh.get_worksheet(1).get_all_values()
    data = parse_horizontal_rosters(raw)
    
    try: intel = "\n".join([f"- {r[0]}: {r[1]}" for r in sh.worksheet("Intel").get_all_values()[1:] if len(r)>1])
    except: intel = ""
    
    return raw, data, intel

# --- 7. MAIN APP UI ---
st.set_page_config(page_title="GM Master Terminal", layout="wide", page_icon="⚡")
st.title("⚡ Dynasty GM Suite: Realism Edition")

try:
    # Load Data (Cached)
    raw_matrix, full_league_data, intel_text = load_league_data()
    
    # Re-connect for write operations (Non-cached)
    gc_live = get_gspread_client()
    sh_live = gc_live.open_by_key(SHEET_ID)
    roster_ws_live = sh_live.get_worksheet(1)
    history_ws_live = sh_live.get_worksheet(0)
    
    user_roster = full_league_data.get(USER_TEAM, [])

    # Sidebar
    if st.sidebar.button("🔄 Force Refresh"): st.cache_data.clear(); st.rerun()
    st.sidebar.divider()
    debug_team = st.sidebar.selectbox("Inspect Team:", ["Select..."] + TEAM_NAMES)
    if debug_team != "Select...":
        r = full_league_data.get(debug_team, [])
        st.sidebar.write(f"Found {len(r)} players.")
        st.sidebar.code("\n".join(sorted([p['name'] for p in r])))

    tabs = st.tabs(["🔁 Terminal", "🔥 Analysis", "🔍 Finder", "🕵️ Intel", "📋 Block Monitor", "📊 Ledger", "🕵️‍♂️ Scouting", "💎 Sleepers", "🎯 Priority", "🎟️ Picks", "📜 History"])

    with tabs[0]: # TERMINAL
        st.subheader("Official Sync Terminal")
        tab_man, tab_vis = st.tabs(["Manual", "Vision"])
        with tab_man:
            c1, c2 = st.columns(2)
            with c1: ta = st.selectbox("Team A:", TEAM_NAMES, key="m_ta"); pa = st.text_area("Giving:", key="m_pa")
            with c2: tb = st.selectbox("Team B:", TEAM_NAMES, key="m_tb"); pb = st.text_area("Giving:", key="m_pb")
            if st.button("Verify Manual"):
                ma = get_fuzzy_matches(pa, full_league_data.get(ta)) if pa else []
                mb = get_fuzzy_matches(pb, full_league_data.get(tb)) if pb else []
                if any(x.get('row') == -1 for x in ma+mb): st.error("Check spelling.")
                else: verify_trade_dialog(ta, ma, tb, mb, roster_ws_live, history_ws_live, raw_matrix, sh_live)

        with tab_vis:
            up_img = st.file_uploader("Upload Trade Screenshot", type=["jpg","png"])
            if up_img:
                raw = parse_trade_screenshot(up_img, TEAM_NAMES)
                if raw:
                    d = smart_correct_vision(raw, full_league_data)
                    c1, c2 = st.columns(2)
                    with c1: ta_v = st.selectbox("Team A", TEAM_NAMES, index=TEAM_NAMES.index(d.get("team_a")) if d.get("team_a") in TEAM_NAMES else 0, key="vta"); pa_v = st.text_area("Players A", ", ".join(d.get("players_a", [])), key="vpa")
                    with c2: tb_v = st.selectbox("Team B", TEAM_NAMES, index=TEAM_NAMES.index(d.get("team_b")) if d.get("team_b") in TEAM_NAMES else 0, key="vtb"); pb_v = st.text_area("Players B", ", ".join(d.get("players_b", [])), key="vpb")
                    if st.button("Verify Vision"):
                        ma = get_fuzzy_matches(pa_v, full_league_data.get(ta_v))
                        mb = get_fuzzy_matches(pb_v, full_league_data.get(tb_v))
                        if any(x.get('row') == -1 for x in ma+mb): st.error("Match failed.")
                        else: verify_trade_dialog(ta_v, ma, tb_v, mb, roster_ws_live, history_ws_live, raw_matrix, sh_live)

    with tabs[1]: # ANALYSIS (REALISM ENGINE)
        st.info("💡 Powered by Fangraphs Auction Calculator Logic & ZiPS 2026")
        q = st.chat_input("Analyze trade...")
        if q:
            res = run_fast_analysis(q, json.dumps(full_league_data), intel_text, "Trade")
            st.write(res["Research"])
            c1, c2 = st.columns(2); c1.info("Verdict"); c1.write(res["Gemini"]); c2.info("Strategy"); c2.write(res["Claude"])

    with tabs[2]: # FINDER (EXPANDED)
        c1, c2 = st.columns(2)
        with c1: 
            # UPGRADED FINDER OPTIONS
            t = st.selectbox("I need:", [
                "Elite Prospects (Top 100)", 
                "MLB-Ready Youth (<24yo)", 
                "Win-Now Veterans (High Floor)", 
                "Buy-Low Candidates (Post-Hype)", 
                "2026 SP Help"
            ])
        with c2: o = st.text_input("Offering:")
        if st.button("Scour League"): st.write(run_fast_analysis(f"Find trades to get {t} for {o}. Use Dynasty Rankings.", json.dumps(full_league_data), intel_text, "Finder")["Gemini"])

    with tabs[3]: # INTEL
        st.subheader("🕵️ League Intel")
        st.markdown(intel_text if intel_text else "No active rumors.")
        with st.form("new_intel"):
            r = st.text_input("Rumor:"); s = st.selectbox("Source:", ["High", "Med", "Low"])
            if st.form_submit_button("Save"):
                try: 
                    ws = sh_live.worksheet("Intel")
                except: ws = sh_live.add_worksheet("Intel", 1000, 5); ws.append_row(["Date","Rumor","Source"])
                ws.append_row([time.strftime("%Y-%m-%d"), r, s]); st.cache_data.clear(); st.success("Saved!"); time.sleep(1); st.rerun()

    with tabs[4]: # BLOCK MONITOR
        st.subheader("📋 Living Trade Block")
        with st.expander("⚠️ Repair Database"):
            if st.button("🧨 Factory Reset"):
                try: sh_live.del_worksheet(sh_live.worksheet("Trade Block"))
                except: pass
                ws = sh_live.add_worksheet("Trade Block", 1000, 20)
                ws.append_row(["Team","Player","Position","Grade","Verdict","Impact %","Outlook Shift","Analysis","Timestamp"])
                st.success("Reset!"); time.sleep(1); st.rerun()
        
        try: st.dataframe(pd.DataFrame(sh_live.worksheet("Trade Block").get_all_records()), use_container_width=True)
        except: st.warning("Empty.")
        
        up_files = st.file_uploader("Upload Block Screenshots", type=["jpg","png"], accept_multiple_files=True)
        if up_files and st.button("Analyze & Save"):
            if analyze_and_save_block(up_files, json.dumps(user_roster), intel_text, sh_live):
                st.success("Saved!"); time.sleep(2); st.rerun()

    with tabs[5]: # LEDGER
        st.subheader("📊 Roster Matrix")
        if full_league_data:
            df = flatten_roster_to_df(full_league_data)
            c1, c2 = st.columns(2)
            ft = c1.multiselect("Filter Team:", TEAM_NAMES)
            fc = c2.multiselect("Filter Pos:", ["Hitter", "Pitcher"])
            if ft: df = df[df["Team"].isin(ft)]
            if fc: df = df[df["Category"].isin(fc)]
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        with st.expander("⚙️ Bulk Organizer"):
            if st.button("🚀 Organize ENTIRE League"):
                h = [str(c).strip() for c in raw_matrix[0]]
                prog = st.progress(0); valid = [(i, x) for i, x in enumerate(h) if x in TEAM_NAMES]
                for i, (idx, team) in enumerate(valid):
                    curr = [r[idx] for r in raw_matrix[1:] if idx < len(r) and r[idx].strip()]
                    s = organize_roster_ai(curr)
                    if s:
                        for r in range(1, len(raw_matrix)):
                            if idx < len(raw_matrix[r]): raw_matrix[r][idx] = ""
                        while len(raw_matrix) < len(s)+1: raw_matrix.append([""]*len(raw_matrix[0]))
                        for k, v in enumerate(s): raw_matrix[k+1][idx] = v
                    prog.progress((i+1)/len(valid))
                roster_ws_live.clear(); roster_ws_live.update(raw_matrix); st.cache_data.clear(); st.success("Done!"); time.sleep(2); st.rerun()

    with tabs[6]: # SCOUTING
        s = st.text_input("Player:")
        if s: 
            r = run_fast_analysis(f"Scout {s}", json.dumps(full_league_data), intel_text, "Scout")
            c1, c2 = st.columns(2); c1.write(r["Gemini"]); c2.write(r["GPT"])

    with tabs[7]: # SLEEPERS
        if st.button("Find Sleepers"): st.write(run_fast_analysis("Find 5 dynasty sleepers", json.dumps(full_league_data), intel_text, "Sleepers")["Gemini"])

    with tabs[8]: # PRIORITY
        if st.button("Targets"): st.write(run_fast_analysis("Top 5 trade targets", json.dumps(full_league_data), intel_text, "Targets")["Gemini"])

    with tabs[9]: # PICKS
        if st.button("2026 Class"): st.write(run_fast_analysis("Analyze 2026 Draft", "N/A", intel_text, "Draft")["Gemini"])

    with tabs[10]: # HISTORY
        for l in history_ws_live.col_values(1)[::-1]: st.write(f"🔹 {l}")

except Exception as e: st.error(f"Error: {e}")
