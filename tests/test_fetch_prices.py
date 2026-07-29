"""Daily ingest behavior without making live Yahoo or Postgres calls."""

from pathlib import Path

import pandas as pd
import pytest

import fetch_prices


def test_normalize_history_rejects_unadjusted_close_fallback():
    history = pd.DataFrame(
        {
            "Open": [99.0],
            "High": [102.0],
            "Low": [98.0],
            "Close": [101.0],
            "Volume": [10],
        },
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


def test_fetch_all_requests_max_and_preserves_each_ticker_inception():
    dates = pd.DatetimeIndex(["2005-07-29", "2020-06-01", "2026-07-29"], name="Date")
    spy = pd.DataFrame(
        {
            "Close": [100.0, 200.0, 300.0],
            "Adj Close": [90.0, 190.0, 290.0],
            "Volume": [10, 20, 30],
        },
        index=dates,
    )
    sgov = pd.DataFrame(
        {
            "Close": [None, 100.0, 101.0],
            "Adj Close": [None, 99.0, 100.0],
            "Volume": [None, 40, 50],
        },
        index=dates,
    )
    response = pd.concat({"SPY": spy, "SGOV": sgov}, axis=1)
    call: dict[str, object] = {}

    def downloader(tickers, **kwargs):
        call["tickers"] = tickers
        call.update(kwargs)
        return response

    frames = fetch_prices.fetch_all(["SPY", "SGOV"], downloader=downloader)

    assert call["period"] == "max"
    assert call["auto_adjust"] is False
    assert call["group_by"] == "ticker"
    assert frames["SPY"]["price_date"].min().isoformat() == "2005-07-29"
    assert frames["SGOV"]["price_date"].min().isoformat() == "2020-06-01"
    assert len(frames["SPY"]) == 3
    assert len(frames["SGOV"]) == 2


def test_fetch_all_fails_loud_when_batch_omits_a_ticker():
    dates = pd.DatetimeIndex(["2026-07-29"], name="Date")
    response = pd.concat(
        {
            "SPY": pd.DataFrame(
                {"Adj Close": [100.0], "Volume": [10]},
                index=dates,
            )
        },
        axis=1,
    )

    with pytest.raises(RuntimeError, match="No data returned for SGOV"):
        fetch_prices.fetch_all(
            ["SPY", "SGOV"],
            downloader=lambda tickers, **kwargs: response,
        )


def test_main_supports_parquet_only_mode(monkeypatch):
    frame = pd.DataFrame(
        {"ticker": ["SPY"], "price_date": ["2026-07-21"], "adj_close": [101.0]}
    )
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.setattr(fetch_prices, "TICKERS", ["SPY"])
    monkeypatch.setattr(fetch_prices, "fetch_all", lambda tickers: {"SPY": frame})
    monkeypatch.setattr(
        fetch_prices, "write_raw_parquet", lambda df, ticker: Path("prices.parquet")
    )
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
    monkeypatch.setattr(
        fetch_prices, "write_raw_parquet", lambda df, ticker: Path("prices.parquet")
    )
    monkeypatch.setattr(
        fetch_prices,
        "load_postgres",
        lambda df: (_ for _ in ()).throw(ConnectionError("warehouse unavailable")),
    )

    with pytest.raises(ConnectionError, match="warehouse unavailable"):
        fetch_prices.main()
