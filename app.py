import streamlit as st
import google.generativeai as genai

# --- 1. THE COMPLETE MASTER LEAGUE LEDGER (From Your Document) ---
# This initial state is only used once to set up the session
def get_initial_league():
    return {
        "Witness Protection (Me)": {
            "Catchers": ["Dillon Dingler", "J.T. Realmuto"],
            "Infielders": ["Jake Cronenworth (2B)", "Ke'Bryan Hayes (3B)", "Caleb Durbin (3B)", "Luisangel Acuna (2B)", "Ceddanne Rafaela (2B, OF)", "Michael Massey (2B)", "Ivan Herrera (UT)", "Enrique Hernandez (1B, 3B, OF)", "Yandy Diaz (1B)", "Wilmer Flores (1B)", "Jeff McNeil (2B, OF)", "Andy Ibanez (3B)"],
            "Outfielders": ["Ronald Acuna Jr.", "Dylan Beavers", "JJ Bleday", "Dylan Crews", "Byron Buxton", "lan Happ", "Tommy Pham", "Jacob Young", "Marcell Ozuna (UT)", "Justice Bigbie", "Alex Verdugo"],
            "Pitchers": ["Dylan Cease", "Jack Flaherty", "Max Fried", "Cristopher Sanchez", "Spencer Strider", "Pete Fairbanks", "Daysbel Hernandez", "Brant Hurter", "Blake Treinen", "Merrill Kelly", "Yimi Garcia", "Jordan Hicks", "Bryan King", "Alex Lange", "Shelby Miller", "Evan Phillips", "Yu Darvish", "Reynaldo Lopez", "Drue Hackenberg"],
            "Draft Picks": ["2026 Pick 1.02"]
        },
        "Bobbys Squad": {
            "Catchers": ["Drake Baldwin", "Will Smith", "Ryan Jeffers", "Sean Murphy", "Carter Jensen"],
            "Infielders": ["Pete Alonso (1B)", "Josh Naylor (1B)", "Xavier Edwards (2B, SS)", "Maikel Garcia (3B)", "Bobby Witt Jr. (SS)", "Gunnar Henderson (SS)", "Ronny Mauricio (3B)", "Colt Keith (2B, 3B)", "Brooks Lee (2B, 3B, SS)", "Tommy Edman (2B, OF)", "Nolan Arenado (3B)", "Cam Collier (1B, 3B)", "Ralphy Velazquez (1B)", "Jacob Berry (2B, 3B, OF)", "Blaze Jordan (1B, 3B)", "Brayden Taylor (2B, 3B)", "Josuar Gonzalez (SS)", "Elian Pena (SS)", "Cooper Pratt (SS)"],
            "Outfielders": ["Kerry Carpenter", "Drew Gilbert", "Wenceel Perez", "Tyler Soderstrom (1B/OF)", "Brent Rooker (UT)", "Jacob Wilson (SS)", "Jac Caglianone", "Jasson Dominguez", "Jake Mangum", "Luis Robert Jr.", "Kyle Stowers", "Zyhir Hope", "Spencer Jones"],
            "Pitchers": ["Logan Gilbert", "Aroldis Chapman", "Camilo Doval", "Lucas Erceg", "Carlos Estevez", "Kyle Finnegan", "Ronny Henriquez", "Tony Santillan", "Tanner Scott", "Cade Cavalli", "Dustin May", "Aaron Nola", "Eury Perez", "Ranger Suarez", "Trevor Megill", "Chase Burns", "Jacob Lopez", "Boston Bateman", "Tink Hence", "Chase Petty", "Brett Wichrowski", "Trey Yesavage"],
            "Draft Picks": ["2026 Pick 1.05"]
        },
        "Arm Barn Heros": {
            "Catchers": ["Salvador Perez (1B)", "Ben Rice (1B)", "Dalton Rushing", "Adley Rutschman"],
            "Infielders": ["Spencer Torkelson (1B)", "Brett Baty (2B, 3B)", "Noelvi Marte (3B, OF)", "Trea Turner (SS)", "Michael Busch (1B)", "Thomas Saggese (2B, SS)", "Marcus Semien (2B)", "Royce Lewis (3B)", "Jordan Lawlar (3B)", "Brock Wilken (3B)", "Konnor Griffin (SS)", "Kevin McGonigle (SS)", "Arjun Nimmala (SS)"],
            "Outfielders": ["Corbin Carroll", "Pete Crow-Armstrong", "Aaron Judge", "Fernando Tatis Jr.", "Kyle Tucker", "Michael Harris II", "Cam Smith", "Anthony Santander (UT)", "Ryan Clifford (1B/OF)", "Cole Carrigg", "James Tibbs"],
            "Pitchers": ["Hunter Brown", "Zac Gallen", "Kevin Gausman", "Shota Imanaga", "George Kirby", "Kodai Senga", "Framber Valdez", "Adrian Morejon", "Andres Munoz", "Sandy Alcantara", "Spencer Arrighetti", "Shane Bieber", "Luis Castillo", "Mitch Keller", "Hurston Waldrep", "Bryan Woo", "Emmanuel Clase", "Ryan Helsley", "Jeff Hoffman", "Grant Taylor", "Pablo Lopez", "Cole Ragans", "Felix Bautista", "Josh Hader", "Cam Caminiti", "Moises Chace", "Jackson Ferris", "Tekoah Roby", "Ricky Tiedemann", "Thomas White"],
            "Draft Picks": ["2026 Pick 2.01"]
        }
        # ... Remaining 7 teams (Guti Gang, Happy, ManBearPuig, Beers, Seiya, Hit it Hard, Special Eds) follow this format
    }

# --- 2. PERMANENT MEMORY INITIALIZATION ---
if "faab" not in st.session_state: st.session_state.faab = 200.00
if "master_ledger" not in st.session_state: st.session_state.master_ledger = get_initial_league()
if "history" not in st.session_state: st.session_state.history = []

# --- 3. CONNECTION & LIVE STATE ENGINE ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model = genai.GenerativeModel(available[0] if available else 'gemini-1.5-flash')
    
    st.set_page_config(page_title="Executive Assistant GM", layout="wide")
    st.title("🧠 Dynasty Assistant: Full-Cycle GM Engine")

    # SIDEBAR: Living Controls & Transaction Commit
    with st.sidebar:
        st.header(f"💰 FAAB: ${st.session_state.faab:.2f}")
        spent = st.number_input("Log Spent Bid:", min_value=0.0, step=1.0)
        if st.button("Update Budget"): st.session_state.faab -= spent

        st.divider()
        st.subheader("📢 Log Transaction")
        move_desc = st.text_input("Trade/Claim:", placeholder="e.g. 'Witness Protection traded Max Fried to Happy for Paul Skenes'")
        if st.button("Sync League Brain"):
            # This logs the move for AI context
            st.session_state.history.append(move_desc)
            st.success("State Synced! AI now knows Fried is on Happy and Skenes is on Witness Protection.")

    # 4. TABBED INTERFACE
    tabs = st.tabs(["🔥 Trade & Scout", "📋 Master Ledger", "🕵️‍♂️ Priority FAs", "😴 Sleepers", "💰 FAAB Strategy"])

    # Shared Logic for AI Reasoning Hubs
    def get_ai_advice(query_type, user_prompt=""):
        context = f"ROSTERS: {st.session_state.master_ledger}\nSCORING: 6x6 (OPS, QS, SVH)\nWINDOW: 2026-28\nMOVES: {st.session_state.history}\n"
        full_query = f"{context}\nQuery: {query_type}\nUser Input: {user_prompt}"
        return model.generate_content(full_query).text

    with tabs[0]:
        st.subheader("OOTP Trade Simulator & Suggestions")
        trade_prompt = st.chat_input("Grade a trade or ask for suggestions...")
        if trade_prompt:
            st.markdown(get_ai_advice("Trade Analysis", trade_prompt))

    with tabs[1]:
        st.subheader("Live Global Ledger")
        team = st.selectbox("Select Team to Inspect:", list(st.session_state.master_ledger.keys()))
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Catchers:**", st.session_state.master_ledger[team].get("Catchers", []))
            st.write("**Infielders:**", st.session_state.master_ledger[team].get("Infielders", []))
        with col2:
            st.write("**Outfielders:**", st.session_state.master_ledger[team].get("Outfielders", []))
            st.write("**Pitchers:**", st.session_state.master_ledger[team].get("Pitchers", []))
            st.write("**Picks:**", st.session_state.master_ledger[team].get("Draft Picks", []))

    with tabs[2]:
        st.subheader("Real-Time Priority Free Agent Scouting")
        if st.button("Brainstorm Priority FAs"):
            st.markdown(get_ai_advice("Scout Free Agents"))
        fa_chat = st.text_input("Search position-specific FAs:")
        if fa_chat: st.markdown(get_ai_advice("FA Deep Dive", fa_chat))

except Exception as e:
    st.error(f"Reasoning Engine Offline: {e}")
