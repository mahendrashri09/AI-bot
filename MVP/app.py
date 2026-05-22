import streamlit as st
from copilot import init_vector_db, query_copilot

st.set_page_config(page_title="AI Incident Copilot", layout="centered")

st.title("🤖 AI Incident Copilot")
st.write("Paste your logs or incident description below and let AI help you debug!")

log_input = st.text_area("🔎 Paste Logs / Incident Description", height=200)

if "collection" not in st.session_state:
    st.session_state.collection = init_vector_db()

if st.button("Analyze Incident"):
    if log_input.strip():
        with st.spinner("Analyzing with Copilot..."):
            result = query_copilot(log_input, st.session_state.collection)
        st.success("✅ Copilot Suggestion")
        st.write(result)
    else:
        st.warning("Please paste some logs first!")
