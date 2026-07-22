"""Hosted demo-mode data stays aligned with the warehouse mart definitions."""

import numpy as np
import pandas as pd
import pytest

import db


def test_latest_snapshot_per_ticker_is_loaded_and_cleaned(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "raw"
    old_spy = raw / "SPY" / "dt=2026-07-20"
    new_spy = raw / "SPY" / "dt=2026-07-21"
    qqq = raw / "QQQ" / "dt=2026-07-20"
    for directory in (old_spy, new_spy, qqq):
        directory.mkdir(parents=True)

    pd.DataFrame(
        {"ticker": ["SPY"], "price_date": ["2026-07-18"], "adj_close": [90.0]}
    ).to_parquet(old_spy / "prices.parquet", index=False)
    pd.DataFrame(
        {
            "ticker": [" spy ", "SPY"],
            "price_date": ["2026-07-21", "2026-07-21"],
            "adj_close": [100.0, 999.0],
        }
    ).to_parquet(new_spy / "prices.parquet", index=False)
    pd.DataFrame(
        {"ticker": ["qqq"], "price_date": ["2026-07-20"], "adj_close": [200.0]}
    ).to_parquet(qqq / "prices.parquet", index=False)
    monkeypatch.setattr(db, "ROOT", tmp_path)

    result = db._read_latest_snapshots()

    assert result[["ticker", "adj_close"]].to_dict("records") == [
        {"ticker": "QQQ", "adj_close": 200.0},
        {"ticker": "SPY", "adj_close": 100.0},
    ]
    assert pd.api.types.is_datetime64_any_dtype(result["price_date"])


def test_parquet_marts_match_return_volatility_and_drawdown_definitions(monkeypatch):
    dates = pd.bdate_range("2026-01-01", periods=31)
    snapshots = pd.DataFrame(
        {
            "ticker": ["FLAT"] * 31 + ["DROP"] * 31,
            "price_date": list(dates) * 2,
            "adj_close": [100.0] * 31 + [100.0] * 30 + [80.0],
            "volume": [1_000] * 31 + [2_000] * 31,
        }
    )
    monkeypatch.setattr(db, "_read_latest_snapshots", lambda: snapshots)

    returns, risk = db._parquet_marts.__wrapped__()

    assert returns.groupby("ticker")["volume"].first().to_dict() == {
        "DROP": 2_000,
        "FLAT": 1_000,
    }
    assert returns.groupby("ticker").head(1)["daily_return"].isna().all()
    drop_last = risk[risk["ticker"] == "DROP"].iloc[-1]
    assert drop_last["drawdown"] == pytest.approx(-0.2)
    assert drop_last["annualized_vol_30d"] == pytest.approx(
        drop_last["rolling_vol_30d"] * np.sqrt(252)
    )
    assert (risk[risk["ticker"] == "FLAT"]["drawdown"] == 0.0).all()


def test_short_dataframes_use_content_width_without_widening_two_columns():
    two_columns = pd.DataFrame({"ticker": ["SPY"], "return": [0.1]})
    three_columns = two_columns.assign(as_of_date="2026-07-22")

    assert db.dataframe_width(two_columns) == "content"
    assert db.dataframe_width(three_columns) == "stretch"


def test_shared_plotly_layout_keeps_mobile_plot_area_for_the_chart():
    legend = db.PLOTLY_LAYOUT["legend"]
    margin = db.PLOTLY_LAYOUT["margin"]

    assert legend["orientation"] == "h"
    assert legend["font"]["size"] >= 14
    assert margin["r"] <= 20
    assert db.PLOTLY_LAYOUT["font"]["size"] >= 15
