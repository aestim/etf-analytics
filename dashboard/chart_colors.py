"""Color utilities shared by the dark-themed dashboard charts."""

from __future__ import annotations

import plotly.express as px


# Every Light24 color has at least 5.5:1 contrast against black. Dark24 is not
# suitable here: its sixth entry (#222A2A) is nearly invisible on plotly_dark.
DARK_THEME_TICKER_PALETTE = tuple(px.colors.qualitative.Light24)


def ticker_color_map(tickers) -> dict[str, str]:
    """Return a stable, high-contrast color for every ticker."""
    return {
        ticker: DARK_THEME_TICKER_PALETTE[i % len(DARK_THEME_TICKER_PALETTE)]
        for i, ticker in enumerate(sorted(tickers))
    }
