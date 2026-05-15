import pandas as pd
import pytest

from transform import daily_simple_returns


def test_daily_simple_returns_first_row_nan():
    prices = pd.Series([100.0, 102.0, 101.0])
    out = daily_simple_returns(prices)
    assert pd.isna(out.iloc[0])
    assert out.iloc[1] == pytest.approx(0.02)
    assert out.iloc[2] == pytest.approx(101.0 / 102.0 - 1)


def test_daily_simple_returns_empty():
    out = daily_simple_returns(pd.Series(dtype=float))
    assert len(out) == 0
