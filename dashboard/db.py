"""
Shared data access for the Streamlit dashboard (all pages).

Primary source: PostgreSQL marts (local Docker stack).
Fallback ("demo mode"): parquet snapshots committed under data/raw/ —
lets the app run on Streamlit Community Cloud with no database.
The mart logic is mirrored in pandas so both modes show the same metrics.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

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


# --------------------------------------------------------------------------
# Warehouse (primary)
# --------------------------------------------------------------------------


@st.cache_resource
def get_engine():
    """SQLAlchemy engine (pandas requires a SQLAlchemy connectable)."""
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL

    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER", "etf"),
        password=os.getenv("POSTGRES_PASSWORD", "etf"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "etf_analytics"),
    )
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3})


@st.cache_resource
def warehouse_available() -> bool:
    """True if the Postgres marts are reachable (checked once per session)."""
    try:
        with get_engine().connect() as conn:
            conn.exec_driver_sql("select 1")
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# Parquet fallback ("demo mode")
# --------------------------------------------------------------------------


def _read_latest_snapshots() -> pd.DataFrame:
    """Latest dt= partition per ticker from data/raw (committed daily by CI)."""
    raw = ROOT / "data" / "raw"
    frames = []
    if raw.exists():
        for tdir in sorted(p for p in raw.iterdir() if p.is_dir()):
            parts = sorted(tdir.glob("dt=*/prices.parquet"))
            if parts:
                frames.append(pd.read_parquet(parts[-1]))
    if not frames:
        raise FileNotFoundError(f"No parquet snapshots under {raw}")
    df = pd.concat(frames, ignore_index=True)
    df["ticker"] = df["ticker"].str.upper().str.strip()
    df["price_date"] = pd.to_datetime(df["price_date"])
    df = (
        df.dropna(subset=["adj_close"])
        .drop_duplicates(["ticker", "price_date"])
        .sort_values(["ticker", "price_date"])
        .reset_index(drop=True)
    )
    return df


@st.cache_data(ttl=3600)
def _parquet_marts() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recompute both marts in pandas — mirrors the dbt models."""
    df = _read_latest_snapshots()
    grouped = df.groupby("ticker")["adj_close"]

    returns = df[["ticker", "price_date", "adj_close"]].copy()
    returns["daily_return"] = grouped.pct_change()

    risk = df[["ticker", "price_date"]].copy()
    risk["rolling_vol_30d"] = grouped.transform(
        lambda s: s.pct_change().rolling(30, min_periods=2).std()
    )
    risk["drawdown"] = grouped.transform(lambda s: s / s.cummax() - 1.0)
    return returns, risk


# --------------------------------------------------------------------------
# Loaders (used by all pages)
# --------------------------------------------------------------------------


@st.cache_data(ttl=300)
def load_mart_returns() -> pd.DataFrame:
    if warehouse_available():
        query = """
            select ticker, price_date, adj_close, daily_return
            from public_marts.mart_etf_returns
            order by ticker, price_date
        """
        df = pd.read_sql(query, get_engine())
        df["price_date"] = pd.to_datetime(df["price_date"])
        return df
    returns, _ = _parquet_marts()
    return returns


@st.cache_data(ttl=300)
def load_mart_risk() -> pd.DataFrame:
    if warehouse_available():
        query = """
            select ticker, price_date, rolling_vol_30d, drawdown
            from public_marts.mart_etf_risk_metrics
            order by ticker, price_date
        """
        df = pd.read_sql(query, get_engine())
        df["price_date"] = pd.to_datetime(df["price_date"])
        return df
    _, risk = _parquet_marts()
    return risk


@st.cache_data(ttl=3600)
def load_dim_etf() -> pd.DataFrame:
    if warehouse_available():
        query = """
            select ticker, name, asset_class, sub_class, leverage, description
            from public_marts.dim_etf
            order by asset_class, sub_class, ticker
        """
        return pd.read_sql(query, get_engine())
    dim = pd.read_csv(ROOT / "dbt" / "seeds" / "etf_info.csv")
    return dim.sort_values(["asset_class", "sub_class", "ticker"]).reset_index(drop=True)


def demo_mode_banner() -> None:
    """Small caption shown when running without a database."""
    if not warehouse_available():
        st.caption(
            "⚡ Demo mode — reading parquet snapshots committed to the repo "
            "(refreshed daily by GitHub Actions). Run the Docker stack locally "
            "for the full Postgres + dbt warehouse."
        )
