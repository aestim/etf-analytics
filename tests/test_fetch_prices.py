"""Daily ingest behavior without making live Yahoo or Postgres calls."""

from pathlib import Path

import pandas as pd
import pytest

import fetch_prices


def test_normalize_history_rejects_unadjusted_close_fallback():
    history = pd.DataFrame(
        {"Open": [99.0], "High": [102.0], "Low": [98.0], "Close": [101.0], "Volume": [10]},
        index=pd.DatetimeIndex(["2026-07-21"], name="Date"),
    )

    with pytest.raises(RuntimeError, match="no Adjusted Close.*refusing"):
        fetch_prices._normalize_history(history, "SPY")


def test_normalize_history_keeps_only_usable_adjusted_prices():
    history = pd.DataFrame(
        {
            "Close": [101.0, 102.0],
            "Adj Close": [100.5, None],
            "Volume": [10, 11],
        },
        index=pd.DatetimeIndex(["2026-07-21", "2026-07-22"], name="Date"),
    )

    result = fetch_prices._normalize_history(history, "SPY")

    assert result["ticker"].tolist() == ["SPY"]
    assert result["adj_close"].tolist() == [100.5]
    assert str(result.loc[0, "price_date"]) == "2026-07-21"


def test_configured_tickers_uses_file_and_deduplicates(monkeypatch, tmp_path):
    universe = tmp_path / "etf_universe.txt"
    universe.write_text("# comment\nspy\nQQQ\nSPY\n", encoding="utf-8")
    monkeypatch.delenv("ETF_TICKERS", raising=False)
    monkeypatch.setattr(fetch_prices, "UNIVERSE_FILE", universe)

    assert fetch_prices.configured_tickers() == ["SPY", "QQQ"]


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
