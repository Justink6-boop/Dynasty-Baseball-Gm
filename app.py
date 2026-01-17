import streamlit as st
import google.generativeai as genai

st.title("🧠 Dynasty GM: Reasoning Engine")

try:
    # 1. Setup Connection
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # 2. Scanner (To find the right model name for your region)
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # We try the most stable one first
    target_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
    
    model = genai.GenerativeModel(target_model)
    st.success(f"Connected to: {target_model}")

    # 3. Reasoning Interface
    if p := st.chat_input("Reason with me..."):
        st.chat_message("user").write(p)
        # Deep Reasoning Logic
        context = "Rules: 2-Catcher, CI, MI slots. Rebuilding strategy."
        response = model.generate_content(f"{context}\nUser: {p}")
        st.chat_message("assistant").write(response.text)
        
except Exception as e:
    st.error(f"Reasoning Engine Offline: {e}")
    st.write("Check if 'Generative Language API' is enabled in your Google Cloud Console.")
