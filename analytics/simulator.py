"""Pure historical simulations for a user-defined ETF portfolio.

The simulator tracks the full account value, including cash deliberately kept
aside for staged investing.  This makes lump-sum, staged-entry and rebalancing
results comparable from the same starting budget.

Historical adjusted prices already reflect each ETF's operating expenses,
dividends and stock splits.  Trading fees, taxes, slippage, cash interest and
currency movements are intentionally excluded.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class SimulationResult:
    """One complete account-value path and its execution details."""

    value: pd.Series
    cash: pd.Series
    invested: pd.Series
    event_count: int
    deployment_end: pd.Timestamp
    final_weights: dict[str, float]


def _prepare(
    prices: pd.DataFrame,
    weights: dict[str, float],
    total_capital: float,
) -> tuple[pd.DataFrame, pd.Series]:
    if total_capital <= 0:
        raise ValueError("total_capital must be positive")
    if not weights:
        raise ValueError("at least one portfolio weight is required")
    if any(weight <= 0 for weight in weights.values()):
        raise ValueError("portfolio weights must be positive")
    if not np.isclose(sum(weights.values()), 1.0, atol=1e-8):
        raise ValueError("portfolio weights must sum to 1")

    missing = set(weights) - set(prices.columns)
    if missing:
        raise ValueError(f"missing price columns: {', '.join(sorted(missing))}")

    clean = prices[list(weights)].copy()
    clean.index = pd.to_datetime(clean.index)
    clean = clean.sort_index()
    clean = clean[~clean.index.duplicated(keep="last")].dropna()
    if clean.empty:
        raise ValueError("no common price history is available")
    if (clean <= 0).any().any():
        raise ValueError("prices must be positive")

    return clean.astype(float), pd.Series(weights, dtype=float)


def _final_weights(prices: pd.Series, shares: pd.Series) -> dict[str, float]:
    holdings = prices * shares
    total = float(holdings.sum())
    if total <= 0:
        return {ticker: 0.0 for ticker in holdings.index}
    return {ticker: float(value / total) for ticker, value in holdings.items()}


def lump_sum_portfolio(
    prices: pd.DataFrame,
    weights: dict[str, float],
    total_capital: float,
) -> SimulationResult:
    """Invest the full budget at target weights on the first trading date."""
    clean, target = _prepare(prices, weights, total_capital)
    shares = total_capital * target / clean.iloc[0]
    value = clean.mul(shares).sum(axis=1).rename("value")
    cash = pd.Series(0.0, index=clean.index, name="cash")
    invested = pd.Series(total_capital, index=clean.index, name="invested")
    return SimulationResult(
        value=value,
        cash=cash,
        invested=invested,
        event_count=1,
        deployment_end=clean.index[0],
        final_weights=_final_weights(clean.iloc[-1], shares),
    )


def staged_portfolio(
    prices: pd.DataFrame,
    weights: dict[str, float],
    total_capital: float,
    months: int,
) -> SimulationResult:
    """Invest equal monthly slices while counting undeployed money as cash."""
    clean, target = _prepare(prices, weights, total_capital)
    if months <= 0:
        raise ValueError("months must be positive")

    month_periods = clean.index.to_period("M")
    first_in_month = ~month_periods.duplicated()
    available_dates = clean.index[first_in_month]
    if len(available_dates) < months:
        raise ValueError("not enough monthly observations for the deployment period")
    buy_dates = available_dates[:months]
    buy_set = set(buy_dates)

    shares = pd.Series(0.0, index=target.index)
    remaining_cash = float(total_capital)
    installment = total_capital / months
    values: list[float] = []
    cash_values: list[float] = []
    invested_values: list[float] = []
    buy_number = 0

    for date, row in clean.iterrows():
        if date in buy_set:
            buy_number += 1
            amount = remaining_cash if buy_number == months else installment
            shares += amount * target / row
            remaining_cash = max(0.0, remaining_cash - amount)
        values.append(float(remaining_cash + (shares * row).sum()))
        cash_values.append(remaining_cash)
        invested_values.append(total_capital - remaining_cash)

    return SimulationResult(
        value=pd.Series(values, index=clean.index, name="value"),
        cash=pd.Series(cash_values, index=clean.index, name="cash"),
        invested=pd.Series(invested_values, index=clean.index, name="invested"),
        event_count=months,
        deployment_end=buy_dates[-1],
        final_weights=_final_weights(clean.iloc[-1], shares),
    )


def annually_rebalanced_portfolio(
    prices: pd.DataFrame,
    weights: dict[str, float],
    total_capital: float,
) -> SimulationResult:
    """Invest on day one and restore target weights each new calendar year."""
    clean, target = _prepare(prices, weights, total_capital)
    shares = total_capital * target / clean.iloc[0]
    values: list[float] = []
    rebalance_count = 0
    previous_year = clean.index[0].year

    for date, row in clean.iterrows():
        if date.year != previous_year:
            account_value = float((shares * row).sum())
            shares = account_value * target / row
            rebalance_count += 1
            previous_year = date.year
        values.append(float((shares * row).sum()))

    value = pd.Series(values, index=clean.index, name="value")
    cash = pd.Series(0.0, index=clean.index, name="cash")
    invested = pd.Series(total_capital, index=clean.index, name="invested")
    return SimulationResult(
        value=value,
        cash=cash,
        invested=invested,
        event_count=rebalance_count,
        deployment_end=clean.index[0],
        final_weights=_final_weights(clean.iloc[-1], shares),
    )


def result_metrics(result: SimulationResult) -> dict[str, float]:
    """Beginner-facing account metrics based on the full value path."""
    value = result.value.dropna()
    initial = float(value.iloc[0])
    final = float(value.iloc[-1])
    returns = value.pct_change().dropna()
    annualized_vol = (
        float(returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
        if len(returns) >= 2
        else float("nan")
    )
    drawdown = value / value.cummax() - 1.0
    return {
        "final_value": final,
        "profit": final - initial,
        "total_return": final / initial - 1.0,
        "max_drawdown": float(drawdown.min()),
        "annualized_vol": annualized_vol,
    }

