"""
Strategy Lab — representative short/mid/long-horizon strategies backtested
on the mart price data. Pure functions live in analytics/strategies.py
(pytest-covered); this page only wires data to them and renders results.

Educational illustration — NOT investment advice.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT / "dashboard", _ROOT / "analytics"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import strategies as strat  # noqa: E402
from db import GLOSSARY, PLOTLY_LAYOUT, glossary_expander, load_mart_returns  # noqa: E402

st.set_page_config(page_title="Strategy Lab", page_icon="🧪", layout="wide")

st.title("Strategy Lab")
st.caption(
    "Representative strategies backtested on mart data (adjusted close). "
    "Simplified rules, no fees/taxes/slippage, idle cash at 0%. "
    "**Educational illustration — not investment advice.**"
)

REQUIRED = {"SPY", "QQQ", "BND", "TQQQ"}

try:
    returns_df = load_mart_returns()
except Exception as exc:
    st.error(f"Could not load data from PostgreSQL: {exc}")
    st.stop()

prices = returns_df.pivot(index="price_date", columns="ticker", values="adj_close").sort_index()
missing = REQUIRED - set(prices.columns)
if missing:
    st.warning(
        f"Missing tickers in marts: {', '.join(sorted(missing))}. "
        "Add them to ETF_TICKERS, re-run ingest + dbt, then refresh."
    )
    st.stop()

# Common window: all required tickers must have data (fair comparison)
prices = prices[sorted(REQUIRED)].dropna()

STRATEGY_NOTES = {
    "Buy & Hold (SPY)": "Put everything in on day one and never touch it. The benchmark every other strategy has to justify itself against.",
    "DCA monthly (QQQ)": "Invest one fixed slice every ~21 trading days. Smooths the entry price; in a steadily rising market it lags buy-and-hold because cash waits on the sidelines.",
    "60/40 quarterly rebalance (SPY/BND)": "60% stocks / 40% bonds, rebalanced quarterly — trims whatever ran up, adds to whatever lagged. Similar direction to stocks with smaller swings and drawdowns.",
    "SMA-200 trend (QQQ, cash park)": "Hold QQQ while it closes above its 200-day average, otherwise sit in cash. Tries to sidestep long bear markets; pays for it with whipsaw losses when the market goes sideways. The signal acts one day late (no look-ahead).",
    "Infinite-buying style (TQQQ, 40 splits, +10% TP)": "Split capital into 40 parts, buy one part daily, sell everything at +10% over average cost. Caps each cycle's upside while keeping full crash exposure once the cash runs out — watch the asymmetry in the drawdown chart.",
}

equity_curves = {
    "Buy & Hold (SPY)": strat.lump_sum(prices["SPY"]),
    "DCA monthly (QQQ)": strat.dca(prices["QQQ"], every=21),
    "60/40 quarterly rebalance (SPY/BND)": strat.rebalance(
        prices, {"SPY": 0.6, "BND": 0.4}, every=63
    ),
    "SMA-200 trend (QQQ, cash park)": strat.sma_trend(prices["QQQ"], window=200),
    "Infinite-buying style (TQQQ, 40 splits, +10% TP)": strat.infinite_buy(
        prices["TQQQ"], n_splits=40, take_profit=0.10
    ),
}

curves = pd.DataFrame(equity_curves)
curves.index.name = "price_date"

log_scale = st.checkbox("Log scale", value=True)

fig = px.line(
    curves.reset_index().melt(id_vars="price_date", var_name="strategy", value_name="equity"),
    x="price_date",
    y="equity",
    color="strategy",
    title=f"Growth of invested capital · {curves.index.min():%Y-%m-%d} → {curves.index.max():%Y-%m-%d}",
    log_y=log_scale,
)
fig.update_layout(**PLOTLY_LAYOUT)
st.plotly_chart(fig, width="stretch")

st.subheader("Drawdown")
st.caption("How far each strategy sat below its own previous peak — the 'pain' view of the same curves.")
dd = curves.div(curves.cummax()) - 1.0
fig_dd = px.line(
    dd.reset_index().melt(id_vars="price_date", var_name="strategy", value_name="drawdown"),
    x="price_date",
    y="drawdown",
    color="strategy",
)
fig_dd.update_layout(**PLOTLY_LAYOUT)
fig_dd.update_yaxes(tickformat=".0%")
st.plotly_chart(fig_dd, width="stretch")

st.subheader("Metrics")
metrics = pd.DataFrame(
    {name: strat.summary_metrics(eq) for name, eq in equity_curves.items()}
).T.rename(
    columns={
        "cagr": "CAGR",
        "ann_vol": "Ann. vol",
        "max_drawdown": "Max drawdown",
        "sharpe": "Sharpe (rf=0)",
    }
)
display = metrics.copy()
for col in ("CAGR", "Ann. vol", "Max drawdown"):
    display[col] = display[col].map("{:.2%}".format)
display["Sharpe (rf=0)"] = display["Sharpe (rf=0)"].map("{:.2f}".format)

st.dataframe(
    display,
    width="stretch",
    column_config={
        col: st.column_config.TextColumn(col, help=GLOSSARY[col]) for col in display.columns
    },
)

with st.expander("📖 Strategy guide"):
    for name, note in STRATEGY_NOTES.items():
        st.markdown(f"**{name}**  \n{note}")

glossary_expander(["CAGR", "Ann. vol", "Max drawdown", "Sharpe (rf=0)"])

st.caption(
    "Why the leveraged strategy caps its upside but not its downside, and why "
    "trend following looks smoother than it feels — see each function's "
    "assumptions in `analytics/strategies.py`."
)
