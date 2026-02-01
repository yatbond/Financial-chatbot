"""
Financial Chatbot - Streamlit Web App
Simple test to verify Streamlit works
"""
import streamlit as st

st.set_page_config(page_title="Financial Chatbot", page_icon="📊")

st.title("📊 Financial Chatbot")
st.write("Testing Streamlit deployment")
st.success("If you see this, Streamlit is working!")

# Show simple data
st.markdown("---")
st.markdown("### Quick Test")
if st.button("Click me"):
    st.balloons()
    st.write("🎉 You clicked the button!")
