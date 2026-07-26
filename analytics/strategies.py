"""
Pure, deterministic historical simulations of representative investment rules
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
    is_buy = pd.Series(np.arange(len(prices)) % every == 0, index=prices.index)
    shares = (is_buy / prices).cumsum()  # 1 unit buys 1/price shares on buy days
    invested = is_buy.cumsum()
    return shares * prices / invested


def rebalance(prices: pd.DataFrame, weights: dict[str, float], every: int = 63) -> pd.Series:
    """Fixed-weight portfolio rebalanced every `every` trading days (~quarterly).

    `weights` maps column name -> target weight (should sum to 1).
    """
    prices = prices[list(weights)].dropna()
    w = pd.Series(weights)
    period = np.arange(len(prices)) // every
    # Within a period, value grows as the weighted sum of each asset's
    # price relative to the period's first day (fixed shares in between).
    growth = (prices / prices.groupby(period).transform("first")).mul(w).sum(axis=1)
    # Chain periods: factor linking one period start to the next.
    starts = prices.iloc[::every]
    link = (starts / starts.shift(1)).mul(w).sum(axis=1)
    link.iloc[0] = 1.0
    base = link.cumprod().to_numpy()
    return pd.Series(base[period] * growth.to_numpy(), index=prices.index)


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


def sma_trend_for_period(
    risk: pd.Series,
    start: pd.Timestamp,
    end: pd.Timestamp,
    window: int = 200,
) -> pd.Series:
    """Build the signal with pre-period warm-up, then rebase at ``start``."""

    clean = risk.dropna().sort_index().loc[:end]
    evaluation_index = clean.loc[start:end].index
    if evaluation_index.empty:
        raise ValueError("no trend data is available in the requested period")
    full_curve = sma_trend(clean, window=window)
    period_curve = full_curve.reindex(evaluation_index)
    return period_curve / period_curve.iloc[0]


def infinite_buy(prices: pd.Series, n_splits: int = 40, take_profit: float = 0.10) -> pd.Series:
    """Simplified "infinite buying" style cycle strategy.

    Capital is split into `n_splits` equal parts. Each day one part is
    invested (while cash remains). When the position gains `take_profit`
    versus its average cost, everything is sold and the cycle restarts.
    Idle cash earns 0%.

    This is a stylized illustration of the popular retail strategy for
    leveraged ETFs — the real method has more rules (LOC orders, halves,
    variants). Deliberately simplified and deterministic for testing.

    Kept as an explicit loop: each day's action depends on the running
    cash/cost state (path-dependent), so it doesn't vectorize cleanly.
    """
    prices = prices.dropna()
    per_buy = 1.0 / n_splits
    cash = 1.0
    shares = 0.0
    cost = 0.0
    values = []
    sell_next_bar = False
    for price in prices:
        # A threshold observed at close t is executable no earlier than close
        # t+1 in this daily-close simulator. Do not sell and repurchase at the
        # same close.
        sold_today = sell_next_bar and shares > 0
        if sold_today:
            cash += shares * price
            shares = 0.0
            cost = 0.0
        sell_next_bar = False

        if not sold_today and cash >= per_buy:
            shares += per_buy / price
            cash -= per_buy
            cost += per_buy

        values.append(cash + shares * price)
        sell_next_bar = (
            shares > 0 and shares * price >= cost * (1.0 + take_profit)
        )
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


def observed_periods_per_year(
    index: pd.Index,
    fallback: float = TRADING_DAYS_PER_YEAR,
) -> float:
    """Infer annualization from the aligned observations actually simulated.

    A US/European inner-joined calendar can contain fewer sessions than either
    market alone. Short samples use the conventional fallback because their
    calendar-derived rate is unstable.
    """

    dates = pd.DatetimeIndex(pd.to_datetime(index)).sort_values().unique()
    if len(dates) < 2:
        return float(fallback)
    elapsed_days = (dates[-1] - dates[0]).days
    if elapsed_days < 180:
        return float(fallback)
    observed_rate = (len(dates) - 1) * 365.25 / elapsed_days
    return float(min(max(observed_rate, 1.0), 366.0))


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
