"""
Pure transform functions for ETF price series.
Used by ingest and covered by tests/ (pytest).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def daily_simple_returns(adj_close: pd.Series) -> pd.Series:
    """Simple daily returns: (price_t / price_{t-1}) - 1."""
    return adj_close.pct_change()


def rolling_volatility(returns: pd.Series, window: int = 30) -> pd.Series:
    """Sample standard deviation of returns over a rolling window."""
    return returns.rolling(window=window, min_periods=window).std()


def drawdown_series(adj_close: pd.Series) -> pd.Series:
    """Drawdown from running maximum: (price / cummax) - 1."""
    running_max = adj_close.cummax()
    return (adj_close / running_max) - 1.0


def max_drawdown(adj_close: pd.Series) -> float:
    """Minimum drawdown value (most negative) over the series."""
    dd = drawdown_series(adj_close)
    return float(dd.min()) if len(dd.dropna()) else np.nan
