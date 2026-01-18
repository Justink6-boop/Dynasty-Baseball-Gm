import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

# --- 1. DIRECT PERMANENT CONNECTION ENGINE ---
def get_gspread_client():
    # Convert secrets to a mutable dictionary
    info = dict(st.secrets["gcp_service_account"])
    
    # THE JANITOR: Self-repairing key logic
    key = info["private_key"]
    
    # 1. Strip all spaces/newlines iOS might have added
    key = "".join(key.split())
    
    # 2. Put the headers back in properly
    key = key.replace("-----BEGINPRIVATEKEY-----", "-----BEGIN PRIVATE KEY-----\n")
    key = key.replace("-----ENDPRIVATEKEY-----", "\n-----END PRIVATE KEY-----\n")
    
    # 3. Fix internal padding (force multiple of 4)
    # We do this by splitting the key body and adding '=' if needed
    body = key.split("-----")
    if len(body) > 2:
        main_content = body[2].strip()
        padding = len(main_content) % 4
        if padding > 0:
            main_content += "=" * (4 - padding)
        key = f"-----BEGIN PRIVATE KEY-----\n{main_content}\n-----END PRIVATE KEY-----\n"

    info["private_key"] = key
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

# --- 2. YOUR GOOGLE SHEET ID ---
# Paste the ID from your URL: docs.google.com/spreadsheets/d/[THIS_PART]/edit
SHEET_ID = "https://docs.google.com/spreadsheets/d/1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A/edit?usp=drivesdk" 

# --- 3. THE COMPLETE MASTER LEAGUE LEDGER (Rosters from PDF) ---
def get_initial_league():
    return {
        "Witness Protection (Me)": {
            "Catchers": ["Dillon Dingler", "J.T. Realmuto"],
            "Infielders": ["Jake Cronenworth (2B)", "Ke'Bryan Hayes (3B)", "Caleb Durbin (3B)", "Luisangel Acuna (2B)", "Ceddanne Rafaela (2B, OF)", "Michael Massey (2B)", "Ivan Herrera (UT)", "Enrique Hernandez (1B, 3B, OF)", "Yandy Diaz (1B)", "Wilmer Flores (1B)", "Jeff McNeil (2B, OF)", "Andy Ibanez (3B)"],
            "Outfielders": ["Ronald Acuna Jr.", "Dylan Beavers", "JJ Bleday", "Dylan Crews", "Byron Buxton", "Ian Happ", "Tommy Pham", "Jacob Young", "Marcell Ozuna (UT)", "Justice Bigbie", "Alex Verdugo"],
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
    }

# --- 4. THE LIVE ENGINE ---
st.set_page_config(page_title="Executive Assistant GM", layout="wide")
st.title("🧠 Dynasty Assistant: Permanent Living Ledger")

if "faab" not in st.session_state: st.session_state.faab = 200.00

try:
    # Authenticate and Connect
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    worksheet = sh.get_worksheet(0)
    
    # Read persistent history from the Google Sheet
    permanent_history = worksheet.col_values(1)
    
    # Configure Gemini
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')

    # SIDEBAR: Permanent Logging & FAAB
    with st.sidebar:
        st.header(f"💰 FAAB: ${st.session_state.faab:.2f}")
        spent = st.number_input("Log Spent Bid:", min_value=0.0, step=1.0)
        if st.button("Update Budget"): st.session_state.faab -= spent

        st.divider()
        st.subheader("📢 Log Transaction")
        move = st.text_input("Trade/Claim:", placeholder="e.g. 'Fried to Happy for Skenes'")
        if st.button("Commit to Cloud"):
            worksheet.append_row([move])
            st.success("Synced to Permanent Ledger!")
            st.rerun()

    # APP TABS
    tabs = st.tabs(["🔥 Analysis & Scout", "📋 Master Ledger", "🕵️‍♂️ Permanent History", "😴 Sleepers", "💰 FAAB Strategy"])

    # Core AI Logic
    def get_ai_advice(query_type, user_prompt=""):
        context = f"""
        ROSTERS: {get_initial_league()}
        PERMANENT_HISTORY: {permanent_history}
        SCORING: 6x6 (OPS, QS, SVH)
        WINDOW: 2026-28 Rebuild/Youth Pivot
        """
        full_query = f"{context}\nTask: {query_type}\nUser Input: {user_prompt}"
        response = model.generate_content(full_query)
        return response.text

    with tabs[0]:
        st.subheader("OOTP-Style Trade Analysis")
        trade_prompt = st.chat_input("Grade a trade or ask for suggestions...")
        if trade_prompt:
            with st.spinner("Analyzing league impact..."):
                st.markdown(get_ai_advice("Trade Analysis", trade_prompt))

    with tabs[1]:
        st.subheader("Global Roster View (Initial)")
        team = st.selectbox("Select Team:", list(get_initial_league().keys()))
        t_data = get_initial_league()[team]
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Catchers:**", t_data.get("Catchers", []))
            st.write("**Infielders:**", t_data.get("Infielders", []))
        with col2:
            st.write("**Outfielders:**", t_data.get("Outfielders", []))
            st.write("**Pitchers:**", t_data.get("Pitchers", []))
            st.write("**Picks:**", t_data.get("Draft Picks", []))

    with tabs[2]:
        st.subheader("Every Trade Ever Logged (From Sheet)")
        for idx, trade in enumerate(permanent_history):
            st.write(f"{idx+1}. ✅ {trade}")

    with tabs[3]:
        st.subheader("Sleeper Cell")
        if st.button("Generate Sleeper Report"):
            st.markdown(get_ai_advice("Sleeper Identification", "Find undervalued assets."))

except Exception as e:
    st.error(f"Reasoning Engine Offline: {e}")
