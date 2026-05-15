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

st.set_page_config(page_title="ETF Analytics", layout="wide")
st.title("SGOV vs VGIT — Treasury ETF Analytics")


@st.cache_data(ttl=300)
def load_mart_returns() -> pd.DataFrame:
    import psycopg2

    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "etf_analytics"),
        user=os.getenv("POSTGRES_USER", "etf"),
        password=os.getenv("POSTGRES_PASSWORD", "etf"),
    )
    query = """
        select ticker, price_date, adj_close, daily_return
        from public_marts.mart_etf_returns
        order by ticker, price_date
    """
    df = pd.read_sql(query, conn)
    conn.close()
    df["price_date"] = pd.to_datetime(df["price_date"])
    return df


@st.cache_data(ttl=300)
def load_mart_risk() -> pd.DataFrame:
    import psycopg2

    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "etf_analytics"),
        user=os.getenv("POSTGRES_USER", "etf"),
        password=os.getenv("POSTGRES_PASSWORD", "etf"),
    )
    query = """
        select ticker, price_date, rolling_vol_30d, drawdown
        from public_marts.mart_etf_risk_metrics
        order by ticker, price_date
    """
    df = pd.read_sql(query, conn)
    conn.close()
    df["price_date"] = pd.to_datetime(df["price_date"])
    return df


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

col1, col2 = st.columns(2)

with col1:
    st.subheader("Adjusted close")
    fig_price = px.line(
        filtered,
        x="price_date",
        y="adj_close",
        color="ticker",
    )
    st.plotly_chart(fig_price, use_container_width=True)

with col2:
    st.subheader("Cumulative return")
    cum = filtered.copy()
    cum["cum_return"] = cum.groupby("ticker")["daily_return"].transform(
        lambda s: (1 + s.fillna(0)).cumprod() - 1
    )
    fig_cum = px.line(cum, x="price_date", y="cum_return", color="ticker")
    st.plotly_chart(fig_cum, use_container_width=True)

st.subheader("30-day rolling volatility")
risk_filtered = risk_df[risk_df["ticker"].isin(selected)]
fig_vol = px.line(
    risk_filtered,
    x="price_date",
    y="rolling_vol_30d",
    color="ticker",
)
st.plotly_chart(fig_vol, use_container_width=True)

st.subheader("Latest snapshot")
latest = (
    risk_filtered.sort_values("price_date")
    .groupby("ticker")
    .tail(1)[["ticker", "price_date", "rolling_vol_30d", "drawdown"]]
)
st.dataframe(latest, use_container_width=True)
