"""
Shared data access for the Streamlit dashboard (all pages).

Primary source: PostgreSQL marts (local Docker stack).
Fallback ("demo mode"): a bundled parquet snapshot under data/raw/ —
lets the app run on Streamlit Community Cloud with no database. Scheduled
automation does not mutate this repository snapshot.
The mart logic is mirrored in pandas so both modes show the same metrics.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from i18n import Language

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(size=15, color="#fafafa"),
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.20,
        xanchor="left",
        x=0,
        font=dict(size=14),
        title=dict(font=dict(size=14)),
    ),
    margin=dict(l=56, r=20, t=48, b=112),
    hoverlabel=dict(font=dict(size=15)),
    xaxis=dict(
        automargin=True,
        tickfont=dict(size=14),
        title=dict(font=dict(size=15)),
    ),
    yaxis=dict(
        automargin=True,
        tickfont=dict(size=14),
        title=dict(font=dict(size=15)),
    ),
)

DATAFRAME_ROW_HEIGHT = 38


def dataframe_width(df: pd.DataFrame) -> str:
    """Size tables from their columns instead of filling the chart container.

    Streamlit still constrains content-width dataframes to the available mobile
    viewport and provides horizontal scrolling when a schema is genuinely wide.
    """

    return "content"

GLOSSARIES: dict[Language, dict[str, str]] = {
    # Definitions only. The label is rendered separately by glossary_expander
    # and by each column header, so repeating it here printed it twice.
    "en": {
        "CAGR": "The average yearly growth rate over the full period.",
        "Ann. vol": "How much daily returns moved up and down, expressed as a yearly number. Higher means wider price swings.",
        "Max drawdown": "The largest percentage drop from a previous high. −50% means the value fell by half.",
        "Sharpe (rf=0)": "Return compared with price swings. Higher values mean more return for the amount of risk taken. This app assumes a risk-free rate of 0%.",
        "adj_close": "A historical price adjusted for dividends and stock splits so returns can be compared fairly.",
        "cum_return": "How much a starting value of 1 gained or lost. 0.5 means +50%.",
        "rolling_vol_30d": "How much daily returns moved up and down over the latest 30 trading days.",
        "drawdown": "How far the price sits below its own earlier peak. 0 means a new high, −0.12 means 12% below it.",
    },
    "ko": {
        "CAGR": "전체 기간의 성과를 '매년 같은 비율로 늘었다면'으로 바꿔 표시한 값.",
        "Ann. vol": "가격이 오르내린 정도를 1년 기준으로 바꾼 값. 클수록 가격 흔들림이 큼.",
        "Max drawdown": "이전 고점에서 가장 크게 떨어진 비율. −50%면 가치가 절반으로 줄었다는 뜻.",
        "Sharpe (rf=0)": "가격 흔들림과 비교해 어느 정도 수익을 냈는지 보여주는 값. 이 앱은 무위험 수익률을 0%로 가정.",
        "adj_close": "배당과 주식 분할을 반영해 수익률을 공정하게 비교할 수 있도록 조정한 과거 가격.",
        "cum_return": "시작일에 1을 투자했을 때 전체 기간에 얼마나 늘거나 줄었는지. 0.5는 +50%.",
        "rolling_vol_30d": "최근 30거래일 동안 일간 수익률이 얼마나 크게 오르내렸는지 나타낸 값.",
        "drawdown": "이전 최고 가격에서 현재 얼마나 내려왔는지. 0은 최고점, −0.12는 12% 아래.",
    },
}

GLOSSARY_LABELS: dict[Language, dict[str, str]] = {
    "en": {
        "CAGR": "CAGR",
        "Ann. vol": "Annualized volatility",
        "Max drawdown": "Maximum drawdown",
        "Sharpe (rf=0)": "Sharpe ratio",
        "adj_close": "Dividend-adjusted price",
        "cum_return": "Total return",
        "rolling_vol_30d": "30-day price swings",
        "drawdown": "Drop from a previous high",
    },
    "ko": {
        "CAGR": "연평균 복리수익률(CAGR)",
        "Ann. vol": "연환산 변동성",
        "Max drawdown": "최대 낙폭",
        "Sharpe (rf=0)": "샤프 지수",
        "adj_close": "배당 반영 가격",
        "cum_return": "누적수익률",
        "rolling_vol_30d": "30일 가격 변동",
        "drawdown": "고점 대비 하락률",
    },
}


def glossary_help(key: str, lang: Language) -> str:
    """Return one glossary definition in the interface language."""
    return GLOSSARIES[lang][key]


def glossary_items(keys, lang: Language) -> None:
    """Render metric definitions with no container of their own.

    Kept separate from the expander so a page that already has an explanatory
    panel can put the definitions inside it, rather than opening a second
    panel that reads as a duplicate of the first.
    """
    for k in keys:
        st.markdown(f"**{GLOSSARY_LABELS[lang][k]}** — {glossary_help(k, lang)}")


def glossary_expander(keys, lang: Language, title: str = "📖 Metrics guide") -> None:
    """Render metric definitions in an expander of their own."""
    with st.expander(title):
        glossary_items(keys, lang)


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
    # Managed Postgres (Neon/Supabase) requires SSL; local Docker has none.
    host = os.getenv("POSTGRES_HOST", "localhost")
    local = host in ("localhost", "127.0.0.1", "", "postgres")
    sslmode = os.getenv("POSTGRES_SSLMODE", "prefer" if local else "require")
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3, "sslmode": sslmode},
    )


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
    """Latest bundled dt= partition per ticker from data/raw."""
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

    # reindex keeps the serving schema stable for an older snapshot that may
    # predate volume ingestion (the column is then present with null values).
    returns = df.reindex(columns=["ticker", "price_date", "adj_close", "volume"]).copy()
    returns["daily_return"] = grouped.pct_change()

    risk = df[["ticker", "price_date"]].copy()
    risk["rolling_vol_30d"] = grouped.transform(
        lambda s: s.pct_change().rolling(30, min_periods=2).std()
    )
    risk["annualized_vol_30d"] = risk["rolling_vol_30d"] * (252**0.5)
    risk["drawdown"] = grouped.transform(lambda s: s / s.cummax() - 1.0)
    return returns, risk


# --------------------------------------------------------------------------
# Loaders (used by all pages)
# --------------------------------------------------------------------------


@st.cache_data(ttl=300)
def load_mart_returns() -> pd.DataFrame:
    if warehouse_available():
        query = """
            select ticker, price_date, adj_close, volume, daily_return
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
            select ticker, price_date, rolling_vol_30d, annualized_vol_30d, drawdown
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
    return dim.sort_values(["asset_class", "sub_class", "ticker"]).reset_index(
        drop=True
    )


def demo_mode_banner(lang: Language = "en") -> None:
    """Small caption shown when running without a database."""
    if not warehouse_available():
        messages = {
            "en": "⚡ Demo data — this view may be behind the latest market data.",
            "ko": "⚡ 예시 데이터 — 최신 시장 상황보다 늦을 수 있습니다.",
        }
        st.caption(messages[lang])
