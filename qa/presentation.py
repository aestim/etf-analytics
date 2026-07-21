"""Presentation rules shared by Ask tables and charts."""

from __future__ import annotations

import math

import pandas as pd


PERCENT_METRIC_COLUMNS = frozenset(
    {
        "cagr",
        "daily_return",
        "drawdown",
        "max_drawdown",
        "ann_vol",
        "annualized_vol_30d",
        "rolling_vol_30d",
    }
)


def is_percent_metric(column_name: str | None) -> bool:
    """Whether a decimal-valued metric should be displayed as a percentage."""
    if not column_name:
        return False
    normalized = column_name.lower()
    return normalized.endswith("_return") or normalized in PERCENT_METRIC_COLUMNS


def correlation_summary(df: pd.DataFrame | None) -> str:
    """Summarize a returned Pearson coefficient using the executed result."""
    if df is None or "correlation" not in df.columns:
        return ""
    values = pd.to_numeric(df["correlation"], errors="coerce").dropna()
    if values.empty:
        return ""
    coefficient = float(values.iloc[0])
    if not math.isfinite(coefficient):
        return ""

    magnitude = abs(coefficient)
    if magnitude < 0.2:
        strength = "very weak"
    elif magnitude < 0.4:
        strength = "weak"
    elif magnitude < 0.6:
        strength = "moderate"
    elif magnitude < 0.8:
        strength = "strong"
    else:
        strength = "very strong"
    if coefficient > 0:
        direction = "positive"
    elif coefficient < 0:
        direction = "negative"
    else:
        direction = "neutral"
    return (
        f"**Pearson correlation: {coefficient:.2f}** "
        f"({strength} {direction} relationship). Correlation does not establish causation."
    )
