"""
Streamlit dashboard — reads mart tables from PostgreSQL.
Run after: docker compose up, ingest, dbt run.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
    margin=dict(l=40, r=120, t=30, b=40),
)


def pg_conn():
    import psycopg2

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5433"),
        dbname=os.getenv("POSTGRES_DB", "etf_analytics"),
        user=os.getenv("POSTGRES_USER", "etf"),
        password=os.getenv("POSTGRES_PASSWORD", "etf"),
    )


@st.cache_data(ttl=300)
def load_mart_returns() -> pd.DataFrame:
    query = """
        select ticker, price_date, adj_close, daily_return
        from public_marts.mart_etf_returns
        order by ticker, price_date
    """
    with pg_conn() as conn:
        df = pd.read_sql(query, conn)
    df["price_date"] = pd.to_datetime(df["price_date"])
    return df


@st.cache_data(ttl=300)
def load_mart_risk() -> pd.DataFrame:
    query = """
        select ticker, price_date, rolling_vol_30d, drawdown
        from public_marts.mart_etf_risk_metrics
        order by ticker, price_date
    """
    with pg_conn() as conn:
        df = pd.read_sql(query, conn)
    df["price_date"] = pd.to_datetime(df["price_date"])
    return df


def line_chart(df: pd.DataFrame, y: str, title: str) -> None:
    fig = px.line(df, x="price_date", y=y, color="ticker", title=title)
    fig.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)


st.set_page_config(
    page_title="ETF Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("SGOV vs VGIT — Treasury ETF Analytics")
st.caption(
    "Short-term vs intermediate-term U.S. Treasury ETFs · "
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

tickers = sorted(returns_df["ticker"].unique())
selected = st.multiselect("Tickers", tickers, default=tickers)
filtered = returns_df[returns_df["ticker"].isin(selected)]
risk_filtered = risk_df[risk_df["ticker"].isin(selected)]

col1, col2 = st.columns(2)

with col1:
    st.subheader("Adjusted close")
    line_chart(filtered, "adj_close", "Adjusted close")

with col2:
    st.subheader("Cumulative return")
    cum = filtered.copy()
    cum["cum_return"] = cum.groupby("ticker")["daily_return"].transform(
        lambda s: (1 + s.fillna(0)).cumprod() - 1
    )
    line_chart(cum, "cum_return", "Cumulative return")

st.subheader("30-day rolling volatility")
line_chart(risk_filtered, "rolling_vol_30d", "30-day rolling volatility")

st.subheader("Latest snapshot")
latest = (
    risk_filtered.sort_values("price_date")
    .groupby("ticker", as_index=False)
    .tail(1)[["ticker", "price_date", "rolling_vol_30d", "drawdown"]]
)
latest["price_date"] = latest["price_date"].dt.strftime("%Y-%m-%d %H:%M:%S")
latest["rolling_vol_30d"] = latest["rolling_vol_30d"].round(4)
latest["drawdown"] = latest["drawdown"].round(4)

st.dataframe(latest, use_container_width=True, hide_index=True)
