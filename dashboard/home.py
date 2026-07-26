"""
Streamlit dashboard home page — reads mart tables from PostgreSQL.
Run after: docker compose up, ingest, dbt run.
"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd
import plotly.express as px
import streamlit as st

from chart_colors import ticker_color_map
from currency_conversion import (
    BASE_CURRENCY_STATE_KEY,
    RETURN_BASIS_STATE_KEY,
    SUPPORTED_BASE_CURRENCIES,
    CurrencyConversionError,
    convert_prices_to_base_currency,
    currency_symbol,
    fetch_listing_currency,
    fetch_usd_exchange_rates,
    normalize_listing_currency,
)
from custom_etf import (
    CustomEtfLimitError,
    DuplicateTickerError,
    InsufficientHistoryError,
    InstrumentCandidate,
    InstrumentSearchError,
    InvalidSearchQueryError,
    InvalidTickerError,
    IsinNotSupportedError,
    PriceDataUnavailableError,
    add_session_prices,
    build_custom_marts,
    build_indexed_price_comparison,
    RESULT_ROW_KEY_PREFIX,
    candidate_button_label,
    clear_session_prices,
    format_compact_volume,
    direct_symbol_candidate,
    fetch_price_history,
    looks_like_isin,
    merge_custom_data,
    normalize_search_query,
    normalize_ticker,
    remove_session_ticker,
    search_instruments,
    session_instrument_candidates,
    session_prices,
    session_tickers,
)
from db import (
    DATAFRAME_ROW_HEIGHT,
    PLOTLY_LAYOUT,
    dataframe_width,
    demo_mode_banner,
    glossary_expander,
    glossary_help,
    load_dim_etf,
    load_mart_returns,
    load_mart_risk,
)
from i18n import (
    ASSET_LABELS_KO,
    SUBCLASS_LABELS_KO,
    TICKER_DESCRIPTIONS_KO,
    Language,
    current_language,
    tr,
)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_custom_history(ticker: str) -> pd.DataFrame:
    """Cache vendor calls globally while keeping selections session-specific."""

    return fetch_price_history(ticker)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_listing_currency(ticker: str) -> str:
    """Cache the selected listing's provider-reported quote currency."""

    return fetch_listing_currency(ticker)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_usd_exchange_rates(currencies: tuple[str, ...]) -> pd.DataFrame:
    """Cache the small set of daily FX series used for chart conversion."""

    return fetch_usd_exchange_rates(currencies)


@st.cache_data(ttl=900, show_spinner=False)
def cached_instrument_search(
    query: str,
    sort_mode: str,
) -> tuple[InstrumentCandidate, ...]:
    """Cache public Yahoo results while keeping user choices session-specific."""

    return search_instruments(query, sort_mode=sort_mode)


SEARCH_QUERY_KEY = "custom_etf_search_query"
SEARCH_RESULTS_KEY = "custom_etf_search_results"
SEARCH_DIRECT_FALLBACK_KEY = "custom_etf_direct_fallback"
SEARCH_GENERATION_KEY = "custom_etf_search_generation"
SEARCH_SORT_KEY = "custom_etf_search_sort_v2"
SEARCH_FLASH_KEY = "custom_etf_flash"
HOME_SELECTED_TICKERS_KEY = "home_selected_tickers"


def _store_search_state(
    query: str,
    candidates: tuple[InstrumentCandidate, ...],
    *,
    direct_fallback: bool,
    sort_mode: str = "volume",
) -> None:
    """Replace the search state for the current query."""

    st.session_state[SEARCH_QUERY_KEY] = query
    st.session_state[SEARCH_RESULTS_KEY] = candidates
    st.session_state[SEARCH_DIRECT_FALLBACK_KEY] = direct_fallback
    st.session_state[SEARCH_SORT_KEY] = sort_mode
    generation = st.session_state.get(SEARCH_GENERATION_KEY, 0)
    st.session_state[SEARCH_GENERATION_KEY] = generation + 1


def _select_ticker_for_charts(ticker: str) -> None:
    """Include a successfully resolved ticker in the Overview charts."""

    current = st.session_state.get(HOME_SELECTED_TICKERS_KEY, [])
    selected = list(current) if isinstance(current, (list, tuple)) else []
    if ticker not in selected:
        st.session_state[HOME_SELECTED_TICKERS_KEY] = [*selected, ticker]


def _unselect_ticker_for_charts(ticker: str) -> None:
    """Remove a deleted session ticker from the Overview chart widget."""

    current = st.session_state.get(HOME_SELECTED_TICKERS_KEY, [])
    if isinstance(current, (list, tuple)):
        st.session_state[HOME_SELECTED_TICKERS_KEY] = [
            selected for selected in current if selected != ticker
        ]


def _add_custom_symbol(
    candidate: InstrumentCandidate,
    returns_df: pd.DataFrame,
    lang: Language,
) -> bool:
    """Fetch only the selected symbol, then add it to this session."""

    try:
        normalized_ticker = normalize_ticker(candidate.symbol)
        built_in = set(returns_df["ticker"].dropna().astype(str))
        if normalized_ticker in built_in:
            _select_ticker_for_charts(normalized_ticker)
            st.session_state[SEARCH_FLASH_KEY] = tr(
                "custom.already_available",
                lang,
                ticker=normalized_ticker,
            )
            return True
        listing_currency = (
            normalize_listing_currency(candidate.currency)
            if candidate.currency
            else cached_listing_currency(normalized_ticker)
        )
        resolved_candidate = replace(candidate, currency=listing_currency)
        with st.spinner(tr("custom.loading", lang, ticker=normalized_ticker)):
            prices = cached_custom_history(normalized_ticker)
        add_session_prices(
            st.session_state,
            prices,
            candidate=resolved_candidate,
        )
        _select_ticker_for_charts(normalized_ticker)
        st.session_state[SEARCH_FLASH_KEY] = tr(
            "custom.added",
            lang,
            ticker=normalized_ticker,
        )
        return True
    except IsinNotSupportedError:
        st.error(tr("custom.isin_error", lang))
    except InvalidTickerError:
        st.error(tr("custom.invalid_ticker", lang))
    except DuplicateTickerError as exc:
        _select_ticker_for_charts(str(exc))
        st.session_state[SEARCH_FLASH_KEY] = tr(
            "custom.duplicate",
            lang,
            ticker=str(exc),
        )
        return True
    except CustomEtfLimitError:
        st.error(tr("custom.limit", lang))
    except InsufficientHistoryError as exc:
        st.error(tr("custom.insufficient", lang, ticker=str(exc)))
    except PriceDataUnavailableError as exc:
        st.error(tr("custom.unavailable", lang, ticker=str(exc)))
    except CurrencyConversionError:
        st.error(
            tr(
                "custom.currency_unavailable",
                lang,
                ticker=candidate.symbol,
            )
        )
    return False


def custom_etf_dialog(
    base_returns_df: pd.DataFrame,
    lang: Language,
) -> None:
    """Open the session ETF search and management dialog."""

    # "large" is up to 1280px — wider than the page itself. A search list needs
    # room for a fund name and a number, not the whole monitor.
    @st.dialog(tr("custom.dialog_title", lang), width="medium")
    def render_dialog() -> None:
        st.caption(tr("custom.help", lang))
        with st.form("custom_etf_search_form"):
            raw_query = st.text_input(
                tr("custom.input_label", lang),
                placeholder=tr("custom.input_placeholder", lang),
                value=st.session_state.get(SEARCH_QUERY_KEY, ""),
                key="custom_etf_dialog_query",
            )
            submitted = st.form_submit_button(
                tr("custom.search", lang),
                type="primary",
            )

        # Deliberately outside the form: a form defers widget values until the
        # next submit, so changing the order there looked like it did nothing.
        sort_mode = st.segmented_control(
            tr("custom.sort_label", lang),
            options=["volume", "relevance"],
            default=st.session_state.get(
                SEARCH_SORT_KEY,
                "volume",
            ),
            format_func=lambda value: tr(
                f"custom.sort_{value}",
                lang,
            ),
            key="custom_etf_dialog_sort",
        )
        resolved_sort = sort_mode if sort_mode in {"relevance", "volume"} else "volume"
        stored_query = st.session_state.get(SEARCH_QUERY_KEY, "")
        # Re-order the results the user is already looking at, without asking
        # them to submit the same query again.
        sort_changed = (
            not submitted
            and bool(stored_query)
            and resolved_sort != st.session_state.get(SEARCH_SORT_KEY, "volume")
        )

        if submitted or sort_changed:
            try:
                query = normalize_search_query(
                    raw_query if submitted else stored_query
                )
                with st.spinner(tr("custom.searching", lang)):
                    candidates = cached_instrument_search(
                        query,
                        resolved_sort,
                    )
                direct_fallback = False
                if not candidates:
                    direct = direct_symbol_candidate(query)
                    if direct is not None:
                        candidates = (direct,)
                        direct_fallback = True
                _store_search_state(
                    query,
                    candidates,
                    direct_fallback=direct_fallback,
                    sort_mode=resolved_sort,
                )
            except InvalidSearchQueryError:
                _store_search_state(
                    "", (), direct_fallback=False, sort_mode=resolved_sort
                )
                st.error(tr("custom.invalid_query", lang))
            except InstrumentSearchError as exc:
                # Record the attempted sort too, otherwise the state still holds
                # the previous mode and this failing search repeats every rerun.
                query = str(exc)
                direct = direct_symbol_candidate(query)
                candidates = (direct,) if direct is not None else ()
                _store_search_state(
                    query,
                    candidates,
                    direct_fallback=direct is not None,
                    sort_mode=resolved_sort,
                )
                st.error(tr("custom.search_unavailable", lang))
                with st.expander(tr("home.admin_details", lang)):
                    detail = exc.__cause__ if exc.__cause__ is not None else exc
                    st.code(str(detail))

        search_query = st.session_state.get(SEARCH_QUERY_KEY, "")
        candidates = st.session_state.get(SEARCH_RESULTS_KEY, ())
        direct_fallback = st.session_state.get(
            SEARCH_DIRECT_FALLBACK_KEY,
            False,
        )
        result_sort = st.session_state.get(SEARCH_SORT_KEY, "volume")
        if isinstance(candidates, tuple) and candidates:
            if direct_fallback:
                st.info(tr("custom.direct_fallback", lang))
            else:
                st.caption(
                    tr(
                        "custom.results_for",
                        lang,
                        query=search_query,
                        count=len(candidates),
                    )
                )
            if result_sort == "volume" and not any(
                candidate.average_daily_volume is not None for candidate in candidates
            ):
                st.warning(tr("custom.volume_unavailable_notice", lang))
            else:
                st.caption(
                    tr(
                        f"custom.sort_notice_{result_sort}",
                        lang,
                    )
                )
            generation = st.session_state.get(SEARCH_GENERATION_KEY, 0)

            # One plain button per listing: the row is the click target and a
            # single element cannot wrap away from itself on a phone. app.py
            # restyles these keyed buttons into flat list rows; without that
            # stylesheet they degrade to ordinary buttons and still work.
            with st.container(gap=None):
                for candidate in candidates:
                    volume = candidate.average_daily_volume
                    caption = (
                        tr(
                            "custom.volume_caption",
                            lang,
                            volume=format_compact_volume(volume),
                        )
                        if volume is not None
                        else None
                    )
                    tooltip = (
                        tr("custom.average_volume", lang, volume=f"{volume:,.0f}")
                        if volume is not None
                        else tr("custom.volume_unavailable", lang)
                    )
                    if st.button(
                        candidate_button_label(candidate, volume_caption=caption),
                        key=f"{RESULT_ROW_KEY_PREFIX}_{generation}_{candidate.symbol}",
                        help=tooltip,
                        width="stretch",
                    ) and _add_custom_symbol(candidate, base_returns_df, lang):
                        st.rerun()
        elif search_query:
            st.info(tr("custom.no_results", lang))

        # The notes below are a separate section, not another result row.
        st.divider()

        tickers = session_tickers(st.session_state)
        if tickers:
            with st.expander(
                tr(
                    "custom.current_count",
                    lang,
                    count=len(tickers),
                    limit=5,
                )
            ):
                for ticker in tickers:
                    label_col, remove_col = st.columns([4, 1])
                    label_col.code(ticker)
                    if remove_col.button(
                        tr("custom.remove", lang),
                        key=f"remove_custom_{ticker}",
                    ):
                        remove_session_ticker(st.session_state, ticker)
                        _unselect_ticker_for_charts(ticker)
                        st.rerun()
                if st.button(
                    tr("custom.clear", lang),
                    key="clear_custom_etfs",
                ):
                    for ticker in tickers:
                        _unselect_ticker_for_charts(ticker)
                    clear_session_prices(st.session_state)
                    st.rerun()

        with st.expander(tr("custom.search_notes", lang)):
            if looks_like_isin(search_query):
                st.warning(tr("custom.verify_isin", lang))
            else:
                st.caption(tr("custom.verify_listing", lang))
            st.caption(tr("custom.session_notice", lang))
            st.caption(tr("custom.currency_notice", lang))

    render_dialog()


def render_compare_selector(
    returns_df: pd.DataFrame,
    base_returns_df: pd.DataFrame,
    lang: Language,
) -> tuple[list[str], str, str]:
    """Render one compact selection surface for built-in and session ETFs."""

    tickers = sorted(returns_df["ticker"].unique())
    defaults = [ticker for ticker in ("SPY", "BND", "GLD") if ticker in tickers]
    stored_selection = st.session_state.get(HOME_SELECTED_TICKERS_KEY)
    if isinstance(stored_selection, (list, tuple)):
        valid_selection = [ticker for ticker in stored_selection if ticker in tickers]
    else:
        valid_selection = defaults
    if st.session_state.get(HOME_SELECTED_TICKERS_KEY) != valid_selection:
        st.session_state[HOME_SELECTED_TICKERS_KEY] = valid_selection

    st.subheader(tr("home.compare_title", lang))
    with st.container(border=True):
        selection_col, add_col = st.columns(
            [5, 1],
            vertical_alignment="bottom",
        )
        selected = selection_col.multiselect(
            tr("home.select_etfs", lang),
            tickers,
            key=HOME_SELECTED_TICKERS_KEY,
        )
        # A content-width button sits at the left of its column by default,
        # leaving a gap before the card edge. Align it to the card's padding.
        if add_col.container(horizontal_alignment="right").button(
            tr("home.add_etf", lang),
            type="primary",
        ):
            custom_etf_dialog(base_returns_df, lang)
        currency_col, basis_col = st.columns([1, 2])
        base_currency = currency_col.segmented_control(
            tr("currency.base_label", lang),
            options=list(SUPPORTED_BASE_CURRENCIES),
            default="USD",
            key=BASE_CURRENCY_STATE_KEY,
            help=tr("currency.base_help", lang),
        )
        return_basis = basis_col.segmented_control(
            tr("currency.return_basis_label", lang),
            options=["base", "listing"],
            default="base",
            format_func=lambda value: tr(
                f"currency.return_basis_{value}",
                lang,
            ),
            key=RETURN_BASIS_STATE_KEY,
            help=tr("currency.return_basis_help", lang),
        )
        st.caption(tr("home.compare_help", lang))
    resolved_currency = (
        base_currency if base_currency in SUPPORTED_BASE_CURRENCIES else "USD"
    )
    resolved_basis = return_basis if return_basis in {"base", "listing"} else "base"
    return selected, resolved_currency, resolved_basis


def _listing_currency_map(base_returns_df: pd.DataFrame) -> dict[str, str]:
    """Combine the USD warehouse universe with session listing metadata."""

    currencies = {
        ticker: "USD"
        for ticker in base_returns_df["ticker"].dropna().astype(str).unique()
    }
    currencies.update(
        {
            candidate.symbol: candidate.currency
            for candidate in session_instrument_candidates(st.session_state)
            if candidate.currency
        }
    )
    return currencies


def render_ticker_guide(lang: Language) -> None:
    """Render the reference universe as optional, secondary information."""

    with st.expander(tr("home.ticker_guide", lang)):
        try:
            dim = load_dim_etf()
            session_rows = []
            for candidate in session_instrument_candidates(st.session_state):
                exchange = candidate.exchange or tr(
                    "custom.exchange_unknown",
                    lang,
                )
                provider_type = candidate.provider_type or tr(
                    "custom.type_unknown",
                    lang,
                )
                currency = candidate.currency or tr(
                    "custom.currency_unknown",
                    lang,
                )
                session_rows.append(
                    {
                        "ticker": candidate.symbol,
                        "name": candidate.display_name,
                        "asset_class": "unclassified",
                        "sub_class": "unclassified",
                        "leverage": float("nan"),
                        "description": tr(
                            "home.session_guide_description",
                            lang,
                            exchange=exchange,
                            provider_type=provider_type,
                            currency=currency,
                        ),
                    }
                )
            if session_rows:
                dim = pd.concat(
                    [dim, pd.DataFrame(session_rows)],
                    ignore_index=True,
                )

            display_dim = dim.drop(
                columns=["description", "leverage"],
            ).copy()
            display_dim["asset_class"] = display_dim["asset_class"].replace(
                {"unclassified": tr("home.not_classified", lang)}
            )
            display_dim["sub_class"] = display_dim["sub_class"].replace(
                {"unclassified": tr("home.not_classified", lang)}
            )
            if lang == "ko":
                display_dim["asset_class"] = display_dim["asset_class"].replace(
                    ASSET_LABELS_KO
                )
                display_dim["sub_class"] = display_dim["sub_class"].replace(
                    SUBCLASS_LABELS_KO
                )
            st.dataframe(
                display_dim,
                width="stretch",
                row_height=DATAFRAME_ROW_HEIGHT,
                hide_index=True,
                column_config={
                    "ticker": st.column_config.TextColumn(
                        tr("home.ticker", lang),
                        width=65,
                        alignment="left",
                    ),
                    "name": st.column_config.TextColumn(
                        tr("home.fund_name", lang),
                        width=280,
                        alignment="left",
                    ),
                    "asset_class": st.column_config.TextColumn(
                        tr("home.asset_class", lang),
                        width=110,
                        help=tr("home.asset_class_help", lang),
                        alignment="left",
                    ),
                    "sub_class": st.column_config.TextColumn(
                        tr("home.sub_class", lang),
                        width=155,
                        help=tr("home.sub_class_help", lang),
                        alignment="left",
                    ),
                },
            )
            pick = st.selectbox(
                tr("home.detail_select", lang),
                dim["ticker"],
            )
            row = dim.set_index("ticker").loc[pick]
            leverage = (
                (
                    f" · 일간 {int(row['leverage'])}배"
                    if lang == "ko"
                    else f" · {int(row['leverage'])}x daily"
                )
                if row["leverage"] > 1
                else ""
            )
            asset_class = (
                tr("home.not_classified", lang)
                if row["asset_class"] == "unclassified"
                else (
                    ASSET_LABELS_KO.get(
                        row["asset_class"],
                        row["asset_class"],
                    )
                    if lang == "ko"
                    else row["asset_class"]
                )
            )
            sub_class = (
                tr("home.not_classified", lang)
                if row["sub_class"] == "unclassified"
                else (
                    SUBCLASS_LABELS_KO.get(
                        row["sub_class"],
                        row["sub_class"],
                    )
                    if lang == "ko"
                    else row["sub_class"]
                )
            )
            description = (
                TICKER_DESCRIPTIONS_KO.get(pick, row["description"])
                if lang == "ko"
                else row["description"]
            )
            st.info(
                f"**{pick} — {row['name']}**  \n"
                f"`{asset_class} / {sub_class}`{leverage}\n\n"
                f"{description}"
            )
        except Exception:
            st.caption(tr("home.dim_missing", lang))


def line_chart(
    df: pd.DataFrame,
    y: str,
    lang: Language,
    colors: dict | None = None,
    *,
    money_currency: str | None = None,
) -> None:
    # No figure title — the st.subheader above each chart already labels it
    labels = (
        {
            "price_date": "Date",
            "adj_close": "Dividend-adjusted price",
            "indexed_price": "Growth of 100",
            "cum_return": "Total return",
            "rolling_vol_30d": "30-day price swings",
            "ticker": "ETF",
        }
        if lang == "en"
        else {
            "price_date": "날짜",
            "adj_close": "배당 반영 가격",
            "indexed_price": "100 기준 성장",
            "cum_return": "누적수익률",
            "rolling_vol_30d": "30일 가격 변동",
            "ticker": "ETF",
        }
    )
    fig = px.line(
        df,
        x="price_date",
        y=y,
        color="ticker",
        line_dash="ticker",
        color_discrete_map=colors,
        line_dash_sequence=["solid", "dash", "dot", "dashdot"],
        labels=labels,
    )
    if y in {"cum_return", "rolling_vol_30d"}:
        fig.update_yaxes(tickformat=".1%")
    elif y == "adj_close" and money_currency is not None:
        fig.update_yaxes(tickprefix=currency_symbol(money_currency), tickformat=",.2f")
    fig.update_layout(**PLOTLY_LAYOUT, title_text="", legend_title_text="")
    # Date ticks already make the horizontal scale clear. Omitting the
    # redundant axis title keeps it from colliding with the mobile legend.
    fig.update_xaxes(title_text="")
    st.plotly_chart(fig, width="stretch")


lang = current_language()

st.title("ETF Analytics")
st.caption(tr("home.subtitle", lang))

try:
    base_returns_df = load_mart_returns()
    risk_df = load_mart_risk()
except Exception as exc:
    st.error(tr("home.data_error", lang))
    with st.expander(tr("home.admin_details", lang)):
        st.code(str(exc))
    st.stop()

demo_mode_banner(lang)

custom_prices = session_prices(st.session_state)
returns_df, merged_risk = merge_custom_data(
    base_returns_df,
    risk_df,
    custom_prices,
)
if merged_risk is not None:
    risk_df = merged_risk

tickers = sorted(returns_df["ticker"].unique())
COLORS = ticker_color_map(tickers)  # stable palette across all charts
flash_message = st.session_state.pop(SEARCH_FLASH_KEY, None)
if isinstance(flash_message, str) and flash_message:
    st.toast(flash_message, icon="✅")

selected, base_currency, return_basis = render_compare_selector(
    returns_df,
    base_returns_df,
    lang,
)
if not selected:
    st.info(tr("home.empty_selection", lang))
listing_filtered = returns_df[returns_df["ticker"].isin(selected)]
listing_risk_filtered = risk_df[risk_df["ticker"].isin(selected)]
filtered = listing_filtered
risk_filtered = listing_risk_filtered
currency_error = False
if selected and return_basis == "base":
    try:
        listing_currencies = _listing_currency_map(base_returns_df)
        selected_currencies = tuple(
            sorted(
                {
                    listing_currencies[ticker]
                    for ticker in selected
                    if ticker in listing_currencies
                }
                | {base_currency}
            )
        )
        usd_rates = cached_usd_exchange_rates(selected_currencies)
        filtered = convert_prices_to_base_currency(
            listing_filtered,
            listing_currencies,
            base_currency,
            usd_rates,
        )
        _, risk_filtered = build_custom_marts(filtered)
    except CurrencyConversionError as exc:
        currency_error = True
        filtered = listing_filtered.iloc[0:0].copy()
        risk_filtered = listing_risk_filtered.iloc[0:0].copy()
        st.error(
            tr(
                "currency.conversion_error",
                lang,
                detail=str(exc),
            )
        )
comparison = build_indexed_price_comparison(filtered)
comparison_start = (
    comparison["price_date"].min().strftime("%Y-%m-%d") if not comparison.empty else ""
)
if selected and comparison.empty and not currency_error:
    st.warning(tr("home.no_common_dates", lang))

price_tab, return_tab, risk_tab = st.tabs(
    [
        tr("home.tab_price", lang),
        tr("home.tab_return", lang),
        tr("home.tab_risk", lang),
    ]
)

with price_tab:
    show_raw_prices = st.toggle(
        tr("home.show_raw_prices", lang),
        help=tr("home.show_raw_prices_help", lang),
    )
    if show_raw_prices:
        st.subheader(tr("home.adjusted_price", lang))
        st.caption(
            tr(
                (
                    "home.adjusted_price_base_caption"
                    if return_basis == "base"
                    else "home.adjusted_price_caption"
                ),
                lang,
                currency=base_currency,
            )
        )
        line_chart(
            filtered,
            "adj_close",
            lang,
            COLORS,
            money_currency=base_currency if return_basis == "base" else None,
        )
    else:
        st.subheader(tr("home.indexed_price", lang))
        st.caption(
            tr(
                (
                    "home.indexed_price_base_caption"
                    if return_basis == "base"
                    else "home.indexed_price_caption"
                ),
                lang,
                date=comparison_start,
                currency=base_currency,
            )
        )
        line_chart(comparison, "indexed_price", lang, COLORS)

with return_tab:
    st.subheader(tr("home.cumulative_return", lang))
    st.caption(
        tr(
            (
                "home.cumulative_return_base_caption"
                if return_basis == "base"
                else "home.cumulative_return_caption"
            ),
            lang,
            date=comparison_start,
            currency=base_currency,
        )
    )
    cum = comparison.copy()
    cum["cum_return"] = cum["indexed_price"] / 100.0 - 1.0
    line_chart(cum, "cum_return", lang, COLORS)

with risk_tab:
    st.subheader(tr("home.volatility", lang))
    st.caption(
        tr(
            (
                "home.volatility_base_caption"
                if return_basis == "base"
                else "home.volatility_caption"
            ),
            lang,
            currency=base_currency,
        )
    )
    line_chart(risk_filtered, "rolling_vol_30d", lang, COLORS)

    st.subheader(tr("home.latest", lang))
    latest = (
        risk_filtered.sort_values("price_date")
        .groupby("ticker", as_index=False)
        .tail(1)[["ticker", "price_date", "rolling_vol_30d", "drawdown"]]
    )
    latest["price_date"] = latest["price_date"].dt.strftime("%Y-%m-%d")
    latest["rolling_vol_30d"] = latest["rolling_vol_30d"].round(4)
    latest["drawdown"] = latest["drawdown"].round(4)

    st.dataframe(
        latest,
        width=dataframe_width(latest),
        row_height=DATAFRAME_ROW_HEIGHT,
        hide_index=True,
        column_config={
            "rolling_vol_30d": st.column_config.NumberColumn(
                tr("home.volatility", lang),
                help=glossary_help("rolling_vol_30d", lang),
                format="percent",
                alignment="right",
            ),
            "drawdown": st.column_config.NumberColumn(
                tr("home.drawdown", lang),
                help=glossary_help("drawdown", lang),
                format="percent",
                alignment="right",
            ),
            "ticker": st.column_config.TextColumn(
                tr("home.ticker", lang),
                alignment="left",
            ),
            "price_date": st.column_config.TextColumn(
                tr("home.as_of_date", lang),
                alignment="left",
            ),
        },
    )

with st.expander(tr("home.intro_title", lang)):
    st.markdown(tr("home.intro_body", lang))

render_ticker_guide(lang)

with st.expander(tr("home.technical_title", lang)):
    st.caption(tr("home.technical_body", lang))

glossary_expander(
    ["adj_close", "cum_return", "rolling_vol_30d", "drawdown"],
    lang,
    title=tr("home.metrics_guide", lang),
)
