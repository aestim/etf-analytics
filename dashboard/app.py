"""Multipage Streamlit entrypoint with session-preserving navigation."""

from __future__ import annotations

import streamlit as st

from custom_etf import RESULT_ROW_KEY_PREFIX
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
    /* Search results are plain full-width buttons — one element per listing,
       so nothing can wrap onto its own line and the whole row is the click
       target. These rules only restyle those keyed buttons into flat list
       rows: two lines from the label's hard break, everything dimmed except
       the bold symbol, a hairline between rows, hover highlight. If Streamlit
       stops emitting st-key- classes they degrade to ordinary buttons and
       keep working. */
    [class*="st-key-{RESULT_ROW_KEY_PREFIX}"] button {{
        justify-content: flex-start;
        text-align: left;
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 0.75rem;
        min-height: 0;
    }}
    /* Between the button and its markdown sit two centring wrappers (a div
       and a span) that shrink-wrap the text — they are what centred the
       label. Stretch both so the text starts at the row's left edge.
       (Verified against the rendered DOM, not assumed.) */
    [class*="st-key-{RESULT_ROW_KEY_PREFIX}"] button > div,
    [class*="st-key-{RESULT_ROW_KEY_PREFIX}"] button span,
    [class*="st-key-{RESULT_ROW_KEY_PREFIX}"] button
      [data-testid="stMarkdownContainer"] {{
        justify-content: flex-start;
        width: 100%;
    }}
    [class*="st-key-{RESULT_ROW_KEY_PREFIX}"] button p {{
        text-align: left;
        width: 100%;
        line-height: 1.5;
        font-size: 0.85rem;
        color: rgba(250, 250, 250, 0.6);
    }}
    /* A long fund name must truncate, not wrap and push the identifiers to a
       third line. display:block + overflow:hidden makes the name its own
       block formatting context, so it narrows beside the floated badge and
       volume and ellipsises exactly at that boundary. The <br> then becomes
       redundant (a block already ends the line), so it is hidden to avoid a
       blank line. */
    [class*="st-key-{RESULT_ROW_KEY_PREFIX}"] button strong {{
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 1rem;
        font-weight: 600;
        color: #fafafa;
    }}
    [class*="st-key-{RESULT_ROW_KEY_PREFIX}"] button p br {{
        display: none;
    }}
    /* Monogram badge — the label's leading markdown image, floated so both
       text lines sit beside it like a brokerage row. */
    [class*="st-key-{RESULT_ROW_KEY_PREFIX}"] button img {{
        float: left;
        width: 2.4rem;
        height: 2.4rem;
        max-height: none;
        border-radius: 0.65rem;
        margin-right: 0.75rem;
    }}
    /* Captioned volume — the label's code span, floated to the right edge
       and stripped of Streamlit's inline-code chrome. */
    [class*="st-key-{RESULT_ROW_KEY_PREFIX}"] button code {{
        float: right;
        background: transparent;
        border: none;
        padding: 0.1rem 0 0 0.5rem;
        font-family: inherit;
        font-size: 0.78rem;
        color: rgba(250, 250, 250, 0.45);
    }}
    [class*="st-key-{RESULT_ROW_KEY_PREFIX}"] button:hover {{
        background: rgba(250, 250, 250, 0.07);
    }}
    [class*="st-key-{RESULT_ROW_KEY_PREFIX}"]
      + [class*="st-key-{RESULT_ROW_KEY_PREFIX}"] {{
        border-top: 1px solid rgba(250, 250, 250, 0.07);
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
