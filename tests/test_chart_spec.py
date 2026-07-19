"""qa/chart_spec.py + qa/render.py — 검증·폴백·렌더러 4종 (LLM·DB 불필요)."""

import pandas as pd
import pytest

from chart_spec import ChartSpec, validate_spec
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


# --- validate_spec: 통과 -----------------------------------------------------


def test_valid_line_spec_passes(df):
    spec = ChartSpec(chart_type="line", x="price_date", y="rolling_vol_30d", group_by="ticker")
    assert validate_spec(spec, df) == spec


def test_bad_group_by_is_dropped_but_chart_survives(df):
    spec = ChartSpec(chart_type="line", x="price_date", y="rolling_vol_30d", group_by="없는컬럼")
    out = validate_spec(spec, df)
    assert out.chart_type == "line" and out.group_by is None


# --- validate_spec: 표 폴백 --------------------------------------------------


@pytest.mark.parametrize(
    "spec",
    [
        ChartSpec(chart_type="line", x="없는컬럼", y="rolling_vol_30d"),  # 없는 x
        ChartSpec(chart_type="line", x="price_date", y="ticker"),  # y 비수치
        ChartSpec(chart_type="bar", x=None, y=None),  # 미지정
    ],
    ids=["missing-col", "non-numeric-y", "unspecified"],
)
def test_invalid_specs_fall_back_to_table(spec, df):
    assert validate_spec(spec, df).chart_type == "table"


# --- render: 4종 -------------------------------------------------------------


@pytest.mark.parametrize("chart_type", ["line", "bar", "scatter"])
def test_renderers_return_figure(chart_type, df):
    spec = ChartSpec(chart_type=chart_type, x="price_date", y="rolling_vol_30d", title="t")
    fig = render(spec, df)
    assert fig is not None and fig.data  # plotly Figure에 trace가 있음


def test_table_spec_renders_none(df):
    assert render(ChartSpec(chart_type="table"), df) is None
