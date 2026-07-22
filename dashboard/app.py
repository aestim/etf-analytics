"""Multipage Streamlit entrypoint with session-preserving navigation."""

from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="ETF Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

language = st.session_state.get("ui_language_persisted", "English")
korean = language == "한국어"

pages = [
    st.Page(
        "home.py",
        title="대시보드" if korean else "Dashboard",
        icon="📈",
        url_path="",
        default=True,
    ),
    st.Page(
        "pages/1_Strategy_Lab.py",
        title="투자 규칙 비교" if korean else "Strategy Lab",
        icon="🧪",
        url_path="Strategy_Lab",
    ),
    st.Page(
        "pages/2_Ask.py",
        title="데이터에 질문" if korean else "Ask",
        icon="💬",
        url_path="Ask",
    ),
]

st.navigation(pages, position="sidebar", expanded=True).run()
