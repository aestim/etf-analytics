"""
Pure, deterministic backtests of representative investment strategies
over daily adjusted-close price series.

Educational illustrations for the dashboard's Strategy Lab page —
NOT investment advice.

Conventions
-----------
* Input: ``pd.Series`` of adj_close indexed by sorted trading dates
  (or a DataFrame of such columns for multi-asset strategies).
* Output: equity curve as ``pd.Series`` — portfolio value divided by
  total invested capital at each date (1.0 = break-even).
* No look-ahead: trading signals always act on the *next* bar.

Covered by tests/test_strategies.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


def lump_sum(prices: pd.Series) -> pd.Series:
    """Buy-and-hold: invest everything on day one."""
    prices = prices.dropna()
    return prices / prices.iloc[0]


def dca(prices: pd.Series, every: int = 21) -> pd.Series:
    """Dollar-cost averaging: invest 1 unit every `every` trading days.

    Equity = market value of holdings / total invested so far.
    """
    prices = prices.dropna()
    shares = 0.0
    invested = 0.0
    values = []
    for i, price in enumerate(prices):
        if i % every == 0:
            shares += 1.0 / price
            invested += 1.0
        values.append(shares * price / invested)
    return pd.Series(values, index=prices.index)


def rebalance(prices: pd.DataFrame, weights: dict[str, float], every: int = 63) -> pd.Series:
    """Fixed-weight portfolio rebalanced every `every` trading days (~quarterly).

    `weights` maps column name -> target weight (should sum to 1).
    """
    prices = prices[list(weights)].dropna()
    value = 1.0
    holdings: dict[str, float] | None = None
    values = []
    for i, (_, row) in enumerate(prices.iterrows()):
        if holdings is not None:
            value = sum(shares * row[t] for t, shares in holdings.items())
        if holdings is None or i % every == 0:
            holdings = {t: value * w / row[t] for t, w in weights.items()}
        values.append(value)
    return pd.Series(values, index=prices.index)


def sma_trend(risk: pd.Series, window: int = 200, park: pd.Series | None = None) -> pd.Series:
    """Trend following: hold `risk` while it closes above its SMA, else park.

    `park=None` parks in cash at 0% (simplification). The signal is lagged
    one day so the strategy trades on the close *after* the crossover.
    """
    risk = risk.dropna()
    sma = risk.rolling(window).mean()
    in_risk = (risk > sma).shift(1, fill_value=False)
    risk_ret = risk.pct_change().fillna(0.0)
    if park is None:
        park_ret = pd.Series(0.0, index=risk.index)
    else:
        park_ret = park.reindex(risk.index).pct_change().fillna(0.0)
    rets = np.where(in_risk, risk_ret, park_ret)
    return (1.0 + pd.Series(rets, index=risk.index)).cumprod()


def infinite_buy(prices: pd.Series, n_splits: int = 40, take_profit: float = 0.10) -> pd.Series:
    """Simplified "infinite buying" style cycle strategy.

    Capital is split into `n_splits` equal parts. Each day one part is
    invested (while cash remains). When the position gains `take_profit`
    versus its average cost, everything is sold and the cycle restarts.
    Idle cash earns 0%.

    This is a stylized illustration of the popular retail strategy for
    leveraged ETFs — the real method has more rules (LOC orders, halves,
    variants). Deliberately simplified and deterministic for testing.
    """
    prices = prices.dropna()
    per_buy = 1.0 / n_splits
    cash = 1.0
    shares = 0.0
    cost = 0.0
    values = []
    for price in prices:
        # 1) take-profit check on the existing position
        if shares > 0 and shares * price >= cost * (1.0 + take_profit):
            cash += shares * price
            shares = 0.0
            cost = 0.0
        # 2) daily split buy while cash lasts
        if cash >= per_buy:
            shares += per_buy / price
            cash -= per_buy
            cost += per_buy
        values.append(cash + shares * price)
    return pd.Series(values, index=prices.index)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def cagr(equity: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    equity = equity.dropna()
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return float("nan")
    years = (len(equity) - 1) / periods_per_year
    total = equity.iloc[-1] / equity.iloc[0]
    if total <= 0 or years <= 0:
        return float("nan")
    return float(total ** (1.0 / years) - 1.0)


def annualized_vol(equity: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    rets = equity.dropna().pct_change().dropna()
    if len(rets) < 2:
        return float("nan")
    return float(rets.std() * np.sqrt(periods_per_year))


def max_drawdown(equity: pd.Series) -> float:
    equity = equity.dropna()
    if equity.empty:
        return float("nan")
    return float(((equity / equity.cummax()) - 1.0).min())


def sharpe(equity: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    """Annualized Sharpe ratio with risk-free rate assumed 0."""
    rets = equity.dropna().pct_change().dropna()
    if len(rets) < 2 or rets.std() == 0:
        return float("nan")
    return float(rets.mean() / rets.std() * np.sqrt(periods_per_year))


def summary_metrics(equity: pd.Series) -> dict[str, float]:
    return {
        "cagr": cagr(equity),
        "ann_vol": annualized_vol(equity),
        "max_drawdown": max_drawdown(equity),
        "sharpe": sharpe(equity),
    }
