import streamlit as st
import google.generativeai as genai

# Use 'gemini-1.5-flash' - it is the most stable across all keys
MODEL_NAME = 'gemini-1.5-flash'

try:
    # 1. Pull the key from Streamlit Secrets
    api_key = st.secrets["GEMINI_API_KEY"]
    
    # 2. Configure the connection
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
    
    st.title("🧠 GM Reasoning Engine")
    
    # Simple test button to verify the key
    if st.button("Verify Connection"):
        test_response = model.generate_content("Hello")
        st.success("Connection Successful!")

    if prompt := st.chat_input("Reason with me..."):
        st.chat_message("user").write(prompt)
        # Deep Reasoning Logic
        response = model.generate_content(f"You are a Pro GM. Answer this: {prompt}")
        st.chat_message("assistant").write(response.text)
        
except Exception as e:
    # This will now tell us if the key is missing from Secrets vs. being 'invalid'
    st.error(f"Reasoning Engine Offline: {e}")
