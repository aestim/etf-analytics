import pandas as pd
import pytest

from transform import drawdown_series, max_drawdown, rolling_volatility


def test_drawdown_at_peak_is_zero():
    prices = pd.Series([100.0, 110.0, 120.0])
    dd = drawdown_series(prices)
    assert dd.iloc[-1] == pytest.approx(0.0)


def test_max_drawdown_after_decline():
    prices = pd.Series([100.0, 120.0, 90.0])
    assert max_drawdown(prices) == pytest.approx(90.0 / 120.0 - 1)


def test_rolling_volatility_requires_window():
    returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.01] * 10)
    vol = rolling_volatility(returns, window=30)
    assert pd.isna(vol.iloc[28])
    assert not pd.isna(vol.iloc[29])
