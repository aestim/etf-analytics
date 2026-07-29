"""Quote-currency metadata, FX loading and deterministic price conversion."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
import pandas as pd

SUPPORTED_BASE_CURRENCIES = ("USD", "EUR", "GBP")
BASE_CURRENCY_STATE_KEY = "analytics_base_currency_v1"
RETURN_BASIS_STATE_KEY = "overview_return_basis_v1"
FX_FORWARD_FILL_DAYS = 5

_FX_USD_SYMBOLS = {
    "EUR": "EURUSD=X",
    "GBP": "GBPUSD=X",
}
_CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
}
_PENCE_CODES = {"GBp", "GBX"}


class CurrencyConversionError(ValueError):
    """Base class for expected currency conversion failures."""


class CurrencyMetadataUnavailableError(CurrencyConversionError):
    """A listing's quote currency is missing or unsupported."""


class FxDataUnavailableError(CurrencyConversionError):
    """Required daily FX history is missing."""


def normalize_base_currency(value: str) -> str:
    """Validate a user-selected account currency."""

    currency = str(value).strip().upper()
    if currency not in SUPPORTED_BASE_CURRENCIES:
        raise CurrencyMetadataUnavailableError(currency)
    return currency


def normalize_listing_currency(value: str) -> str:
    """Normalize Yahoo quote currencies while preserving British pence."""

    raw_currency = str(value).strip()
    if raw_currency in _PENCE_CODES:
        return raw_currency
    currency = raw_currency.upper()
    if currency not in SUPPORTED_BASE_CURRENCIES:
        raise CurrencyMetadataUnavailableError(raw_currency)
    return currency


def listing_currency_code(value: str) -> str:
    """Return the ISO currency used for FX conversion."""

    currency = normalize_listing_currency(value)
    return "GBP" if currency in _PENCE_CODES else currency


def listing_price_multiplier(value: str) -> float:
    """Convert a Yahoo listing price unit to one full currency unit."""

    currency = normalize_listing_currency(value)
    return 0.01 if currency in _PENCE_CODES else 1.0


def currency_symbol(value: str) -> str:
    """Return the display symbol for a supported base currency."""

    return _CURRENCY_SYMBOLS[normalize_base_currency(value)]


def format_money(value: float, currency: str) -> str:
    """Format a monetary value independently from the interface language."""

    symbol = currency_symbol(currency)
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol}{abs(value):,.0f}"


def format_compact_money(value: float, currency: str) -> str:
    """Format large values without hiding their selected currency."""

    symbol = currency_symbol(currency)
    magnitude = abs(value)
    sign = "-" if value < 0 else ""
    for threshold, suffix in (
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
    ):
        if magnitude >= threshold:
            return f"{sign}{symbol}{magnitude / threshold:,.2f}{suffix}"
    return format_money(value, currency)


def fetch_listing_currency(
    ticker: str,
    *,
    metadata_loader: Callable[[], Mapping[str, Any]] | None = None,
) -> str:
    """Resolve one listing currency from Yahoo history metadata."""

    if metadata_loader is None:
        import yfinance as yf

        metadata_loader = yf.Ticker(ticker).get_history_metadata
    try:
        metadata = metadata_loader()
    except Exception as exc:
        raise CurrencyMetadataUnavailableError(ticker) from exc
    if not isinstance(metadata, Mapping):
        raise CurrencyMetadataUnavailableError(ticker)
    try:
        return normalize_listing_currency(str(metadata.get("currency", "")))
    except CurrencyMetadataUnavailableError as exc:
        raise CurrencyMetadataUnavailableError(ticker) from exc


def _market_field(
    history: pd.DataFrame,
    names: tuple[str, ...],
) -> pd.DataFrame | pd.Series | None:
    """Extract the first matching price field from flat or MultiIndex data."""

    if isinstance(history.columns, pd.MultiIndex):
        for name in names:
            for level in range(history.columns.nlevels):
                values = history.columns.get_level_values(level).astype(str)
                if name in values:
                    return history.xs(name, axis=1, level=level, drop_level=True)
        return None
    for name in names:
        if name in history.columns:
            return history[name]
    return None


def fetch_usd_exchange_rates(
    currencies: tuple[str, ...] | list[str] | set[str],
    *,
    downloader: Callable[..., pd.DataFrame] | None = None,
    period: str = "max",
) -> pd.DataFrame:
    """Return USD per EUR/GBP unit, indexed by provider trading date."""

    normalized_codes = sorted(
        {
            code
            for code in (listing_currency_code(currency) for currency in currencies)
            if code != "USD"
        }
    )
    if not normalized_codes:
        return pd.DataFrame(index=pd.DatetimeIndex([], name="price_date"))
    if downloader is None:
        import yfinance as yf

        downloader = yf.download

    requested_symbols = [_FX_USD_SYMBOLS[currency] for currency in normalized_codes]
    try:
        history = downloader(
            requested_symbols,
            period=period,
            auto_adjust=False,
            group_by="column",
            progress=False,
            threads=True,
            timeout=10,
        )
    except Exception as exc:
        raise FxDataUnavailableError(", ".join(normalized_codes)) from exc
    if not isinstance(history, pd.DataFrame) or history.empty:
        raise FxDataUnavailableError(", ".join(normalized_codes))

    close = _market_field(history, ("Adj Close", "Close"))
    if close is None:
        raise FxDataUnavailableError(", ".join(normalized_codes))
    if isinstance(close, pd.Series):
        close = close.to_frame(name=requested_symbols[0])
    if isinstance(close.columns, pd.MultiIndex):
        close = close.copy()
        close.columns = close.columns.get_level_values(-1)

    result = pd.DataFrame(index=pd.to_datetime(close.index, errors="coerce"))
    if isinstance(result.index.dtype, pd.DatetimeTZDtype):
        result.index = result.index.tz_localize(None)
    result.index = result.index.normalize()
    result = result[~result.index.isna()]
    for currency, symbol in zip(normalized_codes, requested_symbols, strict=True):
        if symbol in close:
            values = close[symbol]
        elif len(requested_symbols) == 1 and close.shape[1] == 1:
            values = close.iloc[:, 0]
        else:
            raise FxDataUnavailableError(currency)
        result[currency] = pd.to_numeric(values, errors="coerce").to_numpy()

    result = result[~result.index.duplicated(keep="last")].sort_index()
    result = result.where(result > 0).dropna(how="all")
    missing = [
        currency for currency in normalized_codes if result[currency].isna().all()
    ]
    if missing:
        raise FxDataUnavailableError(", ".join(missing))
    result.index.name = "price_date"
    return result


def _aligned_rate(
    usd_rates: pd.DataFrame,
    currency: str,
    dates: pd.DatetimeIndex,
) -> pd.Series:
    if currency == "USD":
        return pd.Series(1.0, index=dates)
    if currency not in usd_rates:
        raise FxDataUnavailableError(currency)
    if usd_rates.empty:
        raise FxDataUnavailableError(currency)
    calendar = pd.date_range(
        min(usd_rates.index.min(), dates.min()),
        max(usd_rates.index.max(), dates.max()),
        freq="D",
    )
    daily = (
        pd.to_numeric(usd_rates[currency], errors="coerce")
        .reindex(calendar)
        .ffill(limit=FX_FORWARD_FILL_DAYS)
    )
    return daily.reindex(dates)


def convert_prices_to_base_currency(
    prices: pd.DataFrame,
    listing_currencies: Mapping[str, str],
    base_currency: str,
    usd_rates: pd.DataFrame,
) -> pd.DataFrame:
    """Convert long-form adjusted prices into one account currency.

    Leading or trailing dates outside FX coverage are removed. Market-holiday
    gaps are filled for at most ``FX_FORWARD_FILL_DAYS`` calendar days.
    """

    required = {"ticker", "price_date", "adj_close"}
    if prices.empty or not required.issubset(prices.columns):
        return prices.copy()
    base = normalize_base_currency(base_currency)
    frame = prices.copy()
    frame["ticker"] = frame["ticker"].astype(str)
    frame["price_date"] = pd.to_datetime(frame["price_date"], errors="coerce")
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame = frame.dropna(subset=["ticker", "price_date", "adj_close"])
    if frame.empty:
        return frame

    tickers = frame["ticker"].unique()
    missing_metadata = sorted(set(tickers) - set(listing_currencies))
    if missing_metadata:
        raise CurrencyMetadataUnavailableError(", ".join(missing_metadata))
    normalized_listing = {
        ticker: normalize_listing_currency(listing_currencies[ticker])
        for ticker in tickers
    }
    dates = pd.DatetimeIndex(sorted(frame["price_date"].unique()))
    required_codes = {
        base,
        *(listing_currency_code(currency) for currency in normalized_listing.values()),
    }
    aligned_rates = {
        currency: _aligned_rate(usd_rates, currency, dates)
        for currency in required_codes
    }

    converted_parts = []
    for ticker, ticker_prices in frame.groupby("ticker", sort=False):
        listing_currency = normalized_listing[ticker]
        source_code = listing_currency_code(listing_currency)
        row_dates = pd.DatetimeIndex(ticker_prices["price_date"])
        source_usd = aligned_rates[source_code].reindex(row_dates).to_numpy()
        base_usd = aligned_rates[base].reindex(row_dates).to_numpy()
        converted = ticker_prices.copy()
        converted["adj_close"] = (
            converted["adj_close"].to_numpy()
            * listing_price_multiplier(listing_currency)
            * source_usd
            / base_usd
        )
        converted = converted.replace([np.inf, -np.inf], np.nan).dropna(
            subset=["adj_close"]
        )
        if len(converted) < 2:
            raise FxDataUnavailableError(f"{ticker} ({source_code}/{base})")
        converted_parts.append(converted)

    return (
        pd.concat(converted_parts, ignore_index=True)
        .sort_values(["ticker", "price_date"])
        .reset_index(drop=True)
    )
