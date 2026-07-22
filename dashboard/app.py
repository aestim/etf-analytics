"""
Streamlit dashboard — reads mart tables from PostgreSQL.
Run after: docker compose up, ingest, dbt run.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from chart_colors import ticker_color_map
from db import (
    GLOSSARY,
    PLOTLY_LAYOUT,
    demo_mode_banner,
    glossary_expander,
    load_dim_etf,
    load_mart_returns,
    load_mart_risk,
)


def line_chart(df: pd.DataFrame, y: str, colors: dict | None = None) -> None:
    # No figure title — the st.subheader above each chart already labels it
    fig = px.line(df, x="price_date", y=y, color="ticker", color_discrete_map=colors)
    fig.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig, width="stretch")


st.set_page_config(
    page_title="ETF Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("ETF Analytics")
st.caption(
    "Cross-asset ETF universe (set via ETF_TICKERS) · "
    "Data: `public_marts` when configured · bundled parquet fallback otherwise"
)

try:
    returns_df = load_mart_returns()
    risk_df = load_mart_risk()
except Exception as exc:
    st.error(
        "No data available: neither PostgreSQL nor parquet snapshots. "
        "Start Docker + run ingest & `dbt run`, or commit raw parquet.\n\n"
        f"Details: {exc}"
    )
    st.stop()

demo_mode_banner()

with st.expander("📖 Ticker guide"):
    try:
        dim = load_dim_etf()
        st.dataframe(
            dim.drop(columns=["description"]),
            width="stretch",
            hide_index=True,
            column_config={
                "asset_class": st.column_config.TextColumn(
                    "asset_class", help="Broad bucket — compare like with like"
                ),
                "sub_class": st.column_config.TextColumn(
                    "sub_class", help="Machine-readable filter key used by the SQL layer"
                ),
                "leverage": st.column_config.NumberColumn(
                    "leverage", help="Daily leverage multiple (1 = unleveraged)"
                ),
            },
        )
        pick = st.selectbox("Show details for", dim["ticker"], label_visibility="collapsed")
        row = dim.set_index("ticker").loc[pick]
        lev = f" · {int(row['leverage'])}x daily" if row["leverage"] > 1 else ""
        st.info(
            f"**{pick} — {row['name']}**  \n"
            f"`{row['asset_class']} / {row['sub_class']}`{lev}\n\n{row['description']}"
        )
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
    line_chart(filtered, "adj_close", COLORS)

with col2:
    st.subheader("Cumulative return")
    cum = filtered.copy()
    cum["cum_return"] = cum.groupby("ticker")["daily_return"].transform(
        lambda s: (1 + s.fillna(0)).cumprod() - 1
    )
    line_chart(cum, "cum_return", COLORS)

st.subheader("30-day rolling volatility")
line_chart(risk_filtered, "rolling_vol_30d", COLORS)

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
    width="stretch",
    hide_index=True,
    column_config={
        "rolling_vol_30d": st.column_config.NumberColumn(
            "rolling_vol_30d", help=GLOSSARY["rolling_vol_30d"]
        ),
        "drawdown": st.column_config.NumberColumn("drawdown", help=GLOSSARY["drawdown"]),
    },
)

glossary_expander(["adj_close", "cum_return", "rolling_vol_30d", "drawdown"])
