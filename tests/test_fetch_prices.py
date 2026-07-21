"""Daily ingest behavior without making live Yahoo or Postgres calls."""

from pathlib import Path

import pandas as pd
import pytest

import fetch_prices


def test_normalize_history_uses_close_when_adjusted_close_is_missing():
    history = pd.DataFrame(
        {"Open": [99.0], "High": [102.0], "Low": [98.0], "Close": [101.0], "Volume": [10]},
        index=pd.DatetimeIndex(["2026-07-21"], name="Date"),
    )

    result = fetch_prices._normalize_history(history, "SPY")

    assert result.loc[0, "ticker"] == "SPY"
    assert result.loc[0, "adj_close"] == 101.0
    assert str(result.loc[0, "price_date"]) == "2026-07-21"


def test_main_supports_parquet_only_mode(monkeypatch):
    frame = pd.DataFrame(
        {"ticker": ["SPY"], "price_date": ["2026-07-21"], "adj_close": [101.0]}
    )
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.setattr(fetch_prices, "TICKERS", ["SPY"])
    monkeypatch.setattr(fetch_prices, "fetch_all", lambda tickers: {"SPY": frame})
    monkeypatch.setattr(fetch_prices, "write_raw_parquet", lambda df, ticker: Path("prices.parquet"))
    monkeypatch.setattr(
        fetch_prices,
        "load_postgres",
        lambda df: pytest.fail("Postgres load must be skipped without POSTGRES_HOST"),
    )

    fetch_prices.main()


def test_main_fails_loud_when_configured_warehouse_load_fails(monkeypatch):
    frame = pd.DataFrame(
        {"ticker": ["SPY"], "price_date": ["2026-07-21"], "adj_close": [101.0]}
    )
    monkeypatch.setenv("POSTGRES_HOST", "warehouse.example")
    monkeypatch.setattr(fetch_prices, "TICKERS", ["SPY"])
    monkeypatch.setattr(fetch_prices, "fetch_all", lambda tickers: {"SPY": frame})
    monkeypatch.setattr(fetch_prices, "write_raw_parquet", lambda df, ticker: Path("prices.parquet"))
    monkeypatch.setattr(
        fetch_prices,
        "load_postgres",
        lambda df: (_ for _ in ()).throw(ConnectionError("warehouse unavailable")),
    )

    with pytest.raises(ConnectionError, match="warehouse unavailable"):
        fetch_prices.main()
