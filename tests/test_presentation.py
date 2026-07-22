"""Ask metric formatting remains semantic rather than query-specific."""

import pandas as pd
import pytest

from presentation import (
    correlation_summary,
    display_column_label,
    is_dollar_metric,
    is_percent_metric,
)


@pytest.mark.parametrize(
    "column",
    [
        "daily_return",
        "cumulative_return",
        "ytd_return",
        "drawdown",
        "annualized_vol_30d",
    ],
)
def test_percent_metrics(column):
    assert is_percent_metric(column)


@pytest.mark.parametrize(
    "column", ["ticker", "adj_close", "observations", "as_of_date"]
)
def test_non_percent_columns(column):
    assert not is_percent_metric(column)


def test_dollar_volume_metric():
    assert is_dollar_metric("avg_daily_dollar_volume")
    assert not is_dollar_metric("avg_daily_volume")


def test_table_column_labels_follow_question_language():
    assert (
        display_column_label("cumulative_return", "최근 1년 수익률은?") == "누적수익률"
    )
    assert display_column_label("period_start", "최근 1년 수익률은?") == "비교 시작일"
    assert display_column_label("cumulative_return", "Show returns") == "Cumulative return"


@pytest.mark.parametrize(
    ("coefficient", "description"),
    [
        (0.1, "very weak positive"),
        (-0.45, "moderate negative"),
        (0.81, "very strong positive"),
    ],
)
def test_correlation_summary_uses_executed_value(coefficient, description):
    summary = correlation_summary(pd.DataFrame({"correlation": [coefficient] * 3}))
    assert f"{coefficient:.2f}" in summary
    assert description in summary
    assert "does not establish causation" in summary


def test_correlation_summary_is_conclusion_first_and_scoped():
    frame = pd.DataFrame(
        {
            "ticker": ["SPY", "QQQ", "IWM"],
            "cumulative_return": [0.1, 0.2, 0.15],
            "avg_annualized_vol_30d": [0.12, 0.18, 0.2],
            "period_start": ["2025-07-22"] * 3,
            "as_of_date": ["2026-07-22"] * 3,
            "correlation": [0.93] * 3,
        }
    )

    summary = correlation_summary(
        frame,
        "How do return performance and volatility move together across ETFs?",
    )

    assert summary.startswith("Within the current 3-ETF warehouse universe")
    assert "higher cumulative return" in summary
    assert "higher average annualized 30-day volatility" in summary
    assert "2025-07-22 to 2026-07-22" in summary
    assert "cross-sectional relationship; 3 ETFs" in summary
    assert "population-wide statistical significance" in summary


def test_correlation_summary_uses_executed_universe_scope():
    frame = pd.DataFrame(
        {
            "ticker": ["SPY", "QQQ"],
            "cagr": [0.1, 0.2],
            "avg_annualized_vol_30d": [0.12, 0.18],
            "universe_scope": ["the current unleveraged ETF subset (leverage = 1)"] * 2,
            "correlation": [0.7, 0.7],
        }
    )

    summary = correlation_summary(frame, "CAGR versus volatility")

    assert summary.startswith("Within the current unleveraged ETF subset")
    assert "2 ETFs" in summary


def test_correlation_summary_matches_korean_question_language():
    frame = pd.DataFrame(
        {
            "ticker": ["SPY", "QQQ"],
            "cumulative_return": [0.1, 0.2],
            "max_drawdown": [-0.1, -0.3],
            "period_start": ["2025-07-22"] * 2,
            "as_of_date": ["2026-07-22"] * 2,
            "correlation": [0.72, 0.72],
        }
    )

    summary = correlation_summary(frame, "수익률이 높을수록 최대 낙폭도 큰가?")

    assert summary.startswith("현재 데이터에 있는 ETF 2개")
    assert "Pearson 상관계수: 0.72" in summary
    assert "상관관계는 원인·결과" in summary


def test_correlation_summary_ignores_missing_coefficient():
    assert correlation_summary(pd.DataFrame({"ticker": ["SPY"]})) == ""
