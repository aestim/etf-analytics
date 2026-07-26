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

# "wide" lets narrow laptops use their full width, but left unbounded it also
# stretches charts and prose across a large desktop monitor, where a line of
# text becomes tiring to follow. Cap the content instead of switching to
# "centered", which is too narrow for a multi-series chart.
CONTENT_MAX_WIDTH = "1200px"

st.markdown(
    f"""
    <style>
    /* stBottomBlockContainer holds the docked st.chat_input, which lives
       outside the main block and would otherwise span the whole window. */
    [data-testid="stMainBlockContainer"],
    [data-testid="stBottomBlockContainer"] {{
        max-width: {CONTENT_MAX_WIDTH};
        margin-inline: auto;
    }}
    section[data-testid="stSidebar"][aria-expanded="true"],
    section[data-testid="stSidebar"][aria-expanded="true"]
      > div[data-testid="stSidebarContent"] {{
        width: 260px !important;
        min-width: 260px !important;
        max-width: 260px !important;
    }}
    [data-testid="stCaptionContainer"] p,
    [data-testid="stWidgetLabel"] p,
    section[data-testid="stSidebar"] p {{
        font-size: 0.95rem !important;
        line-height: 1.55 !important;
    }}
    /* Streamlit overlays "Press Enter to submit form" on the right of a text
       input. On a phone it lands on top of the placeholder. Every form here
       has a visible submit button, so the hint is redundant anyway. */
    [data-testid="stForm"] [data-testid="InputInstructions"] {{
        display: none;
    }}
    /* Search results are plain full-width buttons: one element per listing,
       so nothing can wrap onto its own line and the click target is the row. */
    [data-testid="stButton"] button p {{
        text-align: left;
        width: 100%;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

lang = ui_controls()
korean = lang == "ko"

pages = [
    st.Page(
        "home.py",
        title="ETF 한눈에 보기" if korean else "ETF Overview",
        icon="📈",
        url_path="",
        default=True,
    ),
    st.Page(
        "pages/1_Strategy_Lab.py",
        title="투자 방법 비교" if korean else "Compare Strategies",
        icon="🧪",
        url_path="Strategy_Lab",
    ),
    st.Page(
        "pages/2_Ask.py",
        title="ETF 질문하기" if korean else "Ask About ETFs",
        icon="💬",
        url_path="Ask",
    ),
]

st.navigation(pages, position="sidebar", expanded=True).run()
