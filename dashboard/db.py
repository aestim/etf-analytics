"""
Shared warehouse access for the Streamlit dashboard (all pages).
Reads mart tables from PostgreSQL; connection settings come from .env.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
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
