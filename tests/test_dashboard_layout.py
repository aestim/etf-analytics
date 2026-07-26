"""Page chrome the three pages share, asserted against the entrypoint source.

app.py runs Streamlit commands at import time, so it is read rather than
imported. The testids below were confirmed against the frontend bundle shipped
with the pinned Streamlit version.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"
APP_SOURCE = (DASHBOARD / "app.py").read_text(encoding="utf-8")
BUTTON_COMMANDS = {"button", "form_submit_button", "download_button", "link_button"}
# Search results are rendered as one full-width button per listing, so the whole
# row is the click target. That button is a list row, not a control, and is the
# single reason a stretched button is allowed anywhere in the dashboard. Its key
# is built from this constant, which is what the unparsed keyword contains.
FULL_WIDTH_ROW_KEY = "RESULT_ROW_KEY_PREFIX"


def _button_key_source(node: ast.Call) -> str:
    for keyword in node.keywords:
        if keyword.arg == "key":
            return ast.unparse(keyword.value)
    return ""


def test_content_width_is_capped_on_large_monitors():
    """layout="wide" alone stretches charts and prose across a whole monitor."""
    assert 'layout="wide"' in APP_SOURCE
    assert '[data-testid="stMainBlockContainer"]' in APP_SOURCE

    width = re.search(r'CONTENT_MAX_WIDTH = "(\d+)px"', APP_SOURCE)
    assert width, "the cap should stay one readable, named constant"
    # Wide enough for a multi-series chart, narrow enough to scan a line of text.
    assert 900 <= int(width.group(1)) <= 1400
    assert "margin-inline: auto" in APP_SOURCE


def test_the_docked_chat_input_is_capped_too():
    """st.chat_input renders outside the main block, so it needs its own cap."""
    assert '[data-testid="stBottomBlockContainer"]' in APP_SOURCE
    assert "st.chat_input" in (DASHBOARD / "pages" / "2_Ask.py").read_text(
        encoding="utf-8"
    )


def test_form_submit_hint_does_not_overlap_the_placeholder():
    """Streamlit overlays the hint on the input, which collides on a phone."""
    assert '[data-testid="stForm"] [data-testid="InputInstructions"]' in APP_SOURCE


@pytest.mark.parametrize("page", ["home.py", "pages/1_Strategy_Lab.py", "pages/2_Ask.py"])
def test_every_page_is_registered_through_the_shared_entrypoint(page):
    """Page-level st.set_page_config would bypass the chrome asserted above."""
    assert f'"{page}"' in APP_SOURCE
    assert "set_page_config" not in (DASHBOARD / page).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "path", sorted(DASHBOARD.rglob("*.py")), ids=lambda path: path.name
)
def test_buttons_size_to_their_label(path):
    """st.button already defaults to width="content".

    Passing width="stretch" makes a three-letter label span its whole column,
    which reads as a full-width bar on a desktop monitor. Charts and dataframes
    are the elements that should fill the container, not controls.
    """
    stretched = [
        node.lineno
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in BUTTON_COMMANDS
        and any(
            keyword.arg == "width" and getattr(keyword.value, "value", None) == "stretch"
            for keyword in node.keywords
        )
        and FULL_WIDTH_ROW_KEY not in _button_key_source(node)
    ]

    assert stretched == [], f"{path.name} stretches buttons on lines {stretched}"


@pytest.mark.parametrize(
    "path", sorted(DASHBOARD.rglob("*.py")), ids=lambda path: path.name
)
def test_dialogs_are_not_wider_than_the_page(path):
    """st.dialog "large" is up to 1280px — wider than CONTENT_MAX_WIDTH."""
    oversized = [
        node.lineno
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "dialog"
        and any(
            keyword.arg == "width" and getattr(keyword.value, "value", None) == "large"
            for keyword in node.keywords
        )
    ]

    assert oversized == [], f"{path.name} opens a 1280px dialog on {oversized}"
