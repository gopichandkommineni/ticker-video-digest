"""Streamlit entrypoint for Ticker Video Digest."""
import streamlit as st

st.set_page_config(page_title="Ticker Video Digest", layout="centered")

st.title("Ticker Video Digest")
st.write("Enter a stock ticker symbol to get a 7-day digest of YouTube videos.")

ticker = st.text_input("Ticker symbol", placeholder="e.g. RKLB")

if st.button("Analyze") and ticker:
    st.info("Analysis not yet implemented.")

st.caption(
    "Not investment advice. Output is aggregated commentary from public YouTube videos."
)
