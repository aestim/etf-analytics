"""Presentation rules shared by Ask tables and charts."""

from __future__ import annotations


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
