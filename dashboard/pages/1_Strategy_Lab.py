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
from db import (  # noqa: E402
    DATAFRAME_ROW_HEIGHT,
    PLOTLY_LAYOUT,
    dataframe_width,
    demo_mode_banner,
    glossary_expander,
    glossary_help,
    load_mart_returns,
)
from i18n import current_language, tr  # noqa: E402

lang = current_language()

st.title(tr("strategy.title", lang))
st.caption(tr("strategy.subtitle", lang))

with st.expander(tr("strategy.guide_title", lang), expanded=True):
    st.markdown(tr("strategy.guide_body", lang))

REQUIRED = {"SPY", "QQQ", "BND", "TQQQ"}

try:
    returns_df = load_mart_returns()
except Exception as exc:
    st.error(tr("strategy.data_error", lang))
    with st.expander(tr("home.admin_details", lang)):
        st.code(str(exc))
    st.stop()

demo_mode_banner(lang)

prices = returns_df.pivot(
    index="price_date", columns="ticker", values="adj_close"
).sort_index()
missing = REQUIRED - set(prices.columns)
if missing:
    st.warning(tr("strategy.missing", lang, tickers=", ".join(sorted(missing))))
    st.stop()

# Common window: all required tickers must have data (fair comparison)
prices = prices[sorted(REQUIRED)].dropna()

STRATEGY_NOTES = {
    tr("strategy.buy_hold_name", lang): tr("strategy.buy_hold_note", lang),
    tr("strategy.dca_name", lang): tr("strategy.dca_note", lang),
    tr("strategy.balanced_name", lang): tr("strategy.balanced_note", lang),
    tr("strategy.trend_name", lang): tr("strategy.trend_note", lang),
    tr("strategy.split_name", lang): tr("strategy.split_note", lang),
}

equity_curves = {
    tr("strategy.buy_hold_name", lang): strat.lump_sum(prices["SPY"]),
    tr("strategy.dca_name", lang): strat.dca(prices["QQQ"], every=21),
    tr("strategy.balanced_name", lang): strat.rebalance(
        prices, {"SPY": 0.6, "BND": 0.4}, every=63
    ),
    tr("strategy.trend_name", lang): strat.sma_trend(prices["QQQ"], window=200),
    tr("strategy.split_name", lang): strat.infinite_buy(
        prices["TQQQ"], n_splits=40, take_profit=0.10
    ),
}

curves = pd.DataFrame(equity_curves)
curves.index.name = "price_date"

CHART_LABELS = {
    tr("strategy.buy_hold_name", lang): tr("strategy.buy_hold_short", lang),
    tr("strategy.dca_name", lang): tr("strategy.dca_short", lang),
    tr("strategy.balanced_name", lang): tr("strategy.balanced_short", lang),
    tr("strategy.trend_name", lang): tr("strategy.trend_short", lang),
    tr("strategy.split_name", lang): tr("strategy.split_short", lang),
}
chart_curves = curves.rename(columns=CHART_LABELS)

log_scale = st.checkbox(
    tr("strategy.log_scale", lang),
    value=True,
    help=tr("strategy.log_help", lang),
)

st.subheader(tr("strategy.growth_title", lang))
st.caption(f"{curves.index.min():%Y-%m-%d} → {curves.index.max():%Y-%m-%d}")

fig = px.line(
    chart_curves.reset_index().melt(
        id_vars="price_date", var_name="strategy", value_name="equity"
    ),
    x="price_date",
    y="equity",
    color="strategy",
    line_dash="strategy",
    log_y=log_scale,
    labels={
        "price_date": tr("strategy.date", lang),
        "equity": tr("strategy.capital", lang),
        "strategy": tr("strategy.rule", lang),
    },
)
fig.update_layout(**PLOTLY_LAYOUT, title_text="", legend_title_text="")
st.plotly_chart(fig, width="stretch")

st.subheader(tr("strategy.drawdown_title", lang))
st.caption(tr("strategy.drawdown_caption", lang))
dd = chart_curves.div(chart_curves.cummax()) - 1.0
fig_dd = px.line(
    dd.reset_index().melt(
        id_vars="price_date", var_name="strategy", value_name="drawdown"
    ),
    x="price_date",
    y="drawdown",
    color="strategy",
    line_dash="strategy",
    labels={
        "price_date": tr("strategy.date", lang),
        "drawdown": tr("home.drawdown", lang),
        "strategy": tr("strategy.rule", lang),
    },
)
fig_dd.update_layout(**PLOTLY_LAYOUT, title_text="", legend_title_text="")
fig_dd.update_yaxes(tickformat=".0%")
st.plotly_chart(fig_dd, width="stretch")

st.subheader(tr("strategy.metrics", lang))
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

metric_labels = {
    "CAGR": tr("strategy.cagr", lang),
    "Ann. vol": tr("strategy.ann_vol", lang),
    "Max drawdown": tr("strategy.max_drawdown", lang),
    "Sharpe (rf=0)": tr("strategy.sharpe", lang),
}
display = display.rename(columns=metric_labels)

st.dataframe(
    display,
    width=dataframe_width(display),
    row_height=DATAFRAME_ROW_HEIGHT,
    column_config={
        label: st.column_config.TextColumn(label, help=glossary_help(key, lang))
        for key, label in metric_labels.items()
    },
)

with st.expander(tr("strategy.rule_guide", lang)):
    for name, note in STRATEGY_NOTES.items():
        st.markdown(f"**{name}**  \n{note}")

glossary_expander(
    ["CAGR", "Ann. vol", "Max drawdown", "Sharpe (rf=0)"],
    lang,
    title=tr("strategy.metric_guide", lang),
)

st.caption(tr("strategy.footer", lang))
