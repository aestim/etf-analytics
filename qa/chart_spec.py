"""Deterministic chart selection plus validation for the Ask result table.

Chart choice is based only on the executed result contract, question and
dataframe shape. It never needs another LLM request: time series become lines,
rankings/comparisons become bars, relationship results become scatter plots,
and everything else remains a table.

Validation is still fail-safe. If a spec cannot be drawn, callers receive a
table instead of a broken chart.
"""

from __future__ import annotations

import re
from typing import Literal

import pandas as pd
from pydantic import BaseModel

ChartType = Literal["line", "bar", "scatter", "table"]


class ChartSpec(BaseModel):
    chart_type: ChartType
    x: str | None = None  # column name (not needed for table)
    y: str | None = None  # column name — must be numeric
    group_by: str | None = None  # column to color by (e.g. ticker)
    x_label: str | None = None
    y_label: str | None = None
    group_label: str | None = None
    title: str = ""


TABLE_FALLBACK_REASONS: dict[str, str] = {}  # observability: last fallback reason

MAX_BAR_CATEGORIES = 20

_RELATION_TERMS = (
    "relationship",
    "correlation",
    "correlate",
    "relation",
    "scatter",
    "tend to",
    "associated with",
    "linked to",
    "versus",
    "상관",
    "관계",
    "연관",
    "산점도",
    "비례",
    "일수록",
    "을수록",
    "할수록",
    "클수록",
)

_ENGLISH_COMPARATIVE_RELATION = re.compile(
    r"\b(?:higher|lower|larger|smaller|greater|more|less)\b"
    r".*\b(?:higher|lower|larger|smaller|greater|more|less)\b"
)

_METADATA_NUMERIC_COLUMNS = {
    "correlation",
    "count",
    "observations",
    "price_observations",
    "return_observations",
    "observation_count",
    "row_count",
    "rank",
}

_METRIC_HINTS = (
    (("레버리지", "leverage"), ("leverage",)),
    (
        ("거래대금", "거래량", "dollar volume", "volume", "liquidity"),
        ("avg_daily_dollar_volume", "avg_daily_volume", "volume"),
    ),
    (
        ("cagr", "수익", "return", "performance"),
        ("cagr", "cumulative_return", "ytd_return", "daily_return", "return"),
    ),
    (
        ("변동", "volatility", "volatile"),
        ("annualized_vol_30d", "rolling_vol_30d", "volatility"),
    ),
    (("낙폭", "drawdown"), ("drawdown",)),
    (("가격", "price"), ("adj_close", "close", "price")),
)

_METRIC_PRIORITY = (
    "cagr",
    "cumulative_return",
    "ytd_return",
    "leverage",
    "avg_daily_dollar_volume",
    "avg_daily_volume",
    "annualized_vol_30d",
    "period_annualized_volatility",
    "rolling_vol_30d",
    "drawdown",
    "period_max_drawdown",
    "daily_return",
    "adj_close",
    "close",
    "volume",
)

_CATEGORY_PRIORITY = ("ticker", "symbol", "fund", "category", "name")


def _is_metadata_numeric(column: str) -> bool:
    name = column.lower()
    return (
        name in _METADATA_NUMERIC_COLUMNS
        or name.startswith("count_")
        or name.endswith("_count")
    )


def _asks_for_relationship(question: str) -> bool:
    lowered = question.lower()
    return (
        any(term in lowered for term in _RELATION_TERMS)
        or _ENGLISH_COMPARATIVE_RELATION.search(lowered) is not None
    )


def _has_correlation_result(df: pd.DataFrame) -> bool:
    """Recognize the SQL relationship-result contract independent of wording."""
    return any(str(column).lower() == "correlation" for column in df.columns)


def metric_columns(question: str, df: pd.DataFrame) -> list[str]:
    """Return drawable numeric metrics ordered by their mention in the question."""
    candidates = [
        column
        for column in df.columns
        if pd.api.types.is_numeric_dtype(df[column])
        and not pd.api.types.is_bool_dtype(df[column])
        and not _is_metadata_numeric(str(column))
    ]
    if not candidates:
        return []

    lowered_question = question.lower()
    ordered: list[str] = []
    matched_hints = []
    for terms, preferred_names in _METRIC_HINTS:
        positions = [
            lowered_question.find(term) for term in terms if term in lowered_question
        ]
        if positions:
            matched_hints.append((min(positions), preferred_names))
    for _, preferred_names in sorted(matched_hints, key=lambda match: match[0]):
        for preferred in preferred_names:
            ordered.extend(
                column
                for column in candidates
                if preferred in str(column).lower() and column not in ordered
            )
    for preferred in _METRIC_PRIORITY:
        ordered.extend(
            column
            for column in candidates
            if preferred in str(column).lower() and column not in ordered
        )
    ordered.extend(column for column in candidates if column not in ordered)
    return ordered


def relationship_axes(question: str, df: pd.DataFrame) -> tuple[str, str] | None:
    """Return the two relationship metrics, excluding counts and coefficients."""
    numeric = metric_columns(question, df)
    if len(numeric) < 2:
        return None
    return str(numeric[0]), str(numeric[1])


def _date_columns(df: pd.DataFrame) -> list[str]:
    date_columns: list[str] = []
    for column in df.columns:
        name = str(column).lower()
        looks_like_date = (
            name == "date"
            or "date" in name
            or name in {"day", "week", "month", "quarter", "year"}
        )
        if not looks_like_date and not pd.api.types.is_datetime64_any_dtype(
            df[column].dtype
        ):
            continue
        non_null = df[column].dropna()
        if non_null.empty:
            continue
        parsed = pd.to_datetime(non_null, errors="coerce")
        if parsed.notna().mean() >= 0.8 and parsed.nunique() > 1:
            date_columns.append(column)
    return date_columns


def _category_column(df: pd.DataFrame, date_columns: list[str]) -> str | None:
    candidates = []
    for column in df.columns:
        if column in date_columns or pd.api.types.is_numeric_dtype(df[column]):
            continue
        unique = df[column].nunique(dropna=True)
        if 2 <= unique <= MAX_BAR_CATEGORIES:
            candidates.append(column)
    for preferred in _CATEGORY_PRIORITY:
        for column in candidates:
            if str(column).lower() == preferred:
                return column
    return candidates[0] if candidates else None


_KOREAN_LABELS = {
    "ticker": "티커",
    "cagr": "연평균 복리수익률",
    "cumulative_return": "누적수익률",
    "ytd_return": "연초 이후 수익률",
    "daily_return": "일간수익률",
    "leverage": "레버리지 배수",
    "avg_daily_volume": "평균 일일 거래량",
    "avg_daily_dollar_volume": "평균 일일 거래대금",
    "annualized_vol_30d": "30일 연환산 변동성",
    "avg_annualized_vol_30d": "평균 30일 연환산 변동성",
    "period_annualized_volatility": "선택 기간 연환산 변동성",
    "rolling_vol_30d": "30일 가격 변동",
    "drawdown": "고점 대비 하락률",
    "max_drawdown": "최대 낙폭",
    "period_max_drawdown": "선택 기간 최대 낙폭",
    "adj_close": "배당 반영 가격",
}

_ENGLISH_LABELS = {
    "ticker": "ETF",
    "cagr": "CAGR",
    "cumulative_return": "Total Return",
    "ytd_return": "Year-to-Date Return",
    "daily_return": "Daily Return",
    "leverage": "Leverage",
    "avg_daily_volume": "Average Daily Share Volume",
    "avg_daily_dollar_volume": "Average Daily Trading Value",
    "annualized_vol_30d": "Annualized 30-Day Price Swings",
    "avg_annualized_vol_30d": "Average Annualized 30-Day Price Swings",
    "period_annualized_volatility": "Annualized Volatility over the Selected Period",
    "rolling_vol_30d": "30-Day Price Swings",
    "drawdown": "Drop from a Previous High",
    "max_drawdown": "Largest Drop",
    "period_max_drawdown": "Largest Drop within the Selected Period",
    "adj_close": "Dividend-Adjusted Price",
}


def _is_korean(text: str) -> bool:
    return any("\uac00" <= character <= "\ud7a3" for character in text)


def _label(column: str, question: str = "") -> str:
    if _is_korean(question):
        return _KOREAN_LABELS.get(column.lower(), str(column).replace("_", " "))
    return _ENGLISH_LABELS.get(
        column.lower(), str(column).replace("_", " ").strip().title()
    )


def _period_suffix(df: pd.DataFrame, question: str = "") -> str:
    end_column = "period_end" if "period_end" in df.columns else "as_of_date"
    if "period_start" not in df.columns or end_column not in df.columns:
        return ""
    starts = pd.to_datetime(df["period_start"], errors="coerce").dropna()
    ends = pd.to_datetime(df[end_column], errors="coerce").dropna()
    if starts.empty or ends.empty:
        return ""
    separator = "~" if _is_korean(question) else " to "
    return f" ({starts.min():%Y-%m-%d}{separator}{ends.max():%Y-%m-%d})"


def auto_chart_spec(question: str, df: pd.DataFrame) -> ChartSpec:
    """Choose a useful visualization without an LLM call.

    A chart is only selected when the dataframe has at least two rows and its
    structure clearly supports one. Exact/single-value answers stay tables.
    """
    if df is None or len(df) < 2:
        return ChartSpec(
            chart_type="table", title="결과" if _is_korean(question) else "Result"
        )

    numeric = metric_columns(question, df)
    if not numeric:
        return ChartSpec(
            chart_type="table", title="결과" if _is_korean(question) else "Result"
        )

    relationship_result = _has_correlation_result(df)
    relationship_wording = _asks_for_relationship(question)
    if (relationship_result or relationship_wording) and len(numeric) >= 2:
        x, y = numeric[:2]
        title = (
            f"{_label(x, question)}과 {_label(y, question)}의 관계"
            f"{_period_suffix(df, question)}"
            if _is_korean(question)
            else f"{_label(y)} vs {_label(x)}{_period_suffix(df)}"
        )
        return ChartSpec(
            chart_type="scatter",
            x=x,
            y=y,
            group_by="ticker" if "ticker" in df.columns else None,
            x_label=_label(x, question),
            y_label=_label(y, question),
            group_label=_label("ticker", question),
            title=title,
        )

    dates = _date_columns(df)
    if dates:
        y = numeric[0]
        title = (
            f"{_label(y, question)} 추이{_period_suffix(df, question)}"
            if _is_korean(question)
            else f"{_label(y)} over time{_period_suffix(df)}"
        )
        return ChartSpec(
            chart_type="line",
            x=dates[0],
            y=y,
            group_by=(
                "ticker"
                if "ticker" in df.columns and df["ticker"].nunique(dropna=True) > 1
                else None
            ),
            x_label="날짜" if _is_korean(question) else "Date",
            y_label=_label(y, question),
            group_label=_label("ticker", question),
            title=title,
        )

    category = _category_column(df, dates)
    if category:
        y = numeric[0]
        title = (
            f"{_label(category, question)}별 {_label(y, question)}"
            f"{_period_suffix(df, question)}"
            if _is_korean(question)
            else f"{_label(y)} by {_label(category)}{_period_suffix(df)}"
        )
        return ChartSpec(
            chart_type="bar",
            x=category,
            y=y,
            x_label=_label(category, question),
            y_label=_label(y, question),
            title=title,
        )

    return ChartSpec(
        chart_type="table", title="결과" if _is_korean(question) else "Result"
    )


def validate_spec(spec: ChartSpec, df: pd.DataFrame) -> ChartSpec:
    """Check the spec is drawable against df — otherwise fall back to a table.

    Fallback triggers: x/y missing, unknown column, non-numeric y.
    If only group_by is wrong, keep the chart and just drop group_by.
    """

    def fallback(reason: str) -> ChartSpec:
        TABLE_FALLBACK_REASONS["last"] = reason
        return ChartSpec(chart_type="table", title=spec.title)

    TABLE_FALLBACK_REASONS.pop("last", None)  # clear the previous call's reason
    if spec.chart_type == "table":
        return spec
    cols = set(df.columns)
    if not spec.x or not spec.y:
        return fallback("x/y not specified")
    if spec.x not in cols or spec.y not in cols:
        return fallback(f"unknown column: {spec.x if spec.x not in cols else spec.y}")
    if not pd.api.types.is_numeric_dtype(df[spec.y]):
        return fallback(f"y is not numeric: {spec.y}")
    if spec.chart_type == "scatter" and not pd.api.types.is_numeric_dtype(df[spec.x]):
        return fallback(f"scatter x is not numeric: {spec.x}")
    if spec.group_by and spec.group_by not in cols:
        spec = spec.model_copy(update={"group_by": None})
    return spec
