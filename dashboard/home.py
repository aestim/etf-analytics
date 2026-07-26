"""
Streamlit dashboard home page — reads mart tables from PostgreSQL.
Run after: docker compose up, ingest, dbt run.
"""

from __future__ import annotations

import html

import pandas as pd
import plotly.express as px
import streamlit as st

from chart_colors import ticker_color_map
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
    build_indexed_price_comparison,
    clear_session_prices,
    direct_symbol_candidate,
    fetch_price_history,
    looks_like_isin,
    merge_custom_data,
    normalize_search_query,
    normalize_ticker,
    remove_session_ticker,
    search_instruments,
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


def _candidate_identity_html(
    candidate: InstrumentCandidate,
    lang: Language,
) -> str:
    """Render provider text as escaped, non-interactive card content."""

    badge = html.escape(candidate.symbol.partition(".")[0][:4])
    name = html.escape(candidate.display_name)
    symbol = html.escape(candidate.symbol)
    exchange = html.escape(candidate.exchange or tr("custom.exchange_unknown", lang))
    provider_type = html.escape(
        candidate.provider_type or tr("custom.type_unknown", lang)
    )
    volume = (
        tr(
            "custom.average_volume",
            lang,
            volume=f"{candidate.average_daily_volume:,.0f}",
        )
        if candidate.average_daily_volume is not None
        else tr("custom.volume_unavailable", lang)
    )
    return (
        "<div style='display:flex;gap:.75rem;align-items:center'>"
        "<div style='min-width:3rem;height:3rem;border-radius:.75rem;"
        "display:flex;align-items:center;justify-content:center;"
        "background:#12a8d8;color:white;font-size:.72rem;font-weight:700'>"
        f"{badge}</div>"
        "<div style='min-width:0'>"
        f"<div style='font-weight:650;line-height:1.25'>{name}</div>"
        "<div style='opacity:.68;font-size:.82rem;margin-top:.2rem'>"
        f"{symbol} · {exchange} · {provider_type}</div>"
        "<div style='opacity:.68;font-size:.78rem;margin-top:.16rem'>"
        f"{html.escape(volume)}</div>"
        "</div></div>"
    )


def _add_custom_symbol(
    ticker: str,
    returns_df: pd.DataFrame,
    lang: Language,
) -> bool:
    """Fetch only the selected symbol, then add it to this session."""

    try:
        normalized_ticker = normalize_ticker(ticker)
        built_in = set(returns_df["ticker"].dropna().astype(str))
        if normalized_ticker in built_in:
            _select_ticker_for_charts(normalized_ticker)
            st.session_state[SEARCH_FLASH_KEY] = tr(
                "custom.already_available",
                lang,
                ticker=normalized_ticker,
            )
            return True
        with st.spinner(tr("custom.loading", lang, ticker=normalized_ticker)):
            prices = cached_custom_history(normalized_ticker)
        add_session_prices(st.session_state, prices)
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
    return False


def custom_etf_dialog(
    base_returns_df: pd.DataFrame,
    lang: Language,
) -> None:
    """Open the session ETF search and management dialog."""

    @st.dialog(tr("custom.dialog_title", lang), width="large")
    def render_dialog() -> None:
        st.caption(tr("custom.help", lang))
        with st.form("custom_etf_search_form"):
            raw_query = st.text_input(
                tr("custom.input_label", lang),
                placeholder=tr("custom.input_placeholder", lang),
                value=st.session_state.get(SEARCH_QUERY_KEY, ""),
                key="custom_etf_dialog_query",
            )
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
            submitted = st.form_submit_button(
                tr("custom.search", lang),
                type="primary",
                width="stretch",
            )

        if submitted:
            try:
                query = normalize_search_query(raw_query)
                resolved_sort = (
                    sort_mode if sort_mode in {"relevance", "volume"} else "volume"
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
                _store_search_state("", (), direct_fallback=False)
                st.error(tr("custom.invalid_query", lang))
            except InstrumentSearchError as exc:
                query = str(exc)
                direct = direct_symbol_candidate(query)
                candidates = (direct,) if direct is not None else ()
                _store_search_state(
                    query,
                    candidates,
                    direct_fallback=direct is not None,
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

            def render_candidate_card(
                candidate: InstrumentCandidate,
            ) -> None:
                with st.container(border=True):
                    identity_col, action_col = st.columns(
                        [8, 1],
                        vertical_alignment="center",
                    )
                    identity_col.markdown(
                        _candidate_identity_html(candidate, lang),
                        unsafe_allow_html=True,
                    )
                    if action_col.button(
                        tr("custom.add", lang),
                        type="primary",
                        key=(f"add_custom_etf_{generation}_{candidate.symbol}"),
                        width="stretch",
                    ) and _add_custom_symbol(
                        candidate.symbol,
                        base_returns_df,
                        lang,
                    ):
                        st.rerun()

            for candidate in candidates[:5]:
                render_candidate_card(candidate)
            if len(candidates) > 5:
                show_all_key = f"custom_etf_show_all_{generation}"
                show_all = bool(st.session_state.get(show_all_key, False))
                if not show_all and st.button(
                    tr(
                        "custom.show_more",
                        lang,
                        count=len(candidates) - 5,
                    ),
                    key=f"show_more_custom_etfs_{generation}",
                    width="stretch",
                ):
                    st.session_state[show_all_key] = True
                    show_all = True
                if show_all:
                    for candidate in candidates[5:]:
                        render_candidate_card(candidate)
        elif search_query:
            st.info(tr("custom.no_results", lang))

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
                        width="stretch",
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
) -> list[str]:
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
        if add_col.button(
            tr("home.add_etf", lang),
            type="primary",
            width="stretch",
        ):
            custom_etf_dialog(base_returns_df, lang)
        st.caption(tr("home.compare_help", lang))
    return selected


def render_ticker_guide(lang: Language) -> None:
    """Render the reference universe as optional, secondary information."""

    with st.expander(tr("home.ticker_guide", lang)):
        try:
            dim = load_dim_etf()
            display_dim = dim.drop(columns=["description"]).copy()
            if lang == "ko":
                display_dim["asset_class"] = display_dim["asset_class"].replace(
                    ASSET_LABELS_KO
                )
                display_dim["sub_class"] = display_dim["sub_class"].replace(
                    SUBCLASS_LABELS_KO
                )
            st.dataframe(
                display_dim,
                width=dataframe_width(display_dim),
                row_height=DATAFRAME_ROW_HEIGHT,
                hide_index=True,
                column_config={
                    "ticker": st.column_config.TextColumn(
                        tr("home.ticker", lang),
                        alignment="left",
                    ),
                    "name": st.column_config.TextColumn(
                        tr("home.fund_name", lang),
                        alignment="left",
                    ),
                    "asset_class": st.column_config.TextColumn(
                        tr("home.asset_class", lang),
                        help=tr("home.asset_class_help", lang),
                        alignment="left",
                    ),
                    "sub_class": st.column_config.TextColumn(
                        tr("home.sub_class", lang),
                        help=tr("home.sub_class_help", lang),
                        alignment="left",
                    ),
                    "leverage": st.column_config.NumberColumn(
                        tr("home.leverage", lang),
                        help=tr("home.leverage_help", lang),
                        alignment="right",
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
                ASSET_LABELS_KO.get(
                    row["asset_class"],
                    row["asset_class"],
                )
                if lang == "ko"
                else row["asset_class"]
            )
            sub_class = (
                SUBCLASS_LABELS_KO.get(
                    row["sub_class"],
                    row["sub_class"],
                )
                if lang == "ko"
                else row["sub_class"]
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

selected = render_compare_selector(
    returns_df,
    base_returns_df,
    lang,
)
if not selected:
    st.info(tr("home.empty_selection", lang))
filtered = returns_df[returns_df["ticker"].isin(selected)]
risk_filtered = risk_df[risk_df["ticker"].isin(selected)]
comparison = build_indexed_price_comparison(filtered)
comparison_start = (
    comparison["price_date"].min().strftime("%Y-%m-%d") if not comparison.empty else ""
)
if selected and comparison.empty:
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
        st.caption(tr("home.adjusted_price_caption", lang))
        line_chart(filtered, "adj_close", lang, COLORS)
    else:
        st.subheader(tr("home.indexed_price", lang))
        st.caption(
            tr(
                "home.indexed_price_caption",
                lang,
                date=comparison_start,
            )
        )
        line_chart(comparison, "indexed_price", lang, COLORS)

with return_tab:
    st.subheader(tr("home.cumulative_return", lang))
    st.caption(
        tr(
            "home.cumulative_return_caption",
            lang,
            date=comparison_start,
        )
    )
    cum = comparison.copy()
    cum["cum_return"] = cum["indexed_price"] / 100.0 - 1.0
    line_chart(cum, "cum_return", lang, COLORS)

with risk_tab:
    st.subheader(tr("home.volatility", lang))
    st.caption(tr("home.volatility_caption", lang))
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
