# utils/pdf.py
import streamlit as st

def pdf_iframe(url: str, height: int = 600):
    # Renders a PDF inline if the host allows embedding. Otherwise shows link.
    st.components.v1.html(
        f"""
        <iframe src="{url}#toolbar=0&navpanes=0" width="100%" height="{height}" style="border:1px solid #ddd;border-radius:8px;"></iframe>
        """,
        height=height+8,
    )
