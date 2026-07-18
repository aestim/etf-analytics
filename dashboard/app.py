"""
Streamlit dashboard — reads mart tables from PostgreSQL.
Run after: docker compose up, ingest, dbt run.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from db import (
    GLOSSARY,
    PLOTLY_LAYOUT,
    glossary_expander,
    load_dim_etf,
    load_mart_returns,
    load_mart_risk,
    ticker_color_map,
)


def line_chart(df: pd.DataFrame, y: str, title: str, colors: dict | None = None) -> None:
    fig = px.line(df, x="price_date", y=y, color="ticker", title=title, color_discrete_map=colors)
    fig.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)


st.set_page_config(
    page_title="ETF Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("ETF Analytics")
st.caption(
    "Cross-asset ETF universe (set via ETF_TICKERS) · "
    "Data: `public_marts` (dbt) · Refreshed on page load"
)

try:
    returns_df = load_mart_returns()
    risk_df = load_mart_risk()
except Exception as exc:
    st.error(
        "Could not load data from PostgreSQL. "
        "Start Docker, run ingest + `dbt run`, then refresh.\n\n"
        f"Details: {exc}"
    )
    st.stop()

with st.expander("📖 Ticker guide"):
    try:
        st.dataframe(load_dim_etf(), use_container_width=True, hide_index=True)
    except Exception:
        st.caption("Run `dbt seed && dbt run` to build the dim_etf reference table.")

tickers = sorted(returns_df["ticker"].unique())
COLORS = ticker_color_map(tickers)  # stable palette across all charts
selected = st.multiselect("Tickers", tickers, default=tickers)
filtered = returns_df[returns_df["ticker"].isin(selected)]
risk_filtered = risk_df[risk_df["ticker"].isin(selected)]

col1, col2 = st.columns(2)

with col1:
    st.subheader("Adjusted close")
    line_chart(filtered, "adj_close", "Adjusted close", COLORS)

with col2:
    st.subheader("Cumulative return")
    cum = filtered.copy()
    cum["cum_return"] = cum.groupby("ticker")["daily_return"].transform(
        lambda s: (1 + s.fillna(0)).cumprod() - 1
    )
    line_chart(cum, "cum_return", "Cumulative return", COLORS)

st.subheader("30-day rolling volatility")
line_chart(risk_filtered, "rolling_vol_30d", "30-day rolling volatility", COLORS)

st.subheader("Latest snapshot")
latest = (
    risk_filtered.sort_values("price_date")
    .groupby("ticker", as_index=False)
    .tail(1)[["ticker", "price_date", "rolling_vol_30d", "drawdown"]]
)
latest["price_date"] = latest["price_date"].dt.strftime("%Y-%m-%d")
latest["rolling_vol_30d"] = latest["rolling_vol_30d"].round(4)
latest["drawdown"] = latest["drawdown"].round(4)

st.dataframe(
    latest,
    use_container_width=True,
    hide_index=True,
    column_config={
        "rolling_vol_30d": st.column_config.NumberColumn(
            "rolling_vol_30d", help=GLOSSARY["rolling_vol_30d"]
        ),
        "drawdown": st.column_config.NumberColumn("drawdown", help=GLOSSARY["drawdown"]),
    },
)

glossary_expander(["adj_close", "cum_return", "rolling_vol_30d", "drawdown"])
