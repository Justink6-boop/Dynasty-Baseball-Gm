import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from io import BytesIO
import requests
import json
import time

# --- 1. CORE ENGINE & ADAPTIVE PARSER ---
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
            league_map[team] = [str(row[col_idx]).strip() for row in matrix[1:] if col_idx < len(row) and str(row[col_idx]).strip() and not str(row[col_idx]).strip().endswith(':')]
    return league_map

def convert_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

SHEET_ID = "1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A"

# --- 2. THE AI BRAIN (MULTI-AGENT) ---
def call_openrouter(model_id, persona, prompt):
    try:
        r = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}", "HTTP-Referer": "https://streamlit.io"},
            data=json.dumps({"model": model_id, "messages": [{"role": "system", "content": persona}, {"role": "user", "content": prompt}]}),
            timeout=30
        )
        return r.json()['choices'][0]['message']['content'] if r.status_code == 200 else f"Offline ({r.status_code})"
    except: return "Connection Timeout."

def run_war_room(query, context_data, mode="Trade"):
    """Stage 1: Live Research. Stage 2: Strategy Evaluation."""
    with st.spinner("📡 Scouting 2026 ZiPS & Dynasty Tiers..."):
        research = call_openrouter("perplexity/sonar", "You are a Sabermetric Researcher.", f"Research 2026 ZiPS, Statcast, and Dynasty Rankings for: {query}")
    
    full_brief = f"ROSTERS: {context_data}\nINTEL: {research}\nQUERY: {query}\nGOAL: Hybrid Retool (Peak 2027)."
    
    return {
        "Research": research,
        "Gemini": model.generate_content(f"You are the Lead Scout. Evaluate this {mode}. Be brutally honest about value. {full_brief}").text,
        "GPT": call_openrouter("openai/gpt-4o", "Aggressive Asset Manager. Focus on market value and surplus.", full_brief),
        "Claude": call_openrouter("anthropic/claude-3.5-sonnet", "Strategy Architect. Focus on long-term roster construction.", full_brief)
    }

# --- 3. PAGE INITIALIZATION ---
st.set_page_config(page_title="GM Executive Terminal", layout="wide", page_icon="⚾")
st.title("🏛️ Dynasty GM Suite: Executive Terminal")

try:
    # DATA BOOTSTRAP
    team_names = ["Witness Protection (Me)", "Bobbys Squad", "Arm Barn Heros", "Guti Gang", "Happy", "Hit it Hard Hit it Far", "ManBearPuig", "Milwaukee Beers", "Seiya Later", "Special Eds"]
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws, roster_ws = sh.get_worksheet(0), sh.get_worksheet(1)
    
    raw_data = roster_ws.get_all_values()
    parsed_league = parse_horizontal_rosters(raw_data, team_names)
    
    # AI BOOTSTRAP
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')

    # --- 4. THE INTERFACE ---
    tabs = st.tabs(["🔁 Terminal", "⚖️ Fairness Analysis", "🔍 Trade Finder", "📋 Live Ledger", "🕵️‍♂️ Pro Scouting", "💎 Sleepers", "📜 History"])

    # TAB 0: TRANSACTION TERMINAL
    with tabs[0]:
        st.subheader("Official League Transaction Terminal")
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            team_a = st.selectbox("Team A (Owner):", team_names, key="term_a")
            p_out = st.text_area("Players/Picks Out:", placeholder="Separated by commas", key="term_out")
        with t_col2:
            team_b = st.selectbox("Team B (Counterparty):", team_names, key="term_b")
            p_in = st.text_area("Players/Picks In:", placeholder="Separated by commas", key="term_in")
        
        if st.button("🔥 Execute Official Trade", use_container_width=True):
            prompt = f"Matrix: {raw_data}. Move {p_out} from {team_a} to {team_b}. Move {p_in} from {team_b} to {team_a}. Return ONLY the updated list of lists for a horizontal sheet."
            res = model.generate_content(prompt).text
            clean = res.replace("```python", "").replace("```", "").strip()
            try:
                new_matrix = eval(clean)
                roster_ws.clear()
                roster_ws.update(new_matrix)
                history_ws.append_row([f"TRADE: {team_a} ↔️ {team_b} | {p_out} for {p_in}"])
                st.success("Ledger Synchronized!")
                time.sleep(1)
                st.rerun()
            except: st.error("Parsing Error. Ensure names match the ledger.")

    # TAB 1: FAIRNESS ARBITRATOR
    with tabs[1]:
        st.subheader("⚖️ Two-Sided Trade Arbitrator")
        trade_input = st.chat_input("Enter Trade: 'My Fried for his Skenes'")
        if trade_input:
            res = run_war_room(trade_input, json.dumps(parsed_league))
            with st.expander("📡 Live Intelligence Briefing", expanded=True): st.write(res["Research"])
            c1, c2, c3 = st.columns(3)
            with c1: st.info("🟢 Lead Scout"); st.write(res["Gemini"])
            with c2: st.info("🔵 Market Analyst"); st.write(res["GPT"])
            with c3: st.info("🟠 Strategy Architect"); st.write(res["Claude"])

    # TAB 2: TRADE FINDER (NEW)
    with tabs[2]:
        st.subheader("🔍 Automated Win-Win Partner Finder")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            find_target = st.selectbox("I am looking for:", ["Elite Youth (<23)", "Impact 2026 Production", "Draft Capital", "Closer/RP Help"])
        with f_col2:
            find_offer = st.text_input("I am shopping:", placeholder="e.g. Max Fried, Veteran OF")
        
        if st.button("Scour League for Partners", use_container_width=True):
            finder_results = run_war_room(f"Find trades to get {find_target} by giving up {find_offer}", json.dumps(parsed_league), mode="Trade Finder")
            st.markdown(finder_results["Gemini"])

    # TAB 3: LEDGER
    with tabs[3]:
        st.subheader("📊 Live Roster Matrix")
        df_display = pd.DataFrame(raw_data)
        st.dataframe(df_display, use_container_width=True)
        st.download_button("📥 Export to Excel", convert_to_excel(df_display), "League_Rosters.xlsx")

    # TAB 4: PRO SCOUTING
    with tabs[4]:
        scout_query = st.text_input("Enter Player for Deep Dive (Live 2026 Projections):")
        if scout_query:
            scout_res = run_war_room(f"Full Scouting Report: {scout_query}", json.dumps(parsed_league), mode="Scouting")
            st.write(scout_res["Gemini"])

    # TAB 5: SLEEPERS
    with tabs[5]:
        if st.button("💎 Scan for 2026 Market Inefficiencies"):
            sleeper_res = run_war_room("Identify 5 players with elite 2026 ZiPS but low Dynasty ECR rankings.", json.dumps(parsed_league), mode="Sleepers")
            st.write(sleeper_res["Gemini"])

    # TAB 6: HISTORY
    with tabs[6]:
        st.subheader("📜 Transaction History")
        for log in history_ws.col_values(1)[::-1]:
            st.write(f"🔹 {log}")

except Exception as e:
    st.error(f"Executive Protocol Failed: {e}")
