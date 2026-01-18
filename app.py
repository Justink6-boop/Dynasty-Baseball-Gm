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
    """Secure connection to Google Sheets."""
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def parse_horizontal_rosters(matrix, team_names):
    """Parses horizontal ledger (Team names in Row 1)."""
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

# --- 3. SELF-HEALING AI ENGINE ---
def get_active_model():
    """Finds active Gemini model to prevent 404 errors."""
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    try:
        # Dynamically list and pick the newest Flash model available
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in models if 'flash' in m]
        flash_models.sort(reverse=True)
        return genai.GenerativeModel(flash_models[0])
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

def call_openrouter(model_id, persona, prompt):
    """Standard API call to OpenRouter/Perplexity."""
    try:
        r = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
                "HTTP-Referer": "https://streamlit.io",
                "X-Title": "Dynasty GM Master Suite"
            },
            data=json.dumps({"model": model_id, "messages": [{"role": "system", "content": persona}, {"role": "user", "content": prompt}]}),
            timeout=30
        )
        return r.json()['choices'][0]['message']['content'] if r.status_code == 200 else f"Error {r.status_code}"
    except: return "Connection Timeout."

# --- 4. MASTER ANALYSIS LOGIC ---
def run_front_office_analysis(query, league_data, task="Trade"):
    """Aggregates multi-agent intelligence with 2026 ZiPS/Ranking data."""
    strategy = "Hybrid Retool: 30% 2026 Competitive / 70% 2027-29 Peak."
    
    with st.spinner("📡 Scouting 2026 ZiPS, FanGraphs, and Dynasty Rankings..."):
        search_query = f"Provide 2026 ZiPS, Dynasty Rankings, and latest news for: {query}."
        live_intel = call_openrouter("perplexity/sonar", "Lead Sabermetrician.", search_query)

    briefing = f"ROSTERS: {league_data}\nINTEL: {live_intel}\nINPUT: {query}\nSTRATEGY: {strategy}"
    
    return {
        "Research": live_intel,
        "Gemini": model.generate_content(f"Lead Scout. Task: {task}. Decide who wins and if it's realistic. {briefing}").text,
        "GPT": call_openrouter("openai/gpt-4o", "Market Expert. Focus on surplus value.", briefing),
        "Claude": call_openrouter("anthropic/claude-3.5-sonnet", "Roster Strategist. Focus on window alignment.", briefing)
    }

# --- 5. UI INITIALIZATION ---
st.set_page_config(page_title="GM Suite: Master Terminal", layout="wide", page_icon="🏛️")
st.title("⚾ Dynasty GM Suite: Master Executive Terminal")

try:
    # A. INITIALIZE DATA & AI
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws, roster_ws = sh.get_worksheet(0), sh.get_worksheet(1)
    
    raw_matrix = roster_ws.get_all_values()
    parsed_league = parse_horizontal_rosters(raw_matrix, TEAM_NAMES)
    model = get_active_model()

    # B. UI TABS
    tabs = st.tabs(["🔁 Terminal", "🔥 Hypothetical Trade Arbitrator", "🔍 Automated Trade Finder", "📊 Live Ledger", "🕵️‍♂️ Scouting", "💎 Sleepers", "📜 History"])

    # --- TAB 0: TRANSACTION TERMINAL ---
    with tabs[0]:
        st.subheader("Official Transaction Terminal")
        col1, col2 = st.columns(2)
        with col1:
            team_a = st.selectbox("From Team:", TEAM_NAMES, key="t_a")
            p_out = st.text_area("Leaving Team A:", placeholder="Separated by commas", key="p_out")
        with col2:
            team_b = st.selectbox("To Team:", TEAM_NAMES, key="t_b")
            p_in = st.text_area("Leaving Team B:", placeholder="Separated by commas", key="p_in")
        
        if st.button("🔥 Execute Official Transaction", use_container_width=True):
            with st.spinner("Updating Horizontal Ledger..."):
                prompt = f"Matrix: {raw_matrix}. Move {p_out} from {team_a} to {team_b}. Move {p_in} from {team_b} to {team_a}. Return ONLY the Python list of lists."
                res = model.generate_content(prompt).text
                clean = res.replace("```python", "").replace("```", "").strip()
                try:
                    new_matrix = eval(clean)
                    roster_ws.clear()
                    roster_ws.update(new_matrix)
                    history_ws.append_row([f"TRADE: {team_a} ↔️ {team_b} | {p_out} for {p_in}"])
                    st.success("Ledger Synchronized!"); time.sleep(1); st.rerun()
                except: st.error("Parsing Error. Ensure names match precisely.")

    # --- TAB 1: HYPOTHETICAL TRADE ARBITRATOR ---
    with tabs[1]:
        st.subheader("🔥 Hypothetical Trade Arbitrator")
        trade_q = st.chat_input("Enter hypothetical trade (e.g. My Fried for his Skenes)")
        if trade_q:
            results = run_front_office_analysis(trade_q, json.dumps(parsed_league))
            with st.expander("📡 Live 2026 Scouting Brief", expanded=True): st.write(results["Research"])
            st.divider()
            c1, c2, c3 = st.columns(3)
            with c1: st.info("🟢 Gemini (Verdict)"); st.write(results["Gemini"])
            with c2: st.info("🔵 GPT-4o (Value)"); st.write(results["GPT"])
            with c3: st.info("🟠 Claude (Fit)"); st.write(results["Claude"])

    # --- TAB 2: AUTOMATED TRADE FINDER ---
    with tabs[2]:
        st.subheader("🔍 Automated Win-Win Partner Finder")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            target_type = st.selectbox("I am looking for:", ["Elite Youth (<23)", "2026 Production", "Draft Capital", "Bullpen Help"])
        with f_col2:
            offer_type = st.text_input("I am shopping:", placeholder="e.g. Max Fried, Veteran Star")
        
        if st.button("Scour League Rosters", use_container_width=True):
            finder_res = run_front_office_analysis(f"Target: {target_type} | Offer: {offer_type}", json.dumps(parsed_league), task="Trade Finder")
            st.markdown(finder_res["Gemini"])

    # --- TAB 3: LIVE LEDGER ---
    with tabs[3]:
        st.subheader("📊 Roster Matrix")
        df_ledger = pd.DataFrame(raw_matrix)
        st.dataframe(df_ledger, use_container_width=True)
        st.download_button("📥 Export to Excel", convert_to_excel(df_ledger), "League_Ledger.xlsx")

    # --- TAB 4: PRO SCOUTING ---
    with tabs[4]:
        scout_p = st.text_input("Scout Player (Live News/ZiPS):", key="scout_q")
        if scout_p:
            scout_res = run_front_office_analysis(scout_p, json.dumps(parsed_league), task="Scouting")
            st.write(scout_res["Gemini"])

    # --- TAB 5: SLEEPERS ---
    with tabs[5]:
        if st.button("💎 Find 2026 Market Inefficiencies", use_container_width=True):
            sleeper_res = run_front_office_analysis("5 players with elite 2026 ZiPS undervalued in dynasty.", json.dumps(parsed_league), task="Sleepers")
            st.write(sleeper_res["Gemini"])

    # --- TAB 6: HISTORY ---
    with tabs[6]:
        st.subheader("📜 History Log")
        for log in history_ws.col_values(1)[::-1]: st.write(f"🔹 {log}")

except Exception as e:
    st.error(f"Executive Protocol Failed: {e}")
