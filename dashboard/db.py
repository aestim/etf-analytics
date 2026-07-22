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
    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
    margin=dict(l=40, r=120, t=30, b=40),
)

GLOSSARIES: dict[Language, dict[str, str]] = {
    "en": {
        "CAGR": "Compound annual growth rate — the constant yearly rate that would turn the starting value into the ending value over the full period.",
        "Ann. vol": "Annualised volatility — daily return variability converted to a one-year scale. Higher means wider price swings.",
        "Max drawdown": "Maximum drawdown — the largest fall from a previous peak to a later low. −50% means the value halved.",
        "Sharpe (rf=0)": "Sharpe ratio — return relative to volatility. This app assumes a risk-free rate of 0%.",
        "adj_close": "Adjusted close — a historical price adjusted for distributions and share splits, suitable for return calculations.",
        "cum_return": "Cumulative return — the total gain or loss from one unit invested on the first date. 0.5 means +50%.",
        "rolling_vol_30d": "30-trading-day volatility — how widely daily returns moved over the latest 30 trading days.",
        "drawdown": "Drawdown — the decline from the previous highest adjusted price. 0 is a peak and −0.12 is 12% below it.",
    },
    "ko": {
        "CAGR": "연평균 복리수익률 — 전체 기간의 성과를 '매년 같은 비율로 늘었다면'으로 바꿔 표시한 값.",
        "Ann. vol": "연환산 변동성 — 일간 수익률의 흔들림을 1년 척도로 바꾼 값. 클수록 가격 흔들림이 큼.",
        "Max drawdown": "최대 낙폭 — 과거의 고점에서 이후 저점까지 가장 크게 떨어진 비율. −50%면 절반으로 줄었다는 뜻.",
        "Sharpe (rf=0)": "샤프 지수 — 가격 흔들림 대비 수익을 나타낸 값. 이 앱은 무위험 수익률을 0으로 가정.",
        "adj_close": "조정 종가 — 배당과 주식 분할을 과거 가격에 반영해 장기 수익률 비교에 맞춘 가격.",
        "cum_return": "누적수익률 — 시작일에 1을 투자했을 때 전체 기간에 얼마나 늘거나 줄었는지. 0.5는 +50%.",
        "rolling_vol_30d": "30거래일 변동성 — 최근 약 한 달의 일간 수익률이 얼마나 크게 흔들렸는지 나타낸 값.",
        "drawdown": "고점 대비 하락률 — 이전 최고 가격에서 현재 얼마나 내려왔는지. 0은 최고점, −0.12는 12% 아래.",
    },
}

GLOSSARY_LABELS: dict[Language, dict[str, str]] = {
    "en": {
        "CAGR": "CAGR",
        "Ann. vol": "Annualised volatility",
        "Max drawdown": "Maximum drawdown",
        "Sharpe (rf=0)": "Sharpe ratio",
        "adj_close": "Adjusted close",
        "cum_return": "Cumulative return",
        "rolling_vol_30d": "30-trading-day volatility",
        "drawdown": "Drawdown",
    },
    "ko": {
        "CAGR": "연평균 복리수익률(CAGR)",
        "Ann. vol": "연환산 변동성",
        "Max drawdown": "최대 낙폭",
        "Sharpe (rf=0)": "샤프 지수",
        "adj_close": "조정 종가",
        "cum_return": "누적수익률",
        "rolling_vol_30d": "30거래일 변동성",
        "drawdown": "고점 대비 하락률",
    },
}


def glossary_help(key: str, lang: Language) -> str:
    """Return one glossary definition in the interface language."""
    return GLOSSARIES[lang][key]


def glossary_expander(keys, lang: Language, title: str = "📖 Metrics guide") -> None:
    """Render an expander explaining metrics in the interface language."""
    with st.expander(title):
        for k in keys:
            st.markdown(f"**{GLOSSARY_LABELS[lang][k]}** — {glossary_help(k, lang)}")


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
            "en": (
                "⚡ Demo mode — using the bundled parquet snapshot, which may lag "
                "the market. Configure PostgreSQL or run the local Docker stack for "
                "the current dbt warehouse."
            ),
            "ko": (
                "⚡ 데모 모드 — 포함된 parquet 예시 데이터를 사용하므로 시장보다 "
                "늦을 수 있습니다. 최신 dbt 분석 표를 사용하려면 PostgreSQL을 "
                "설정하거나 로컬 Docker를 실행하세요."
            ),
        }
        st.caption(messages[lang])
