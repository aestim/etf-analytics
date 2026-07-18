"""Tests for analytics/strategies.py using small synthetic price series."""

import numpy as np
import pandas as pd
import pytest

from strategies import (
    cagr,
    dca,
    infinite_buy,
    lump_sum,
    max_drawdown,
    rebalance,
    sharpe,
    sma_trend,
    summary_metrics,
)


def _series(values):
    idx = pd.bdate_range("2020-01-01", periods=len(values))
    return pd.Series(values, index=idx, dtype=float)


# --- lump_sum ---------------------------------------------------------------


def test_lump_sum_doubling():
    eq = lump_sum(_series([100, 150, 200]))
    assert eq.iloc[0] == pytest.approx(1.0)
    assert eq.iloc[-1] == pytest.approx(2.0)


# --- dca --------------------------------------------------------------------


def test_dca_flat_price_breaks_even():
    eq = dca(_series([100.0] * 100), every=21)
    assert np.allclose(eq.values, 1.0)


def test_dca_rising_market_lags_lump_sum():
    prices = _series(np.linspace(100, 200, 100))
    assert dca(prices, every=21).iloc[-1] < lump_sum(prices).iloc[-1]


# --- rebalance --------------------------------------------------------------


def test_rebalance_identical_assets_equals_lump_sum():
    prices = pd.DataFrame(
        {"A": np.linspace(100, 180, 120), "B": np.linspace(100, 180, 120)},
        index=pd.bdate_range("2020-01-01", periods=120),
    )
    eq = rebalance(prices, {"A": 0.6, "B": 0.4}, every=21)
    assert eq.iloc[-1] == pytest.approx(lump_sum(prices["A"]).iloc[-1])


def test_rebalance_starts_at_one():
    prices = pd.DataFrame(
        {"A": [100.0, 110.0], "B": [50.0, 45.0]},
        index=pd.bdate_range("2020-01-01", periods=2),
    )
    eq = rebalance(prices, {"A": 0.5, "B": 0.5})
    assert eq.iloc[0] == pytest.approx(1.0)


# --- sma_trend --------------------------------------------------------------


def test_sma_trend_falling_market_stays_in_cash():
    prices = _series(np.linspace(200, 100, 300))
    eq = sma_trend(prices, window=50)
    # price is always below its SMA in a monotonic decline -> never invested
    assert eq.iloc[-1] == pytest.approx(1.0)


def test_sma_trend_no_lookahead():
    # flat during warmup, then a jump; entry must happen the bar AFTER the cross
    values = [100.0] * 60 + [150.0, 151.0, 152.0]
    eq = sma_trend(_series(values), window=50)
    # the +50% jump day (first close above SMA) must NOT be captured
    assert eq.iloc[60] == pytest.approx(1.0)
    # but the following days' returns are captured
    assert eq.iloc[62] > 1.0


# --- infinite_buy -----------------------------------------------------------


def test_infinite_buy_flat_price_breaks_even():
    eq = infinite_buy(_series([100.0] * 80), n_splits=40)
    assert np.allclose(eq.values, 1.0)


def test_infinite_buy_takes_profit_on_jump():
    values = [100.0] * 10 + [200.0] + [200.0] * 5
    eq = infinite_buy(_series(values), n_splits=40, take_profit=0.10)
    # 10 splits bought at 100, doubled -> equity above break-even
    assert eq.iloc[-1] > 1.05


def test_infinite_buy_cash_never_negative():
    rng = np.random.default_rng(0)
    prices = _series(100 * np.exp(np.cumsum(rng.normal(0, 0.03, 200))))
    eq = infinite_buy(prices, n_splits=40)
    assert (eq > 0).all()


# --- metrics ----------------------------------------------------------------


def test_max_drawdown_known_value():
    assert max_drawdown(_series([1.0, 0.5, 1.0])) == pytest.approx(-0.5)


def test_cagr_two_years():
    n = 2 * 252 + 1
    eq = _series(np.linspace(1.0, 1.21, n))
    assert cagr(eq) == pytest.approx(0.10, abs=1e-3)


def test_sharpe_flat_is_nan():
    assert np.isnan(sharpe(_series([1.0] * 50)))


def test_summary_metrics_keys():
    m = summary_metrics(_series(np.linspace(1.0, 1.5, 300)))
    assert set(m) == {"cagr", "ann_vol", "max_drawdown", "sharpe"}
