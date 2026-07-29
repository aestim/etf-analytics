#!/usr/bin/env python3
"""
Fetch daily ETF prices from Yahoo Finance in one batched request
(tickers from ETF_TICKERS env). Writes raw parquet under
data/raw/{ticker}/ and optionally loads Postgres.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
UNIVERSE_FILE = ROOT / "config" / "etf_universe.txt"
_raw = Path(os.getenv("RAW_DATA_DIR", ROOT / "data" / "raw"))
RAW_DIR = _raw if _raw.is_absolute() else ROOT / _raw
PERIOD = os.getenv("FETCH_PERIOD", "max")


def configured_tickers() -> list[str]:
    """Load the universe from one shared file, with an explicit env override."""

    configured = os.getenv("ETF_TICKERS", "").strip()
    if configured:
        tickers = [value.strip().upper() for value in configured.split(",")]
    else:
        if not UNIVERSE_FILE.exists():
            raise RuntimeError(f"Ticker universe file is missing: {UNIVERSE_FILE}")
        tickers = [
            line.strip().upper()
            for line in UNIVERSE_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    unique_tickers = list(dict.fromkeys(ticker for ticker in tickers if ticker))
    if not unique_tickers:
        raise RuntimeError("ETF ticker universe is empty")
    return unique_tickers


TICKERS = configured_tickers()


def _normalize_history(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    df = df.reset_index()
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    rename = {
        "date": "price_date",
        "adj_close": "adj_close",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "adj_close" not in df.columns:
        raise RuntimeError(
            f"{ticker}: Yahoo response has no Adjusted Close column; "
            "refusing to substitute unadjusted Close"
        )
    df["adj_close"] = pd.to_numeric(df["adj_close"], errors="coerce")
    df = df.dropna(subset=["adj_close"])
    if df.empty:
        raise RuntimeError(f"{ticker}: Adjusted Close contains no usable values")
    df["ticker"] = ticker
    df["price_date"] = pd.to_datetime(df["price_date"]).dt.date
    df["_ingested_at"] = datetime.now(timezone.utc)
    cols = [
        "ticker",
        "price_date",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "_ingested_at",
    ]
    keep = [c for c in cols if c in df.columns]
    return df[keep].drop_duplicates(subset=["ticker", "price_date"])


def fetch_all(
    tickers: list[str],
    *,
    period: str | None = None,
    downloader: Callable[..., pd.DataFrame] | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch one batch without forcing every ticker to share an inception date."""

    selected_period = period or PERIOD
    download = downloader or yf.download
    data = download(
        tickers,
        period=selected_period,
        auto_adjust=False,
        group_by="ticker",
        progress=False,
    )
    if data is None or data.empty:
        raise RuntimeError(f"No data returned for {tickers}")
    frames: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            history = data[ticker] if isinstance(data.columns, pd.MultiIndex) else data
        except KeyError as exc:
            raise RuntimeError(f"No data returned for {ticker}") from exc
        history = history.dropna(how="all")
        if history.empty:
            raise RuntimeError(f"No data returned for {ticker}")
        frames[ticker] = _normalize_history(history, ticker)
    return frames


def write_raw_parquet(df: pd.DataFrame, ticker: str) -> Path:
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = RAW_DIR / ticker / f"dt={as_of}"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "prices.parquet"
    df.to_parquet(path, index=False)
    return path


def load_postgres(df: pd.DataFrame) -> None:
    host = os.getenv("POSTGRES_HOST")
    if not host:
        return
    import psycopg2
    from psycopg2.extras import execute_values

    # Managed Postgres (Neon/Supabase) requires SSL; local Docker has none.
    _local = host in ("localhost", "127.0.0.1", "", "postgres")
    conn = psycopg2.connect(
        host=host,
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "etf_analytics"),
        user=os.getenv("POSTGRES_USER", "etf"),
        password=os.getenv("POSTGRES_PASSWORD", "etf"),
        sslmode=os.getenv("POSTGRES_SSLMODE", "prefer" if _local else "require"),
    )
    rows = [
        (
            r.ticker,
            r.price_date,
            getattr(r, "open", None),
            getattr(r, "high", None),
            getattr(r, "low", None),
            getattr(r, "close", None),
            r.adj_close,
            int(r.volume) if pd.notna(getattr(r, "volume", None)) else None,
        )
        for r in df.itertuples(index=False)
    ]
    sql = """
        INSERT INTO raw.etf_prices
            (ticker, price_date, open, high, low, close, adj_close, volume)
        VALUES %s
        ON CONFLICT (ticker, price_date) DO UPDATE SET
            adj_close = EXCLUDED.adj_close,
            volume = EXCLUDED.volume,
            ingested_at = NOW()
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()
    conn.close()


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {len(TICKERS)} tickers (batched, period={PERIOD})...")
    frames = fetch_all(TICKERS)
    for ticker, df in frames.items():
        path = write_raw_parquet(df, ticker)
        print(f"  Wrote {path} ({len(df)} rows)")
    # Fail loud when a warehouse is configured: a swallowed load error lets
    # Airflow/dbt "succeed" on stale data (silently wrong metrics). Parquet-only
    # (no POSTGRES_HOST) is a legitimate mode and exits clean.
    if os.getenv("POSTGRES_HOST"):
        load_postgres(pd.concat(frames.values(), ignore_index=True))
        print("Loaded raw.etf_prices")
    else:
        print("No POSTGRES_HOST set — parquet-only (demo mode).")


if __name__ == "__main__":
    main()
