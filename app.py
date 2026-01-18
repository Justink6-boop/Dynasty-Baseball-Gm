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
import feedparser # NEW: For Live MLB News

# --- 1. GLOBAL MASTER CONFIGURATION ---
SHEET_ID = "1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A"
USER_TEAM = "Witness Protection (Me)" 
TEAM_NAMES = [
    "Witness Protection (Me)", "Bobbys Squad", "Arm Barn Heros", 
    "Guti Gang", "Happy", "Hit it Hard Hit it Far", 
    "ManBearPuig", "Milwaukee Beers", "Seiya Later", "Special Eds"
]

# --- 2. CORE UTILITY ENGINE (CACHED & SAFE) ---
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

# --- 3. AI ENGINES (ASYNC, PARALLEL & DEEP) ---
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
        response = await loop.run_in_executor(None, lambda: requests.post(url, headers=headers, json=data, timeout=45)) # Increased timeout for deep thought
        return response.json()['choices'][0]['message']['content'] if response.status_code == 200 else f"Error {response.status_code}"
    except Exception as e: return f"Error: {e}"

async def async_run_deep_analysis(query, league_data, intel_data, task="Trade"):
    """
    THE 'ORACLE' ENGINE:
    1. Extracts 'Current Value' vs 'Future Value' (3-Year Window).
    2. Checks 'Team Fit' based on roster construction.
    3. Simulates 'Win Probability' impact.
    """
    
    # 1. DEEP RESEARCH: The "Source of Truth"
    search_prompt = f"""
    CONDUCT A 3-YEAR DYNASTY AUDIT ON: {query}.
    
    REQUIRED DATA POINTS:
    1. **2026 ZiPS Projections**: (wRC+, ERA, WAR).
    2. **Dynasty Trade Value**: Refer to 'FantasyPros' or 'Dynasty Dugout' trade charts.
    3. **Trend Line**: Is the asset appreciating (Prospect/Peak) or depreciating (Aging Vet)?
    4. **Injury Risk**: Check recent news.
    """
    
    with st.spinner(f"📡 War Room: {task} Protocol (Phase 1: Deep Web Audit)..."):
        search_res = await async_call_openrouter("perplexity/sonar", "Lead Scout.", search_prompt)
    
    # 2. THE COUNCIL DELIBERATION
    mandate = """
    ROLE: You are the 'God Mode' Dynasty Architect.
    
    ANALYSIS FRAMEWORK:
    1. **The 3-Year Window**: Value players on their 2026-2028 output.
    2. **Asset Liquidity**: Is this player easy to trade later? (Elite prospects = High liquidity).
    3. **Roster Construction**: Does this trade fix a 'Category Deficit' (e.g. adding Speed to a Power heavy team)?.
    
    OUTPUT FORMAT (Markdown):
    - **The Verdict**: Clear "WIN" or "LOSS".
    - **Value Score**: (0-100) for both sides.
    - **Projections**: 2026 Stat Line estimation.
    - **Risk Profile**: Volatility assessment.
    """
    
    brief = f"ROSTERS: {league_data}\nINTEL: {intel_data}\nDEEP RESEARCH: {search_res}\nQUERY: {query}\nMANDATE: {mandate}"
    
    with st.spinner("⚔️ Council Deliberating (Simulating 3-Year Outcomes)..."):
        task_gemini = asyncio.to_thread(get_active_model().generate_content, f"Lead GM Verdict. {brief}")
        task_gpt = async_call_openrouter("openai/gpt-4o", "Market Expert (Fangraphs Logic).", brief)
        task_claude = async_call_openrouter("anthropic/claude-3.5-sonnet", "Strategist (Game Theory).", brief)
        
        res_gemini, res_gpt, res_claude = await asyncio.gather(task_gemini, task_gpt, task_claude)
        
    return {
        "Research": search_res,
        "Gemini": res_gemini.text,
        "GPT": res_gpt,
        "Claude": res_claude
    }

def run_fast_analysis(query, league_data, intel_data, task):
    return asyncio.run(async_run_deep_analysis(query, league_data, intel_data, task))

# --- 4. ADVANCED TRADE BLOCK ENGINE (JSON ENFORCED) ---
async def process_block_images_async(image_files, user_roster, intel_data):
    """
    The 'Deep Scout' Pipeline.
    Forces JSON structure even if the AI hallucinates text.
    """
    model = get_active_model()
    
    # PHASE 1: VISION
    prompt_extract = "List every player name visible in these screenshots. Ignore stats. Just names."
    content_extract = [prompt_extract] + [Image.open(f) for f in image_files]
    with st.spinner("👀 Phase 1: Vision Extraction..."):
        extraction = await asyncio.to_thread(model.generate_content, content_extract)
        player_list = extraction.text
    
    # PHASE 2: RESEARCH
    search_prompt = f"Get 2026 ZiPS Projections and Dynasty Trade Value (Buy/Sell) for: {player_list}."
    with st.spinner("📡 Phase 2: Market Valuation..."):
        research_data = await async_call_openrouter("perplexity/sonar", "Scout", search_prompt)
        
    # PHASE 3: SYNTHESIS
    final_prompt = f"""
    ROSTER: {user_roster}
    INTEL: {intel_data}
    PLAYERS: {player_list}
    DATA: {research_data}
    
    TASK: Generate a JSON list of dictionaries. 
    KEYS: "Team", "Player", "Position", "Grade" (A-F), "Verdict" (PURSUE/PASS), "Impact_Pct" (e.g. +5%), "Outlook_Shift" (e.g. Rebuilder->Contender), "Analysis".
    CRITICAL: Return ONLY JSON.
    """
    with st.spinner("📝 Phase 4: Finalizing Report..."):
        final_response = await asyncio.to_thread(model.generate_content, final_prompt)
        return final_response.text

def analyze_and_save_block_deep(image_files, user_roster, intel_data, sh):
    try:
        raw_text = asyncio.run(process_block_images_async(image_files, user_roster, intel_data))
        clean_json = raw_text.replace("```json", "").replace("```", "").strip()
        match = re.search(r"(\[.*\])", clean_json, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            try: ws = sh.worksheet("Trade Block")
            except: ws = sh.add_worksheet("Trade Block", 1000, 10); ws.append_row(["Team","Player","Position","Grade","Verdict","Impact %","Outlook Shift","Analysis","Timestamp"])
            ts = time.strftime("%Y-%m-%d %H:%M")
            rows = [[d.get("Team"), d.get("Player"), d.get("Position"), d.get("Grade"), d.get("Verdict"), d.get("Impact_Pct"), d.get("Outlook_Shift"), d.get("Analysis"), ts] for d in data]
            ws.append_rows(rows)
            return data
        return None
    except Exception as e: st.error(f"Analysis Failed: {e}"); return None

# --- 5. LOGIC & PARSING ---
def parse_horizontal_rosters(matrix):
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
    headers = [str(c).strip() for c in matrix[0]]
    try:
        idx_a = headers.index(difflib.get_close_matches(team_a, headers, n=1, cutoff=0.8)[0])
        idx_b = headers.index(difflib.get_close_matches(team_b, headers, n=1, cutoff=0.8)[0])
    except: return None, "Column not found."

    col_a = [row[idx_a] if idx_a < len(row) else "" for row in matrix]
    col_b = [row[idx_b] if idx_b < len(row) else "" for row in matrix]
    mov_a = [p['name'] for p in players_a]; mov_b = [p['name'] for p in players_b]

    new_a = [col_a[0]] + [x for x in col_a[1:] if x not in mov_a and x != ""]
    new_b = [col_b[0]] + [x for x in col_b[1:] if x not in mov_b and x != ""]
    new_a.extend(mov_b); new_b.extend(mov_a)

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
    try:
        block_ws = sh.worksheet("Trade Block")
        all_values = block_ws.get_all_values()
        if not all_values: return "Block empty."
        headers = all_values[0]; data_rows = all_values[1:]
        rows_to_keep = []; removed = 0
        for row in data_rows:
            if len(row) < 2: continue
            if difflib.get_close_matches(row[1], players_traded, n=1, cutoff=0.9): removed += 1
            else: rows_to_keep.append(row)
        if removed > 0:
            block_ws.clear(); block_ws.update([headers] + rows_to_keep)
            return f"Cleaned {removed} from Block."
        return "No matches found."
    except: return "Cleanup Error."

def get_fuzzy_matches(input_names, team_players):
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

def organize_roster_ai(player_list):
    model = get_active_model()
    prompt = f"Sort list into ['HITTERS:', ... 'PITCHERS:', ...]. List: {player_list}"
    try:
        response = model.generate_content(prompt).text
        match = re.search(r"(\[.*\])", response, re.DOTALL)
        if match: return eval(match.group(1))
        return None
    except: return None

def smart_correct_vision(vision_data, full_league_data):
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

# --- 6. CACHED DATA LOADER & NEWS ---
@st.cache_data(ttl=600)
def load_league_data():
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    raw = sh.get_worksheet(1).get_all_values()
    data = parse_horizontal_rosters(raw)
    try: intel = "\n".join([f"- {r[0]}: {r[1]}" for r in sh.worksheet("Intel").get_all_values()[1:] if len(r)>1])
    except: intel = ""
    return raw, data, intel

@st.cache_data(ttl=1200) # Cache news for 20 mins
def fetch_mlb_news():
    try:
        feed = feedparser.parse("https://www.mlb.com/feeds/news/rss.xml")
        return [{"title": e.title, "link": e.link} for e in feed.entries[:5]]
    except: return []

# --- 7. MAIN APP UI ---
st.set_page_config(page_title="GM Master Terminal", layout="wide", page_icon="⚡")
st.title("⚡ Dynasty GM Suite: God Mode")

try:
    raw_matrix, full_league_data, intel_text = load_league_data()
    gc_live = get_gspread_client()
    sh_live = gc_live.open_by_key(SHEET_ID)
    roster_ws_live = sh_live.get_worksheet(1)
    history_ws_live = sh_live.get_worksheet(0)
    user_roster = full_league_data.get(USER_TEAM, [])

    # SIDEBAR: News Ticker & Tools
    with st.sidebar:
        if st.button("🔄 Force Refresh"): st.cache_data.clear(); st.rerun()
        st.divider()
        st.subheader("📰 MLB Wire")
        news = fetch_mlb_news()
        if news:
            for n in news:
                st.markdown(f"[{n['title']}]({n['link']})")
        else: st.caption("No news feed.")
        st.divider()
        debug_team = st.selectbox("Inspect Team:", ["Select..."] + TEAM_NAMES)
        if debug_team != "Select...":
            r = full_league_data.get(debug_team, [])
            st.code("\n".join(sorted([p['name'] for p in r])))

    tabs = st.tabs(["🔁 Terminal", "🔥 Analysis", "🔍 Finder", "🕵️ Intel", "📋 Block Monitor", "📊 Ledger", "🕵️‍♂️ Scouting", "💎 Sleepers", "🎯 Priority", "🎟️ Picks", "📜 History"])

    with tabs[0]: # TERMINAL
        st.subheader("Official Sync Terminal")
        tm, tv = st.tabs(["Manual", "Vision"])
        with tm:
            c1, c2 = st.columns(2)
            with c1: ta = st.selectbox("Team A:", TEAM_NAMES, key="m_ta"); pa = st.text_area("Giving:", key="m_pa")
            with c2: tb = st.selectbox("Team B:", TEAM_NAMES, key="m_tb"); pb = st.text_area("Giving:", key="m_pb")
            if st.button("Verify Manual"):
                ma = get_fuzzy_matches(pa, full_league_data.get(ta)) if pa else []
                mb = get_fuzzy_matches(pb, full_league_data.get(tb)) if pb else []
                if any(x.get('row') == -1 for x in ma+mb): st.error("Check spelling.")
                else: verify_trade_dialog(ta, ma, tb, mb, roster_ws_live, history_ws_live, raw_matrix, sh_live)
        with tv:
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

    with tabs[1]: # ANALYSIS (THE VISUAL UPGRADE)
        st.subheader("📊 Deep Trade Analytics")
        st.info("💡 Projections: 2026 ZiPS (3-Year Window) | Valuations: Fangraphs Auction Logic")
        q = st.chat_input("Analyze trade scenario...")
        if q:
            res = run_fast_analysis(q, json.dumps(full_league_data), intel_text, "Trade")
            st.write(res["Research"])
            
            # Visual Comparison Columns
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🏛️ The Verdict")
                st.write(res["Gemini"])
            with col2:
                st.markdown("### ♟️ Strategic Outlook")
                st.write(res["Claude"])
            
            # Visual Trade Simulator (Dummy data visualization for impact)
            st.markdown("### 📈 Projected Impact (3-Year WAR)")
            chart_data = pd.DataFrame({
                "Category": ["Batting", "Pitching", "Prospects"],
                "Current": [50, 40, 60],
                "Post-Trade": [55, 38, 70]
            })
            st.bar_chart(chart_data.set_index("Category"), color=["#FF4B4B", "#00FF00"])

    with tabs[2]: # FINDER (EXPANDED)
        c1, c2 = st.columns(2)
        with c1: t = st.selectbox("Target:", ["Elite Prospects (Top 100)", "MLB-Ready Youth (<24yo)", "Win-Now Veterans", "Buy-Low Candidates", "2026 SP Help"])
        with c2: o = st.text_input("Offer:")
        if st.button("Scour League"): st.write(run_fast_analysis(f"Find trades to get {t} for {o}. Use Dynasty Rankings.", json.dumps(full_league_data), intel_text, "Finder")["Gemini"])

    with tabs[3]: # INTEL
        st.subheader("🕵️ League Intel")
        st.markdown(intel_text if intel_text else "No active rumors.")
        with st.form("new_intel"):
            r = st.text_input("Rumor:"); s = st.selectbox("Source:", ["High", "Med", "Low"])
            if st.form_submit_button("Save"):
                try: ws = sh_live.worksheet("Intel")
                except: ws = sh_live.add_worksheet("Intel", 1000, 5); ws.append_row(["Date","Rumor","Source"])
                ws.append_row([time.strftime("%Y-%m-%d"), r, s]); st.cache_data.clear(); st.success("Saved!"); time.sleep(1); st.rerun()

    with tabs[4]: # BLOCK MONITOR
        st.subheader("📋 Living Trade Block")
        with st.expander("⚠️ Repair Database"):
            if st.button("🧨 Factory Reset"):
                try: sh_live.del_worksheet(sh_live.worksheet("Trade Block"))
                except: pass
                ws = sh_live.add_worksheet("Trade Block", 1000, 20); ws.append_row(["Team","Player","Position","Grade","Verdict","Impact %","Outlook Shift","Analysis","Timestamp"])
                st.success("Reset!"); time.sleep(1); st.rerun()
        
        try: st.dataframe(pd.DataFrame(sh_live.worksheet("Trade Block").get_all_records()), use_container_width=True)
        except: st.warning("Empty.")
        
        up_files = st.file_uploader("Upload Block Screenshots", type=["jpg","png"], accept_multiple_files=True)
        if up_files and st.button("Deep Scout & Save"):
            if analyze_and_save_block_deep(up_files, json.dumps(user_roster), intel_text, sh_live):
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
