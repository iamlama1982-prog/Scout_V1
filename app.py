"""Scout — live incident investigator and in-app final presentation.

Run: python -m streamlit run app.py
The original Scout app remains the default for normal use.
"""
import streamlit as st

scout_page = st.Page(
    "pages/Scout.py",
    title="Live Scout",
    icon="🧭",
    default=True,
)
pitch_page = st.Page(
    "pages/Pitch.py",
    title="Product pitch",
    icon="🎯",
)
presentation_page = st.Page(
    "pages/Presentation.py",
    title="Evidence & charts",
    icon="📊",
)

# Present, investigate and inspect the coursework evidence in one Streamlit app.
st.navigation([pitch_page, scout_page, presentation_page], position="top").run()
