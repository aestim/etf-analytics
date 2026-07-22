"""Dashboard ticker colors stay legible on the black Plotly theme."""

import ast
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from chart_colors import DARK_THEME_TICKER_PALETTE, ticker_color_map  # noqa: E402


def _contrast_against_black(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    return (luminance + 0.05) / 0.05


def test_palette_has_accessible_contrast_on_black():
    assert len(DARK_THEME_TICKER_PALETTE) == 24
    assert all(
        _contrast_against_black(color) >= 4.5 for color in DARK_THEME_TICKER_PALETTE
    )


def test_ticker_mapping_is_stable_and_never_uses_old_black_color():
    tickers = ["QLD", "BND", "SPY", "QQQ", "TLT", "GLD"]
    colors = ticker_color_map(tickers)

    assert colors == ticker_color_map(reversed(tickers))
    assert colors["QLD"] != "#222A2A"
    assert all(_contrast_against_black(color) >= 4.5 for color in colors.values())


def test_dashboard_entrypoint_local_imports_resolve():
    """Catch stale re-exports before Streamlit deploys a broken home page."""
    home_path = ROOT / "dashboard" / "home.py"
    tree = ast.parse(home_path.read_text(encoding="utf-8"))
    missing: list[str] = []

    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module not in {
            "chart_colors",
            "db",
            "i18n",
        }:
            continue
        imported_module = importlib.import_module(node.module)
        missing.extend(
            f"{node.module}.{alias.name}"
            for alias in node.names
            if not hasattr(imported_module, alias.name)
        )

    assert missing == []


def test_dashboard_keeps_beginner_onboarding_and_small_default_comparison():
    source = (ROOT / "dashboard" / "home.py").read_text(encoding="utf-8")

    assert "lang = ui_controls()" in source
    assert 'tr("home.intro_title", lang)' in source
    assert '("SPY", "BND", "GLD")' in source
    assert 'line_dash="ticker"' in source
    assert 'tr("home.nav_ask", lang)' in source


def test_entrypoint_uses_session_preserving_navigation():
    source = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")

    assert "st.navigation(" in source
    assert 'url_path="Strategy_Lab"' in source
    assert 'url_path="Ask"' in source
    assert 'st.session_state.get("ui_language_persisted", "English")' in source
