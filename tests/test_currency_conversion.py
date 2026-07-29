"""Currency metadata and FX conversion stay explicit and deterministic."""

from __future__ import annotations

import pandas as pd
import pytest

from currency_conversion import (
    CurrencyMetadataUnavailableError,
    FxDataUnavailableError,
    convert_prices_to_base_currency,
    fetch_listing_currency,
    fetch_usd_exchange_rates,
    format_compact_money,
    format_money,
    listing_currency_code,
    listing_price_multiplier,
    normalize_listing_currency,
)


def _prices() -> pd.DataFrame:
    dates = pd.to_datetime(["2026-01-02", "2026-01-05"])
    return pd.DataFrame(
        {
            "ticker": ["US", "US", "EU", "EU", "UK", "UK"],
            "price_date": [*dates, *dates, *dates],
            "adj_close": [100.0, 110.0, 100.0, 110.0, 10_000.0, 11_000.0],
            "volume": [1_000] * 6,
        }
    )


def test_listing_currency_normalizes_pence_without_losing_scale():
    assert normalize_listing_currency("GBp") == "GBp"
    assert normalize_listing_currency("gbp") == "GBP"
    assert listing_currency_code("GBp") == "GBP"
    assert listing_price_multiplier("GBp") == pytest.approx(0.01)
    assert listing_price_multiplier("GBP") == pytest.approx(1.0)

    with pytest.raises(CurrencyMetadataUnavailableError):
        normalize_listing_currency("CHF")


def test_listing_currency_comes_from_provider_metadata():
    assert (
        fetch_listing_currency(
            "VWCE.DE",
            metadata_loader=lambda: {"currency": "EUR"},
        )
        == "EUR"
    )
    with pytest.raises(CurrencyMetadataUnavailableError):
        fetch_listing_currency("MISSING", metadata_loader=lambda: {})


def test_fx_loader_maps_yahoo_pairs_to_usd_per_currency_unit():
    dates = pd.bdate_range("2026-01-01", periods=2)
    columns = pd.MultiIndex.from_product(
        [["Adj Close"], ["EURUSD=X", "GBPUSD=X"]],
        names=["Price", "Ticker"],
    )
    history = pd.DataFrame(
        [[1.10, 1.25], [1.20, 1.30]],
        index=dates,
        columns=columns,
    )
    calls = []

    def downloader(symbols, **kwargs):
        calls.append((symbols, kwargs))
        return history

    rates = fetch_usd_exchange_rates(
        {"EUR", "GBP", "USD"},
        downloader=downloader,
    )

    assert rates.columns.tolist() == ["EUR", "GBP"]
    assert rates.iloc[-1].tolist() == pytest.approx([1.20, 1.30])
    assert calls[0][0] == ["EURUSD=X", "GBPUSD=X"]
    assert calls[0][1]["period"] == "max"


def test_conversion_uses_cross_rates_and_normalizes_pence():
    dates = pd.to_datetime(["2026-01-02", "2026-01-05"])
    usd_rates = pd.DataFrame(
        {
            "EUR": [1.10, 1.20],
            "GBP": [1.25, 1.30],
        },
        index=dates,
    )

    converted = convert_prices_to_base_currency(
        _prices(),
        {"US": "USD", "EU": "EUR", "UK": "GBp"},
        "USD",
        usd_rates,
    )
    latest = converted.groupby("ticker").tail(1).set_index("ticker")

    assert latest.loc["US", "adj_close"] == pytest.approx(110.0)
    assert latest.loc["EU", "adj_close"] == pytest.approx(132.0)
    assert latest.loc["UK", "adj_close"] == pytest.approx(143.0)

    in_eur = convert_prices_to_base_currency(
        _prices(),
        {"US": "USD", "EU": "EUR", "UK": "GBp"},
        "EUR",
        usd_rates,
    )
    latest_eur = in_eur.groupby("ticker").tail(1).set_index("ticker")
    assert latest_eur.loc["US", "adj_close"] == pytest.approx(110.0 / 1.20)
    assert latest_eur.loc["EU", "adj_close"] == pytest.approx(110.0)
    assert latest_eur.loc["UK", "adj_close"] == pytest.approx(143.0 / 1.20)


def test_conversion_forward_fills_only_short_market_holidays():
    prices = pd.DataFrame(
        {
            "ticker": ["EU", "EU", "EU"],
            "price_date": pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-12"]),
            "adj_close": [100.0, 100.0, 100.0],
        }
    )
    usd_rates = pd.DataFrame(
        {"EUR": [1.20]},
        index=pd.to_datetime(["2026-01-02"]),
    )

    converted = convert_prices_to_base_currency(
        prices,
        {"EU": "EUR"},
        "USD",
        usd_rates,
    )

    assert converted["price_date"].tolist() == list(
        pd.to_datetime(["2026-01-02", "2026-01-05"])
    )
    assert converted["adj_close"].tolist() == pytest.approx([120.0, 120.0])


def test_conversion_rejects_unknown_metadata_and_missing_fx():
    prices = _prices().query("ticker == 'EU'")

    with pytest.raises(CurrencyMetadataUnavailableError, match="EU"):
        convert_prices_to_base_currency(prices, {}, "USD", pd.DataFrame())
    with pytest.raises(FxDataUnavailableError, match="EUR"):
        convert_prices_to_base_currency(
            prices,
            {"EU": "EUR"},
            "USD",
            pd.DataFrame(),
        )


def test_money_formatting_depends_on_currency_not_language():
    assert format_money(12_345, "USD") == "$12,345"
    assert format_money(-12_345, "EUR") == "-€12,345"
    assert format_money(12_345, "GBP") == "£12,345"
    assert format_compact_money(2_500_000, "EUR") == "€2.50M"
