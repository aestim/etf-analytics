"""qa/chart_spec.py + qa/render.py — validation, fallback, four renderers (no LLM/DB)."""

import pandas as pd
import pytest

from chart_spec import ChartSpec, auto_chart_spec, validate_spec
from render import render


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "price_date": pd.bdate_range("2024-01-01", periods=6),
            "ticker": ["TLT", "TLT", "TLT", "SPY", "SPY", "SPY"],
            "rolling_vol_30d": [0.01, 0.012, 0.011, 0.008, 0.009, 0.01],
        }
    )


# --- validate_spec: passes --------------------------------------------------


def test_valid_line_spec_passes(df):
    spec = ChartSpec(chart_type="line", x="price_date", y="rolling_vol_30d", group_by="ticker")
    assert validate_spec(spec, df) == spec


def test_bad_group_by_is_dropped_but_chart_survives(df):
    spec = ChartSpec(chart_type="line", x="price_date", y="rolling_vol_30d", group_by="no_such_col")
    out = validate_spec(spec, df)
    assert out.chart_type == "line" and out.group_by is None


def test_scatter_with_non_numeric_x_falls_back_to_table(df):
    spec = ChartSpec(chart_type="scatter", x="ticker", y="rolling_vol_30d")
    assert validate_spec(spec, df).chart_type == "table"


# --- validate_spec: table fallback ------------------------------------------


@pytest.mark.parametrize(
    "spec",
    [
        ChartSpec(chart_type="line", x="no_such_col", y="rolling_vol_30d"),  # unknown x
        ChartSpec(chart_type="line", x="price_date", y="ticker"),  # non-numeric y
        ChartSpec(chart_type="bar", x=None, y=None),  # unspecified
    ],
    ids=["missing-col", "non-numeric-y", "unspecified"],
)
def test_invalid_specs_fall_back_to_table(spec, df):
    assert validate_spec(spec, df).chart_type == "table"


# --- render: all four -------------------------------------------------------


@pytest.mark.parametrize("chart_type", ["line", "bar", "scatter"])
def test_renderers_return_figure(chart_type, df):
    spec = ChartSpec(chart_type=chart_type, x="price_date", y="rolling_vol_30d", title="t")
    fig = render(spec, df)
    assert fig is not None and fig.data  # the plotly Figure has traces


def test_table_spec_renders_none(df):
    assert render(ChartSpec(chart_type="table"), df) is None


def test_return_chart_uses_percentage_axis():
    returns = pd.DataFrame({"ticker": ["SPY", "QQQ"], "cumulative_return": [0.12, 0.2]})
    fig = render(
        ChartSpec(chart_type="bar", x="ticker", y="cumulative_return"),
        returns,
    )
    assert fig.layout.yaxis.tickformat == ".1%"


# --- deterministic auto selection -----------------------------------------


def test_auto_selects_line_for_time_series(df):
    spec = auto_chart_spec("지난 기간 변동성을 보여줘", df)
    assert (spec.chart_type, spec.x, spec.y, spec.group_by) == (
        "line",
        "price_date",
        "rolling_vol_30d",
        "ticker",
    )


def test_auto_selects_bar_for_return_ranking_and_ignores_observations():
    ranking = pd.DataFrame(
        {
            "ticker": ["TQQQ", "QLD", "IWM"],
            "period_start": ["2025-07-22"] * 3,
            "as_of_date": ["2026-07-22"] * 3,
            "observations": [251, 251, 250],
            "cumulative_return": [0.57, 0.42, 0.33],
        }
    )
    spec = auto_chart_spec("가장 수익률 높은 ETF 3개", ranking)
    assert (spec.chart_type, spec.x, spec.y) == ("bar", "ticker", "cumulative_return")
    assert "2025-07-22 to 2026-07-22" in spec.title


def test_auto_selects_scatter_only_for_explicit_relationship_question():
    relationship = pd.DataFrame(
        {
            "ticker": ["SPY", "QQQ", "TLT"],
            "cumulative_return": [0.12, 0.18, -0.02],
            "annualized_vol_30d": [0.16, 0.22, 0.09],
        }
    )
    spec = auto_chart_spec("수익률과 변동성의 관계를 보여줘", relationship)
    assert spec.chart_type == "scatter"
    assert {spec.x, spec.y} == {"cumulative_return", "annualized_vol_30d"}


def test_auto_understands_korean_comparative_relationship_question():
    relationship = pd.DataFrame(
        {
            "ticker": ["SPY", "QQQ", "TLT"],
            "cumulative_return": [0.12, 0.18, -0.02],
            "max_drawdown": [-0.09, -0.14, -0.17],
        }
    )

    spec = auto_chart_spec("수익률이 높은 ETF일수록 최대 낙폭도 큰가?", relationship)
    fig = render(spec, relationship)

    assert (spec.chart_type, spec.x, spec.y) == (
        "scatter",
        "cumulative_return",
        "max_drawdown",
    )
    assert fig.layout.xaxis.tickformat == ".1%"
    assert fig.layout.yaxis.tickformat == ".1%"


@pytest.mark.parametrize(
    ("question", "x", "y"),
    [
        (
            "레버리지 배수와 연환산 변동성의 상관관계는?",
            "leverage",
            "avg_annualized_vol_30d",
        ),
        (
            "거래량과 변동성 사이에 관계가 있나?",
            "avg_daily_volume",
            "avg_annualized_vol_30d",
        ),
    ],
)
def test_auto_relationship_axes_follow_metric_order_and_ignore_coefficient(
    question, x, y
):
    relationship = pd.DataFrame(
        {
            "ticker": ["SPY", "QQQ", "TLT"],
            "leverage": [1.0, 2.0, 1.0],
            "avg_daily_volume": [10_000.0, 8_000.0, 3_000.0],
            "avg_annualized_vol_30d": [0.16, 0.22, 0.09],
            "correlation": [0.5, 0.5, 0.5],
            "observations": [250, 250, 250],
        }
    )

    spec = auto_chart_spec(question, relationship)

    assert (spec.chart_type, spec.x, spec.y) == ("scatter", x, y)


def test_auto_keeps_single_value_as_table():
    result = pd.DataFrame({"ticker": ["SPY"], "adj_close": [650.0]})
    assert auto_chart_spec("SPY 최신 가격", result).chart_type == "table"


def test_auto_keeps_plain_list_as_table():
    result = pd.DataFrame({"ticker": ["SPY", "QQQ", "TLT"]})
    assert auto_chart_spec("티커 목록", result).chart_type == "table"


def test_auto_keeps_large_category_result_as_table():
    result = pd.DataFrame(
        {"ticker": [f"ETF{i}" for i in range(21)], "cumulative_return": range(21)}
    )
    assert auto_chart_spec("ETF 수익률", result).chart_type == "table"
