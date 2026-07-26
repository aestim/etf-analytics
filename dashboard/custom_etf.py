"""Session-only custom market data for dashboard comparisons.

The batch pipeline owns the configured ETF universe. This module deliberately
keeps visitor-supplied symbols separate: prices live only in Streamlit session
state and are never written to PostgreSQL, parquet, dbt seeds, or the Ask
schema.
"""

from __future__ import annotations

import re
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
import pandas as pd

CUSTOM_ETF_STATE_KEY = "custom_etf_prices"
MAX_CUSTOM_ETFS = 5
MIN_PRICE_ROWS = 30
MAX_SEARCH_RESULTS = 8
MAX_SEARCH_CANDIDATES = 20
MAX_SEARCH_QUERY_LENGTH = 160
TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,19}$")
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
SEARCH_TOKEN_PATTERN = re.compile(r"[A-Z0-9]+")
SHARE_CLASS_SEARCH_TERMS = {
    "ACC",
    "ACCUMULATING",
    "ACCUMULATION",
    "CAPITALISATION",
    "CAPITALIZATION",
    "DIST",
    "DISTRIBUTING",
    "DISTRIBUTION",
}
SEARCH_TERM_ALIASES = {
    "ACCUMULATING": "ACC",
    "ACCUMULATION": "ACC",
    "CAPITALISATION": "ACC",
    "CAPITALIZATION": "ACC",
    "DISTRIBUTING": "DIST",
    "DISTRIBUTION": "DIST",
}
INDEX_QUERY_EXPANSIONS = (
    (
        frozenset({"NASDAQ", "100"}),
        ("NASDAQ 100 UCITS ETF", "Invesco QQQ"),
        frozenset({"QQQ"}),
    ),
)
INDEX_PROVIDER_TERMS = {
    "AMUNDI",
    "AXA",
    "DWS",
    "FIRST",
    "HSBC",
    "INVESCO",
    "ISHARES",
    "JPMORGAN",
    "UBS",
    "VANGUARD",
    "WISDOMTREE",
    "XTRACKERS",
}

PRICE_COLUMNS = ["ticker", "price_date", "adj_close", "volume"]
RETURN_COLUMNS = PRICE_COLUMNS + ["daily_return"]
RISK_COLUMNS = [
    "ticker",
    "price_date",
    "rolling_vol_30d",
    "annualized_vol_30d",
    "drawdown",
]


@dataclass(frozen=True)
class InstrumentCandidate:
    """One best-effort Yahoo search result shown for user selection."""

    symbol: str
    display_name: str
    exchange: str
    provider_type: str
    average_daily_volume: float | None = None


class CustomEtfError(ValueError):
    """Base class for expected, user-facing custom-symbol failures."""


class InvalidTickerError(CustomEtfError):
    """The supplied value is not a supported Yahoo Finance symbol."""


class IsinNotSupportedError(CustomEtfError):
    """An ISIN was supplied where a Yahoo Finance symbol is required."""


class PriceDataUnavailableError(CustomEtfError):
    """Yahoo Finance returned no usable history for the supplied symbol."""


class InsufficientHistoryError(CustomEtfError):
    """The symbol exists but has too little history for useful analytics."""


class DuplicateTickerError(CustomEtfError):
    """The symbol is already available in the current session."""


class CustomEtfLimitError(CustomEtfError):
    """The current session already contains the maximum custom symbols."""


class InvalidSearchQueryError(CustomEtfError):
    """The supplied search text is empty or unreasonably long."""


class InstrumentSearchError(RuntimeError):
    """Yahoo search failed before candidates could be returned."""


def normalize_search_query(value: str) -> str:
    """Normalize free-form names, ISINs and Yahoo symbols for search."""

    query = " ".join(value.strip().split())
    if not query or len(query) > MAX_SEARCH_QUERY_LENGTH:
        raise InvalidSearchQueryError(query)
    return query


def search_query_variants(value: str) -> tuple[str, ...]:
    """Return exact, relaxed and known-index alias searches."""

    query = normalize_search_query(value)
    tokens = query.split()
    relaxed_tokens = [
        token
        for token in tokens
        if token.strip("()[]{}.,").upper() not in SHARE_CLASS_SEARCH_TERMS
    ]
    relaxed_query = " ".join(relaxed_tokens)
    variants = [query]
    if relaxed_query and relaxed_query != query:
        variants.append(relaxed_query)
        relaxed_terms = _canonical_search_terms(relaxed_query)
        if "ETF" not in relaxed_terms and "UCITS" not in relaxed_terms:
            variants.append(f"{relaxed_query} UCITS ETF")

    requested_terms = _canonical_search_terms(query)
    if requested_terms & INDEX_PROVIDER_TERMS:
        return tuple(variants)
    for required_terms, extra_queries, _ in INDEX_QUERY_EXPANSIONS:
        if not required_terms.issubset(requested_terms):
            continue
        variants.extend(
            extra_query for extra_query in extra_queries if extra_query not in variants
        )
    return tuple(variants)


def looks_like_isin(value: str) -> bool:
    """Return whether the normalized query has an ISIN-shaped value."""

    try:
        query = normalize_search_query(value)
    except InvalidSearchQueryError:
        return False
    return ISIN_PATTERN.fullmatch(query.upper()) is not None


def _first_text(*values: Any) -> str:
    for value in values:
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return ""


def _provider_type_rank(candidate: InstrumentCandidate) -> int:
    """Prioritize provider-labeled ETFs without discarding other funds."""

    provider_type = candidate.provider_type.upper()
    if provider_type == "ETF":
        return 0
    if "FUND" in provider_type:
        return 1
    return 2


def _symbol_shaped_query(query: str) -> str | None:
    """Return an uppercase ticker query, excluding ISIN-shaped values."""

    normalized = query.upper()
    if ISIN_PATTERN.fullmatch(normalized):
        return None
    if TICKER_PATTERN.fullmatch(normalized):
        return normalized
    return None


def _canonical_search_terms(value: str) -> frozenset[str]:
    terms = SEARCH_TOKEN_PATTERN.findall(value.upper())
    return frozenset(SEARCH_TERM_ALIASES.get(term, term) for term in terms)


def _preferred_symbols_for_query(query: str) -> frozenset[str]:
    requested_terms = _canonical_search_terms(query)
    if requested_terms & INDEX_PROVIDER_TERMS:
        return frozenset()
    preferred: set[str] = set()
    for required_terms, _, symbols in INDEX_QUERY_EXPANSIONS:
        if required_terms.issubset(requested_terms):
            preferred.update(symbols)
    return frozenset(preferred)


def _candidate_rank(
    candidate: InstrumentCandidate,
    *,
    query_symbol: str | None,
    preferred_symbols: frozenset[str],
    term_matches: int,
    has_long_name: bool,
    provider_position: int,
) -> tuple[int, int, int, int, int, int, int]:
    """Rank exact symbols and complete names before weaker Yahoo matches."""

    exact_symbol = query_symbol is not None and candidate.symbol == query_symbol
    exact_base_symbol = (
        query_symbol is not None
        and "." not in query_symbol
        and candidate.symbol.partition(".")[0] == query_symbol
    )
    return (
        0 if exact_symbol else 1,
        0 if exact_base_symbol else 1,
        0 if candidate.symbol in preferred_symbols else 1,
        -term_matches,
        _provider_type_rank(candidate),
        0 if has_long_name else 1,
        provider_position,
    )


def normalize_search_results(
    quotes: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    query: str = "",
    preferred_symbols: frozenset[str] = frozenset(),
) -> tuple[InstrumentCandidate, ...]:
    """Map partial Yahoo quote dictionaries to ranked, deduplicated candidates."""

    query_symbol = _symbol_shaped_query(query) if query else None
    requested_terms = _canonical_search_terms(query)
    ranked_candidates: list[tuple[InstrumentCandidate, bool, int]] = []
    seen_symbols: set[str] = set()
    for provider_position, quote in enumerate(quotes):
        if not isinstance(quote, dict):
            continue
        raw_symbol = quote.get("symbol")
        if not isinstance(raw_symbol, str):
            continue
        try:
            symbol = normalize_ticker(raw_symbol)
        except (InvalidTickerError, IsinNotSupportedError):
            continue
        if symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        long_name = _first_text(quote.get("longname"))
        candidate = InstrumentCandidate(
            symbol=symbol,
            display_name=_first_text(
                long_name,
                quote.get("shortname"),
                symbol,
            ),
            exchange=_first_text(
                quote.get("exchDisp"),
                quote.get("exchange"),
            ),
            provider_type=_first_text(
                quote.get("quoteType"),
                quote.get("typeDisp"),
            ),
        )
        ranked_candidates.append((candidate, bool(long_name), provider_position))

    ranked_candidates.sort(
        key=lambda item: _candidate_rank(
            item[0],
            query_symbol=query_symbol,
            preferred_symbols=preferred_symbols,
            term_matches=len(
                requested_terms
                & _canonical_search_terms(f"{item[0].symbol} {item[0].display_name}")
            ),
            has_long_name=item[1],
            provider_position=item[2],
        )
    )
    return tuple(item[0] for item in ranked_candidates)


def fetch_average_daily_volumes(
    symbols: tuple[str, ...],
    *,
    downloader: Callable[..., pd.DataFrame] | None = None,
) -> dict[str, float]:
    """Fetch one month of candidate volumes in a single best-effort request."""

    normalized_symbols = tuple(
        dict.fromkeys(normalize_ticker(symbol) for symbol in symbols)
    )
    if not normalized_symbols:
        return {}
    if downloader is None:
        import yfinance as yf

        downloader = yf.download

    try:
        history = downloader(
            list(normalized_symbols),
            period="1mo",
            auto_adjust=False,
            group_by="column",
            progress=False,
            threads=True,
            timeout=10,
        )
    except Exception:
        return {}
    if not isinstance(history, pd.DataFrame) or history.empty:
        return {}

    if isinstance(history.columns, pd.MultiIndex):
        if "Volume" not in history.columns.get_level_values(0):
            return {}
        volumes = history["Volume"]
    elif len(normalized_symbols) == 1 and "Volume" in history.columns:
        volumes = history[["Volume"]].rename(columns={"Volume": normalized_symbols[0]})
    else:
        return {}

    if isinstance(volumes, pd.Series):
        volumes = volumes.to_frame(name=normalized_symbols[0])
    numeric_volumes = volumes.apply(pd.to_numeric, errors="coerce")
    averages = numeric_volumes.where(numeric_volumes > 0).mean(skipna=True)
    return {
        str(symbol): float(volume)
        for symbol, volume in averages.items()
        if pd.notna(volume)
    }


def add_candidate_volumes(
    candidates: tuple[InstrumentCandidate, ...],
    volumes: dict[str, float],
    *,
    query: str,
    sort_mode: str = "relevance",
) -> tuple[InstrumentCandidate, ...]:
    """Attach recent volume and apply an explicit result ordering.

    ``relevance`` keeps text/share-class intent ahead of liquidity. ``volume``
    orders the primary share-class pool by recent average daily volume.
    A full Yahoo symbol remains pinned first in either mode.
    """

    if sort_mode not in {"relevance", "volume"}:
        raise ValueError(f"Unsupported search sort mode: {sort_mode}")
    query_symbol = _symbol_shaped_query(query)
    requested_terms = _canonical_search_terms(query)
    requested_share_classes = requested_terms & {"ACC", "DIST"}
    enriched = tuple(
        replace(
            candidate,
            average_daily_volume=volumes.get(candidate.symbol),
        )
        for candidate in candidates
    )
    ranked_pool = enriched
    if sort_mode == "volume" and requested_share_classes:
        share_class_matches = tuple(
            candidate
            for candidate in enriched
            if requested_share_classes & _canonical_search_terms(candidate.display_name)
        )
        if "ACC" in requested_share_classes:
            share_class_matches += tuple(
                candidate
                for candidate in enriched
                if candidate not in share_class_matches
                and "UCITS" in _canonical_search_terms(candidate.display_name)
            )
        if share_class_matches:
            ranked_pool = share_class_matches

    if sort_mode == "volume":
        ranked = sorted(
            enumerate(ranked_pool),
            key=lambda item: (
                0 if query_symbol is not None and item[1].symbol == query_symbol else 1,
                0 if item[1].average_daily_volume is not None else 1,
                -(item[1].average_daily_volume or 0.0),
                item[0],
            ),
        )
        return tuple(candidate for _, candidate in ranked)

    ranked = sorted(
        enumerate(ranked_pool),
        key=lambda item: (
            0 if query_symbol is not None and item[1].symbol == query_symbol else 1,
            0
            if requested_share_classes & _canonical_search_terms(item[1].display_name)
            else 1,
            -len(
                requested_terms
                & _canonical_search_terms(f"{item[1].symbol} {item[1].display_name}")
            ),
            0
            if requested_share_classes
            and "UCITS" in _canonical_search_terms(item[1].display_name)
            else 1,
            _provider_type_rank(item[1]),
            0 if item[1].average_daily_volume is not None else 1,
            -(item[1].average_daily_volume or 0.0),
            item[0],
        ),
    )
    return tuple(candidate for _, candidate in ranked)


def search_instruments(
    query: str,
    *,
    search_factory: Callable[..., Any] | None = None,
    volume_loader: Callable[[tuple[str, ...]], dict[str, float]] | None = None,
    max_results: int = MAX_SEARCH_RESULTS,
    sort_mode: str = "relevance",
) -> tuple[InstrumentCandidate, ...]:
    """Search Yahoo for names, ISINs or symbols and return selection candidates."""

    query_variants = search_query_variants(query)
    normalized_query = query_variants[0]
    use_default_search = search_factory is None
    if search_factory is None:
        import yfinance as yf

        search_factory = yf.Search
    if volume_loader is None and use_default_search:
        volume_loader = fetch_average_daily_volumes

    if sort_mode not in {"relevance", "volume"}:
        raise ValueError(f"Unsupported search sort mode: {sort_mode}")
    result_limit = max(1, min(int(max_results), MAX_SEARCH_RESULTS))
    provider_limit = MAX_SEARCH_CANDIDATES
    combined_quotes: list[dict[str, Any]] = []
    successful_searches = 0
    first_error: Exception | None = None
    for provider_query in query_variants:
        try:
            search = search_factory(
                provider_query,
                max_results=provider_limit,
                news_count=0,
                lists_count=0,
                include_cb=False,
                include_nav_links=False,
                include_research=False,
                include_cultural_assets=False,
                enable_fuzzy_query=False,
                recommended=0,
                timeout=10,
                raise_errors=True,
            )
            quotes = getattr(search, "quotes", None)
            if not isinstance(quotes, (list, tuple)):
                raise TypeError("Yahoo Search.quotes was not a list or tuple")
        except Exception as exc:
            if first_error is None:
                first_error = exc
            continue
        successful_searches += 1
        if quotes:
            combined_quotes.extend(quote for quote in quotes if isinstance(quote, dict))

    if successful_searches == 0 and first_error is not None:
        raise InstrumentSearchError(normalized_query) from first_error

    candidate_pool = normalize_search_results(
        combined_quotes,
        query=normalized_query,
        preferred_symbols=_preferred_symbols_for_query(normalized_query),
    )[:MAX_SEARCH_CANDIDATES]
    if not candidate_pool or volume_loader is None:
        return candidate_pool[:result_limit]
    try:
        volumes = volume_loader(tuple(candidate.symbol for candidate in candidate_pool))
    except Exception:
        volumes = {}
    return add_candidate_volumes(
        candidate_pool,
        volumes,
        query=normalized_query,
        sort_mode=sort_mode,
    )[:result_limit]


def direct_symbol_candidate(query: str) -> InstrumentCandidate | None:
    """Create an explicit direct-price fallback for a symbol-shaped query."""

    try:
        symbol = normalize_ticker(normalize_search_query(query))
    except (InvalidSearchQueryError, InvalidTickerError, IsinNotSupportedError):
        return None
    return InstrumentCandidate(
        symbol=symbol,
        display_name=symbol,
        exchange="",
        provider_type="",
    )


def candidate_for_symbol(
    candidates: tuple[InstrumentCandidate, ...],
    symbol: str,
) -> InstrumentCandidate:
    """Resolve a user-selected symbol without guessing another listing."""

    for candidate in candidates:
        if candidate.symbol == symbol:
            return candidate
    raise ValueError(f"Unknown candidate symbol: {symbol}")


def empty_price_frame() -> pd.DataFrame:
    """Return the stable schema used for session price storage."""

    return pd.DataFrame(
        {
            "ticker": pd.Series(dtype="object"),
            "price_date": pd.Series(dtype="datetime64[ns]"),
            "adj_close": pd.Series(dtype="float64"),
            "volume": pd.Series(dtype="float64"),
        }
    )


def normalize_ticker(value: str) -> str:
    """Normalize and validate a Yahoo Finance symbol.

    European listings commonly use exchange suffixes such as ``.DE``, ``.L``,
    ``.AS`` or ``.VI``. Dots, hyphens and numeric symbols are therefore
    intentionally supported.
    """

    ticker = value.strip().upper()
    if ISIN_PATTERN.fullmatch(ticker):
        raise IsinNotSupportedError(ticker)
    if not TICKER_PATTERN.fullmatch(ticker):
        raise InvalidTickerError(ticker)
    return ticker


def _flatten_download_columns(history: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Reduce yfinance's possible single-symbol MultiIndex to flat columns."""

    if not isinstance(history.columns, pd.MultiIndex):
        return history

    for level in range(history.columns.nlevels):
        values = history.columns.get_level_values(level).astype(str)
        matches = values.str.upper() == ticker
        if matches.any():
            return history.xs(
                history.columns.get_level_values(level)[matches][0],
                axis=1,
                level=level,
                drop_level=True,
            )

    # Some yfinance versions return a redundant one-value level even when the
    # ticker label is not present. Removing only singleton levels is safe.
    flattened = history.copy()
    singleton_levels = [
        level
        for level in range(flattened.columns.nlevels)
        if len(flattened.columns.get_level_values(level).unique()) == 1
    ]
    if singleton_levels:
        flattened.columns = flattened.columns.droplevel(singleton_levels)
    return flattened


def normalize_price_history(
    history: pd.DataFrame,
    ticker: str,
    *,
    minimum_rows: int = MIN_PRICE_ROWS,
) -> pd.DataFrame:
    """Convert one yfinance response to the dashboard's price schema."""

    normalized_ticker = normalize_ticker(ticker)
    if history is None or history.empty:
        raise PriceDataUnavailableError(normalized_ticker)

    frame = _flatten_download_columns(history.copy(), normalized_ticker)
    if isinstance(frame.columns, pd.MultiIndex):
        raise PriceDataUnavailableError(normalized_ticker)

    frame = frame.reset_index()
    frame.columns = [
        str(column).strip().lower().replace(" ", "_") for column in frame.columns
    ]
    date_column = next(
        (column for column in ("date", "datetime", "price_date") if column in frame),
        None,
    )
    if date_column is None:
        raise PriceDataUnavailableError(normalized_ticker)

    adjusted_column = "adj_close" if "adj_close" in frame else "close"
    if adjusted_column not in frame:
        raise PriceDataUnavailableError(normalized_ticker)

    result = pd.DataFrame()
    dates = pd.to_datetime(frame[date_column], errors="coerce")
    if isinstance(dates.dtype, pd.DatetimeTZDtype):
        dates = dates.dt.tz_localize(None)
    result["price_date"] = dates.dt.normalize()
    result["adj_close"] = pd.to_numeric(
        frame[adjusted_column], errors="coerce"
    ).to_numpy()
    if "volume" in frame:
        result["volume"] = pd.to_numeric(frame["volume"], errors="coerce").to_numpy()
    else:
        result["volume"] = np.nan
    result["ticker"] = normalized_ticker

    result = (
        result.dropna(subset=["price_date", "adj_close"])
        .drop_duplicates(["ticker", "price_date"], keep="last")
        .sort_values("price_date")
        .reset_index(drop=True)
    )
    if result.empty:
        raise PriceDataUnavailableError(normalized_ticker)
    if len(result) < minimum_rows:
        raise InsufficientHistoryError(normalized_ticker)
    return result[PRICE_COLUMNS]


def fetch_price_history(
    ticker: str,
    *,
    downloader: Callable[..., pd.DataFrame] | None = None,
    period: str = "10y",
) -> pd.DataFrame:
    """Fetch and normalize one Yahoo Finance symbol.

    ``downloader`` is injectable so tests never need live network access.
    """

    normalized_ticker = normalize_ticker(ticker)
    if downloader is None:
        import yfinance as yf

        downloader = yf.download

    try:
        history = downloader(
            normalized_ticker,
            period=period,
            auto_adjust=False,
            group_by="column",
            progress=False,
            threads=False,
            timeout=10,
        )
    except Exception as exc:
        raise PriceDataUnavailableError(normalized_ticker) from exc
    return normalize_price_history(history, normalized_ticker)


def build_indexed_price_comparison(
    prices: pd.DataFrame,
    *,
    base_value: float = 100.0,
) -> pd.DataFrame:
    """Rebase selected prices to one common date and starting value.

    Rows are limited to dates shared by every selected ticker, avoiding the
    misleading comparison produced by different inception dates or face values.
    """

    columns = ["ticker", "price_date", "indexed_price"]
    required = {"ticker", "price_date", "adj_close"}
    if prices.empty or not required.issubset(prices.columns):
        return pd.DataFrame(columns=columns)
    if not np.isfinite(base_value) or base_value <= 0:
        raise ValueError("base_value must be a positive finite number")

    frame = prices[["ticker", "price_date", "adj_close"]].copy()
    frame["price_date"] = pd.to_datetime(frame["price_date"], errors="coerce")
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame = (
        frame.dropna(subset=["ticker", "price_date", "adj_close"])
        .drop_duplicates(["ticker", "price_date"], keep="last")
        .sort_values(["price_date", "ticker"])
    )
    frame = frame[frame["adj_close"] > 0]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    pivot = frame.pivot(
        index="price_date",
        columns="ticker",
        values="adj_close",
    ).dropna(how="any")
    if pivot.empty:
        return pd.DataFrame(columns=columns)

    indexed = pivot.divide(pivot.iloc[0]).multiply(base_value)
    result = (
        indexed.rename_axis(columns="ticker")
        .reset_index()
        .melt(
            id_vars="price_date",
            var_name="ticker",
            value_name="indexed_price",
        )
        .sort_values(["ticker", "price_date"])
        .reset_index(drop=True)
    )
    return result[columns]


def build_custom_marts(
    prices: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute returns and risk metrics using the same formulas as demo marts."""

    if prices.empty:
        return (
            pd.DataFrame(columns=RETURN_COLUMNS),
            pd.DataFrame(columns=RISK_COLUMNS),
        )

    frame = prices[PRICE_COLUMNS].copy()
    frame["price_date"] = pd.to_datetime(frame["price_date"])
    frame = (
        frame.dropna(subset=["ticker", "price_date", "adj_close"])
        .drop_duplicates(["ticker", "price_date"], keep="last")
        .sort_values(["ticker", "price_date"])
        .reset_index(drop=True)
    )
    grouped = frame.groupby("ticker")["adj_close"]

    returns = frame.copy()
    returns["daily_return"] = grouped.pct_change()

    risk = frame[["ticker", "price_date"]].copy()
    risk["rolling_vol_30d"] = grouped.transform(
        lambda series: series.pct_change().rolling(30, min_periods=2).std()
    )
    risk["annualized_vol_30d"] = risk["rolling_vol_30d"] * np.sqrt(252)
    risk["drawdown"] = grouped.transform(lambda series: series / series.cummax() - 1.0)
    return returns[RETURN_COLUMNS], risk[RISK_COLUMNS]


def session_prices(state: MutableMapping[str, Any]) -> pd.DataFrame:
    """Read a defensive copy of custom prices from session state."""

    value = state.get(CUSTOM_ETF_STATE_KEY)
    if not isinstance(value, pd.DataFrame) or value.empty:
        return empty_price_frame()
    return value[PRICE_COLUMNS].copy()


def session_tickers(state: MutableMapping[str, Any]) -> list[str]:
    """Return sorted custom symbols stored for this session."""

    prices = session_prices(state)
    return sorted(prices["ticker"].dropna().astype(str).unique())


def add_session_prices(
    state: MutableMapping[str, Any],
    prices: pd.DataFrame,
) -> None:
    """Add one normalized symbol to session state with duplicate/limit guards."""

    if prices.empty or prices["ticker"].nunique() != 1:
        raise PriceDataUnavailableError("")
    ticker = str(prices["ticker"].iloc[0])
    existing = session_prices(state)
    current_tickers = set(existing["ticker"].astype(str))
    if ticker in current_tickers:
        raise DuplicateTickerError(ticker)
    if len(current_tickers) >= MAX_CUSTOM_ETFS:
        raise CustomEtfLimitError(ticker)
    state[CUSTOM_ETF_STATE_KEY] = (
        pd.concat([existing, prices[PRICE_COLUMNS]], ignore_index=True)
        .drop_duplicates(["ticker", "price_date"], keep="last")
        .sort_values(["ticker", "price_date"])
        .reset_index(drop=True)
    )


def remove_session_ticker(
    state: MutableMapping[str, Any],
    ticker: str,
) -> None:
    """Remove one custom symbol from session state."""

    existing = session_prices(state)
    remaining = existing[existing["ticker"] != ticker].reset_index(drop=True)
    state[CUSTOM_ETF_STATE_KEY] = remaining


def clear_session_prices(state: MutableMapping[str, Any]) -> None:
    """Remove all custom symbols from session state."""

    state[CUSTOM_ETF_STATE_KEY] = empty_price_frame()


def _merge_frames(
    base: pd.DataFrame,
    custom: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    if custom.empty:
        return base
    merged = pd.concat([base, custom], ignore_index=True)
    return (
        merged.drop_duplicates(["ticker", "price_date"], keep="last")
        .sort_values(["ticker", "price_date"])
        .reset_index(drop=True)[columns]
    )


def merge_custom_data(
    base_returns: pd.DataFrame,
    base_risk: pd.DataFrame | None,
    prices: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Merge session-specific marts after globally cached loaders have run."""

    if prices.empty:
        return base_returns, base_risk
    custom_returns, custom_risk = build_custom_marts(prices)
    returns = _merge_frames(base_returns, custom_returns, RETURN_COLUMNS)
    risk = (
        None
        if base_risk is None
        else _merge_frames(base_risk, custom_risk, RISK_COLUMNS)
    )
    return returns, risk
