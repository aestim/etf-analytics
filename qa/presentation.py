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

KOREAN_METRIC_LABELS = {
    "cagr": "CAGR(연평균 복리수익률)",
    "cumulative_return": "누적수익률",
    "ytd_return": "연초 이후 수익률",
    "daily_return": "일간수익률",
    "leverage": "레버리지 배수",
    "avg_daily_volume": "평균 일일 거래량",
    "avg_daily_dollar_volume": "평균 일일 거래대금",
    "annualized_vol_30d": "30일 연환산 변동성",
    "avg_annualized_vol_30d": "평균 30일 연환산 변동성",
    "rolling_vol_30d": "30일 변동성",
    "drawdown": "고점 대비 하락률",
    "max_drawdown": "최대 낙폭",
    "adj_close": "조정 종가",
}

KOREAN_COLUMN_LABELS = {
    **KOREAN_METRIC_LABELS,
    "ticker": "티커",
    "name": "상품 이름",
    "asset_class": "자산 종류",
    "sub_class": "세부 종류",
    "price_date": "날짜",
    "period_start": "비교 시작일",
    "as_of_date": "비교 종료일",
    "observations": "사용한 날짜 수",
    "correlation": "상관계수",
    "universe_scope": "비교 대상 범위",
    "volume": "거래량",
}


def _metric_label(column: str) -> str:
    return METRIC_LABELS.get(column.lower(), column.replace("_", " "))


def _korean_metric_label(column: str) -> str:
    return KOREAN_METRIC_LABELS.get(column.lower(), column.replace("_", " "))


def _is_korean(text: str) -> bool:
    return any("\uac00" <= character <= "\ud7a3" for character in text)


def display_column_label(column: str, question: str = "") -> str:
    """Return a readable table heading in the language used by the question."""
    if _is_korean(question):
        return KOREAN_COLUMN_LABELS.get(column.lower(), column.replace("_", " "))
    label = METRIC_LABELS.get(column.lower(), column.replace("_", " ").title())
    return label if label == "CAGR" else label[:1].upper() + label[1:]


def _period_text(df: pd.DataFrame) -> str:
    if "period_start" not in df.columns or "as_of_date" not in df.columns:
        return ""
    starts = pd.to_datetime(df["period_start"], errors="coerce").dropna()
    ends = pd.to_datetime(df["as_of_date"], errors="coerce").dropna()
    if starts.empty or ends.empty:
        return ""
    return f" for {starts.min():%Y-%m-%d} to {ends.max():%Y-%m-%d}"


def _korean_period_text(df: pd.DataFrame) -> str:
    if "period_start" not in df.columns or "as_of_date" not in df.columns:
        return ""
    starts = pd.to_datetime(df["period_start"], errors="coerce").dropna()
    ends = pd.to_datetime(df["as_of_date"], errors="coerce").dropna()
    if starts.empty or ends.empty:
        return ""
    return f" ({starts.min():%Y-%m-%d}~{ends.max():%Y-%m-%d})"


def _universe_text(df: pd.DataFrame) -> tuple[str, int]:
    count = (
        int(df["ticker"].nunique(dropna=True)) if "ticker" in df.columns else len(df)
    )
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
    if _is_korean(question):
        scope_lower = scope.lower()
        if "unleveraged" in scope_lower:
            korean_scope = f"현재 비레버리지 ETF {ticker_count}개"
        elif "including leveraged" in scope_lower:
            korean_scope = f"레버리지를 포함한 현재 ETF {ticker_count}개"
        else:
            korean_scope = f"현재 데이터에 있는 ETF {ticker_count}개"

        korean_strength = {
            "very weak": "매우 약한",
            "weak": "약한",
            "moderate": "중간 정도의",
            "strong": "강한",
            "very strong": "매우 강한",
        }[strength]
        korean_direction = {
            "positive": "양의",
            "negative": "음의",
            "neutral": "중립적인",
        }[direction]

        if axes is None:
            conclusion = (
                f"{korean_scope}에서 두 지표는 {korean_direction} 관계를 보였습니다."
            )
        else:
            x_label, y_label = (_korean_metric_label(column) for column in axes)
            if magnitude < 0.2:
                conclusion = (
                    f"{korean_scope}에서 {x_label}과 {y_label} 사이의 "
                    f"직선 관계는 거의 없었습니다{_korean_period_text(df)}."
                )
            else:
                comparison = "더 높은" if coefficient > 0 else "더 낮은"
                conclusion = (
                    f"{korean_scope}에서 {x_label}이 높은 ETF일수록 "
                    f"{y_label}도 {comparison} 경향을 보였습니다"
                    f"{_korean_period_text(df)}."
                )
        return (
            f"{conclusion}\n\n"
            f"**Pearson 상관계수: {coefficient:.2f}** "
            f"({korean_strength} {korean_direction} 횡단면 관계). "
            "점 하나는 해당 기간을 집계한 ETF 하나입니다. "
            "이 결과는 현재 선정된 ETF 목록에 대한 설명일 뿐이며, "
            "상관관계는 원인·결과나 전체 ETF 시장의 법칙을 의미하지 않습니다."
        )

    if axes is None:
        conclusion = (
            f"Within {scope}, the returned metrics had a {direction} relationship."
        )
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
