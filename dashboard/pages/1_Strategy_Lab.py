"""Custom portfolio simulation and five representative strategy examples."""

from __future__ import annotations

import sys
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


def _money(value: float, lang: str) -> str:
    if lang == "ko":
        return f"{value:,.0f}만원"
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"


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
        st.dataframe(
            table,
            width=dataframe_width(table),
            row_height=DATAFRAME_ROW_HEIGHT,
            hide_index=True,
        )


def _example_labels(lang: str) -> dict[str, str]:
    return {
        "buy_hold": tr("strategy.buy_hold_short", lang),
        "dca": tr("strategy.dca_short", lang),
        "balanced": tr("strategy.balanced_short", lang),
        "trend": tr("strategy.trend_short", lang),
        "split": tr("strategy.split_short", lang),
    }


def _reference_curves(
    all_prices: pd.DataFrame,
    selected: list[str],
    weights: dict[str, float],
    total_capital: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
    comparison: str,
    staged_months: int,
) -> tuple[dict[str, pd.Series], pd.DatetimeIndex] | None:
    columns = sorted(REQUIRED_EXAMPLES | set(selected))
    if set(columns) - set(all_prices.columns):
        return None
    common = all_prices.loc[start:end, columns].dropna()
    if common.empty or common.index[0] != start or common.index[-1] != end:
        return None
    if len(common) < 201:
        return None

    custom_prices = common[selected]
    if comparison == "timing":
        custom = sim.staged_portfolio(
            custom_prices,
            weights,
            total_capital,
            staged_months,
        ).value
    else:
        custom = sim.annually_rebalanced_portfolio(
            custom_prices,
            weights,
            total_capital,
        ).value

    all_months = len(common.index.to_period("M").unique())
    dca = sim.staged_portfolio(
        common[["QQQ"]],
        {"QQQ": 1.0},
        total_capital,
        all_months,
    ).value
    curves = {
        "custom": custom,
        "buy_hold": total_capital * strat.lump_sum(common["SPY"]),
        "dca": dca,
        "balanced": total_capital
        * strat.rebalance(common, {"SPY": 0.6, "BND": 0.4}, every=63),
        "trend": total_capital * strat.sma_trend(common["QQQ"], window=200),
        "split": total_capital
        * strat.infinite_buy(common["TQQQ"], n_splits=40, take_profit=0.10),
    }
    return curves, common.index


def _render_reference_comparison(
    all_prices: pd.DataFrame,
    selected: list[str],
    weights: dict[str, float],
    total_capital: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
    comparison: str,
    staged_months: int,
    lang: str,
) -> None:
    st.subheader(tr("simulation.reference_title", lang))
    st.caption(tr("simulation.reference_caption", lang))
    try:
        built = _reference_curves(
            all_prices,
            selected,
            weights,
            total_capital,
            start,
            end,
            comparison,
            staged_months,
        )
    except ValueError:
        built = None
    if built is None:
        st.warning(tr("simulation.reference_unavailable", lang))
        return

    curves, index = built
    labels = _example_labels(lang)
    custom_label = (
        tr("simulation.my_staged", lang, months=staged_months)
        if comparison == "timing"
        else tr("simulation.my_rebalanced", lang)
    )
    labels = {"custom": custom_label, **labels}

    rows = []
    for key, curve in curves.items():
        metrics = _curve_metrics(curve)
        rows.append(
            {
                tr("strategy.rule", lang): labels[key],
                tr("simulation.final_value", lang): _money(
                    metrics["final_value"], lang
                ),
                tr("simulation.max_drawdown", lang): _percent(
                    metrics["max_drawdown"]
                ),
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
    )

    selected_examples = st.multiselect(
        tr("simulation.reference_select", lang),
        options=list(_example_labels(lang)),
        default=["buy_hold"],
        max_selections=2,
        format_func=lambda key: labels[key],
        key="simulation_reference_examples",
    )
    chart_curves = {custom_label: curves["custom"]}
    chart_curves.update({labels[key]: curves[key] for key in selected_examples})
    st.plotly_chart(_value_chart(chart_curves, lang), width="stretch")


def _render_custom_simulator(
    all_prices: pd.DataFrame,
    dim_etf: pd.DataFrame,
    lang: str,
) -> None:
    st.markdown(tr("simulation.intro", lang))
    options = sorted(all_prices.columns)
    defaults = [ticker for ticker in DEFAULT_TICKERS if ticker in options]
    selected = st.multiselect(
        tr("simulation.select_etfs", lang),
        options=options,
        default=defaults,
        max_selections=5,
        key="simulation_tickers",
    )
    if not selected:
        st.info(tr("home.empty_selection", lang))
        return

    for ticker in selected:
        state_key = f"simulation_weight_{ticker}"
        if state_key not in st.session_state:
            st.session_state[state_key] = DEFAULT_WEIGHTS.get(
                ticker, 100.0 / len(selected)
            )

    if st.button(tr("simulation.equal_weights", lang), key="simulation_equal"):
        equal = round(100.0 / len(selected), 1)
        assigned = 0.0
        for ticker in selected[:-1]:
            st.session_state[f"simulation_weight_{ticker}"] = equal
            assigned += equal
        st.session_state[f"simulation_weight_{selected[-1]}"] = round(
            100.0 - assigned, 1
        )

    weight_percent: dict[str, float] = {}
    for ticker in selected:
        weight_percent[ticker] = st.number_input(
            tr("simulation.weight_label", lang, ticker=ticker),
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            format="%.1f",
            key=f"simulation_weight_{ticker}",
        )
    weight_total = sum(weight_percent.values())
    st.markdown(tr("simulation.weight_total", lang, total=weight_total))
    valid_weights = np.isclose(weight_total, 100.0, atol=1e-6) and all(
        weight > 0 for weight in weight_percent.values()
    )
    if valid_weights:
        st.caption(f"✅ {tr('simulation.weight_valid', lang)}")
    else:
        st.warning(tr("simulation.weight_invalid", lang))
        return

    if not dim_etf.empty and "leverage" in dim_etf:
        leverage = dim_etf.set_index("ticker")["leverage"]
        leveraged = [
            ticker
            for ticker in selected
            if ticker in leverage.index and float(leverage[ticker]) > 1
        ]
        if leveraged:
            st.warning(
                tr(
                    "simulation.leverage_warning",
                    lang,
                    tickers=", ".join(leveraged),
                )
            )

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

    common_prices = all_prices[selected].dropna()
    if len(common_prices) < 2:
        st.warning(tr("simulation.insufficient_history", lang))
        return
    latest = common_prices.index.max()
    desired = latest - pd.DateOffset(years=5)
    default_pos = common_prices.index.searchsorted(desired)
    default_pos = min(default_pos, len(common_prices) - 2)
    default_start = common_prices.index[default_pos].date()
    selection_key = "_".join(selected)
    requested_start = st.date_input(
        tr("simulation.start_date", lang),
        value=default_start,
        min_value=common_prices.index.min().date(),
        max_value=common_prices.index[-2].date(),
        key=f"simulation_start_{selection_key}",
    )
    simulation_prices = common_prices.loc[pd.Timestamp(requested_start) :]

    comparison = st.radio(
        tr("simulation.compare_label", lang),
        options=["timing", "rebalance"],
        format_func=lambda value: tr(f"simulation.compare_{value}", lang),
        key="simulation_comparison",
    )
    staged_months = 12
    if comparison == "timing":
        staged_months = st.selectbox(
            tr("simulation.staged_months", lang),
            options=[6, 12, 24],
            index=1,
            format_func=lambda months: tr(
                "simulation.month_option", lang, months=months
            ),
            key="simulation_staged_months",
        )

    weights = {ticker: value / 100.0 for ticker, value in weight_percent.items()}
    try:
        lump = sim.lump_sum_portfolio(simulation_prices, weights, total_capital)
        if comparison == "timing":
            alternative = sim.staged_portfolio(
                simulation_prices,
                weights,
                total_capital,
                staged_months,
            )
            labels = [
                tr("simulation.lump_name", lang),
                tr("simulation.staged_name", lang, months=staged_months),
            ]
        else:
            alternative = sim.annually_rebalanced_portfolio(
                simulation_prices,
                weights,
                total_capital,
            )
            labels = [
                tr("simulation.no_rebalance_name", lang),
                tr("simulation.annual_rebalance_name", lang),
            ]
    except ValueError:
        st.warning(tr("simulation.insufficient_history", lang))
        return

    results = {labels[0]: lump, labels[1]: alternative}
    metrics = {name: sim.result_metrics(result) for name, result in results.items()}
    start, end = lump.value.index.min(), lump.value.index.max()

    st.subheader(tr("simulation.results", lang))
    st.markdown(
        tr(
            "simulation.actual_period",
            lang,
            start=f"{start:%Y-%m-%d}",
            end=f"{end:%Y-%m-%d}",
        )
    )
    _comparison_summary(labels, metrics, lang)

    st.markdown(f"#### {tr('simulation.value_chart', lang)}")
    st.plotly_chart(
        _value_chart({name: result.value for name, result in results.items()}, lang),
        width="stretch",
    )

    _render_result_tables(labels, metrics, lang)

    if st.checkbox(
        tr("simulation.reference_toggle", lang),
        key="simulation_show_references",
    ):
        _render_reference_comparison(
            all_prices,
            selected,
            weights,
            total_capital,
            start,
            end,
            comparison,
            staged_months,
            lang,
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
            label: st.column_config.TextColumn(label, help=glossary_help(key, lang))
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
