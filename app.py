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

# --- 2. CORE UTILITY ENGINE ---
def get_gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def convert_df_to_excel(df):
    """FIX: Utility for binary download of Excel files."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def parse_horizontal_rosters(matrix):
    """Maps players to columns while maintaining Row 1 as Team Headers."""
    league_map = {}
    if not matrix: return league_map
    headers = [str(cell).strip() for cell in matrix[0]]
    for col_idx, team_header in enumerate(headers):
        if team_header in TEAM_NAMES:
            league_map[team_header] = []
            for row_idx, row in enumerate(matrix[1:]):
                if col_idx < len(row):
                    player_val = str(row[col_idx]).strip()
                    if player_val and not player_val.endswith(':'):
                        league_map[team_header].append({
                            "name": player_val,
                            "row": row_idx + 2,
                            "col": col_idx + 1
                        })
    return league_map

# --- 3. FUZZY IDENTITY & VALIDATION ENGINE ---
def get_fuzzy_matches(input_names, team_players):
    results = []
    ledger_names = [p['name'] for p in team_players]
    raw_list = [n.strip() for n in input_names.split(",") if n.strip()]
    for name in raw_list:
        matches = difflib.get_close_matches(name, ledger_names, n=1, cutoff=0.6)
        if matches:
            match_obj = next(p for p in team_players if p['name'] == matches[0])
            results.append(match_obj)
        else: results.append(None)
    return results

@st.dialog("Verify Roster Sync")
def verify_trade_dialog(team_a, final_a, team_b, final_b, roster_ws, history_ws, raw_matrix):
    st.warning("⚖️ **Identity Verification Required**")
    st.write("The system has identified these players for the move:")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**From {team_a}:**")
        for p in final_a: st.write(f"- {p['name']}")
    with col2:
        st.write(f"**From {team_b}:**")
        for p in final_b: st.write(f"- {p['name']}")
        
    st.divider()
    if st.button("🔥 Confirm & Push to Google Sheets", use_container_width=True):
        with st.spinner("Re-writing Ledger Columns..."):
            names_a = ", ".join([p['name'] for p in final_a])
            names_b = ", ".join([p['name'] for p in final_b])
            
            # Use AI to restructure the list-of-lists for the horizontal sheet
            model = get_active_model()
            logic_prompt = f"Matrix: {raw_matrix}. Swap {names_a} from {team_a} to {team_b}. Swap {names_b} from {team_b} to {team_a}. Return ONLY Python list of lists."
            res = model.generate_content(logic_prompt).text
            try:
                new_m = eval(res.replace("```python", "").replace("```", "").strip())
                roster_ws.clear()
                roster_ws.update(new_m)
                history_ws.append_row([f"TRADE: {team_a} ↔️ {team_b} | {names_a} for {names_b}"])
                st.success("Ledger Synchronized!")
                time.sleep(1)
                st.rerun()
            except: st.error("AI failed to restructure matrix. Check naming conventions.")

# --- 4. THE AI BRAIN (SELF-HEALING) ---
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
    REALISM GATE: Elite cornerstone youth (Witt, Gunnar) > aging SPs (Fried).
    - Analyze ALL players in the trade simultaneously.
    - If lopsided, call it 'UNREALISTIC'.
    """
    with st.spinner("📡 Scouting live 2026 ZiPS & Rankings..."):
        search = call_openrouter("perplexity/sonar", "Dynasty Sabermetrician.", f"Jan 2026 ZiPS and trade values for: {query}")
    
    brief = f"LEAGUE: {league_data}\nINTEL: {search}\nQUERY: {query}\nMANDATE: {mandate}"
    return {
        "Research": search,
        "Gemini": get_active_model().generate_content(f"Lead GM Verdict. {brief}").text,
        "GPT": call_openrouter("openai/gpt-4o", "Market Expert.", brief),
        "Claude": call_openrouter("anthropic/claude-3.5-sonnet", "Strategist.", brief)
    }

# --- 5. MAIN UI ---
st.set_page_config(page_title="GM Suite: Final Polish", layout="wide", page_icon="🏛️")
st.title("🏛️ Dynasty GM Suite: Executive Terminal")

try:
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws, roster_ws = sh.get_worksheet(0), sh.get_worksheet(1)
    
    raw_matrix = roster_ws.get_all_values()
    full_league_data = parse_horizontal_rosters(raw_matrix)
    model = get_active_model()

    tabs = st.tabs(["🔁 Terminal", "🔥 Analysis", "🔍 Finder", "📊 Ledger", "🕵️‍♂️ Scouting", "💎 Sleepers", "🎯 Priority", "🎟️ Picks", "📜 History"])

    with tabs[0]:
        st.subheader("Official Sync Terminal")
        c1, c2 = st.columns(2)
        with c1:
            team_a = st.selectbox("Team A:", TEAM_NAMES, key="t_a_f")
            p_a_input = st.text_area("Leaving A:", key="p_a_f")
        with c2:
            team_b = st.selectbox("Team B:", TEAM_NAMES, key="t_b_f")
            p_b_input = st.text_area("Leaving B:", key="p_b_f")
        if st.button("🔥 Verify & Execute Trade", use_container_width=True):
            match_a = get_fuzzy_matches(p_a_input, full_league_data[team_a])
            match_b = get_fuzzy_matches(p_b_input, full_league_data[team_b])
            if None in match_a or None in match_b: st.error("Player name not found.")
            else: verify_trade_dialog(team_a, match_a, team_b, match_b, roster_ws, history_ws, raw_matrix)

    with tabs[1]:
        trade_q = st.chat_input("Analyze deal...")
        if trade_q:
            res = run_gm_analysis(trade_q, json.dumps(full_league_data))
            st.write(res["Gemini"])

    with tabs[3]:
        st.subheader("📊 Roster Ledger")
        df_display = pd.DataFrame(raw_matrix)
        st.dataframe(df_display, use_container_width=True)
        # FIXED: convert_df_to_excel is now defined
        st.download_button("📥 Export Excel", convert_df_to_excel(df_display), "Rosters.xlsx")

    with tabs[7]:
        st.subheader("🎟️ Draft Assets")
        if st.button("Value My 2026 Picks"):
            st.write(run_gm_analysis("Value of 2026 Pick 1.02 for a retooling team", json.dumps(full_league_data))["Gemini"])

except Exception as e:
    st.error(f"Executive Protocol Failed: {e}")
