import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from io import BytesIO

# --- 1. CONNECTION & UTILITY ENGINE ---
def get_gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    key = info["private_key"].replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rosters')
    return output.getvalue()

SHEET_ID = "1-EDI4TfvXtV6RevuPLqo5DKUqZQLlvfF2fKoMDnv33A" 

# --- 2. MASTER LEAGUE LEDGER ---
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
        },
        "Guti Gang": {
            "Catchers": ["Cal Raleigh", "Kyle Teel", "Blake Mitchell", "Jeferson Quero"],
            "Infielders": ["Lenyn Sosa (1B, 2B)", "Ketel Marte (2B)", "Jazz Chisholm Jr. (2B, 3B)", "Francisco Lindor (SS)", "Vinnie Pasquantino (1B)", "Mookie Betts (SS)", "Zach Neto (SS)", "Willi Castro (2B, 3B, OF)", "Anthony Volpe (SS)", "Jacob Gonzalez (2B, SS)", "George Lombard Jr. (SS)", "Jesus Made (SS)", "Orelvis Martinez (SS)", "Jared Serna (2B, SS)", "Jett Williams (2B, SS, OF)"],
            "Outfielders": ["Cody Bellinger", "Lawrence Butler", "Brandon Nimmo", "James Wood", "Mike Trout (UT)", "Kevin Alcantara", "Adolis Garcia", "Austin Hays", "Chandler Simpson", "Trevor Larnach (UT)", "Xavier Isaac (UT)", "Braden Montgomery"],
            "Pitchers": ["David Peterson", "Carlos Rodon", "Huascar Brazoban", "Jack Dreyer", "Reed Garrett", "Tyler Rogers", "Gabe Speier", "Robert Suarez", "Luke Weaver", "Logan Allen", "Nathan Eovaldi", "Luis Gil", "MacKenzie Gore", "Tylor Megill", "Bryce Miller", "Max Scherzer", "Carson Whisenhunt", "Jaden Hill", "Yariel Rodriguez", "Gerrit Cole", "Zach Eflin", "Rhett Lowder", "Tyler Mahle", "Justin Steele", "Emiliano Teodo"]
        },
        "Happy": {
            "Catchers": ["Hunter Goodman", "Francisco Alvarez", "Ethan Salas"],
            "Infielders": ["Nick Kurtz (1B)", "Jackson Holliday (2B)", "Nathaniel Lowe (1B)", "Corey Seager (SS)", "Willson Contreras (1B)", "Freddie Freeman (1B)", "Nico Hoerner (2B)", "Hyeseong Kim (2B)", "Brice Turang (2B)", "Jose Ramirez (3B)", "Carlos Correa (3B, SS)", "Marcelo Mayer (3B)", "Moises Ballesteros (UT)", "Travis Bazzana (2B)", "Kristian Campbell (2B)", "Josh Jung (3B)", "Franklin Arias (SS)", "Alex Freeland (3B)"],
            "Outfielders": ["Roman Anthony", "Wyatt Langford", "Juan Soto", "Julio Rodriguez", "Jordan Beck", "Owen Caissie", "Evan Carter", "Jackson Chourio", "Brenton Doyle", "Jhostynxon Garcia", "Jackson Merrill", "Enrique Bradfield Jr.", "C.J. Kayfus", "Yohendrick Pinango", "Nelson Rada"],
            "Pitchers": ["Shane Baz", "Brayan Bello", "Tanner Bibee", "Garrett Crochet", "Lucas Giolito", "Clay Holmes", "Jack Leiter", "Garrett Whitlock", "Kyle Bradish", "Luis Garcia", "Sonny Gray", "Cristian Javier", "Michael King", "Quinn Priester", "Drew Rasmussen", "Paul Skenes", "Jhoan Duran", "Reese Olson", "Spencer Schwellenbach", "Jurrangelo Cijntje", "Kumar Rocker", "Jonah Tong", "Payton Tolle"]
        },
        "Hit it Hard Hit it Far": {
            "Catchers": ["Shea Langeliers", "Logan O'Hoppe", "Jonah Heim", "Keibert Ruiz"],
            "Infielders": ["Alec Burleson (1B, OF)", "Jorge Polanco (2B)", "Manny Machado (3B)", "Dansby Swanson (SS)", "Eugenio Suarez (3B)", "Luke Keaschall (2B)", "Ozzie Albies (2B)", "Triston Casas (1B)", "Ryan O'Hearn (1B, OF)", "Pavin Smith (1B)", "Alec Bohm (3B)", "Oswaldo Cabrera (3B)", "Xander Bogaerts (SS)", "Colson Montgomery (SS)", "Carson Williams (SS)", "Charlie Condon (1B)", "Termarr Johnson (2B)"],
            "Outfielders": ["Teoscar Hernandez", "Steven Kwan", "Jung Hoo Lee", "Lars Nootbaar", "Justin Crawford", "Victor Scott", "Masataka Yoshida (UT)", "Walker Jenkins"],
            "Pitchers": ["Matthew Boyd", "Noah Cameron", "Sean Manaea", "Luis Severino", "Brady Singer", "Michael Wacha", "Brandon Woodruff", "Jose Alvarado", "Aaron Civale", "Connelly Early", "Kyle Harrison", "Logan Henderson", "Jake Irvin", "Miles Mikolas", "Charlie Morton", "Roki Sasaki", "Jameson Taillon", "Hagen Smith"]
        },
        "ManBearPuig": {
            "Catchers": ["Samuel Basallo", "William Contreras", "Jimmy Crooks", "Josue Briceno (1B)", "Eduardo Tait"],
            "Infielders": ["Vladimir Guerrero Jr. (1B)", "Sal Stewart (1B)", "Junior Caminero (3B)", "Elly De La Cruz (SS)", "Matt Olson (1B)", "CJ Abrams (SS)", "Coby Mayo (1B)", "Spencer Steer (1B)", "Bryson Stott (2B)", "Cole Young (2B)", "Addison Barger (3B, OF)", "Brady House (3B)", "Mark Vientos (3B)", "Jonathan Aranda (1B)", "Jordan Westburg (3B)", "Michael Arroyo (2B)", "Deyvison De Los Santos (3B)", "Aidan Miller (SS)"],
            "Outfielders": ["Oneil Cruz", "Jarren Duran", "Heliot Ramos", "Daulton Varsho", "Yordan Alvarez (UT)", "Kyle Schwarber (UT)", "Adrian Del Castillo (UT)", "Jeremiah Jackson", "Jakob Marsee", "Max Clark", "Josue De Paula", "Chase DeLauter", "Lazaro Montes", "Emmanuel Rodriguez"],
            "Pitchers": ["Bryan Abreu", "Matt Brash", "Edwin Diaz", "Hunter Gaddis", "Brad Keller", "JoJo Romero", "Cade Smith", "Devin Williams", "Bubba Chandler", "Tyler Glasnow", "Hunter Greene", "Nick Lodolo", "Luis Morales", "Blake Snell", "Nolan McLean (P)", "Jared Jones", "Jason Adam", "Mick Abel", "Gage Jump", "Andrew Painter", "Noah Schultz", "Charlee Soto", "Jarlin Susana", "Travis Sykora", "Hunter Barco"]
        },
        "Milwaukee Beers": {
            "Catchers": ["Yainer Diaz", "Carlos Narvaez", "Harry Ford", "Alejandro Kirk", "Gabriel Moreno"],
            "Infielders": ["Bryce Harper (1B)", "Jose Altuve (2B, OF)", "Matt Chapman (3B)", "Geraldo Perdomo (SS)", "Andrew Vaughn (1B)", "Ezequiel Tovar (SS)", "Nolan Schanuel (1B)", "Brendan Donovan (2B)", "Luis Garcia Jr. (2B)", "Matt McLain (2B)", "Christian Moore (2B)", "Isaac Paredes (3B)", "Austin Riley (3B)", "Jesus Baez (3B, SS)", "Felnin Celesten (SS)", "Leodalis De Vries (SS)", "Colt Emerson (SS)", "Sebastian Walcott (SS)", "JJ Wetherholt (2B, SS)"],
            "Outfielders": ["Colton Cowser", "Tyler Freeman", "Riley Greene", "Andy Pages", "Bryan Reynolds", "Shohei Ohtani (UT)", "Bryce Eldridge (UT)", "TJ Friedl", "Carson Benge", "Joey Loperfido", "Jacob Melton", "Aidan Smith", "Ryan Waldschmidt"],
            "Pitchers": ["Andrew Abbott", "Seth Lugo", "Zebby Matthews", "Casey Mize", "Trevor Rogers", "Brandon Sproat", "Logan Webb", "Orion Kerkering", "Emilio Pagan", "Jose Berrios", "Zack Littell", "Parker Messick", "Joe Ryan", "Brad Lord", "Corbin Burnes", "Zack Wheeler", "Ryan Sloan", "Robby Snelling", "Santiago Suarez", "Miguel Ullola"]
        },
        "Seiya Later": {
            "Catchers": ["Carson Kelly", "Agustin Ramirez", "Kyle Valera (UT)"],
            "Infielders": ["Rafael Devers (1B)", "Gleyber Torres (2B)", "Alex Bregman (3B)", "Trevor Story (SS)", "Matt Shaw (3B)", "Bo Bichette (SS)", "Warming Bernabel (1B)", "Willy Adames (SS)", "Christian Encarnacion-Strand (1B)", "Victor Figueroa (1B)", "Luis Pena (2B, SS)", "Bryce Rainer (SS)"],
            "Outfielders": ["Jo Adell", "Ramon Laureano", "Jurickson Profar", "George Springer", "Giancarlo Stanton (UT)", "Christian Yelich (UT)", "Trent Grisham", "Mickey Moniak", "Seiya Suzuki (UT)", "Joshua Baez", "Edward Florentino", "Mike Sirota", "Zac Veen"],
            "Pitchers": ["Javier Assad", "Gavin Williams", "Yoshinobu Yamamoto", "David Bednar", "Raisel Iglesias", "Griffin Jax", "Mason Miller", "Abner Uribe", "Taj Bradley", "Caden Dana", "Jacob deGrom", "Cade Horton", "Matthew Liberatore", "Jacob Misiorowski", "Robbie Ray", "Chris Sale", "Tarik Skubal", "Jackson Jobe", "Max Meyer", "Grayson Rodriguez", "Ben Joyce", "Daniel Palencia", "Brandon Clarke", "Daniel Espino", "Michael Forret", "Ty Johnson", "Wei-En Lin", "Quinn Mathews", "Noble Meyer", "Jaxon Wiggins"]
        },
        "Special Eds": {
            "Catchers": ["Patrick Bailey", "Austin Wells", "Bo Naylor"],
            "Infielders": ["Christian Walker (1B)", "Brandon Lowe (2B)", "Ryan McMahon (3B)", "Jeremy Pena (SS)", "Max Muncy (3B)", "Masyn Winn (SS)", "Luis Arraez (1B)", "Rhys Hoskins (1B)", "Thairo Estrada (2B)", "Luis Rengifo (2B, 3B)", "Amed Rosario (3B)", "Jose Caballero (2B, 3B, SS, OF)"],
            "Outfielders": ["Wilyer Abreu", "Randy Arozarena", "Sal Frelick", "Lourdes Gurriel Jr.", "Taylor Ward", "Josh Lowe", "Jose Siri"],
            "Pitchers": ["Erick Fedde", "Yusei Kikuchi", "Jesus Luzardo", "Bailey Ober", "Ryan Pepiot", "Freddy Peralta", "Nick Pivetta", "J.P. Sears", "Tomoyuki Sugano", "Griffin Canning", "Nestor Cortes Jr.", "Clarke Schmidt", "Taijuan Walker", "Simeon Woods-Richardson", "Ryan Pressly", "Alex Cobb", "Josiah Gray", "Shane McClanahan", "John Means", "Dane Dunning", "Martin Perez"]
        }
    }

# --- 3. PAGE CONFIG ---
st.set_page_config(page_title="Executive Assistant GM", layout="wide")
st.title("🧠 Dynasty GM Suite: Executive Terminal")

if "faab" not in st.session_state: st.session_state.faab = 200.00

try:
    # A. DATA CONNECTIONS
    gc = get_gspread_client()
    sh = gc.open_by_key(SHEET_ID)
    history_ws = sh.get_worksheet(0)
    roster_ws = sh.get_worksheet(1) 

    permanent_history = history_ws.col_values(1)
    raw_roster_matrix = roster_ws.get_all_values()

    # Define the export_df for team lists before starting tabs
    init_data = get_initial_league()
    flat_data = {team: [p for pos in players.values() if isinstance(pos, list) for p in pos] + players.get("Draft Picks", []) for team, players in init_data.items()}
    export_df = pd.DataFrame.from_dict(flat_data, orient='index').transpose()
    team_list = list(export_df.columns)

    # B. AI CONFIGURATION
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # This logic automatically finds the best available 'flash' model to avoid 404s
    try:
        # Try the most stable current name first
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
    except:
        # Fallback: List all models and pick the first one that supports text generation
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in available_models if 'flash' in m]
        model_to_use = flash_models[0] if flash_models else available_models[0]
        model = genai.GenerativeModel(model_to_use)

    # --- 4. SIDEBAR ---
    with st.sidebar:
        st.header(f"💰 FAAB: ${st.session_state.faab:.2f}")
        spent = st.number_input("Log Spending:", min_value=0.0)
        if st.button("Update Budget"): st.session_state.faab -= spent
        st.divider()
        st.info("💡 Use the 'Transaction Terminal' tab to log trades and roster moves.")

    # --- 5. THE EXECUTIVE SUITE TABS ---
    tabs = st.tabs([
        "🔁 Transaction Terminal", 
        "🔥 Trade Analysis", 
        "📋 Live Ledger", 
        "🎯 Priority Candidates", 
        "🕵️‍♂️ Full Scouting", 
        "💎 Sleeper Cell", 
        "📜 History Log"
    ])

    # --- TAB 0: TRANSACTION TERMINAL ---
    with tabs[0]:
        st.subheader("Official League Transaction Terminal")
        trans_type = st.radio("Select Action Type:", ["Trade", "Waiver/Drop"], horizontal=True)
        
        if trans_type == "Trade":
            col1, col2 = st.columns(2)
            with col1:
                team_a = st.selectbox("From Team:", team_list, key="ta_term")
                players_out = st.text_area("Players Leaving Team A:", placeholder="One per line", key="out_term")
            with col2:
                team_b = st.selectbox("To Team:", team_list, key="tb_term")
                players_in = st.text_area("Players Leaving Team B:", placeholder="One per line", key="in_term")

            if st.button("Execute Trade & Sync"):
                if team_a == team_b:
                    st.error("Select different teams.")
                else:
                    with st.spinner("Processing trade..."):
                        prompt = f"DATA: {raw_roster_matrix}\nACTION: Move {players_out} FROM {team_a} TO {team_b}. Move {players_in} FROM {team_b} TO {team_a}. Return ONLY Python list of lists."
                        response = model.generate_content(prompt).text
                        clean = response.replace("```python", "").replace("```", "").strip()
                        try:
                            new_list = eval(clean)
                            roster_ws.clear()
                            roster_ws.update(new_list)
                            history_ws.append_row([f"TRADE: {team_a} ↔️ {team_b}"])
                            st.success("Synced!")
                            st.rerun()
                        except: st.error("Spelling or Format error.")

        else: # Waiver Logic
            col1, col2 = st.columns(2)
            with col1:
                t_team = st.selectbox("Team:", team_list)
                act = st.selectbox("Action:", ["Add", "Drop"])
            with col2:
                p_name = st.text_input("Player Name:")
            
            if st.button("Submit Waiver Move"):
                with st.spinner("Updating..."):
                    prompt = f"DATA: {raw_roster_matrix}\nACTION: {act} {p_name} to/from {t_team}. Return ONLY Python list of lists."
                    response = model.generate_content(prompt).text
                    clean = response.replace("```python", "").replace("```", "").strip()
                    try:
                        new_list = eval(clean)
                        roster_ws.clear()
                        roster_ws.update(new_list)
                        history_ws.append_row([f"{act.upper()}: {p_name} ({t_team})"])
                        st.success("Roster Updated!")
                        st.rerun()
                    except: st.error("Spelling or Format error.")

    # --- OTHER TABS ---
    with tabs[1]:
        st.subheader("OOTP-Style Trade Consultant")
        trade_q = st.chat_input("Analyze this trade...")
        if trade_q: st.markdown(get_gm_advice("Trade Grading", trade_q))

    with tabs[2]:
        st.subheader("Live Database Status")
        st.download_button(label="📥 Download Template", data=convert_df_to_excel(export_df), file_name="League_Rosters.xlsx")
        st.dataframe(pd.DataFrame(raw_roster_matrix), use_container_width=True)

    with tabs[3]:
        if st.button("Generate Trade Target List"): st.markdown(get_gm_advice("ZiPS Buy-Lows"))

    with tabs[4]:
        scout_p = st.text_input("Enter Player for Fit Analysis:")
        if scout_p: st.markdown(get_gm_advice("Scouting Fit Analysis", scout_p))

    with tabs[5]:
        if st.button("Find Dynasty Sleepers"): st.markdown(get_gm_advice("2026-28 Sleepers"))

    with tabs[6]:
        st.subheader("Transaction History")
        for trade in permanent_history[::-1]: st.write(f"✅ {trade}")

except Exception as e:
    st.error(f"Executive System Offline: {e}")
