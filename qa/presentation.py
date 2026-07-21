"""Presentation rules shared by Ask tables and charts."""

from __future__ import annotations

import math

import pandas as pd

from chart_spec import relationship_axes


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


def is_dollar_metric(column_name: str | None) -> bool:
    """Whether a metric is a USD-denominated liquidity amount."""
    if not column_name:
        return False
    return "dollar_volume" in column_name.lower()


METRIC_LABELS = {
    "cagr": "CAGR",
    "cumulative_return": "cumulative return",
    "ytd_return": "year-to-date return",
    "daily_return": "daily return",
    "leverage": "leverage multiple",
    "avg_daily_volume": "average daily share volume",
    "avg_daily_dollar_volume": "average daily dollar volume (log-scaled)",
    "annualized_vol_30d": "annualized 30-day volatility",
    "avg_annualized_vol_30d": "average annualized 30-day volatility",
    "rolling_vol_30d": "30-day volatility",
    "drawdown": "drawdown",
    "max_drawdown": "maximum drawdown",
    "adj_close": "adjusted close price",
}


def _metric_label(column: str) -> str:
    return METRIC_LABELS.get(column.lower(), column.replace("_", " "))


def _period_text(df: pd.DataFrame) -> str:
    if "period_start" not in df.columns or "as_of_date" not in df.columns:
        return ""
    starts = pd.to_datetime(df["period_start"], errors="coerce").dropna()
    ends = pd.to_datetime(df["as_of_date"], errors="coerce").dropna()
    if starts.empty or ends.empty:
        return ""
    return f" for {starts.min():%Y-%m-%d} to {ends.max():%Y-%m-%d}"


def _universe_text(df: pd.DataFrame) -> tuple[str, int]:
    count = int(df["ticker"].nunique(dropna=True)) if "ticker" in df.columns else len(df)
    if "universe_scope" in df.columns:
        scopes = df["universe_scope"].dropna().astype(str)
        if not scopes.empty:
            return scopes.iloc[0], count
    return f"the current {count}-ETF warehouse universe", count


def correlation_summary(df: pd.DataFrame | None, question: str = "") -> str:
    """Build a conclusion-first relationship answer from the executed result."""
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

    scope, ticker_count = _universe_text(df)
    axes = relationship_axes(question, df)
    if axes is None:
        conclusion = f"Within {scope}, the returned metrics had a {direction} relationship."
    else:
        x_label, y_label = (_metric_label(column) for column in axes)
        if magnitude < 0.2:
            conclusion = (
                f"Within {scope}, {x_label} and {y_label} showed little linear "
                f"relationship{_period_text(df)}."
            )
        else:
            comparison = "higher" if coefficient > 0 else "lower"
            conclusion = (
                f"Within {scope}, ETFs with higher {x_label} tended to have "
                f"{comparison} {y_label}{_period_text(df)}."
            )
    return (
        f"{conclusion}\n\n"
        f"**Pearson correlation: {coefficient:.2f}** "
        f"({strength} {direction} cross-sectional relationship; {ticker_count} ETFs). "
        "Each point is one ticker aggregated over the stated period. This is a "
        "descriptive result for the curated warehouse universe; correlation does "
        "not establish causation or population-wide statistical significance."
    )
