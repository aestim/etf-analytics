"""Multipage Streamlit entrypoint with session-preserving navigation."""

from __future__ import annotations

import streamlit as st

from i18n import ui_controls


st.set_page_config(
    page_title="ETF Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"][aria-expanded="true"],
    section[data-testid="stSidebar"][aria-expanded="true"]
      > div[data-testid="stSidebarContent"] {
        width: 260px !important;
        min-width: 260px !important;
        max-width: 260px !important;
    }
    [data-testid="stCaptionContainer"] p,
    [data-testid="stWidgetLabel"] p,
    section[data-testid="stSidebar"] p {
        font-size: 0.95rem !important;
        line-height: 1.55 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

lang = ui_controls()
korean = lang == "ko"

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
