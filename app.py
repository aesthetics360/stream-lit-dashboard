# app.py
import streamlit as st

st.set_page_config(page_title="A360 Curation", page_icon="🧭", layout="wide")
st.title("A360 — Staging Curation")

st.sidebar.header("Navigation")
st.sidebar.success("Use the left sidebar pages:\n\n- Dashboard\n- Products\n- Product Detail")

st.write("Welcome! Use the sidebar to browse products, edit fields, manage assets, and approve for promotion.")
