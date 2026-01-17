import streamlit as st
import pandas as pd

# Set page config
st.set_page_config(page_title="Dynasty Assistant GM", layout="wide")

# 1. DATABASE: League Rosters (From your PDF data)
league_data = {
    "Team Witness Protection": {
        "Core": ["Ronald Acuna Jr.", "Spencer Strider", "Dylan Crews", "Jesus Made", "Colt Emerson"],
        "Veterans": ["Marcell Ozuna", "J.T. Realmuto", "Max Fried", "Zach Eflin"],
        "Pivots": ["Zach Neto", "Robby Snelling", "Dylan Beavers"]
    },
    "Bobbys Squad": {
        "Core": ["Bobby Witt Jr.", "Gunnar Henderson", "Will Smith"],
        "Assets": ["Tink Hence", "Jac Caglianone", "Chase Burns"]
    },
    "Happy": {
        "Core": ["Juan Soto", "Julio Rodriguez", "Paul Skenes"],
        "Assets": ["Jackson Holliday", "Wyatt Langford", "Ethan Salas"]
    }
}

# 2. PROJECTION LOGIC: ZiPS/Steamer 2026 'Undervalued' Radar
undervalued_targets = [
    {"Player": "Kevin McGonigle", "Reason": "ZiPS Darling - Elite Hit Tool", "Target Team": "Arm Barn Heros"},
    {"Player": "Bubba Chandler", "Reason": "High-Velocity SP projection", "Target Team": "ManBearPuig"},
    {"Player": "Samuel Basallo", "Reason": "Statcast Power Elite for Catcher", "Target Team": "ManBearPuig"}
]

# --- APP UI ---
st.title("⚾ Dynasty Assistant GM: Rebuild Mode")
st.sidebar.header("Navigation")
page = st.sidebar.selectbox("Choose a Module", ["Roster Analysis", "Trade Generator", "Sleeper Radar"])

if page == "Roster Analysis":
    st.subheader("Team Witness Protection: Organizational Windows")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### ✅ Core Youth Assets")
        st.success(", ".join(league_data["Team Witness Protection"]["Core"]))
        
    with col2:
        st.write("### ⚠️ Suggested Trade Exits (Aging Assets)")
        st.warning(", ".join(league_data["Team Witness Protection"]["Veterans"]))
    
    st.info("Strategy: You are in a 'Hard Pivot.' Sell veterans to Contenders for 'Cusp' prospects.")

elif page == "Trade Generator":
    st.subheader("Mock Trade Ideas (Contextual Strategy)")
    
    st.write("#### 🤝 Scenario 1: The SS Logjam Flip")
    st.write("**Give:** Zach Neto + Max Fried")
    st.write("**Get:** Jackson Jobe (DET, SP) + Bubba Chandler (PIT, SP)")
    st.markdown("*Logic: Capitalize on your SS depth to fix your pitching age-curve.*")
    
    st.write("#### 🤝 Scenario 2: The Veteran Dump")
    st.write("**Give:** Marcell Ozuna + J.T. Realmuto")
    st.write("**Get:** Kevin McGonigle (DET, SS) + 2026 1st Round Pick")
    st.markdown("*Logic: Move high-production, low-trade-value assets to a win-now team like 'Happy'.*")

elif page == "Sleeper Radar":
    st.subheader("2026 ZiPS/Steamer Undervalued Radar")
    st.table(pd.DataFrame(undervalued_targets))
