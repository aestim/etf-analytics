"""Custom portfolio simulation and five representative strategy examples."""

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
from db import (  # noqa: E402
    DATAFRAME_ROW_HEIGHT,
    PLOTLY_LAYOUT,
    dataframe_width,
    demo_mode_banner,
    glossary_expander,
    glossary_help,
    load_dim_etf,
    load_mart_returns,
)
from i18n import current_language, tr  # noqa: E402

REQUIRED_EXAMPLES = {"SPY", "QQQ", "BND", "TQQQ"}
DEFAULT_TICKERS = ["SPY", "BND", "GLD"]
DEFAULT_WEIGHTS = {"SPY": 60.0, "BND": 30.0, "GLD": 10.0}


@dataclass(frozen=True)
class PortfolioPlan:
    """One user-configured portfolio and its execution rules."""

    name: str
    tickers: tuple[str, ...]
    weights: dict[str, float]
    deployment_months: int
    rebalance_annually: bool


def _money(value: float, lang: str) -> str:
    if lang == "ko":
        return f"{value:,.0f}만원"
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"


def _compact_money(value: float, lang: str) -> str:
    """Keep large reference-table values readable without hiding magnitude."""

    magnitude = abs(value)
    if lang == "ko":
        if magnitude >= 100_000_000:
            return f"{value / 100_000_000:,.2f}조원"
        if magnitude >= 10_000:
            return f"{value / 10_000:,.2f}억원"
        return f"{value:,.0f}만원"
    if magnitude >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:,.2f}T"
    if magnitude >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}B"
    if magnitude >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    return _money(value, lang)


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
        "annualized_vol": strat.annualized_vol(clean),
    }


def _value_chart(curves: dict[str, pd.Series], lang: str):
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
    if lang == "ko":
        fig.update_yaxes(title_text="", tickformat=",.0f", ticksuffix="만원")
    else:
        fig.update_yaxes(title_text="", tickformat="$,.0f")
    return fig


def _comparison_summary(
    labels: list[str],
    metrics: dict[str, dict[str, float]],
    lang: str,
) -> None:
    first, second = labels
    first_final = metrics[first]["final_value"]
    second_final = metrics[second]["final_value"]
    difference = abs(first_final - second_final)
    if np.isclose(first_final, second_final, rtol=1e-4):
        st.info(tr("simulation.summary_equal", lang))
    else:
        higher, lower = (
            (first, second) if first_final > second_final else (second, first)
        )
        st.info(
            tr(
                "simulation.summary_higher",
                lang,
                higher=higher,
                lower=lower,
                amount=_money(difference, lang),
            )
        )

    smaller_drop = min(
        labels,
        key=lambda name: abs(metrics[name]["max_drawdown"]),
    )
    st.caption(
        tr(
            "simulation.summary_drop",
            lang,
            name=smaller_drop,
            drawdown=_percent(metrics[smaller_drop]["max_drawdown"]),
        )
    )


def _result_table(
    label: str,
    metrics: dict[str, dict[str, float]],
    lang: str,
) -> pd.DataFrame:
    rows = [
        (tr("simulation.final_value", lang), "final_value", _money),
        (tr("simulation.profit", lang), "profit", _money),
        (tr("simulation.total_return", lang), "total_return", _percent),
        (tr("simulation.max_drawdown", lang), "max_drawdown", _percent),
    ]
    values = []
    for _, key, formatter in rows:
        value = metrics[label][key]
        values.append(
            formatter(value, lang) if formatter is _money else formatter(value)
        )
    return pd.DataFrame(
        {
            tr("simulation.metric", lang): [row[0] for row in rows],
            tr("simulation.value", lang): values,
        }
    )


def _render_result_tables(
    labels: list[str],
    metrics: dict[str, dict[str, float]],
    lang: str,
) -> None:
    for label in labels:
        st.markdown(f"**{label}**")
        table = _result_table(label, metrics, lang)
        metric_column = tr("simulation.metric", lang)
        value_column = tr("simulation.value", lang)
        table_key = (
            f"simulation_result_{lang}_{label}_"
            f"{metrics[label]['final_value']:.6f}_"
            f"{metrics[label]['max_drawdown']:.6f}"
        )
        st.dataframe(
            table,
            width=dataframe_width(table),
            row_height=DATAFRAME_ROW_HEIGHT,
            hide_index=True,
            key=table_key,
            column_config={
                metric_column: st.column_config.TextColumn(
                    metric_column, width=145, alignment="left"
                ),
                value_column: st.column_config.TextColumn(
                    value_column, width=195, alignment="right"
                ),
            },
        )


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
    selected = st.multiselect(
        tr("simulation.select_etfs", lang),
        options=options,
        default=defaults,
        max_selections=5,
        key=f"{prefix}_tickers",
    )
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
        st.session_state[f"{prefix}_weight_{selected[-1]}"] = round(
            100.0 - assigned, 1
        )

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
        ticker: percentage / 100.0
        for ticker, percentage in percentages.items()
    }


def _plan_inputs(prefix: str, lang: str, ticker_count: int) -> tuple[int, bool]:
    method = st.segmented_control(
        tr("simulation.plan_method", lang),
        options=["lump", "staged"],
        default="lump",
        required=True,
        format_func=lambda value: tr(f"simulation.plan_{value}", lang),
        key=f"{prefix}_method",
    )
    months = 1
    if method == "staged":
        months = st.selectbox(
            tr("simulation.staged_months", lang),
            options=[6, 12, 24],
            index=1,
            format_func=lambda value: tr(
                "simulation.month_option", lang, months=value
            ),
            key=f"{prefix}_months",
        )
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


def _plan_summary(plan: PortfolioPlan, lang: str) -> str:
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
    return tr(
        "simulation.plan_summary",
        lang,
        name=plan.name,
        entry=entry,
        rebalance=rebalance,
    )


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
            "trend": total_capital
            * strat.sma_trend(common["QQQ"], window=200),
            "split": total_capital
            * strat.infinite_buy(common["TQQQ"], n_splits=40, take_profit=0.10),
        }
    )
    return curves, common.index


def _render_reference_comparison(
    all_prices: pd.DataFrame,
    plans: list[PortfolioPlan],
    total_capital: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
    lang: str,
) -> None:
    st.subheader(tr("simulation.reference_title", lang))
    st.caption(tr("simulation.reference_caption", lang))
    try:
        built = _reference_curves(
            all_prices, plans, total_capital, start, end
        )
    except ValueError:
        built = None
    if built is None:
        st.warning(tr("simulation.reference_unavailable", lang))
        return

    curves, index = built
    labels = {
        **{f"custom_{i}": plan.name for i, plan in enumerate(plans)},
        **_example_labels(lang),
    }
    rule_column = tr("strategy.rule", lang)
    final_value_column = tr("simulation.final_value", lang)
    drawdown_column = tr("simulation.drop_short", lang)
    rows = []
    for key, curve in curves.items():
        metrics = _curve_metrics(curve)
        rows.append(
            {
                rule_column: labels[key],
                final_value_column: _compact_money(metrics["final_value"], lang),
                drawdown_column: _percent(metrics["max_drawdown"]),
            }
        )
    reference_table = pd.DataFrame(rows)
    st.caption(
        tr(
            "simulation.actual_period",
            lang,
            start=f"{index.min():%Y-%m-%d}",
            end=f"{index.max():%Y-%m-%d}",
        )
    )
    st.dataframe(
        reference_table,
        width=dataframe_width(reference_table),
        row_height=DATAFRAME_ROW_HEIGHT,
        hide_index=True,
        key=(
            f"simulation_reference_table_{lang}_{total_capital:g}_"
            f"{start:%Y%m%d}_{end:%Y%m%d}_{len(plans)}"
        ),
        column_config={
            rule_column: st.column_config.TextColumn(
                rule_column, width=170, alignment="left"
            ),
            final_value_column: st.column_config.TextColumn(
                final_value_column, width=100, alignment="right"
            ),
            drawdown_column: st.column_config.TextColumn(
                drawdown_column, width=85, alignment="right"
            ),
        },
    )

    example_labels = _example_labels(lang)
    selected_examples = st.multiselect(
        tr("simulation.reference_select", lang),
        options=list(example_labels),
        default=["buy_hold"],
        max_selections=3,
        format_func=lambda key: labels[key],
        key=f"simulation_reference_examples_{lang}",
    )
    chart_curves = {
        plan.name: curves[f"custom_{index}"]
        for index, plan in enumerate(plans)
    }
    chart_curves.update({labels[key]: curves[key] for key in selected_examples})
    st.plotly_chart(_value_chart(chart_curves, lang), width="stretch")


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
) -> None:
    st.markdown(tr("simulation.intro", lang))
    options = sorted(all_prices.columns)
    defaults = [ticker for ticker in DEFAULT_TICKERS if ticker in options]

    st.subheader(tr("simulation.primary_title", lang))
    primary_allocation = _allocation_inputs(
        options, lang, "simulation", defaults, DEFAULT_WEIGHTS
    )
    if primary_allocation is None:
        return
    primary_tickers, primary_weights = primary_allocation

    unit = "만원" if lang == "ko" else "USD"
    amount_default = 1_000.0 if lang == "ko" else 10_000.0
    amount_step = 100.0 if lang == "ko" else 1_000.0
    total_capital = st.number_input(
        tr("simulation.total_amount", lang, unit=unit),
        min_value=amount_step,
        value=amount_default,
        step=amount_step,
        help=tr("simulation.amount_help", lang),
        key=f"simulation_total_{lang}",
    )

    primary_prices = all_prices[primary_tickers].dropna()
    if len(primary_prices) < 2:
        st.warning(tr("simulation.insufficient_history", lang))
        return
    latest = primary_prices.index.max()
    desired = latest - pd.DateOffset(years=5)
    default_pos = min(
        primary_prices.index.searchsorted(desired), len(primary_prices) - 2
    )
    requested_start = st.date_input(
        tr("simulation.start_date", lang),
        value=primary_prices.index[default_pos].date(),
        min_value=primary_prices.index.min().date(),
        max_value=primary_prices.index[-2].date(),
        key=f"simulation_start_{'_'.join(primary_tickers)}",
    )

    st.markdown(f"#### {tr('simulation.plan_title', lang)}")
    primary_months, primary_rebalance = _plan_inputs(
        "simulation", lang, len(primary_tickers)
    )
    plans = [
        PortfolioPlan(
            name=tr("simulation.my_strategy", lang),
            tickers=tuple(primary_tickers),
            weights=primary_weights,
            deployment_months=primary_months,
            rebalance_annually=primary_rebalance,
        )
    ]

    if not st.session_state.get("simulation_second_enabled", False):
        if st.button(
            tr("simulation.add_second", lang), key="simulation_add_second"
        ):
            st.session_state["simulation_second_enabled"] = True
            st.rerun()
    else:
        st.divider()
        st.subheader(tr("simulation.second_title", lang))
        st.caption(tr("simulation.second_caption", lang))
        second_name = st.text_input(
            tr("simulation.second_name", lang),
            value=tr("simulation.second_default", lang),
            max_chars=30,
            key="simulation_second_name",
        ).strip() or tr("simulation.second_default", lang)
        if second_name == plans[0].name:
            st.warning(tr("simulation.second_name_duplicate", lang))
            return
        second_allocation = _allocation_inputs(
            options,
            lang,
            "simulation_second",
            primary_tickers,
            {ticker: weight * 100 for ticker, weight in primary_weights.items()},
        )
        if second_allocation is None:
            return
        second_tickers, second_weights = second_allocation
        second_months, second_rebalance = _plan_inputs(
            "simulation_second", lang, len(second_tickers)
        )
        plans.append(
            PortfolioPlan(
                name=second_name,
                tickers=tuple(second_tickers),
                weights=second_weights,
                deployment_months=second_months,
                rebalance_annually=second_rebalance,
            )
        )
        if st.button(
            tr("simulation.remove_second", lang),
            key="simulation_remove_second",
        ):
            st.session_state["simulation_second_enabled"] = False
            st.rerun()

    _render_leverage_warning(plans, dim_etf, lang)
    combined_tickers = sorted(
        {ticker for plan in plans for ticker in plan.tickers}
    )
    simulation_prices = all_prices[combined_tickers].dropna().loc[
        pd.Timestamp(requested_start) :
    ]
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

    labels = list(results)
    metrics = {
        name: sim.result_metrics(result) for name, result in results.items()
    }
    start = next(iter(results.values())).value.index.min()
    end = next(iter(results.values())).value.index.max()

    st.subheader(tr("simulation.results", lang))
    st.markdown(
        tr(
            "simulation.actual_period",
            lang,
            start=f"{start:%Y-%m-%d}",
            end=f"{end:%Y-%m-%d}",
        )
    )
    for plan in plans:
        st.caption(_plan_summary(plan, lang))
    if len(labels) == 2:
        _comparison_summary(labels, metrics, lang)
    _render_result_tables(labels, metrics, lang)

    _render_reference_comparison(
        all_prices, plans, total_capital, start, end, lang
    )

    with st.expander(tr("simulation.assumptions_title", lang)):
        st.markdown(tr("simulation.assumptions_body", lang))


def _render_example_strategies(prices: pd.DataFrame, lang: str) -> None:
    with st.expander(tr("strategy.guide_title", lang), expanded=True):
        st.markdown(tr("strategy.guide_body", lang))

    missing = REQUIRED_EXAMPLES - set(prices.columns)
    if missing:
        st.warning(tr("strategy.missing", lang, tickers=", ".join(sorted(missing))))
        return
    common = prices[sorted(REQUIRED_EXAMPLES)].dropna()

    notes = {
        tr("strategy.buy_hold_name", lang): tr("strategy.buy_hold_note", lang),
        tr("strategy.dca_name", lang): tr("strategy.dca_note", lang),
        tr("strategy.balanced_name", lang): tr("strategy.balanced_note", lang),
        tr("strategy.trend_name", lang): tr("strategy.trend_note", lang),
        tr("strategy.split_name", lang): tr("strategy.split_note", lang),
    }
    equity_curves = {
        tr("strategy.buy_hold_name", lang): strat.lump_sum(common["SPY"]),
        tr("strategy.dca_name", lang): strat.dca(common["QQQ"], every=21),
        tr("strategy.balanced_name", lang): strat.rebalance(
            common, {"SPY": 0.6, "BND": 0.4}, every=63
        ),
        tr("strategy.trend_name", lang): strat.sma_trend(
            common["QQQ"], window=200
        ),
        tr("strategy.split_name", lang): strat.infinite_buy(
            common["TQQQ"], n_splits=40, take_profit=0.10
        ),
    }
    curves = pd.DataFrame(equity_curves)
    curves.index.name = "price_date"
    chart_labels = {
        tr("strategy.buy_hold_name", lang): tr("strategy.buy_hold_short", lang),
        tr("strategy.dca_name", lang): tr("strategy.dca_short", lang),
        tr("strategy.balanced_name", lang): tr("strategy.balanced_short", lang),
        tr("strategy.trend_name", lang): tr("strategy.trend_short", lang),
        tr("strategy.split_name", lang): tr("strategy.split_short", lang),
    }
    chart_curves = curves.rename(columns=chart_labels)

    log_scale = st.checkbox(
        tr("strategy.log_scale", lang),
        value=True,
        help=tr("strategy.log_help", lang),
    )
    st.subheader(tr("strategy.growth_title", lang))
    st.caption(f"{curves.index.min():%Y-%m-%d} → {curves.index.max():%Y-%m-%d}")
    fig = px.line(
        chart_curves.reset_index().melt(
            id_vars="price_date", var_name="strategy", value_name="equity"
        ),
        x="price_date",
        y="equity",
        color="strategy",
        line_dash="strategy",
        log_y=log_scale,
        labels={
            "price_date": tr("strategy.date", lang),
            "equity": tr("strategy.capital", lang),
            "strategy": tr("strategy.rule", lang),
        },
    )
    fig.update_layout(**PLOTLY_LAYOUT, title_text="", legend_title_text="")
    fig.update_xaxes(title_text="")
    st.plotly_chart(fig, width="stretch")

    st.subheader(tr("strategy.drawdown_title", lang))
    st.caption(tr("strategy.drawdown_caption", lang))
    drawdown = chart_curves.div(chart_curves.cummax()) - 1.0
    fig_dd = px.line(
        drawdown.reset_index().melt(
            id_vars="price_date", var_name="strategy", value_name="drawdown"
        ),
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
    fig_dd.update_layout(**PLOTLY_LAYOUT, title_text="", legend_title_text="")
    fig_dd.update_xaxes(title_text="")
    fig_dd.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_dd, width="stretch")

    st.subheader(tr("strategy.metrics", lang))
    metrics = pd.DataFrame(
        {name: strat.summary_metrics(eq) for name, eq in equity_curves.items()}
    ).T.rename(
        columns={
            "cagr": "CAGR",
            "ann_vol": "Ann. vol",
            "max_drawdown": "Max drawdown",
            "sharpe": "Sharpe (rf=0)",
        }
    )
    display = metrics.copy()
    for column in ("CAGR", "Ann. vol", "Max drawdown"):
        display[column] = display[column].map("{:.2%}".format)
    display["Sharpe (rf=0)"] = display["Sharpe (rf=0)"].map("{:.2f}".format)
    metric_labels = {
        "CAGR": tr("strategy.cagr", lang),
        "Ann. vol": tr("strategy.ann_vol", lang),
        "Max drawdown": tr("strategy.max_drawdown", lang),
        "Sharpe (rf=0)": tr("strategy.sharpe", lang),
    }
    display = display.rename(columns=metric_labels)
    st.dataframe(
        display,
        width=dataframe_width(display),
        row_height=DATAFRAME_ROW_HEIGHT,
        column_config={
            label: st.column_config.TextColumn(
                label,
                help=glossary_help(key, lang),
                alignment="right",
            )
            for key, label in metric_labels.items()
        },
    )

    with st.expander(tr("strategy.rule_guide", lang)):
        for name, note in notes.items():
            st.markdown(f"**{name}**  \n{note}")
    glossary_expander(
        ["CAGR", "Ann. vol", "Max drawdown", "Sharpe (rf=0)"],
        lang,
        title=tr("strategy.metric_guide", lang),
    )
    st.caption(tr("strategy.footer", lang))


lang = current_language()
st.title(tr("strategy.title", lang))
st.caption(tr("strategy.subtitle", lang))

try:
    returns_df = load_mart_returns()
except Exception as exc:
    st.error(tr("strategy.data_error", lang))
    with st.expander(tr("home.admin_details", lang)):
        st.code(str(exc))
    st.stop()

demo_mode_banner(lang)
all_prices = returns_df.pivot(
    index="price_date", columns="ticker", values="adj_close"
).sort_index()

mode = st.segmented_control(
    tr("strategy.mode_label", lang),
    options=["custom", "examples"],
    default="custom",
    required=True,
    format_func=lambda value: tr(f"strategy.mode_{value}", lang),
    key="strategy_view_mode",
    persist_state="session",
    width="stretch",
)

if mode == "examples":
    _render_example_strategies(all_prices, lang)
else:
    try:
        dimension = load_dim_etf()
    except Exception:
        dimension = pd.DataFrame()
    _render_custom_simulator(all_prices, dimension, lang)
