"""Educational portfolio simulator and five representative rule examples."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT / "dashboard", _ROOT / "analytics"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import simulator as sim  # noqa: E402
import strategies as strat  # noqa: E402
from currency_conversion import (  # noqa: E402
    BASE_CURRENCY_STATE_KEY,
    SUPPORTED_BASE_CURRENCIES,
    CurrencyConversionError,
    convert_prices_to_base_currency,
    currency_symbol,
    fetch_usd_exchange_rates,
    format_compact_money,
    format_money,
)
from custom_etf import (  # noqa: E402
    merge_custom_data,
    session_instrument_candidates,
    session_prices,
    session_tickers,
)
from db import (  # noqa: E402
    DATAFRAME_ROW_HEIGHT,
    PLOTLY_LAYOUT,
    demo_mode_banner,
    glossary_items,
    load_dim_etf,
    load_mart_returns,
)
from i18n import current_language, tr  # noqa: E402

REQUIRED_EXAMPLES = {"SPY", "QQQ", "BND", "TQQQ"}
DEFAULT_TICKERS = ["SPY", "BND", "GLD"]
DEFAULT_WEIGHTS = {"SPY": 60.0, "BND": 30.0, "GLD": 10.0}
PRIMARY_PLAN_STATE_KEY = "strategy_primary_plan_v2"
SECONDARY_PLAN_STATE_KEY = "strategy_secondary_plan_v2"
TOTAL_CAPITAL_STATE_KEY = "strategy_total_capital_v2"
START_DATE_STATE_KEY = "strategy_start_date_v2"
REFERENCE_SELECTION_STATE_KEY = "strategy_reference_examples_v2"


@st.cache_data(ttl=3600, show_spinner=False)
def cached_usd_exchange_rates(currencies: tuple[str, ...]) -> pd.DataFrame:
    """Cache the daily FX series shared by all Strategy Lab calculations."""

    return fetch_usd_exchange_rates(currencies)


@dataclass(frozen=True)
class PortfolioPlan:
    """One user-configured portfolio and its execution rules."""

    name: str
    tickers: tuple[str, ...]
    weights: dict[str, float]
    deployment_months: int
    rebalance_annually: bool


def _percent(value: float) -> str:
    return f"{value:.1%}"


def _curve_metrics(value: pd.Series) -> dict[str, float]:
    clean = value.dropna()
    initial = float(clean.iloc[0])
    final = float(clean.iloc[-1])
    return {
        "final_value": final,
        "profit": final - initial,
        "total_return": final / initial - 1.0,
        "max_drawdown": strat.max_drawdown(clean),
        "annualized_vol": strat.annualized_vol(
            clean,
            periods_per_year=strat.observed_periods_per_year(clean.index),
        ),
    }


def _value_chart(curves: dict[str, pd.Series], lang: str, currency: str):
    frame = pd.DataFrame(curves)
    frame.index.name = "price_date"
    long = frame.reset_index().melt(
        id_vars="price_date",
        var_name="strategy",
        value_name="value",
    )
    fig = px.line(
        long,
        x="price_date",
        y="value",
        color="strategy",
        line_dash="strategy",
        labels={
            "price_date": tr("strategy.date", lang),
            "value": tr("strategy.capital", lang),
            "strategy": tr("strategy.rule", lang),
        },
    )
    fig.update_layout(**PLOTLY_LAYOUT, title_text="", legend_title_text="")
    fig.update_xaxes(title_text="")
    fig.update_yaxes(
        title_text="",
        tickformat=",.0f",
        tickprefix=currency_symbol(currency),
    )
    return fig


def _drawdown_chart(curves: dict[str, pd.Series], lang: str):
    frame = pd.DataFrame(curves)
    frame = frame.div(frame.cummax()) - 1.0
    frame.index.name = "price_date"
    long = frame.reset_index().melt(
        id_vars="price_date",
        var_name="strategy",
        value_name="drawdown",
    )
    fig = px.line(
        long,
        x="price_date",
        y="drawdown",
        color="strategy",
        line_dash="strategy",
        labels={
            "price_date": tr("strategy.date", lang),
            "drawdown": tr("home.drawdown", lang),
            "strategy": tr("strategy.rule", lang),
        },
    )
    fig.update_layout(**PLOTLY_LAYOUT, title_text="", legend_title_text="")
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="", tickformat=".0%")
    return fig


def _example_labels(lang: str) -> dict[str, str]:
    return {
        "buy_hold": tr("strategy.buy_hold_short", lang),
        "dca": tr("strategy.dca_short", lang),
        "balanced": tr("strategy.balanced_short", lang),
        "trend": tr("strategy.trend_short", lang),
        "split": tr("strategy.split_short", lang),
    }


def _allocation_inputs(
    options: list[str],
    lang: str,
    prefix: str,
    defaults: list[str],
    default_weights: dict[str, float],
) -> tuple[list[str], dict[str, float]] | None:
    ticker_key = f"{prefix}_tickers"
    multiselect_kwargs = {
        "label": tr("simulation.select_etfs", lang),
        "options": options,
        "max_selections": 5,
        "key": ticker_key,
    }
    if ticker_key not in st.session_state:
        multiselect_kwargs["default"] = defaults
    selected = st.multiselect(**multiselect_kwargs)
    if not selected:
        st.info(tr("home.empty_selection", lang))
        return None

    for ticker in selected:
        state_key = f"{prefix}_weight_{ticker}"
        if state_key not in st.session_state:
            st.session_state[state_key] = default_weights.get(
                ticker, 100.0 / len(selected)
            )

    if st.button(tr("simulation.equal_weights", lang), key=f"{prefix}_equal"):
        equal = round(100.0 / len(selected), 1)
        assigned = 0.0
        for ticker in selected[:-1]:
            st.session_state[f"{prefix}_weight_{ticker}"] = equal
            assigned += equal
        st.session_state[f"{prefix}_weight_{selected[-1]}"] = round(100.0 - assigned, 1)

    percentages = {
        ticker: st.number_input(
            tr("simulation.weight_label", lang, ticker=ticker),
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            format="%.1f",
            key=f"{prefix}_weight_{ticker}",
        )
        for ticker in selected
    }
    total = sum(percentages.values())
    st.markdown(tr("simulation.weight_total", lang, total=total))
    if not np.isclose(total, 100.0, atol=1e-6) or any(
        value <= 0 for value in percentages.values()
    ):
        st.warning(tr("simulation.weight_invalid", lang))
        return None
    st.caption(f"✅ {tr('simulation.weight_valid', lang)}")
    return selected, {
        ticker: percentage / 100.0 for ticker, percentage in percentages.items()
    }


def _plan_inputs(prefix: str, lang: str, ticker_count: int) -> tuple[int, bool]:
    method_key = f"{prefix}_method"
    method_kwargs = {
        "label": tr("simulation.plan_method", lang),
        "options": ["lump", "staged"],
        "required": True,
        "format_func": lambda value: tr(f"simulation.plan_{value}", lang),
        "key": method_key,
    }
    if method_key not in st.session_state:
        method_kwargs["default"] = "lump"
    method = st.segmented_control(**method_kwargs)
    months = 1
    if method == "staged":
        months_key = f"{prefix}_months"
        month_kwargs = {
            "label": tr("simulation.staged_months", lang),
            "options": [6, 12, 24],
            "format_func": lambda value: tr(
                "simulation.month_option", lang, months=value
            ),
            "key": months_key,
        }
        if months_key not in st.session_state:
            month_kwargs["index"] = 1
        months = st.selectbox(**month_kwargs)
    rebalance_key = f"{prefix}_rebalance"
    rebalance_disabled = ticker_count < 2
    if rebalance_disabled and st.session_state.get(rebalance_key):
        st.session_state[rebalance_key] = False
    rebalance = st.toggle(
        tr("simulation.plan_rebalance", lang),
        help=tr("simulation.plan_rebalance_help", lang),
        disabled=rebalance_disabled,
        key=rebalance_key,
    )
    if rebalance_disabled:
        st.caption(tr("simulation.plan_single_etf", lang))
    return months, rebalance


def _plan_rule_parts(plan: PortfolioPlan, lang: str) -> tuple[str, str]:
    entry = (
        tr("simulation.plan_lump", lang)
        if plan.deployment_months == 1
        else tr(
            "simulation.plan_staged_summary",
            lang,
            months=plan.deployment_months,
        )
    )
    rebalance = tr(
        "simulation.plan_yearly" if plan.rebalance_annually else "simulation.plan_hold",
        lang,
    )
    return entry, rebalance


def _plan_summary(plan: PortfolioPlan, lang: str) -> str:
    entry, rebalance = _plan_rule_parts(plan, lang)
    return tr(
        "simulation.plan_summary",
        lang,
        name=plan.name,
        entry=entry,
        rebalance=rebalance,
    )


def _plan_state(plan: PortfolioPlan) -> dict[str, object]:
    return {
        "name": plan.name,
        "tickers": list(plan.tickers),
        "weights": dict(plan.weights),
        "deployment_months": plan.deployment_months,
        "rebalance_annually": plan.rebalance_annually,
    }


def _plan_from_state(
    value: object,
    options: list[str],
    *,
    name_override: str | None = None,
) -> PortfolioPlan | None:
    if not isinstance(value, dict):
        return None
    raw_tickers = value.get("tickers")
    raw_weights = value.get("weights")
    if not isinstance(raw_tickers, list) or not isinstance(raw_weights, dict):
        return None
    tickers = tuple(
        ticker
        for ticker in raw_tickers
        if isinstance(ticker, str) and ticker in options
    )
    if not tickers or len(tickers) != len(raw_tickers):
        return None
    try:
        weights = {ticker: float(raw_weights[ticker]) for ticker in tickers}
        deployment_months = int(value.get("deployment_months", 1))
    except (KeyError, TypeError, ValueError):
        return None
    if (
        any(weight <= 0 for weight in weights.values())
        or not np.isclose(sum(weights.values()), 1.0)
        or deployment_months not in {1, 6, 12, 24}
    ):
        return None
    name = name_override or str(value.get("name", "")).strip()
    if not name:
        return None
    return PortfolioPlan(
        name=name,
        tickers=tickers,
        weights=weights,
        deployment_months=deployment_months,
        rebalance_annually=bool(value.get("rebalance_annually", False)),
    )


def _default_primary_plan(options: list[str], lang: str) -> PortfolioPlan:
    tickers = tuple(ticker for ticker in DEFAULT_TICKERS if ticker in options)
    if not tickers:
        tickers = (options[0],)
    raw_weights = {
        ticker: DEFAULT_WEIGHTS.get(ticker, 100.0 / len(tickers)) for ticker in tickers
    }
    total = sum(raw_weights.values())
    weights = {ticker: weight / total for ticker, weight in raw_weights.items()}
    return PortfolioPlan(
        name=tr("simulation.my_strategy", lang),
        tickers=tickers,
        weights=weights,
        deployment_months=1,
        rebalance_annually=False,
    )


def _available_start_date(
    all_prices: pd.DataFrame,
    tickers: tuple[str, ...],
) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp] | None:
    prices = all_prices[list(tickers)].dropna()
    if len(prices) < 2:
        return None
    latest = prices.index.max()
    desired = latest - pd.DateOffset(years=5)
    position = min(prices.index.searchsorted(desired), len(prices) - 2)
    return prices.index.min(), prices.index[-2], prices.index[position]


def _prepare_strategy_draft(
    target: str,
    plan: PortfolioPlan,
    *,
    total_capital: float,
    requested_start: pd.Timestamp,
) -> None:
    prefix = f"strategy_editor_{target}"
    st.session_state[f"{prefix}_tickers"] = list(plan.tickers)
    for ticker, weight in plan.weights.items():
        st.session_state[f"{prefix}_weight_{ticker}"] = weight * 100
    st.session_state[f"{prefix}_method"] = (
        "lump" if plan.deployment_months == 1 else "staged"
    )
    st.session_state[f"{prefix}_months"] = max(plan.deployment_months, 6)
    st.session_state[f"{prefix}_rebalance"] = plan.rebalance_annually
    st.session_state[f"{prefix}_name"] = plan.name
    st.session_state[f"{prefix}_total"] = float(total_capital)
    st.session_state[f"{prefix}_start"] = requested_start.date()


def _strategy_editor_dialog(
    target: str,
    current_plan: PortfolioPlan,
    all_prices: pd.DataFrame,
    options: list[str],
    total_capital: float,
    requested_start: pd.Timestamp,
    lang: str,
    currency: str,
) -> None:
    title_key = (
        "simulation.editor_primary_title"
        if target == "primary"
        else "simulation.editor_second_title"
    )

    @st.dialog(tr(title_key, lang), width="medium")
    def render_editor() -> None:
        prefix = f"strategy_editor_{target}"
        st.caption(tr("simulation.editor_caption", lang))
        strategy_name = current_plan.name
        if target == "secondary":
            strategy_name = st.text_input(
                tr("simulation.second_name", lang),
                max_chars=30,
                key=f"{prefix}_name",
            ).strip() or tr("simulation.second_default", lang)

        allocation = _allocation_inputs(
            options,
            lang,
            prefix,
            list(current_plan.tickers),
            {ticker: weight * 100 for ticker, weight in current_plan.weights.items()},
        )

        editor_total = total_capital
        editor_start = requested_start
        date_range = None
        if allocation is not None:
            selected_tickers, _ = allocation
            date_range = _available_start_date(
                all_prices,
                tuple(selected_tickers),
            )

        if target == "primary":
            amount_step = 1_000.0
            editor_total = st.number_input(
                tr("simulation.total_amount", lang, unit=currency),
                min_value=amount_step,
                step=amount_step,
                help=tr("simulation.amount_help", lang),
                key=f"{prefix}_total",
            )
            if date_range is not None:
                minimum, maximum, fallback = date_range
                start_key = f"{prefix}_start"
                candidate = pd.Timestamp(
                    st.session_state.get(start_key, fallback.date())
                )
                clamped = min(max(candidate, minimum), maximum)
                st.session_state[start_key] = clamped.date()
                editor_start = pd.Timestamp(
                    st.date_input(
                        tr("simulation.start_date", lang),
                        min_value=minimum.date(),
                        max_value=maximum.date(),
                        key=start_key,
                    )
                )

        ticker_count = len(allocation[0]) if allocation is not None else 0
        months, rebalance = _plan_inputs(prefix, lang, ticker_count)
        can_apply = allocation is not None and date_range is not None
        if target == "secondary":
            can_apply = allocation is not None
            if strategy_name == tr("simulation.my_strategy", lang):
                st.warning(tr("simulation.second_name_duplicate", lang))
                can_apply = False

        if st.button(
            tr("simulation.apply", lang),
            type="primary",
            disabled=not can_apply,
            key=f"{prefix}_apply",
        ):
            selected_tickers, weights = allocation
            plan = PortfolioPlan(
                name=(
                    tr("simulation.my_strategy", lang)
                    if target == "primary"
                    else strategy_name
                ),
                tickers=tuple(selected_tickers),
                weights=weights,
                deployment_months=months,
                rebalance_annually=rebalance,
            )
            state_key = (
                PRIMARY_PLAN_STATE_KEY
                if target == "primary"
                else SECONDARY_PLAN_STATE_KEY
            )
            st.session_state[state_key] = _plan_state(plan)
            if target == "primary":
                st.session_state[f"{TOTAL_CAPITAL_STATE_KEY}_{currency}"] = float(
                    editor_total
                )
                st.session_state[START_DATE_STATE_KEY] = editor_start.date()
            st.rerun()

    render_editor()


def _allocation_summary(plan: PortfolioPlan) -> str:
    return " · ".join(
        f"{ticker} {weight:.0%}" for ticker, weight in plan.weights.items()
    )


def _comparison_summary_frame(
    curves: dict[str, pd.Series],
    lang: str,
    currency: str,
) -> pd.DataFrame:
    rows = []
    for name, curve in curves.items():
        metrics = _curve_metrics(curve)
        rows.append(
            {
                tr("strategy.rule", lang): name,
                tr("simulation.final_value", lang): format_compact_money(
                    metrics["final_value"], currency
                ),
                tr("simulation.total_return", lang): _percent(metrics["total_return"]),
                tr("simulation.max_drawdown", lang): _percent(metrics["max_drawdown"]),
                tr("simulation.annualized_vol", lang): _percent(
                    metrics["annualized_vol"]
                ),
            }
        )
    return pd.DataFrame(rows)


def _reference_curves(
    all_prices: pd.DataFrame,
    plans: list[PortfolioPlan],
    total_capital: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[dict[str, pd.Series], pd.DatetimeIndex] | None:
    custom_tickers = {ticker for plan in plans for ticker in plan.tickers}
    columns = sorted(REQUIRED_EXAMPLES | custom_tickers)
    if set(columns) - set(all_prices.columns):
        return None
    common = all_prices.loc[start:end, columns].dropna()
    if common.empty or common.index[0] != start or common.index[-1] != end:
        return None

    curves = {
        f"custom_{index}": sim.portfolio_strategy(
            common[list(plan.tickers)],
            plan.weights,
            total_capital,
            deployment_months=plan.deployment_months,
            rebalance_annually=plan.rebalance_annually,
        ).value
        for index, plan in enumerate(plans)
    }
    all_months = len(common.index.to_period("M").unique())
    curves.update(
        {
            "buy_hold": total_capital * strat.lump_sum(common["SPY"]),
            "dca": sim.staged_portfolio(
                common[["QQQ"]],
                {"QQQ": 1.0},
                total_capital,
                all_months,
            ).value,
            "balanced": total_capital
            * strat.rebalance(common, {"SPY": 0.6, "BND": 0.4}, every=63),
            "split": total_capital
            * strat.infinite_buy(common["TQQQ"], n_splits=40, take_profit=0.10),
        }
    )
    # Calculate the 200-day signal on history before the displayed period, then
    # rebase the resulting equity curve at the common start. Without this
    # warm-up, every comparison falsely parks in cash for its first ~200 rows.
    trend_window = strat.sma_trend_for_period(
        all_prices["QQQ"],
        start,
        end,
        window=200,
    )
    trend_window = trend_window.reindex(common.index).dropna()
    if len(trend_window) != len(common):
        return None
    curves["trend"] = total_capital * trend_window
    return curves, common.index


def _render_leverage_warning(
    plans: list[PortfolioPlan], dim_etf: pd.DataFrame, lang: str
) -> None:
    if dim_etf.empty or "leverage" not in dim_etf:
        return
    leverage = dim_etf.set_index("ticker")["leverage"]
    leveraged = sorted(
        {
            ticker
            for plan in plans
            for ticker in plan.tickers
            if ticker in leverage.index and float(leverage[ticker]) > 1
        }
    )
    if leveraged:
        st.warning(
            tr(
                "simulation.leverage_warning",
                lang,
                tickers=", ".join(leveraged),
            )
        )


def _render_custom_simulator(
    all_prices: pd.DataFrame,
    dim_etf: pd.DataFrame,
    lang: str,
    currency: str,
) -> None:
    options = sorted(all_prices.columns)
    if not options:
        st.warning(tr("simulation.insufficient_history", lang))
        return

    default_plan = _default_primary_plan(options, lang)
    primary_plan = _plan_from_state(
        st.session_state.get(PRIMARY_PLAN_STATE_KEY),
        options,
        name_override=tr("simulation.my_strategy", lang),
    )
    if primary_plan is None:
        primary_plan = default_plan
        st.session_state[PRIMARY_PLAN_STATE_KEY] = _plan_state(primary_plan)

    capital_key = f"{TOTAL_CAPITAL_STATE_KEY}_{currency}"
    amount_default = 10_000.0
    total_capital = float(st.session_state.get(capital_key, amount_default))
    start_range = _available_start_date(all_prices, primary_plan.tickers)
    if start_range is None:
        st.warning(tr("simulation.insufficient_history", lang))
        return
    minimum_start, maximum_start, default_start = start_range
    requested_start = pd.Timestamp(
        st.session_state.get(START_DATE_STATE_KEY, default_start.date())
    )
    requested_start = min(
        max(requested_start, minimum_start),
        maximum_start,
    )
    st.session_state[START_DATE_STATE_KEY] = requested_start.date()

    secondary_plan = _plan_from_state(
        st.session_state.get(SECONDARY_PLAN_STATE_KEY),
        options,
    )
    plans = [primary_plan]
    if secondary_plan is not None:
        plans.append(secondary_plan)

    st.subheader(tr("simulation.reference_title", lang))
    st.caption(tr("simulation.workspace_caption", lang))
    with st.container(border=True):
        primary_text, primary_action = st.columns(
            [5, 1],
            vertical_alignment="center",
        )
        primary_text.markdown(f"**{primary_plan.name}**")
        primary_text.caption(_allocation_summary(primary_plan))
        primary_text.caption(
            f"{format_money(total_capital, currency)} · "
            f"{requested_start:%Y-%m-%d} · "
            f"{' · '.join(_plan_rule_parts(primary_plan, lang))}"
        )
        # Right-aligned so the action lines up with the card edge instead of
        # floating in the middle of an oversized column.
        if primary_action.container(horizontal_alignment="right").button(
            tr("simulation.edit", lang),
            key="strategy_edit_primary",
        ):
            _prepare_strategy_draft(
                "primary",
                primary_plan,
                total_capital=total_capital,
                requested_start=requested_start,
            )
            _strategy_editor_dialog(
                "primary",
                primary_plan,
                all_prices,
                options,
                total_capital,
                requested_start,
                lang,
                currency,
            )

        if secondary_plan is not None:
            st.divider()
            secondary_text, secondary_actions = st.columns(
                [5, 1],
                vertical_alignment="center",
            )
            secondary_text.markdown(f"**{secondary_plan.name}**")
            secondary_text.caption(_allocation_summary(secondary_plan))
            secondary_text.caption(" · ".join(_plan_rule_parts(secondary_plan, lang)))
            secondary_buttons = secondary_actions.container(
                horizontal_alignment="right"
            )
            if secondary_buttons.button(
                tr("simulation.edit", lang),
                key="strategy_edit_secondary",
            ):
                _prepare_strategy_draft(
                    "secondary",
                    secondary_plan,
                    total_capital=total_capital,
                    requested_start=requested_start,
                )
                _strategy_editor_dialog(
                    "secondary",
                    secondary_plan,
                    all_prices,
                    options,
                    total_capital,
                    requested_start,
                    lang,
                    currency,
                )
            if secondary_buttons.button(
                tr("simulation.remove_second", lang),
                key="strategy_remove_secondary",
            ):
                st.session_state.pop(SECONDARY_PLAN_STATE_KEY, None)
                st.rerun()
        elif st.button(
            tr("simulation.add_second", lang),
            key="strategy_add_secondary",
        ):
            new_plan = PortfolioPlan(
                name=tr("simulation.second_default", lang),
                tickers=primary_plan.tickers,
                weights=primary_plan.weights,
                deployment_months=primary_plan.deployment_months,
                rebalance_annually=primary_plan.rebalance_annually,
            )
            _prepare_strategy_draft(
                "secondary",
                new_plan,
                total_capital=total_capital,
                requested_start=requested_start,
            )
            _strategy_editor_dialog(
                "secondary",
                new_plan,
                all_prices,
                options,
                total_capital,
                requested_start,
                lang,
                currency,
            )

        example_labels = _example_labels(lang)
        st.multiselect(
            tr("simulation.reference_select", lang),
            options=list(example_labels),
            default=["buy_hold"],
            max_selections=3,
            format_func=lambda key: example_labels[key],
            key=REFERENCE_SELECTION_STATE_KEY,
        )

    _render_leverage_warning(plans, dim_etf, lang)
    combined_tickers = sorted({ticker for plan in plans for ticker in plan.tickers})
    simulation_prices = (
        all_prices[combined_tickers].dropna().loc[pd.Timestamp(requested_start) :]
    )
    try:
        results = {
            plan.name: sim.portfolio_strategy(
                simulation_prices[list(plan.tickers)],
                plan.weights,
                total_capital,
                deployment_months=plan.deployment_months,
                rebalance_annually=plan.rebalance_annually,
            )
            for plan in plans
        }
    except ValueError:
        st.warning(tr("simulation.insufficient_history", lang))
        return

    start = next(iter(results.values())).value.index.min()
    end = next(iter(results.values())).value.index.max()
    selected_examples = st.session_state.get(
        REFERENCE_SELECTION_STATE_KEY,
        ["buy_hold"],
    )
    curves = {name: result.value for name, result in results.items()}
    examples_available = True
    if selected_examples:
        try:
            built = _reference_curves(
                all_prices,
                plans,
                total_capital,
                start,
                end,
            )
        except ValueError:
            built = None
        if built is None:
            examples_available = False
        else:
            reference_curves, _ = built
            curves = {
                plan.name: reference_curves[f"custom_{index}"]
                for index, plan in enumerate(plans)
            }
            labels = _example_labels(lang)
            curves.update(
                {
                    labels[key]: reference_curves[key]
                    for key in selected_examples
                    if key in labels
                }
            )

    st.subheader(tr("simulation.results", lang))
    st.caption(
        tr(
            "simulation.actual_period",
            lang,
            start=f"{start:%Y-%m-%d}",
            end=f"{end:%Y-%m-%d}",
        )
    )
    overview_tab, growth_tab, drawdown_tab, details_tab = st.tabs(
        [
            tr("strategy.tab_overview", lang),
            tr("strategy.tab_growth", lang),
            tr("strategy.tab_drawdown", lang),
            tr("strategy.tab_details", lang),
        ]
    )

    primary_metrics = _curve_metrics(curves[primary_plan.name])
    with overview_tab:
        metric_columns = st.columns(3)
        metric_columns[0].metric(
            tr("simulation.final_value", lang),
            format_money(primary_metrics["final_value"], currency),
        )
        metric_columns[1].metric(
            tr("simulation.total_return", lang),
            _percent(primary_metrics["total_return"]),
        )
        metric_columns[2].metric(
            tr("simulation.max_drawdown", lang),
            _percent(primary_metrics["max_drawdown"]),
        )
        if not examples_available:
            st.warning(tr("simulation.reference_unavailable", lang))
        st.dataframe(
            _comparison_summary_frame(curves, lang, currency),
            width="stretch",
            hide_index=True,
            row_height=DATAFRAME_ROW_HEIGHT,
        )

    with growth_tab:
        st.plotly_chart(_value_chart(curves, lang, currency), width="stretch")

    with drawdown_tab:
        st.caption(tr("strategy.drawdown_caption", lang))
        st.plotly_chart(_drawdown_chart(curves, lang), width="stretch")

    with details_tab:
        for plan in plans:
            st.markdown(_plan_summary(plan, lang))
        # One reference panel, not two. The strategy rules and the metric
        # definitions have the same audience and sat directly on top of each
        # other, which read as the page explaining itself twice.
        with st.expander(tr("strategy.rule_guide", lang)):
            notes = {
                tr("strategy.buy_hold_name", lang): tr("strategy.buy_hold_note", lang),
                tr("strategy.dca_name", lang): tr("strategy.dca_note", lang),
                tr("strategy.balanced_name", lang): tr("strategy.balanced_note", lang),
                tr("strategy.trend_name", lang): tr("strategy.trend_note", lang),
                tr("strategy.split_name", lang): tr("strategy.split_note", lang),
            }
            for name, note in notes.items():
                st.markdown(f"**{name}**  \n{note}")
            st.markdown(f"**{tr('strategy.metric_guide', lang)}**")
            glossary_items(["CAGR", "Ann. vol", "Max drawdown", "Sharpe (rf=0)"], lang)
        with st.expander(tr("simulation.assumptions_title", lang)):
            st.markdown(tr("simulation.assumptions_body", lang))


lang = current_language()
st.title(tr("strategy.title", lang))
st.caption(tr("strategy.subtitle", lang))
base_currency = st.segmented_control(
    tr("currency.base_label", lang),
    options=list(SUPPORTED_BASE_CURRENCIES),
    default="USD",
    key=BASE_CURRENCY_STATE_KEY,
    help=tr("currency.strategy_help", lang),
)
if base_currency not in SUPPORTED_BASE_CURRENCIES:
    base_currency = "USD"

try:
    base_returns_df = load_mart_returns()
except Exception as exc:
    st.error(tr("strategy.data_error", lang))
    with st.expander(tr("home.admin_details", lang)):
        st.code(str(exc))
    st.stop()

demo_mode_banner(lang)
custom_prices = session_prices(st.session_state)
returns_df = base_returns_df
returns_df, _ = merge_custom_data(returns_df, None, custom_prices)
custom_symbols = session_tickers(st.session_state)
if custom_symbols:
    st.caption(
        tr(
            "custom.strategy_notice",
            lang,
            tickers=", ".join(custom_symbols),
            currency=base_currency,
        )
    )
listing_currencies = {
    ticker: "USD" for ticker in base_returns_df["ticker"].dropna().astype(str).unique()
}
listing_currencies.update(
    {
        candidate.symbol: candidate.currency
        for candidate in session_instrument_candidates(st.session_state)
        if candidate.currency
    }
)
unknown_currencies = sorted(
    set(returns_df["ticker"].dropna().astype(str)) - set(listing_currencies)
)
if unknown_currencies:
    st.warning(
        tr(
            "currency.missing_metadata",
            lang,
            tickers=", ".join(unknown_currencies),
        )
    )
    returns_df = returns_df[~returns_df["ticker"].isin(unknown_currencies)]

try:
    required_currencies = tuple(
        sorted(set(listing_currencies.values()) | {base_currency})
    )
    usd_rates = cached_usd_exchange_rates(required_currencies)
    converted_returns = convert_prices_to_base_currency(
        returns_df,
        listing_currencies,
        base_currency,
        usd_rates,
    )
except CurrencyConversionError as exc:
    st.error(
        tr(
            "currency.conversion_error",
            lang,
            detail=str(exc),
        )
    )
    st.stop()

all_prices = converted_returns.pivot(
    index="price_date", columns="ticker", values="adj_close"
).sort_index()

try:
    dimension = load_dim_etf()
except Exception:
    dimension = pd.DataFrame()
_render_custom_simulator(all_prices, dimension, lang, base_currency)
