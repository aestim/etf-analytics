"""Historical custom-portfolio simulations use one comparable starting budget."""

import numpy as np
import pandas as pd
import pytest

from simulator import (
    annually_rebalanced_portfolio,
    lump_sum_portfolio,
    portfolio_strategy,
    result_metrics,
    staged_portfolio,
)


def _prices(a, b=None, start="2020-01-02"):
    index = pd.bdate_range(start, periods=len(a))
    data = {"A": np.asarray(a, dtype=float)}
    if b is not None:
        data["B"] = np.asarray(b, dtype=float)
    return pd.DataFrame(data, index=index)


def test_lump_sum_flat_portfolio_keeps_full_budget():
    result = lump_sum_portfolio(
        _prices([100, 100, 100], [50, 50, 50]),
        {"A": 0.6, "B": 0.4},
        10_000,
    )

    assert result.value.tolist() == pytest.approx([10_000] * 3)
    assert result.cash.eq(0).all()
    assert result.invested.eq(10_000).all()


def test_lump_sum_respects_custom_weights():
    result = lump_sum_portfolio(
        _prices([100, 200], [100, 50]),
        {"A": 0.75, "B": 0.25},
        1_000,
    )

    assert result.value.iloc[-1] == pytest.approx(1_625)
    assert sum(result.final_weights.values()) == pytest.approx(1.0)


def test_staged_investing_counts_reserved_money_as_cash():
    prices = _prices([100.0] * 70)
    result = staged_portfolio(prices, {"A": 1.0}, 1_200, months=3)

    assert result.value.eq(1_200).all()
    assert result.cash.iloc[0] == pytest.approx(800)
    assert result.invested.iloc[0] == pytest.approx(400)
    assert result.cash.iloc[-1] == pytest.approx(0)
    assert result.invested.iloc[-1] == pytest.approx(1_200)
    assert result.event_count == 3


def test_staged_investing_lags_lump_sum_in_steadily_rising_market():
    prices = _prices(np.linspace(100, 200, 90))

    lump = lump_sum_portfolio(prices, {"A": 1.0}, 12_000)
    staged = staged_portfolio(prices, {"A": 1.0}, 12_000, months=3)

    assert lump.value.iloc[-1] > staged.value.iloc[-1]


def test_staged_investing_uses_first_available_date_in_each_month():
    prices = _prices([100.0] * 70, start="2020-01-15")
    result = staged_portfolio(prices, {"A": 1.0}, 3_000, months=3)

    buy_dates = result.invested.diff().fillna(result.invested.iloc[0]) > 0
    actual = result.invested.index[buy_dates]
    expected = pd.DatetimeIndex(["2020-01-15", "2020-02-03", "2020-03-02"])
    assert actual.equals(expected)
    assert result.deployment_end == expected[-1]


def test_staged_investing_rejects_period_longer_than_history():
    with pytest.raises(ValueError, match="not enough monthly"):
        staged_portfolio(_prices([100.0] * 20), {"A": 1.0}, 1_000, months=6)


def test_annual_rebalancing_restores_target_weights_on_new_year():
    index = pd.to_datetime(["2020-12-30", "2020-12-31", "2021-01-04"])
    prices = pd.DataFrame(
        {"A": [100.0, 150.0, 180.0], "B": [100.0, 100.0, 90.0]},
        index=index,
    )
    result = annually_rebalanced_portfolio(
        prices,
        {"A": 0.6, "B": 0.4},
        10_000,
    )

    assert result.event_count == 1
    assert result.final_weights["A"] == pytest.approx(0.6)
    assert result.final_weights["B"] == pytest.approx(0.4)


def test_annual_rebalancing_preserves_value_at_trade_time():
    index = pd.to_datetime(["2020-12-31", "2021-01-04"])
    prices = pd.DataFrame(
        {"A": [100.0, 200.0], "B": [100.0, 50.0]},
        index=index,
    )
    result = annually_rebalanced_portfolio(
        prices,
        {"A": 0.5, "B": 0.5},
        1_000,
    )

    assert result.value.iloc[-1] == pytest.approx(1_250)


def test_configurable_strategy_matches_staged_entry_without_rebalancing():
    prices = _prices(np.linspace(100, 140, 90), np.linspace(80, 70, 90))
    weights = {"A": 0.7, "B": 0.3}

    expected = staged_portfolio(prices, weights, 12_000, months=3)
    actual = portfolio_strategy(
        prices,
        weights,
        12_000,
        deployment_months=3,
        rebalance_annually=False,
    )

    assert actual.value.equals(expected.value)
    assert actual.cash.equals(expected.cash)


def test_configurable_strategy_matches_lump_sum_with_yearly_rebalancing():
    index = pd.to_datetime(
        ["2020-12-30", "2020-12-31", "2021-01-04", "2021-01-05"]
    )
    prices = pd.DataFrame(
        {"A": [100.0, 150.0, 180.0, 170.0], "B": [100.0, 100.0, 90.0, 95.0]},
        index=index,
    )
    weights = {"A": 0.6, "B": 0.4}

    expected = annually_rebalanced_portfolio(prices, weights, 10_000)
    actual = portfolio_strategy(
        prices,
        weights,
        10_000,
        deployment_months=1,
        rebalance_annually=True,
    )

    assert actual.value.equals(expected.value)
    assert actual.final_weights == pytest.approx(expected.final_weights)


def test_staged_entry_keeps_reserved_cash_during_yearly_rebalance():
    index = pd.to_datetime(
        [
            "2020-12-15",
            "2020-12-31",
            "2021-01-04",
            "2021-02-01",
            "2021-03-01",
        ]
    )
    prices = pd.DataFrame(
        {"A": [100.0, 150.0, 180.0, 170.0, 175.0], "B": [100.0] * 5},
        index=index,
    )

    result = portfolio_strategy(
        prices,
        {"A": 0.5, "B": 0.5},
        12_000,
        deployment_months=4,
        rebalance_annually=True,
    )

    assert result.cash.loc["2021-01-04"] == pytest.approx(6_000)
    assert result.invested.loc["2021-01-04"] == pytest.approx(6_000)
    assert result.cash.iloc[-1] == pytest.approx(0)


@pytest.mark.parametrize(
    ("weights", "capital", "message"),
    [
        ({"A": 0.7}, 1_000, "sum to 1"),
        ({"A": 1.0}, 0, "positive"),
        ({"A": 0.0, "B": 1.0}, 1_000, "positive"),
    ],
)
def test_simulator_validates_budget_and_weights(weights, capital, message):
    with pytest.raises(ValueError, match=message):
        lump_sum_portfolio(_prices([100, 101], [50, 51]), weights, capital)


def test_result_metrics_use_full_account_path():
    result = lump_sum_portfolio(_prices([100, 80, 120]), {"A": 1.0}, 1_000)
    metrics = result_metrics(result)

    assert metrics["final_value"] == pytest.approx(1_200)
    assert metrics["profit"] == pytest.approx(200)
    assert metrics["total_return"] == pytest.approx(0.2)
    assert metrics["max_drawdown"] == pytest.approx(-0.2)
    assert np.isfinite(metrics["annualized_vol"])
