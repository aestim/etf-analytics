"""
Shared warehouse access for the Streamlit dashboard (all pages).
Reads mart tables from PostgreSQL; connection settings come from .env.
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


GLOSSARY = {
    "CAGR": "Compound Annual Growth Rate — the constant yearly return that would turn the starting value into the ending value over the period.",
    "Ann. vol": "Annualized volatility — standard deviation of daily returns × √252. Higher = bigger day-to-day swings.",
    "Max drawdown": "Worst peak-to-trough decline of the curve. −50% means the value halved from its previous peak before recovering.",
    "Sharpe (rf=0)": "Average return per unit of volatility, risk-free rate assumed 0. Rough guide: below 0.5 weak, around 1 solid.",
    "adj_close": "Close price retroactively adjusted for splits and distributions — the correct series for return math.",
    "cum_return": "Growth of 1 unit invested at the start, compounding daily returns (0.5 = +50%).",
    "rolling_vol_30d": "Standard deviation of daily returns over the trailing 30 trading days. Daily scale — multiply by √252 to annualize.",
    "drawdown": "Decline from the running maximum adjusted close. 0 = at peak; −0.12 = 12% below the peak.",
}


def glossary_expander(keys, title: str = "📖 Metrics guide") -> None:
    """Render an expander explaining the given GLOSSARY terms."""
    with st.expander(title):
        for k in keys:
            st.markdown(f"**{k}** — {GLOSSARY[k]}")


def ticker_color_map(tickers) -> dict[str, str]:
    """Stable, distinct color per ticker.

    Plotly's default qualitative palette has only 10 colors, so with more
    than 10 tickers lines start sharing colors. Dark24 gives 24 distinct
    colors, and sorting makes the mapping consistent across charts.
    """
    palette = px.colors.qualitative.Dark24
    return {t: palette[i % len(palette)] for i, t in enumerate(sorted(tickers))}


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


@st.cache_data(ttl=3600)
def load_dim_etf() -> pd.DataFrame:
    query = """
        select ticker, name, asset_class, sub_class, leverage, description
        from public_marts.dim_etf
        order by asset_class, sub_class, ticker
    """
    with pg_conn() as conn:
        return pd.read_sql(query, conn)


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
