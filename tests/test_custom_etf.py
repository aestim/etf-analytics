"""Session ETF input supports European listings without live network calls."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from custom_etf import (
    CUSTOM_ETF_STATE_KEY,
    MAX_CUSTOM_ETFS,
    CustomEtfLimitError,
    DuplicateTickerError,
    InstrumentSearchError,
    InvalidSearchQueryError,
    InvalidTickerError,
    IsinNotSupportedError,
    PriceDataUnavailableError,
    add_session_prices,
    build_custom_marts,
    candidate_for_symbol,
    direct_symbol_candidate,
    fetch_price_history,
    looks_like_isin,
    merge_custom_data,
    normalize_search_query,
    normalize_search_results,
    normalize_price_history,
    normalize_ticker,
    remove_session_ticker,
    search_instruments,
    session_tickers,
)


def _history(ticker: str, *, rows: int = 35, start: float = 100.0) -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-01", periods=rows)
    return pd.DataFrame(
        {
            "ticker": ticker,
            "price_date": dates,
            "adj_close": np.linspace(start, start + rows - 1, rows),
            "volume": np.arange(rows) + 1_000,
        }
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" vwce.de ", "VWCE.DE"),
        ("VUSA.L", "VUSA.L"),
        ("EXAMPLE.VI", "EXAMPLE.VI"),
        ("069500.KS", "069500.KS"),
        ("BRK-B", "BRK-B"),
    ],
)
def test_normalize_ticker_supports_exchange_suffixes(raw, expected):
    assert normalize_ticker(raw) == expected


@pytest.mark.parametrize("raw", ["", "BAD SYMBOL", "../SPY", "ETF/EUR"])
def test_normalize_ticker_rejects_unsafe_symbols(raw):
    with pytest.raises(InvalidTickerError):
        normalize_ticker(raw)


def test_normalize_ticker_rejects_isin_with_specific_error():
    with pytest.raises(IsinNotSupportedError):
        normalize_ticker("IE00BK5BQT80")


def test_search_query_accepts_names_isins_and_symbols_before_ticker_validation():
    assert normalize_search_query("  Vanguard   FTSE All-World  ") == (
        "Vanguard FTSE All-World"
    )
    assert normalize_search_query(" IE00BK5BQT80 ") == "IE00BK5BQT80"
    assert normalize_search_query(" vwce.de ") == "vwce.de"
    assert looks_like_isin(" ie00bk5bqt80 ")

    with pytest.raises(InvalidSearchQueryError):
        normalize_search_query("   ")


def test_search_results_prioritize_etfs_without_dropping_other_funds():
    quotes = [
        {
            "symbol": "IE00BK5BQT80.SG",
            "shortname": "Vanguard FTSE All-World",
            "exchDisp": "Stuttgart",
            "quoteType": "MUTUALFUND",
        },
        {
            "symbol": "VWCE.DE",
            "longname": "Vanguard FTSE All-World UCITS ETF USD Accumulation",
            "shortname": "ignored",
            "exchDisp": "XETRA",
            "quoteType": "ETF",
        },
        {
            "symbol": "VWRL.AS",
            "longname": "Vanguard FTSE All-World UCITS ETF",
            "exchange": "AMS",
            "quoteType": "ETF",
        },
        {
            "symbol": "VWCE.DE",
            "longname": "duplicate must not replace first",
            "quoteType": "ETF",
        },
        {"symbol": "UNKNOWN.L"},
        {"shortname": "missing symbol"},
    ]

    candidates = normalize_search_results(quotes)

    assert [candidate.symbol for candidate in candidates] == [
        "VWCE.DE",
        "VWRL.AS",
        "IE00BK5BQT80.SG",
        "UNKNOWN.L",
    ]
    assert candidates[0].display_name.endswith("USD Accumulation")
    assert candidates[1].exchange == "AMS"
    assert candidates[2].display_name == "Vanguard FTSE All-World"
    assert candidates[2].provider_type == "MUTUALFUND"
    assert candidates[3].display_name == "UNKNOWN.L"
    assert candidates[3].exchange == ""
    assert candidates[3].provider_type == ""


def test_search_instruments_uses_injected_factory_and_no_market_history_call():
    calls = []

    class FakeSearch:
        quotes = [
            {
                "symbol": "VWCE.DE",
                "longname": "Vanguard FTSE All-World UCITS ETF",
                "quoteType": "ETF",
            }
        ]

    def search_factory(query, **kwargs):
        calls.append((query, kwargs))
        return FakeSearch()

    candidates = search_instruments(
        " Vanguard FTSE All-World ",
        search_factory=search_factory,
    )

    assert [candidate.symbol for candidate in candidates] == ["VWCE.DE"]
    assert calls[0][0] == "Vanguard FTSE All-World"
    assert calls[0][1]["max_results"] == 8
    assert calls[0][1]["news_count"] == 0
    assert calls[0][1]["timeout"] == 10


def test_search_instruments_enforces_result_limit_on_provider_response():
    class OverfullSearch:
        quotes = [
            {"symbol": f"ETF{index}.DE", "quoteType": "ETF"}
            for index in range(12)
        ]

    candidates = search_instruments(
        "European ETF",
        search_factory=lambda *args, **kwargs: OverfullSearch(),
    )

    assert len(candidates) == 8


def test_search_instruments_maps_provider_failure_and_empty_results():
    def failing_factory(*args, **kwargs):
        raise TimeoutError("search timeout")

    with pytest.raises(InstrumentSearchError) as exc_info:
        search_instruments("VWCE", search_factory=failing_factory)
    assert isinstance(exc_info.value.__cause__, TimeoutError)

    class EmptySearch:
        quotes = []

    assert search_instruments(
        "not found",
        search_factory=lambda *args, **kwargs: EmptySearch(),
    ) == ()


def test_direct_symbol_fallback_excludes_isins_and_names_with_spaces():
    candidate = direct_symbol_candidate(" vwce.de ")
    assert candidate is not None
    assert candidate.symbol == "VWCE.DE"
    assert direct_symbol_candidate("IE00BK5BQT80") is None
    assert direct_symbol_candidate("Vanguard FTSE All-World") is None


def test_candidate_selection_resolves_only_the_chosen_listing():
    candidates = normalize_search_results(
        [
            {"symbol": "VWCE.DE", "quoteType": "ETF"},
            {"symbol": "VWRA.L", "quoteType": "ETF"},
        ]
    )

    selected = candidate_for_symbol(candidates, "VWRA.L")

    assert selected.symbol == "VWRA.L"
    assert selected.symbol != candidates[0].symbol


def test_normalize_history_handles_yfinance_multiindex_for_european_symbol():
    ticker = "VWCE.DE"
    dates = pd.bdate_range("2026-01-01", periods=35)
    columns = pd.MultiIndex.from_product(
        [["Adj Close", "Close", "Volume"], [ticker]],
        names=["Price", "Ticker"],
    )
    values = np.column_stack(
        [
            np.linspace(100.0, 134.0, 35),
            np.linspace(101.0, 135.0, 35),
            np.arange(35) + 1_000,
        ]
    )
    raw = pd.DataFrame(values, index=dates, columns=columns)
    raw.index.name = "Date"

    result = normalize_price_history(raw, ticker)

    assert list(result.columns) == ["ticker", "price_date", "adj_close", "volume"]
    assert result["ticker"].unique().tolist() == [ticker]
    assert result.iloc[0]["adj_close"] == pytest.approx(100.0)
    assert pd.api.types.is_datetime64_any_dtype(result["price_date"])


def test_fetch_price_history_uses_injected_downloader():
    dates = pd.bdate_range("2026-01-01", periods=35)
    raw = pd.DataFrame(
        {
            "Adj Close": np.linspace(100.0, 134.0, 35),
            "Volume": np.arange(35) + 1_000,
        },
        index=dates,
    )
    raw.index.name = "Date"
    calls = []

    def downloader(ticker, **kwargs):
        calls.append((ticker, kwargs))
        return raw

    result = fetch_price_history(" vwce.de ", downloader=downloader)

    assert result["ticker"].unique().tolist() == ["VWCE.DE"]
    assert calls[0][0] == "VWCE.DE"
    assert calls[0][1]["period"] == "10y"
    assert calls[0][1]["timeout"] == 10


def test_fetch_price_history_maps_provider_failure_to_user_error():
    def failing_downloader(*args, **kwargs):
        raise TimeoutError("vendor timed out")

    with pytest.raises(PriceDataUnavailableError):
        fetch_price_history("VUSA.L", downloader=failing_downloader)


def test_custom_marts_match_dashboard_formulas():
    prices = _history("VWCE.DE")
    returns, risk = build_custom_marts(prices)

    assert pd.isna(returns.iloc[0]["daily_return"])
    assert returns.iloc[1]["daily_return"] == pytest.approx(1 / 100)
    assert risk.iloc[-1]["drawdown"] == pytest.approx(0.0)
    assert risk.iloc[-1]["annualized_vol_30d"] == pytest.approx(
        risk.iloc[-1]["rolling_vol_30d"] * np.sqrt(252)
    )


def test_session_add_remove_duplicate_and_limit_guards():
    state = {}
    add_session_prices(state, _history("VWCE.DE"))
    assert session_tickers(state) == ["VWCE.DE"]

    with pytest.raises(DuplicateTickerError):
        add_session_prices(state, _history("VWCE.DE"))

    for index in range(1, MAX_CUSTOM_ETFS):
        add_session_prices(state, _history(f"ETF{index}.DE", start=100 + index))
    with pytest.raises(CustomEtfLimitError):
        add_session_prices(state, _history("ONE-MORE.L"))

    remove_session_ticker(state, "VWCE.DE")
    assert "VWCE.DE" not in session_tickers(state)
    assert isinstance(state[CUSTOM_ETF_STATE_KEY], pd.DataFrame)


def test_custom_data_merges_without_mutating_base_frames():
    base_returns, base_risk = build_custom_marts(_history("SPY"))
    original_returns = base_returns.copy(deep=True)
    original_risk = base_risk.copy(deep=True)

    merged_returns, merged_risk = merge_custom_data(
        base_returns,
        base_risk,
        _history("VWCE.DE"),
    )

    assert set(merged_returns["ticker"]) == {"SPY", "VWCE.DE"}
    assert merged_risk is not None
    assert set(merged_risk["ticker"]) == {"SPY", "VWCE.DE"}
    pd.testing.assert_frame_equal(base_returns, original_returns)
    pd.testing.assert_frame_equal(base_risk, original_risk)
