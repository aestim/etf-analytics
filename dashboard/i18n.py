"""Shared interface copy and controls for the multipage Streamlit app."""

from __future__ import annotations

from typing import Literal

import streamlit as st

Language = Literal["en", "ko"]
DEFAULT_LANGUAGE: Language = "en"
LANGUAGE_OPTIONS = {"English": "en", "한국어": "ko"}


COPY: dict[str, dict[Language, str]] = {
    "home.subtitle": {
        "en": "Compare historical prices, returns, and risk across 17 ETFs.",
        "ko": "17개 ETF의 과거 가격과 수익률, 위험을 한눈에 비교합니다.",
    },
    "home.intro_title": {
        "en": "👋 New to ETFs? Start here",
        "ko": "👋 ETF가 처음이라면 여기부터",
    },
    "home.intro_body": {
        "en": """
        An **ETF** is a fund that holds a basket of investments, such as stocks or bonds.

        A **ticker** is its short market code. For example: `SPY` = large US companies,
        `BND` = US bonds and `GLD` = gold.

        1. Choose the ETFs you want to compare. The dashboard starts with `SPY`, `BND` and `GLD`.
        2. **Dividend-adjusted price** includes dividends and stock splits.
        3. **Total return** shows how much a starting value of `1` gained or lost.
        4. **30-day price swings** show how sharply daily returns moved up and down.

        ⚠️ For education only. Past results do not predict future performance, and this app does not recommend buying or selling.
        """,
        "ko": """
        **ETF**는 여러 주식이나 채권을 한 바구니에 담은 상품입니다.

        **티커**(ticker)는 그 상품의 짧은 이름입니다. 예: `SPY`=미국 대형주,
        `BND`=미국 채권, `GLD`=금.

        1. 비교할 ETF를 고릅니다. 처음에는 `SPY`·`BND`·`GLD`를 보여줍니다.
        2. **배당 반영 가격**은 배당과 주식 분할을 반영한 비교용 가격입니다.
        3. **누적수익률**은 시작할 때 `1`을 투자했다면 얼마나 늘거나 줄었는지 보여줍니다.
        4. **최근 30일 가격 변동**은 일간 수익률이 얼마나 크게 오르내렸는지 보여줍니다.

        ⚠️ 학습용 도구입니다. 과거 성과가 미래 수익을 보장하지 않으며, 매수·매도를 권하지 않습니다.
        """,
    },
    "home.technical_title": {
        "en": "⚙️ Technical data source",
        "ko": "⚙️ 기술 정보",
    },
    "home.technical_body": {
        "en": "Cross-asset universe set via `ETF_TICKERS` · data from `public_marts` when configured · bundled parquet fallback otherwise",
        "ko": "`ETF_TICKERS`로 비교 대상을 설정합니다 · 연결되면 `public_marts` 사용 · 연결되지 않으면 포함된 parquet 예시 데이터 사용",
    },
    "home.nav_strategy": {
        "en": "🧪 Compare investment strategies",
        "ko": "🧪 투자 방법 비교하기",
    },
    "home.nav_ask": {
        "en": "💬 Ask a question about ETFs",
        "ko": "💬 ETF 정보 물어보기",
    },
    "home.data_error": {
        "en": "No data is available from PostgreSQL or the bundled parquet snapshot. Start Docker, run ingest and `dbt run`, or add a reviewed parquet snapshot.",
        "ko": "PostgreSQL과 포함된 parquet 예시 데이터에서 자료를 읽지 못했습니다. Docker를 시작하고 ingest와 `dbt run`을 실행하거나 검토된 parquet 스냅샷을 추가하세요.",
    },
    "home.admin_details": {"en": "Technical details", "ko": "관리자용 상세 정보"},
    "home.ticker_guide": {"en": "📖 ETF guide", "ko": "📖 ETF 알아보기"},
    "home.ticker": {"en": "Ticker", "ko": "티커"},
    "home.fund_name": {"en": "ETF name", "ko": "ETF 이름"},
    "home.asset_class": {"en": "Asset type", "ko": "자산 유형"},
    "home.asset_class_help": {
        "en": "A broad group such as equity, bonds, gold or real estate.",
        "ko": "주식·채권·금·부동산 같은 큰 분류입니다.",
    },
    "home.sub_class": {"en": "Category", "ko": "세부 유형"},
    "home.sub_class_help": {
        "en": "A more specific category within the broad asset class.",
        "ko": "같은 자산 안에서 나누는 더 자세한 분류입니다.",
    },
    "home.leverage": {"en": "Daily leverage", "ko": "레버리지 배수"},
    "home.leverage_help": {
        "en": "1 means unleveraged. 2 and 3 target two or three times the daily move.",
        "ko": "1은 일반 ETF, 2·3은 일간 변동을 두 배·세 배로 추종하는 ETF입니다.",
    },
    "home.detail_select": {
        "en": "Choose an ETF to learn more",
        "ko": "자세히 알아볼 ETF",
    },
    "home.dim_missing": {
        "en": "Run `dbt seed && dbt run` to build the ETF reference table.",
        "ko": "ETF 설명 표를 만들려면 `dbt seed && dbt run`을 실행하세요.",
    },
    "home.select_etfs": {
        "en": "Choose ETFs to compare",
        "ko": "비교할 ETF 선택",
    },
    "home.empty_selection": {
        "en": "Select at least one ETF to display the charts.",
        "ko": "차트를 보려면 ETF를 하나 이상 골라주세요.",
    },
    "home.adjusted_price": {
        "en": "Dividend-adjusted price",
        "ko": "배당 반영 가격",
    },
    "home.adjusted_price_caption": {
        "en": "Historical price adjusted for dividends and stock splits",
        "ko": "배당과 주식 분할을 반영한 과거 가격입니다",
    },
    "home.cumulative_return": {"en": "Total return", "ko": "누적수익률"},
    "home.cumulative_return_caption": {
        "en": "How much a starting value of 1 would have gained or lost",
        "ko": "시작할 때 1을 투자했다면 얼마나 늘거나 줄었는지 보여줍니다",
    },
    "home.volatility": {
        "en": "30-day price swings",
        "ko": "최근 30일 가격 변동",
    },
    "home.volatility_caption": {
        "en": "Higher values mean the ETF moved more sharply over the past 30 trading days",
        "ko": "값이 클수록 최근 30거래일 동안 가격이 더 크게 오르내렸습니다",
    },
    "home.latest": {"en": "Latest risk snapshot", "ko": "최근 위험 지표"},
    "home.as_of_date": {"en": "Data through", "ko": "기준일"},
    "home.drawdown": {
        "en": "Drop from previous high",
        "ko": "고점 대비 하락률",
    },
    "home.metrics_guide": {"en": "📖 Metrics guide", "ko": "📖 용어 설명"},
    "strategy.title": {
        "en": "🧪 Compare Investment Strategies",
        "ko": "🧪 투자 방법 비교",
    },
    "strategy.subtitle": {
        "en": "See how five example strategies performed over the same historical period. Results exclude fees, taxes, and differences between expected and actual trade prices. Uninvested cash earns no interest. **For education only. Past results do not predict future performance.**",
        "ko": "같은 과거 기간에 다섯 가지 투자 방법의 성과를 비교합니다. 수수료·세금·주문 가격과 실제 체결 가격의 차이는 반영하지 않고, 투자하지 않은 현금에는 이자가 붙지 않는다고 가정합니다. **학습용 비교이며 과거 성과가 미래 수익을 보장하지 않습니다.**",
    },
    "strategy.guide_title": {
        "en": "👋 How to read the results",
        "ko": "👋 결과는 이렇게 읽어보세요",
    },
    "strategy.guide_body": {
        "en": """
        1. **Portfolio growth** starts every line at `1`. A final value of `2` means the portfolio doubled.
        2. **Drop from a previous high** shows how far each strategy fell below its earlier peak. A deeper drop means a larger loss along the way.
        3. **Results summary** should be read together: check price swings and the largest drop, not just returns.

        The strategy with the highest past return is not automatically the safest or the best choice for the future.
        """,
        "ko": """
        1. **투자 성과 추이**에서 모든 선은 시작 금액을 `1`로 맞춥니다. 마지막 값이 `2`면 두 배가 된 것입니다.
        2. **고점 대비 하락률**은 이전 최고점에서 얼마나 떨어졌는지 보여줍니다. 아래로 깊을수록 투자 중 겪은 손실 폭이 컸습니다.
        3. **성과 요약**에서는 수익률뿐 아니라 가격 흔들림과 가장 큰 하락 폭도 함께 봅니다.

        과거 수익이 가장 높았던 방법이 가장 안전하거나 앞으로도 가장 좋다는 뜻은 아닙니다.
        """,
    },
    "strategy.data_error": {
        "en": "No data is available from PostgreSQL or parquet.",
        "ko": "PostgreSQL 또는 parquet에서 데이터를 읽지 못했습니다.",
    },
    "strategy.missing": {
        "en": "The required ETF data is missing: {tickers}. Add the tickers to `ETF_TICKERS`, rerun ingest and dbt, then refresh.",
        "ko": "비교에 필요한 ETF 데이터가 없습니다: {tickers}. `ETF_TICKERS`에 추가하고 ingest와 dbt를 다시 실행한 뒤 새로고침하세요.",
    },
    "strategy.buy_hold_name": {
        "en": "Buy once and hold (SPY)",
        "ko": "한 번에 사고 계속 보유 (SPY)",
    },
    "strategy.buy_hold_short": {
        "en": "Buy & hold · SPY",
        "ko": "매수·보유 · SPY",
    },
    "strategy.buy_hold_note": {
        "en": "Invest everything on the first day and keep holding. This is the benchmark for the other rules.",
        "ko": "첫날 전액을 사고 계속 보유합니다. 다른 규칙과 비교하는 기준선입니다.",
    },
    "strategy.dca_name": {
        "en": "Monthly investing (QQQ)",
        "ko": "매달 나눠 투자 (QQQ)",
    },
    "strategy.dca_short": {
        "en": "Monthly · QQQ",
        "ko": "월 적립 · QQQ",
    },
    "strategy.dca_note": {
        "en": "Invest the same amount about every 21 trading days. It spreads entry timing, but cash waiting on the sidelines can lag a steadily rising market.",
        "ko": "약 21거래일마다 같은 금액을 투자합니다. 매수 시점을 나누지만 계속 오르는 시장에서는 기다리는 현금 때문에 한 번에 산 경우보다 뒤처질 수 있습니다.",
    },
    "strategy.balanced_name": {
        "en": "60% stocks / 40% bonds (SPY/BND)",
        "ko": "주식 60%·채권 40% (SPY/BND)",
    },
    "strategy.balanced_short": {
        "en": "60/40 · SPY/BND",
        "ko": "60/40 · SPY/BND",
    },
    "strategy.balanced_note": {
        "en": "Reset the portfolio to 60/40 each quarter. Sell some of the asset that rose and add to the asset that lagged to reduce swings.",
        "ko": "분기마다 비중을 60 대 40으로 되돌립니다. 많이 오른 쪽을 줄이고 덜 오른 쪽을 늘려 흔들림을 낮추려는 규칙입니다.",
    },
    "strategy.trend_name": {
        "en": "Follow the 200-day trend (QQQ/cash)",
        "ko": "200일 추세 따라가기 (QQQ/현금)",
    },
    "strategy.trend_short": {
        "en": "200-day trend · QQQ",
        "ko": "200일 추세 · QQQ",
    },
    "strategy.trend_note": {
        "en": "Hold QQQ above its 200-day average and otherwise hold cash. It may avoid long declines but can lose repeatedly when direction changes often. Signals act the next day.",
        "ko": "QQQ 가격이 200일 평균보다 높으면 보유하고 낮으면 현금으로 둡니다. 긴 하락을 피하려 하지만 방향이 자주 바뀌면 반복 손실이 날 수 있습니다. 신호는 다음 날 반영합니다.",
    },
    "strategy.split_name": {
        "en": "Buy in stages, sell after a 10% gain (TQQQ)",
        "ko": "나눠 사고 10% 오르면 매도 (TQQQ)",
    },
    "strategy.split_short": {
        "en": "Split buys · TQQQ",
        "ko": "분할매수 · TQQQ",
    },
    "strategy.split_note": {
        "en": "Split capital into 40 daily buys and sell all at 10% above average cost. Each cycle's gain is capped, while crash risk remains after cash runs out.",
        "ko": "돈을 40번으로 나눠 매일 사고 평균 매수가보다 10% 오르면 전부 팝니다. 한 번의 상승 이익은 제한되지만 현금을 다 쓴 뒤의 큰 하락 위험은 남습니다.",
    },
    "strategy.log_scale": {
        "en": "Make large differences easier to compare (log scale)",
        "ko": "차이가 큰 결과 함께 보기 (로그 눈금)",
    },
    "strategy.log_help": {
        "en": "Makes lower lines easier to see when results differ greatly. It does not change the underlying values.",
        "ko": "수익 차이가 매우 클 때 낮은 선도 잘 보이게 합니다. 실제 결과값은 바뀌지 않습니다.",
    },
    "strategy.growth_title": {
        "en": "Portfolio growth (starts at 1)",
        "ko": "투자 성과 추이 (시작=1)",
    },
    "strategy.date": {"en": "Date", "ko": "날짜"},
    "strategy.capital": {"en": "Portfolio value", "ko": "투자 가치"},
    "strategy.rule": {"en": "Strategy", "ko": "투자 방법"},
    "strategy.drawdown_title": {
        "en": "Drop from a previous high",
        "ko": "고점 대비 하락률",
    },
    "strategy.drawdown_caption": {
        "en": "How far each strategy fell below its own previous high. −30% means 30% below that high.",
        "ko": "각 투자 방법이 이전 최고점에서 얼마나 내려왔는지 보여줍니다. −30%는 최고점보다 30% 낮다는 뜻입니다.",
    },
    "strategy.metrics": {"en": "Results summary", "ko": "성과 요약"},
    "strategy.cagr": {"en": "CAGR", "ko": "연평균 복리수익률 (CAGR)"},
    "strategy.ann_vol": {"en": "Annualized volatility", "ko": "연환산 변동성"},
    "strategy.max_drawdown": {"en": "Maximum drawdown", "ko": "최대 낙폭"},
    "strategy.sharpe": {"en": "Sharpe ratio", "ko": "샤프 지수"},
    "strategy.rule_guide": {"en": "📖 Strategy details", "ko": "📖 투자 방법 설명"},
    "strategy.metric_guide": {"en": "📖 Metric definitions", "ko": "📖 지표 설명"},
    "strategy.footer": {
        "en": "The calculation rules and assumptions are documented in `analytics/strategies.py`. TQQQ is leveraged and can suffer much larger losses than an unleveraged ETF.",
        "ko": "계산 규칙과 가정은 `analytics/strategies.py`에 있습니다. TQQQ는 레버리지 ETF이므로 일반 ETF보다 손실 폭이 매우 커질 수 있습니다.",
    },
    "ask.title": {"en": "💬 Ask About ETFs", "ko": "💬 ETF 정보 물어보기"},
    "ask.subtitle": {
        "en": "Ask in English or Korean about ETF and basic investing terms, or explore historical prices, returns, trading value, price swings, and drawdowns. This tool does not predict future returns or provide personal investment advice.",
        "ko": "ETF와 기초 투자 용어의 뜻을 물어보거나 과거 가격, 수익률, 거래대금, 가격 변동, 하락 폭을 살펴보세요. 한국어와 영어 모두 사용할 수 있습니다. 미래 수익을 예측하거나 개인 투자 조언을 하지는 않습니다.",
    },
    "ask.defaults": {
        "en": "If you do not specify a period, the app uses the past year. Broad comparisons exclude leveraged ETFs unless you ask to include them. Volume means average daily trading value.",
        "ko": "기간을 말하지 않으면 최근 1년을 기준으로 봅니다. 여러 ETF를 폭넓게 비교할 때는 따로 요청하지 않는 한 레버리지 ETF를 제외합니다. 거래량 질문은 평균 일일 거래대금을 기준으로 답합니다.",
    },
    "ask.examples": {
        "en": "Examples: `What is positive correlation?` · `Which 3 ETFs had the highest return over the past year?` · `Did ETFs with higher returns also have deeper maximum drawdowns?`",
        "ko": "예시: `양의 상관관계가 뭐야?` · `최근 1년 수익률이 가장 높은 ETF 3개는?` · `수익률이 높은 ETF일수록 최대 낙폭도 큰가?`",
    },
    "ask.unavailable": {
        "en": "ETF questions are unavailable until the AI key is configured. The other pages still work.\n\nLocal setup: add `GEMINI_API_KEY` to `.env` → refresh",
        "ko": "AI 키가 설정될 때까지 ETF 질문 기능을 사용할 수 없습니다. 다른 화면은 계속 이용할 수 있습니다.\n\n로컬 설정: `.env`에 `GEMINI_API_KEY` 추가 → 새로고침",
    },
    "ask.data_unavailable": {
        "en": "I can explain ETF and basic investing terms right now, but historical data lookups and comparisons are temporarily unavailable.",
        "ko": "지금은 ETF와 기초 투자 용어를 설명할 수 있지만, 과거 데이터 조회와 비교는 잠시 사용할 수 없습니다.",
    },
    "ask.password": {"en": "Demo password", "ko": "데모 접속 비밀번호"},
    "ask.password_info": {
        "en": "A password protects the shared AI quota for this public demo.",
        "ko": "공용 AI 사용 한도를 보호하기 위해 비밀번호가 필요합니다.",
    },
    "ask.dependency_error": {
        "en": "The question feature could not start. If you just deployed the app, restart it once. The other pages still work.",
        "ko": "질문 기능을 시작하지 못했습니다. 방금 배포했다면 앱을 한 번 재시작하세요. 다른 화면은 계속 이용할 수 있습니다.",
    },
    "ask.admin_error": {
        "en": "Technical error details",
        "ko": "관리자용 상세 정보",
    },
    "ask.database_error": {
        "en": "Historical data is unavailable. Basic concept explanations still work. Try data questions again later or notify the administrator.",
        "ko": "과거 데이터에 연결하지 못했습니다. 기초 개념 설명은 계속 사용할 수 있습니다. 데이터 질문은 잠시 후 다시 시도하거나 관리자에게 알려주세요.",
    },
    "ask.admin_connection": {
        "en": "Technical connection details",
        "ko": "관리자용 연결 상세",
    },
    "ask.refusal_alternative": {
        "en": "Try asking what an ETF term means, or ask me to look up historical data, compare ETFs, show rankings, or explore relationships.",
        "ko": "ETF 용어의 뜻을 묻거나 과거 데이터를 찾고 ETF를 비교하는 질문을 해보세요.",
    },
    "ask.truncated": {
        "en": "Only {rows} rows are shown. Reduce the number of ETFs or shorten the period to see the full result.",
        "ko": "표를 {rows}행까지만 표시했습니다. ETF 수나 기간을 줄이면 전체 결과를 볼 수 있습니다.",
    },
    "ask.sql": {
        "en": "Show query details (SQL)",
        "ko": "실행한 조회문(SQL) 보기",
    },
    "ask.auto_view": {
        "en": "Concept questions get a short explanation. For data questions, the app chooses the clearest table or chart.",
        "ko": "개념 질문에는 짧은 설명으로 답하고, 데이터 질문에는 가장 알기 쉬운 표나 차트를 골라 보여드립니다.",
    },
    "ask.placeholder": {
        "en": "e.g. How much did TLT swing over the past year?",
        "ko": "예: 최근 1년 동안 TLT는 얼마나 흔들렸어?",
    },
    "ask.spinner": {"en": "Preparing the answer...", "ko": "답변을 준비하는 중..."},
    "ask.quota_error": {
        "en": "Today's free AI quota has been exhausted. Please try again tomorrow.",
        "ko": "오늘 사용할 수 있는 무료 AI 질문 횟수를 모두 썼습니다. 내일 다시 시도해주세요.",
    },
    "ask.provider_error": {
        "en": "The AI service is temporarily unavailable. Please try again in a few minutes. The other pages still work.",
        "ko": "AI 서비스가 잠시 응답하지 않습니다. 몇 분 뒤 다시 시도해주세요. 다른 화면은 계속 이용할 수 있습니다.",
    },
    "ask.schema_error": {
        "en": "I could not answer that question with the available data. Try asking about historical prices, returns, price swings, or drawdowns.",
        "ko": "현재 데이터로 답하기 어려운 질문입니다. 과거 가격, 수익률, 가격 변동, 하락 폭에 관해 다시 물어보세요.",
    },
    "ask.generic_error": {
        "en": "An error occurred while processing the question. Please try again later.",
        "ko": "질문을 처리하는 중 오류가 생겼습니다. 잠시 후 다시 시도해주세요.",
    },
    "ask.table_reason": {
        "en": "This result is easier to read as a table. ({reason})",
        "ko": "이 결과는 표로 보는 편이 더 알기 쉽습니다. ({reason})",
    },
    "ask.table_auto": {
        "en": "A table is the clearest view for this result.",
        "ko": "이 결과는 표로 보는 것이 가장 알기 쉽습니다.",
    },
    "ask.chart_error": {
        "en": "The chart could not be created, so the result is shown as a table.",
        "ko": "차트를 만들지 못해 결과를 표로 표시했습니다.",
    },
}


def tr(key: str, lang: Language, **values: object) -> str:
    """Return one interface string in the selected language."""
    message = COPY[key][lang]
    return message.format(**values) if values else message


def ui_controls() -> Language:
    """Render the entrypoint-level language control for the whole session."""

    choice = st.sidebar.segmented_control(
        "Language / 언어",
        options=list(LANGUAGE_OPTIONS),
        default="English",
        required=True,
        key="ui_language",
        persist_state="session",
    )
    return LANGUAGE_OPTIONS[choice or "English"]  # type: ignore[index,return-value]


def current_language() -> Language:
    """Return the language selected by the shared entrypoint control."""

    choice = st.session_state.get("ui_language", "English")
    return LANGUAGE_OPTIONS.get(choice, DEFAULT_LANGUAGE)  # type: ignore[return-value]


ASSET_LABELS_KO = {
    "bond": "채권",
    "equity": "주식",
    "leveraged_equity": "레버리지 주식",
    "real_estate": "부동산",
    "commodity": "원자재",
}

SUBCLASS_LABELS_KO = {
    "treasury_short": "미국 초단기 국채",
    "treasury_intermediate": "미국 중기 국채",
    "treasury_long": "미국 장기 국채",
    "aggregate": "미국 종합 채권",
    "corporate_ig": "투자등급 회사채",
    "corporate_hy": "하이일드 회사채",
    "tips": "물가연동 국채",
    "us_large_cap": "미국 대형주",
    "nasdaq_100": "나스닥 100",
    "nasdaq_100_2x": "나스닥 100 일간 2배",
    "nasdaq_100_3x": "나스닥 100 일간 3배",
    "intl_developed": "미국 외 선진국 주식",
    "us_dividend": "미국 배당주",
    "emerging_markets": "신흥국 주식",
    "us_small_cap": "미국 소형주",
    "us_reit": "미국 리츠",
    "gold": "금",
}

TICKER_DESCRIPTIONS_KO = {
    "SGOV": "만기 3개월 이내의 미국 국채를 담습니다. 가격 움직임이 작고 단기 금리와 비슷한 수익을 추구합니다.",
    "VGIT": "만기 3~10년의 미국 국채를 담습니다. 금리가 내리면 오르고 금리가 오르면 내리는 경향이 있습니다.",
    "TLT": "만기 20년 이상의 미국 장기 국채를 담습니다. 금리 변화에 민감해 양방향 움직임이 큽니다.",
    "BND": "미국 국채·회사채·주택저당채권 등 투자등급 채권시장 전반을 한 상품에 담습니다.",
    "LQD": "미국 투자등급 회사채를 담습니다. 국채보다 높은 이자를 추구하지만 기업 신용 위험이 있습니다.",
    "HYG": "신용등급이 낮은 미국 회사채를 담습니다. 이자는 높지만 시장 불안 때 주식과 함께 하락할 수 있습니다.",
    "TIP": "원금이 미국 소비자물가에 연동되는 국채를 담습니다. 물가 충격을 방어하지만 금리 위험은 남습니다.",
    "SPY": "미국의 대표적인 대형 기업 약 500개를 담아 S&P 500 지수를 추종합니다.",
    "QQQ": "나스닥의 대형 비금융 기업 100개를 담습니다. 기술·성장주 비중이 높습니다.",
    "QLD": "파생상품을 이용해 나스닥 100의 일간 수익률 2배를 추구합니다. 장기 성과가 단순히 2배가 되지는 않습니다.",
    "TQQQ": "나스닥 100의 일간 수익률 3배를 추구합니다. 하락장에서 손실 폭이 매우 클 수 있습니다.",
    "VEA": "유럽·일본 등 미국 밖의 선진국 주식을 폭넓게 담습니다.",
    "SCHD": "배당을 꾸준히 지급하고 재무 상태가 비교적 튼튼한 미국 기업을 담습니다.",
    "VWO": "중국·인도·대만·브라질 등 신흥국 주식을 폭넓게 담습니다. 환율과 정치 위험이 큽니다.",
    "IWM": "미국 소형 기업 약 2,000개를 담습니다. 대형주보다 미국 경기 변화에 민감합니다.",
    "VNQ": "사무실·아파트·물류창고 등을 보유한 미국 부동산 투자회사(REIT)를 담습니다.",
    "GLD": "금고에 보관된 실물 금을 바탕으로 금 가격을 추종합니다. 이자나 배당은 없습니다.",
}
