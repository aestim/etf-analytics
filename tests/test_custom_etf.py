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
    InstrumentCandidate,
    InstrumentSearchError,
    InvalidSearchQueryError,
    InvalidTickerError,
    IsinNotSupportedError,
    PriceDataUnavailableError,
    add_candidate_volumes,
    add_session_prices,
    build_indexed_price_comparison,
    build_custom_marts,
    candidate_for_symbol,
    direct_symbol_candidate,
    fetch_average_daily_volumes,
    fetch_price_history,
    looks_like_isin,
    merge_custom_data,
    normalize_search_query,
    normalize_search_results,
    normalize_price_history,
    normalize_ticker,
    remove_session_ticker,
    search_instruments,
    search_query_variants,
    session_instrument_candidates,
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


def test_search_query_variants_relax_share_class_terms_only():
    assert search_query_variants(" iShares  NASDAQ 100 (Acc) ") == (
        "iShares NASDAQ 100 (Acc)",
        "iShares NASDAQ 100",
        "iShares NASDAQ 100 UCITS ETF",
    )
    assert search_query_variants("NASDAQ 100 Acc ETF") == (
        "NASDAQ 100 Acc ETF",
        "NASDAQ 100 ETF",
        "NASDAQ 100 UCITS ETF",
        "Invesco QQQ",
    )
    assert search_query_variants("NASDAQ 100") == (
        "NASDAQ 100",
        "NASDAQ 100 UCITS ETF",
        "Invesco QQQ",
    )
    assert search_query_variants("Vanguard FTSE All-World") == (
        "Vanguard FTSE All-World",
    )


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
            "currency": "EUR",
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
    assert candidates[0].currency == "EUR"
    assert candidates[1].exchange == "AMS"
    assert candidates[2].display_name == "Vanguard FTSE All-World"
    assert candidates[2].provider_type == "MUTUALFUND"
    assert candidates[3].display_name == "UNKNOWN.L"
    assert candidates[3].exchange == ""
    assert candidates[3].provider_type == ""


def test_symbol_search_prioritizes_exact_base_and_complete_name():
    quotes = [
        {
            "symbol": "SXRV.HM",
            "shortname": "iShsVII-NASDAQ 100 UCITS ETF R",
            "exchDisp": "Hamburg",
            "quoteType": "ETF",
        },
        {
            "symbol": "SXRVD.XD",
            "shortname": "iShares NASDAQ 100 UCITS ETF",
            "exchDisp": "DXE",
            "quoteType": "ETF",
        },
        {
            "symbol": "SXRV.SG",
            "shortname": "iShares NASDAQ 100 UCITS ETF",
            "exchDisp": "Stuttgart",
            "quoteType": "MUTUALFUND",
        },
        {
            "symbol": "SXRV.DE",
            "longname": "iShares NASDAQ 100 UCITS ETF USD (Acc)",
            "exchDisp": "XETRA",
            "quoteType": "ETF",
        },
    ]

    candidates = normalize_search_results(quotes, query="sxrv")

    assert [candidate.symbol for candidate in candidates] == [
        "SXRV.DE",
        "SXRV.HM",
        "SXRV.SG",
        "SXRVD.XD",
    ]


def test_full_yahoo_symbol_outranks_provider_classification():
    quotes = [
        {"symbol": "SXRV.DE", "quoteType": "ETF"},
        {"symbol": "SXRV.SG", "quoteType": "MUTUALFUND"},
    ]

    candidates = normalize_search_results(quotes, query="SXRV.SG")

    assert [candidate.symbol for candidate in candidates] == [
        "SXRV.SG",
        "SXRV.DE",
    ]


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
    assert calls[0][1]["max_results"] == 20
    assert calls[0][1]["news_count"] == 0
    assert calls[0][1]["timeout"] == 10


def test_search_instruments_enforces_result_limit_on_provider_response():
    class OverfullSearch:
        quotes = [
            {"symbol": f"ETF{index}.DE", "quoteType": "ETF"} for index in range(12)
        ]

    candidates = search_instruments(
        "European ETF",
        search_factory=lambda *args, **kwargs: OverfullSearch(),
    )

    assert len(candidates) == 8


def test_search_instruments_retries_without_share_class_hint_and_reranks():
    calls = []

    class SearchResult:
        def __init__(self, quotes):
            self.quotes = quotes

    def search_factory(query, **kwargs):
        calls.append(query)
        if query == "iShares NASDAQ 100 (Acc)":
            return SearchResult([])
        return SearchResult(
            [
                {
                    "symbol": "EXXT.DE",
                    "longname": "iShares NASDAQ-100 UCITS ETF (DE)",
                    "quoteType": "ETF",
                },
                {
                    "symbol": "NASQ.AS",
                    "longname": ("iShares NASDAQ 100 Swap UCITS ETF USD (Acc)"),
                    "quoteType": "ETF",
                },
            ]
        )

    candidates = search_instruments(
        "iShares NASDAQ 100 (Acc)",
        search_factory=search_factory,
    )

    assert calls == [
        "iShares NASDAQ 100 (Acc)",
        "iShares NASDAQ 100",
        "iShares NASDAQ 100 UCITS ETF",
    ]
    assert [candidate.symbol for candidate in candidates] == [
        "NASQ.AS",
        "EXXT.DE",
    ]


def test_candidate_volume_sort_pins_exact_symbol_and_keeps_missing_last():
    candidates = normalize_search_results(
        [
            {"symbol": "SXRV.DE", "quoteType": "ETF"},
            {"symbol": "SXRV.HM", "quoteType": "ETF"},
            {"symbol": "SXRV.SG", "quoteType": "MUTUALFUND"},
        ],
        query="SXRV.SG",
    )

    ranked = add_candidate_volumes(
        candidates,
        {"SXRV.DE": 50_000, "SXRV.HM": 100_000},
        query="SXRV.SG",
    )

    assert [candidate.symbol for candidate in ranked] == [
        "SXRV.SG",
        "SXRV.HM",
        "SXRV.DE",
    ]
    assert ranked[0].average_daily_volume is None
    assert ranked[1].average_daily_volume == pytest.approx(100_000)


def test_candidate_volume_sort_keeps_acc_matches_above_high_volume_income_funds():
    candidates = normalize_search_results(
        [
            {
                "symbol": "QQQI",
                "longname": "NEOS Nasdaq 100 High Income ETF",
                "quoteType": "ETF",
            },
            {
                "symbol": "EQQB.DE",
                "longname": "Invesco EQQQ Nasdaq-100 UCITS ETF Acc",
                "quoteType": "ETF",
            },
            {
                "symbol": "XNAS.L",
                "longname": "Xtrackers Nasdaq 100 UCITS ETF 1C",
                "quoteType": "ETF",
            },
        ],
        query="NASDAQ 100 acc",
    )

    ranked = add_candidate_volumes(
        candidates,
        {"QQQI": 5_000_000, "EQQB.DE": 3_000, "XNAS.L": 40_000},
        query="NASDAQ 100 acc",
    )

    assert [candidate.symbol for candidate in ranked] == [
        "EQQB.DE",
        "XNAS.L",
        "QQQI",
    ]


def test_candidate_volume_mode_sorts_primary_acc_pool_by_volume():
    candidates = normalize_search_results(
        [
            {
                "symbol": "QQQI",
                "longname": "NEOS Nasdaq 100 High Income ETF",
                "quoteType": "ETF",
            },
            {
                "symbol": "EQQB.DE",
                "longname": "Invesco EQQQ Nasdaq-100 UCITS ETF Acc",
                "quoteType": "ETF",
            },
            {
                "symbol": "NQSE.DE",
                "longname": "iShares Nasdaq 100 UCITS ETF",
                "quoteType": "ETF",
            },
        ],
        query="NASDAQ 100 acc",
    )

    ranked = add_candidate_volumes(
        candidates,
        {"QQQI": 5_000_000, "EQQB.DE": 3_000, "NQSE.DE": 250_000},
        query="NASDAQ 100 acc",
        sort_mode="volume",
    )

    assert [candidate.symbol for candidate in ranked] == [
        "NQSE.DE",
        "EQQB.DE",
    ]


def test_search_instruments_uses_injected_volume_ordering():
    class FakeSearch:
        quotes = [
            {"symbol": "LOW.DE", "quoteType": "ETF"},
            {"symbol": "HIGH.DE", "quoteType": "ETF"},
        ]

    volume_calls = []

    def volume_loader(symbols):
        volume_calls.append(symbols)
        return {"LOW.DE": 10, "HIGH.DE": 1_000}

    candidates = search_instruments(
        "European ETF",
        search_factory=lambda *args, **kwargs: FakeSearch(),
        volume_loader=volume_loader,
    )

    assert [candidate.symbol for candidate in candidates] == [
        "HIGH.DE",
        "LOW.DE",
    ]
    assert volume_calls == [("LOW.DE", "HIGH.DE")]


def test_fetch_average_daily_volumes_uses_one_batch_and_ignores_zeroes():
    symbols = ("LOW.DE", "HIGH.DE")
    columns = pd.MultiIndex.from_product(
        [["Close", "Volume"], symbols],
        names=["Price", "Ticker"],
    )
    history = pd.DataFrame(
        [
            [10.0, 20.0, 0.0, 1_000.0],
            [11.0, 21.0, 100.0, 3_000.0],
        ],
        columns=columns,
    )
    calls = []

    def downloader(requested_symbols, **kwargs):
        calls.append((requested_symbols, kwargs))
        return history

    volumes = fetch_average_daily_volumes(
        symbols,
        downloader=downloader,
    )

    assert volumes == {"LOW.DE": 100.0, "HIGH.DE": 2_000.0}
    assert calls[0][0] == ["LOW.DE", "HIGH.DE"]
    assert calls[0][1]["period"] == "1mo"


def test_search_instruments_volume_mode_enriches_before_final_limit():
    class LargeSearch:
        quotes = [
            {
                "symbol": f"ETF{index}.DE",
                "longname": f"European UCITS ETF {index}",
                "quoteType": "ETF",
            }
            for index in range(12)
        ]

    candidates = search_instruments(
        "European ETF",
        search_factory=lambda *args, **kwargs: LargeSearch(),
        volume_loader=lambda symbols: {
            symbol: (1_000_000 if symbol == "ETF10.DE" else 1) for symbol in symbols
        },
        sort_mode="volume",
    )

    assert len(candidates) == 8
    assert candidates[0].symbol == "ETF10.DE"


def test_search_instruments_keeps_results_when_one_variant_fails():
    class SearchResult:
        def __init__(self, quotes):
            self.quotes = quotes

    def search_factory(query, **kwargs):
        if query != "NASDAQ 100":
            raise TimeoutError("one Yahoo variant failed")
        return SearchResult([{"symbol": "NQSE.DE", "quoteType": "ETF"}])

    candidates = search_instruments(
        "NASDAQ 100 acc",
        search_factory=search_factory,
    )

    assert [candidate.symbol for candidate in candidates] == ["NQSE.DE"]


def test_nasdaq_100_alias_search_keeps_qqq_in_large_candidate_pool():
    class SearchResult:
        def __init__(self, quotes):
            self.quotes = quotes

    def search_factory(query, **kwargs):
        if query == "Invesco QQQ":
            return SearchResult(
                [
                    {
                        "symbol": "QQQ",
                        "longname": "Invesco QQQ Trust",
                        "quoteType": "ETF",
                    }
                ]
            )
        return SearchResult(
            [
                {
                    "symbol": f"ETF{index}.{query[-2:].upper()}",
                    "longname": f"NASDAQ 100 ETF {index}",
                    "quoteType": "ETF",
                }
                for index in range(20)
            ]
        )

    candidates = search_instruments(
        "NASDAQ 100",
        search_factory=search_factory,
        volume_loader=lambda symbols: {
            symbol: 50_000_000 if symbol == "QQQ" else 1_000 for symbol in symbols
        },
        sort_mode="volume",
    )

    assert candidates[0].symbol == "QQQ"


def test_search_instruments_maps_provider_failure_and_empty_results():
    def failing_factory(*args, **kwargs):
        raise TimeoutError("search timeout")

    with pytest.raises(InstrumentSearchError) as exc_info:
        search_instruments("VWCE", search_factory=failing_factory)
    assert isinstance(exc_info.value.__cause__, TimeoutError)

    class EmptySearch:
        quotes = []

    assert (
        search_instruments(
            "not found",
            search_factory=lambda *args, **kwargs: EmptySearch(),
        )
        == ()
    )


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


def test_normalize_history_rejects_close_only_response():
    raw = pd.DataFrame(
        {"Close": np.linspace(100.0, 134.0, 35)},
        index=pd.bdate_range("2026-01-01", periods=35, name="Date"),
    )

    with pytest.raises(PriceDataUnavailableError):
        normalize_price_history(raw, "VWCE.DE")


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


def test_indexed_price_comparison_uses_first_shared_date_and_common_base():
    prices = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "AAA", "BBB", "BBB"],
            "price_date": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-02",
                    "2026-01-03",
                ]
            ),
            "adj_close": [10.0, 20.0, 30.0, 200.0, 100.0],
        }
    )

    indexed = build_indexed_price_comparison(prices)

    assert indexed["price_date"].min() == pd.Timestamp("2026-01-02")
    first_values = indexed.groupby("ticker").head(1)
    assert first_values["indexed_price"].tolist() == pytest.approx([100.0, 100.0])
    final_values = indexed.groupby("ticker").tail(1).set_index("ticker")
    assert final_values.loc["AAA", "indexed_price"] == pytest.approx(150.0)
    assert final_values.loc["BBB", "indexed_price"] == pytest.approx(50.0)


def test_indexed_price_comparison_returns_empty_without_shared_dates():
    prices = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "price_date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "adj_close": [10.0, 20.0],
        }
    )

    assert build_indexed_price_comparison(prices).empty


def test_session_add_remove_duplicate_and_limit_guards():
    state = {}
    add_session_prices(state, _history("VWCE.DE"))
    assert session_tickers(state) == ["VWCE.DE"]
    assert session_instrument_candidates(state) == (
        InstrumentCandidate(
            symbol="VWCE.DE",
            display_name="VWCE.DE",
            exchange="",
            provider_type="",
        ),
    )

    with pytest.raises(DuplicateTickerError):
        add_session_prices(state, _history("VWCE.DE"))

    for index in range(1, MAX_CUSTOM_ETFS):
        add_session_prices(state, _history(f"ETF{index}.DE", start=100 + index))
    with pytest.raises(CustomEtfLimitError):
        add_session_prices(state, _history("ONE-MORE.L"))

    remove_session_ticker(state, "VWCE.DE")
    assert "VWCE.DE" not in session_tickers(state)
    assert isinstance(state[CUSTOM_ETF_STATE_KEY], pd.DataFrame)


def test_session_search_metadata_is_stored_and_removed_with_prices():
    state = {}
    candidate = InstrumentCandidate(
        symbol="NQSE.DE",
        display_name="iShares NASDAQ 100 UCITS ETF",
        exchange="XETRA",
        provider_type="ETF",
        average_daily_volume=252_746,
        currency="EUR",
    )

    add_session_prices(
        state,
        _history("NQSE.DE"),
        candidate=candidate,
    )

    assert session_instrument_candidates(state) == (candidate,)

    remove_session_ticker(state, "NQSE.DE")

    assert session_instrument_candidates(state) == ()


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
