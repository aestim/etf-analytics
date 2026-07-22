"""
Streamlit dashboard home page — reads mart tables from PostgreSQL.
Run after: docker compose up, ingest, dbt run.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from chart_colors import ticker_color_map
from db import (
    PLOTLY_LAYOUT,
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
    tr,
    ui_controls,
)


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
            "adj_close": "Adjusted price",
            "cum_return": "Return",
            "rolling_vol_30d": "Volatility",
            "ticker": "ETF ticker",
        }
        if lang == "en"
        else {
            "price_date": "날짜",
            "adj_close": "조정 가격",
            "cum_return": "수익률",
            "rolling_vol_30d": "변동성",
            "ticker": "ETF 티커",
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
    fig.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig, width="stretch")


lang = ui_controls()

st.title("ETF Analytics")
st.caption(tr("home.subtitle", lang))

with st.expander(tr("home.intro_title", lang), expanded=True):
    st.markdown(tr("home.intro_body", lang))

with st.expander(tr("home.technical_title", lang)):
    st.caption(tr("home.technical_body", lang))

nav_col1, nav_col2 = st.columns(2)
with nav_col1:
    st.page_link("pages/1_Strategy_Lab.py", label=tr("home.nav_strategy", lang))
with nav_col2:
    st.page_link("pages/2_Ask.py", label=tr("home.nav_ask", lang))

try:
    returns_df = load_mart_returns()
    risk_df = load_mart_risk()
except Exception as exc:
    st.error(tr("home.data_error", lang))
    with st.expander(tr("home.admin_details", lang)):
        st.code(str(exc))
    st.stop()

demo_mode_banner(lang)

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
            width="stretch",
            hide_index=True,
            column_config={
                "ticker": st.column_config.TextColumn(tr("home.ticker", lang)),
                "name": st.column_config.TextColumn(tr("home.fund_name", lang)),
                "asset_class": st.column_config.TextColumn(
                    tr("home.asset_class", lang),
                    help=tr("home.asset_class_help", lang),
                ),
                "sub_class": st.column_config.TextColumn(
                    tr("home.sub_class", lang),
                    help=tr("home.sub_class_help", lang),
                ),
                "leverage": st.column_config.NumberColumn(
                    tr("home.leverage", lang),
                    help=tr("home.leverage_help", lang),
                ),
            },
        )
        pick = st.selectbox(tr("home.detail_select", lang), dim["ticker"])
        row = dim.set_index("ticker").loc[pick]
        lev = (
            (
                f" · 일간 {int(row['leverage'])}배"
                if lang == "ko"
                else f" · {int(row['leverage'])}x daily"
            )
            if row["leverage"] > 1
            else ""
        )
        asset_class = (
            ASSET_LABELS_KO.get(row["asset_class"], row["asset_class"])
            if lang == "ko"
            else row["asset_class"]
        )
        sub_class = (
            SUBCLASS_LABELS_KO.get(row["sub_class"], row["sub_class"])
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
            f"`{asset_class} / {sub_class}`{lev}\n\n{description}"
        )
    except Exception:
        st.caption(tr("home.dim_missing", lang))

tickers = sorted(returns_df["ticker"].unique())
COLORS = ticker_color_map(tickers)  # stable palette across all charts
beginner_defaults = [ticker for ticker in ("SPY", "BND", "GLD") if ticker in tickers]
selected = st.multiselect(
    tr("home.select_etfs", lang), tickers, default=beginner_defaults
)
if not selected:
    st.info(tr("home.empty_selection", lang))
filtered = returns_df[returns_df["ticker"].isin(selected)]
risk_filtered = risk_df[risk_df["ticker"].isin(selected)]

col1, col2 = st.columns(2)

with col1:
    st.subheader(tr("home.adjusted_price", lang))
    st.caption(tr("home.adjusted_price_caption", lang))
    line_chart(filtered, "adj_close", lang, COLORS)

with col2:
    st.subheader(tr("home.cumulative_return", lang))
    st.caption(tr("home.cumulative_return_caption", lang))
    cum = filtered.copy()
    cum["cum_return"] = cum.groupby("ticker")["daily_return"].transform(
        lambda s: (1 + s.fillna(0)).cumprod() - 1
    )
    line_chart(cum, "cum_return", lang, COLORS)

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
    width="stretch",
    hide_index=True,
    column_config={
        "rolling_vol_30d": st.column_config.NumberColumn(
            tr("home.volatility", lang),
            help=glossary_help("rolling_vol_30d", lang),
            format="percent",
        ),
        "drawdown": st.column_config.NumberColumn(
            tr("home.drawdown", lang),
            help=glossary_help("drawdown", lang),
            format="percent",
        ),
        "ticker": st.column_config.TextColumn(tr("home.ticker", lang)),
        "price_date": st.column_config.TextColumn(tr("home.as_of_date", lang)),
    },
)

glossary_expander(
    ["adj_close", "cum_return", "rolling_vol_30d", "drawdown"],
    lang,
    title=tr("home.metrics_guide", lang),
)
