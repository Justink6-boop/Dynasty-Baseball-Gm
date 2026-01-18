import streamlit as st
import google.generativeai as genai

# --- 1. THE COMPLETE LEAGUE DATABASE (From Your Document) ---
FULL_ROSTERS = {
    "Witness Protection (Me)": ["Ronald Acuna Jr.", "Spencer Strider", "Dylan Crews", "J.T. Realmuto", "Max Fried", "2026 Pick 1.02"],
    "Bobbys Squad": ["Bobby Witt Jr.", "Gunnar Henderson", "Will Smith", "Pete Alonso", "2026 Pick 1.05"],
    "Arm Barn Heros": ["Aaron Judge", "Adley Rutschman", "Fernando Tatis Jr.", "Corbin Carroll", "Royce Lewis"],
    "Guti Gang": ["Mookie Betts", "Francisco Lindor", "Ketel Marte", "James Wood", "Cal Raleigh"],
    "Happy": ["Juan Soto", "Julio Rodriguez", "Jackson Merrill", "Ethan Salas", "Jackson Holliday"],
    "ManBearPuig": ["Elly De La Cruz", "Yordan Alvarez", "Samuel Basallo", "Vladimir Guerrero Jr.", "Matt Olson"],
    "Milwaukee Beers": ["Shohei Ohtani", "Bryce Harper", "Austin Riley", "Sebastian Walcott", "Harry Ford"],
    "Seiya Later": ["Tarik Skubal", "Chris Sale", "Rafael Devers", "Agustin Ramirez", "Bo Bichette"],
    "Special Eds": ["Randy Arozarena", "Masyn Winn", "Bo Naylor", "Freddy Peralta"],
    "Hit it Hard Hit it Far": ["Logan O'Hoppe", "Ozzie Albies", "Manny Machado", "Roki Sasaki", "Triston Casas"]
}

# --- 2. PERMANENT MEMORY & SCORING ---
if "faab" not in st.session_state: st.session_state.faab = 200.00
if "history" not in st.session_state: st.session_state.history = []
if "messages" not in st.session_state: st.session_state.messages = []

# --- 3. CONNECTION SETUP ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    target = 'models/gemini-2.0-flash' if 'models/gemini-2.0-flash' in str(available) else available[0]
    model = genai.GenerativeModel(target)
    
    st.set_page_config(page_title="Executive Assistant GM", layout="wide")
    st.title("🧠 Dynasty Assistant: Full-Cycle GM Engine")

    # SIDEBAR: The 'Living' League Controls
    with st.sidebar:
        st.header(f"💰 FAAB: ${st.session_state.faab:.2f}")
        bid = st.number_input("Deduct Spent Bid:", min_value=0.0, step=1.0)
        if st.button("Update Budget"): st.session_state.faab -= bid
        
        st.divider()
        st.subheader("📢 Commit Roster Change")
        move = st.text_input("Log Trade/Claim:", placeholder="e.g. 'Guti Gang claimed Kazuma Okamoto'")
        if st.button("Sync League Brain"):
            st.session_state.history.append(move)
            st.success("State Synced!")

    # 4. TABBED INTERFACE
    t1, t2, t3 = st.tabs(["🔥 Trade Simulator", "📊 Roster Valuation", "🎯 FYPD Strategy"])

    with t1:
        st.subheader("OOTP-Style Trade Grading")
        if prompt := st.chat_input("Grade a trade..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Context injection: Rules, Rosters, History, and Scoring
            context = f"Rules: 2-C, CI, MI. Scoring: OPS, QS, SVH. Strategy: Youth Pivot 2026-28.\n" \
                      f"ROSTERS: {FULL_ROSTERS}\nMOVES: {st.session_state.history}\nPROMPT: {prompt}"
            
            with st.spinner("Calculating Surplus Value..."):
                response = model.generate_content(context)
                st.markdown(response.text)

    with t2:
        st.subheader("Numerical Player Ratings (0-100)")
        st.info("The Assistant analyzes every player on 'Current' vs 'Potential' impact.")
        # Static table representation
        st.table({"Manager": list(FULL_ROSTERS.keys()), "Star Players": [", ".join(v[:2]) for v in FULL_ROSTERS.values()]})

    with t3:
        st.subheader("FYPD Pick Valuation & Scouting")
        st.write("**Top Priority Free Agents & Picks:**")
        st.caption("1. 2026 Pick 1.01 - 1.03 (Valuation: 92/100)")
        st.caption("2. Samuel Basallo (C/1B) - Target for 2-C leagues")
        st.caption("3. Tatsuya Imai (RHP) - High-floor ZiPS 2026 impact")

except Exception as e:
    st.error(f"Reasoning Engine Offline: {e}")
