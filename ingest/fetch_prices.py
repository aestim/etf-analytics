#!/usr/bin/env python3
"""
Fetch daily ETF prices from Yahoo Finance in one batched request
(tickers from ETF_TICKERS env). Writes raw parquet under
data/raw/{ticker}/ and optionally loads Postgres.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
# Defaults mirror .env.example (17-ticker cross-asset universe, 10y window)
DEFAULT_TICKERS = "SGOV,VGIT,TLT,BND,LQD,HYG,TIP,SPY,QQQ,QLD,TQQQ,VEA,SCHD,VWO,IWM,VNQ,GLD"
TICKERS = [t.strip() for t in os.getenv("ETF_TICKERS", DEFAULT_TICKERS).split(",") if t.strip()]
_raw = Path(os.getenv("RAW_DATA_DIR", ROOT / "data" / "raw"))
RAW_DIR = _raw if _raw.is_absolute() else ROOT / _raw
PERIOD = os.getenv("FETCH_PERIOD", "10y")


def _normalize_history(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    df = df.reset_index()
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    rename = {
        "date": "price_date",
        "adj_close": "adj_close",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "adj_close" not in df.columns and "close" in df.columns:
        df["adj_close"] = df["close"]
    df["ticker"] = ticker
    df["price_date"] = pd.to_datetime(df["price_date"]).dt.date
    df["_ingested_at"] = datetime.now(timezone.utc)
    cols = ["ticker", "price_date", "open", "high", "low", "close", "adj_close", "volume", "_ingested_at"]
    keep = [c for c in cols if c in df.columns]
    return df[keep].drop_duplicates(subset=["ticker", "price_date"])


def fetch_all(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """One batched yfinance request for the whole universe (threaded under the hood)."""
    data = yf.download(
        tickers, period=PERIOD, auto_adjust=False, group_by="ticker", progress=False
    )
    if data is None or data.empty:
        raise RuntimeError(f"No data returned for {tickers}")
    frames: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        history = data[ticker] if isinstance(data.columns, pd.MultiIndex) else data
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

    conn = psycopg2.connect(
        host=host,
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "etf_analytics"),
        user=os.getenv("POSTGRES_USER", "etf"),
        password=os.getenv("POSTGRES_PASSWORD", "etf"),
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
    print(f"Fetching {len(TICKERS)} tickers (batched)...")
    frames = fetch_all(TICKERS)
    for ticker, df in frames.items():
        path = write_raw_parquet(df, ticker)
        print(f"  Wrote {path} ({len(df)} rows)")
    try:
        load_postgres(pd.concat(frames.values(), ignore_index=True))
        print("Loaded raw.etf_prices")
    except Exception as exc:  # noqa: BLE001 — portfolio script; log and continue without DB
        print(f"Postgres skip: {exc}")


if __name__ == "__main__":
    main()
