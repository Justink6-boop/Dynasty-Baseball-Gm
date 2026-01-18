import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from io import BytesIO
import requests
import json

# --- 1. CONNECTION & UTILITY ENGINE ---
def get_gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def parse_roster_matrix(matrix, team_names):
    """
    Horizontal Ledger Brain:
    Parses data where Team Names are in Row 1 and players are in the columns below.
    """
    league_data = {}
    if not matrix:
        return league_data

    # Row 1 (matrix[0]) contains the headers
    header_row = matrix[0]
    
    for col_idx, cell_value in enumerate(header_row):
        team_name = str(cell_value).strip()
        
        # If this column header matches one of our known team names
        if team_name in team_names:
            league_data[team_name] = []
            
            # Scan down the rows [1:] in this specific column [col_idx]
            for row in matrix[1:]:
                if col_idx < len(row):
                    player_name = str(row[col_idx]).strip()
                    # Only add if the cell isn't empty and isn't a category header (like "Pitchers:")
                    if player_name and not player_name.endswith(':'):
                        league_data[team_name].append(player_name)
                        
    return league_data

def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rosters')
    return output.getvalue()

SHEET_ID = "1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A"

# --- 2. MASTER LEAGUE DATA ---
def get_initial_league():
    # Defining the base team list for the parser to look for in Row 1
    return {
        "Witness Protection (Me)": {}, "Bobbys Squad": {}, "Arm Barn Heros": {}, 
        "Guti Gang": {}, "Happy": {}, "Hit it Hard Hit it Far": {}, 
        "ManBearPuig": {}, "Milwaukee Beers": {}, "Seiya Later": {}, "Special Eds": {}
    }

# --- 3. PAGE CONFIG ---
st.set_page_config(page_title="Executive GM Terminal", layout="wide")
st.title("🧠 Dynasty GM Suite: Executive Terminal")

# --- 4. MAIN APP LOGIC ---
try:
    # A. INITIALIZE DATA & CONNECTIONS
    init_data = get_initial_league()
    team_list = list(init_data.keys())

    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws = sh.get_worksheet(0)
    roster_ws = sh.get_worksheet(1)

    permanent_history = history_ws.col_values(1)
    raw_roster_matrix = roster_ws.get_all_values()
    
    # CRITICAL: Using the new horizontal parser
    parsed_rosters = parse_roster_matrix(raw_roster_matrix, team_list)

    # B. AI CONFIGURATION
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    flash_models = [m for m in available_models if 'flash' in m]
    model = genai.GenerativeModel(flash_models[0] if flash_models else 'gemini-1.5-pro')

    # C. WAR ROOM LOGIC
    def call_openrouter(model_id, persona, prompt):
        try:
            r = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
                    "HTTP-Referer": "https://streamlit.io",
                    "X-Title": "Dynasty GM Suite"
                },
                data=json.dumps({"model": model_id, "messages": [{"role": "system", "content": persona}, {"role": "user", "content": prompt}]}),
                timeout=30
            )
            return r.json()['choices'][0]['message']['content'] if r.status_code == 200 else f"Error {r.status_code}"
        except: return "Connection Timeout."

    def get_multi_ai_opinions(user_query, task_type="Trade"):
        directive = "MISSION: 30% 2026 win-now / 70% 2027-29 peak. Hybrid Retool Strategy."
        with st.spinner("📡 Scanning Jan 2026 ZiPS & Rankings..."):
            search_query = f"Provide 2026 ZiPS, Dynasty Rankings, and latest news for: {user_query}."
            live_intel = call_openrouter("perplexity/sonar", "Lead Researcher.", search_query)

        briefing = f"ROSTERS: {json.dumps(parsed_rosters)}\nINTEL: {live_intel}\nINPUT: {user_query}\nGOAL: {directive}"
        return {
            'Perplexity': live_intel,
            'Gemini': model.generate_content(f"Lead Scout. Task: {task_type}. Briefing: {briefing}").text,
            'ChatGPT': call_openrouter("openai/gpt-4o", "Market Analyst.", briefing),
            'Claude': call_openrouter("anthropic/claude-3.5-sonnet", "Window Strategist.", briefing)
        }

    # --- 5. UI TABS ---
    tabs = st.tabs(["🔁 Terminal", "🔥 Trade Analysis", "📋 Ledger", "🎯 Priority Candidates", "🕵️‍♂️ Scouting", "💎 Sleeper Cell", "📜 History"])

    with tabs[0]:
        st.subheader("Official League Transaction Terminal")
        # Horizontal Spreadsheet Logic: Trades need to find the right column
        st.info("💡 Changes made here update the horizontal columns in your Google Sheet.")
        # ... (Rest of terminal logic)

    with tabs[1]:
        st.subheader("🚀 War Room: Live 2026 Intelligence")
        trade_q = st.chat_input("Analyze trade...")
        if trade_q:
            results = get_multi_ai_opinions(trade_q)
            with st.expander("📡 Live Field Report", expanded=True): st.write(results['Perplexity'])
            st.divider()
            c1, c2, c3 = st.columns(3)
            with c1: st.info("🟢 Gemini"); st.write(results['Gemini'])
            with c2: st.info("🔵 GPT-4o"); st.write(results['ChatGPT'])
            with c3: st.info("🟠 Claude"); st.write(results['Claude'])

    with tabs[2]:
        st.download_button("📥 Excel Download", convert_df_to_excel(pd.DataFrame(raw_roster_matrix)), "Rosters.xlsx")
        st.dataframe(pd.DataFrame(raw_roster_matrix), use_container_width=True)

except Exception as e:
    st.error(f"Executive System Offline: {e}")
