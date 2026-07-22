"""Shared interface copy and controls for the multipage Streamlit app."""

from __future__ import annotations

from typing import Literal

import streamlit as st

Language = Literal["en", "ko"]
DEFAULT_LANGUAGE: Language = "en"
LANGUAGE_OPTIONS = {"English": "en", "한국어": "ko"}


COPY: dict[str, dict[Language, str]] = {
    "home.subtitle": {
        "en": "An educational dashboard comparing the price, return and risk of 17 ETFs",
        "ko": "17개 ETF의 가격·수익·위험을 비교하는 교육용 대시보드",
    },
    "home.intro_title": {
        "en": "👋 New here? One-minute guide",
        "ko": "👋 처음 오셨나요? 1분 안내",
    },
    "home.intro_body": {
        "en": """
        An **ETF** is one product that holds a basket of investments such as shares or bonds.

        A **ticker** is its short market code. For example: `SPY` = large US companies,
        `BND` = US bonds and `GLD` = gold.

        1. Choose the ETFs you want to compare. The first view uses only `SPY`, `BND` and `GLD`.
        2. **Adjusted price** includes the effect of distributions and share splits.
        3. **Cumulative return** shows the total gain or loss since the first date on the chart.
        4. **Volatility** describes how widely daily returns moved over the latest 30 trading days.

        ⚠️ This app explains historical data for education. It does not predict returns or recommend buying or selling.
        """,
        "ko": """
        **ETF**는 여러 주식이나 채권을 한 바구니에 담은 상품입니다.

        **티커**(ticker)는 그 상품의 짧은 이름입니다. 예: `SPY`=미국 대형주,
        `BND`=미국 채권, `GLD`=금.

        1. 아래에서 비교할 ETF를 고릅니다. 처음에는 서로 다른 `SPY`·`BND`·`GLD`만 보여줍니다.
        2. **조정 가격**은 배당·주식 분할을 반영한 비교용 가격입니다.
        3. **누적수익률**은 처음부터 지금까지 얼마나 늘거나 줄었는지 보여줍니다.
        4. **변동성**은 최근 30거래일 동안 일간 수익률이 얼마나 크게 흔들렸는지 나타냅니다.

        ⚠️ 이 앱은 과거 데이터를 설명하는 교육용 도구이며, 미래 수익을 예측하거나 매수·매도를 권하지 않습니다.
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
        "en": "🧪 Compare historical investing rules",
        "ko": "🧪 과거 투자 규칙 비교",
    },
    "home.nav_ask": {
        "en": "💬 Ask questions about the data",
        "ko": "💬 데이터에 질문하기",
    },
    "home.data_error": {
        "en": "No data is available from PostgreSQL or the bundled parquet snapshot. Start Docker, run ingest and `dbt run`, or add a reviewed parquet snapshot.",
        "ko": "PostgreSQL과 포함된 parquet 예시 데이터에서 자료를 읽지 못했습니다. Docker를 시작하고 ingest와 `dbt run`을 실행하거나 검토된 parquet 스냅샷을 추가하세요.",
    },
    "home.admin_details": {"en": "Technical details", "ko": "관리자용 상세 정보"},
    "home.ticker_guide": {"en": "📖 ETF guide", "ko": "📖 ETF 이름표"},
    "home.ticker": {"en": "Ticker", "ko": "티커"},
    "home.fund_name": {"en": "Fund name", "ko": "상품 이름"},
    "home.asset_class": {"en": "Asset class", "ko": "큰 자산 분류"},
    "home.asset_class_help": {
        "en": "A broad group such as equity, bonds, gold or real estate.",
        "ko": "주식·채권·금·부동산 같은 큰 분류입니다.",
    },
    "home.sub_class": {"en": "Sub-class", "ko": "세부 분류"},
    "home.sub_class_help": {
        "en": "A more specific category within the broad asset class.",
        "ko": "같은 자산 안에서 나누는 더 자세한 분류입니다.",
    },
    "home.leverage": {"en": "Daily leverage", "ko": "레버리지 배수"},
    "home.leverage_help": {
        "en": "1 means unleveraged. 2 and 3 target two or three times the daily move.",
        "ko": "1은 일반 ETF, 2·3은 일간 변동을 두 배·세 배로 추종하는 ETF입니다.",
    },
    "home.detail_select": {"en": "Show details for", "ko": "자세히 볼 ETF"},
    "home.dim_missing": {
        "en": "Run `dbt seed && dbt run` to build the ETF reference table.",
        "ko": "ETF 설명 표를 만들려면 `dbt seed && dbt run`을 실행하세요.",
    },
    "home.select_etfs": {"en": "ETFs to compare", "ko": "비교할 ETF"},
    "home.empty_selection": {
        "en": "Select at least one ETF to display the charts.",
        "ko": "차트를 보려면 ETF를 하나 이상 골라주세요.",
    },
    "home.adjusted_price": {"en": "Adjusted price", "ko": "조정 가격"},
    "home.adjusted_price_caption": {
        "en": "Price adjusted for distributions and share splits, suitable for long-term comparison",
        "ko": "배당과 주식 분할을 반영해 장기 비교에 맞춘 가격",
    },
    "home.cumulative_return": {"en": "Cumulative return", "ko": "누적수익률"},
    "home.cumulative_return_caption": {
        "en": "Total return assuming one unit was invested on the first chart date",
        "ko": "차트의 첫날에 1을 투자했다고 가정한 전체 수익률",
    },
    "home.volatility": {
        "en": "Rolling 30-trading-day volatility",
        "ko": "최근 30거래일 변동성",
    },
    "home.volatility_caption": {
        "en": "Higher values mean daily returns moved more widely over the latest 30 trading days",
        "ko": "값이 클수록 최근 30거래일의 일간 수익률이 더 크게 흔들렸습니다",
    },
    "home.latest": {"en": "Latest snapshot", "ko": "가장 최근 상태"},
    "home.as_of_date": {"en": "As-of date", "ko": "기준일"},
    "home.drawdown": {"en": "Drawdown from peak", "ko": "고점 대비 하락률"},
    "home.metrics_guide": {"en": "📖 Metrics guide", "ko": "📖 용어 설명"},
    "strategy.title": {"en": "🧪 Strategy Lab", "ko": "🧪 과거 투자 규칙 비교"},
    "strategy.subtitle": {
        "en": "Compare five investing rules on the same historical adjusted-price data. Fees, taxes and slippage are excluded, and idle cash earns 0%. **This is a historical educational experiment, not a forecast or investment advice.**",
        "ko": "다섯 가지 투자 규칙을 같은 과거 조정 가격에 적용해 결과를 비교합니다. 수수료·세금·매매 오차는 제외하며, 남은 현금의 이자는 0%로 가정합니다. **과거 교육용 실험이며 미래 예측이나 투자 조언이 아닙니다.**",
    },
    "strategy.guide_title": {
        "en": "👋 New here? Read the results in this order",
        "ko": "👋 처음 보는 분: 결과 읽는 순서",
    },
    "strategy.guide_body": {
        "en": """
        1. **Growth of capital** starts every line at `1`. A final value of `2` means the capital doubled.
        2. **Drawdown** shows how far each rule fell below its own previous peak. Deeper is more painful.
        3. **Metrics** should be read together: do not judge a rule by return without checking volatility and maximum drawdown.

        The highest historical return is not automatically the safest rule or the best rule for the future.
        """,
        "ko": """
        1. **자산 변화**에서 모든 선은 시작 금액을 `1`로 맞춥니다. 마지막 값이 `2`면 두 배가 된 것입니다.
        2. **고점 대비 하락**에서 아래로 깊게 내려갈수록 투자 중 겪은 손실 폭이 컸습니다.
        3. **핵심 숫자**에서 수익률만 보지 말고 최대 낙폭과 변동성을 함께 봅니다.

        가장 높은 수익을 낸 규칙이 가장 안전하거나 앞으로도 가장 좋다는 뜻은 아닙니다.
        """,
    },
    "strategy.data_error": {
        "en": "No data is available from PostgreSQL or parquet.",
        "ko": "PostgreSQL 또는 parquet에서 데이터를 읽지 못했습니다.",
    },
    "strategy.missing": {
        "en": "The marts are missing these required tickers: {tickers}. Add them to `ETF_TICKERS`, rerun ingest and dbt, then refresh.",
        "ko": "분석 표에 필요한 티커가 없습니다: {tickers}. `ETF_TICKERS`에 추가하고 ingest와 dbt를 다시 실행한 뒤 새로고침하세요.",
    },
    "strategy.buy_hold_name": {
        "en": "Buy and hold (SPY)",
        "ko": "한 번 사고 보유 (SPY)",
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
        "en": "Monthly instalments (QQQ)",
        "ko": "매월 나눠 사기 (QQQ)",
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
        "en": "60% equity / 40% bonds (SPY/BND)",
        "ko": "주식 60%·채권 40% (SPY/BND)",
    },
    "strategy.balanced_short": {
        "en": "60/40 · SPY/BND",
        "ko": "60/40 · SPY/BND",
    },
    "strategy.balanced_note": {
        "en": "Reset the portfolio to 60/40 each quarter. The rule trims the side that rose and adds to the side that lagged to reduce swings.",
        "ko": "분기마다 비중을 60 대 40으로 되돌립니다. 많이 오른 쪽을 줄이고 덜 오른 쪽을 늘려 흔들림을 낮추려는 규칙입니다.",
    },
    "strategy.trend_name": {
        "en": "200-day trend (QQQ/cash)",
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
        "en": "Split buys, sell at +10% (TQQQ)",
        "ko": "분할 매수 후 10% 매도 (TQQQ)",
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
        "en": "Compress large value differences (log scale)",
        "ko": "큰 값의 차이를 압축해서 보기 (로그 눈금)",
    },
    "strategy.log_help": {
        "en": "Makes lower lines easier to see when results differ greatly. It does not change the underlying values.",
        "ko": "수익 차이가 매우 클 때 낮은 선도 잘 보이게 합니다. 실제 결과값은 바뀌지 않습니다.",
    },
    "strategy.growth_title": {
        "en": "Growth of capital (start = 1)",
        "ko": "자산 변화 (시작 금액=1)",
    },
    "strategy.date": {"en": "Date", "ko": "날짜"},
    "strategy.capital": {"en": "Capital", "ko": "자산"},
    "strategy.rule": {"en": "Investing rule", "ko": "투자 규칙"},
    "strategy.drawdown_title": {"en": "Drawdown", "ko": "고점 대비 하락"},
    "strategy.drawdown_caption": {
        "en": "How far each rule fell below its own previous peak. −30% means 30% below that peak.",
        "ko": "각 규칙의 이전 최고점에서 얼마나 내려왔는지 보여줍니다. −30%는 최고점보다 30% 낮다는 뜻입니다.",
    },
    "strategy.metrics": {"en": "Metrics", "ko": "핵심 숫자"},
    "strategy.cagr": {"en": "CAGR", "ko": "연복리 수익률 (CAGR)"},
    "strategy.ann_vol": {"en": "Annualised volatility", "ko": "연환산 변동성"},
    "strategy.max_drawdown": {"en": "Maximum drawdown", "ko": "최대 낙폭"},
    "strategy.sharpe": {"en": "Sharpe ratio", "ko": "샤프 지수"},
    "strategy.rule_guide": {"en": "📖 Strategy guide", "ko": "📖 투자 규칙 설명"},
    "strategy.metric_guide": {"en": "📖 Metrics guide", "ko": "📖 숫자 용어 설명"},
    "strategy.footer": {
        "en": "The calculation rules and assumptions are documented in `analytics/strategies.py`. TQQQ is leveraged and can suffer much larger losses than an unleveraged ETF.",
        "ko": "계산 규칙과 가정은 `analytics/strategies.py`에 있습니다. TQQQ는 레버리지 ETF이므로 일반 ETF보다 손실 폭이 매우 커질 수 있습니다.",
    },
    "ask.title": {"en": "💬 Ask the data", "ko": "💬 데이터에 물어보기"},
    "ask.subtitle": {
        "en": "Ask in English or Korean about prices, returns, dollar volume, volatility and drawdown. The tool handles historical lookups, comparisons, rankings and relationships—not forecasts or investment advice.",
        "ko": "가격·수익률·거래대금·변동성·낙폭을 한국어나 영어로 물어보세요. 과거 데이터 조회·비교·순위·관계를 다루며 미래 예측과 투자 조언은 하지 않습니다.",
    },
    "ask.defaults": {
        "en": "No period specified → trailing 1 year · generic relationship questions → unleveraged ETFs · volume → average daily dollar volume",
        "ko": "기간 생략 → 최근 1년 · 일반 관계 질문 → 비레버리지 ETF · 거래량 → 평균 일일 거래대금",
    },
    "ask.examples": {
        "en": "Examples: `Which 3 ETFs had the highest return over the past year?` · `Did ETFs with higher returns also have deeper maximum drawdowns?`",
        "ko": "예시: `최근 1년 수익률이 가장 높은 ETF 3개는?` · `수익률이 높은 ETF일수록 최대 낙폭도 큰가?`",
    },
    "ask.unavailable": {
        "en": "Ask requires the PostgreSQL analytics marts and a `GEMINI_API_KEY`. The other dashboard pages remain available.\n\nLocal setup: `docker compose up -d` → ingest → `dbt run` → add the key to `.env` → refresh",
        "ko": "Ask를 사용하려면 PostgreSQL 분석 테이블과 `GEMINI_API_KEY`가 필요합니다. 대시보드의 다른 화면은 계속 사용할 수 있습니다.\n\n로컬 설정: `docker compose up -d` → ingest → `dbt run` → `.env`에 키 추가 → 새로고침",
    },
    "ask.password": {"en": "Access password", "ko": "접속 비밀번호"},
    "ask.password_info": {
        "en": "A password protects the shared AI quota for this public demo.",
        "ko": "공용 AI 사용 한도를 보호하기 위해 비밀번호가 필요합니다.",
    },
    "ask.dependency_error": {
        "en": "Ask could not start. If this was just deployed, reboot the app and try again. The other dashboard pages remain available.",
        "ko": "질문 기능을 준비하지 못했습니다. 방금 배포했다면 앱을 Reboot한 뒤 다시 시도하세요. 다른 대시보드 화면은 계속 사용할 수 있습니다.",
    },
    "ask.admin_error": {
        "en": "Administrator error details",
        "ko": "관리자용 오류 정보",
    },
    "ask.database_error": {
        "en": "The read-only question database is unavailable. Try again later or notify the administrator. The other dashboard pages remain available.",
        "ko": "질문용 읽기 전용 데이터베이스에 연결하지 못했습니다. 잠시 후 다시 시도하거나 관리자에게 알려주세요. 다른 대시보드 화면은 계속 사용할 수 있습니다.",
    },
    "ask.admin_connection": {
        "en": "Administrator connection details",
        "ko": "관리자용 연결 정보",
    },
    "ask.refusal_alternative": {
        "en": "I can instead answer historical lookups, comparisons, rankings and relationships over the stored data.",
        "ko": "대신 저장된 과거 데이터의 조회·비교·순위·관계는 답할 수 있습니다.",
    },
    "ask.truncated": {
        "en": "Only {rows} rows are shown. Reduce the number of ETFs or shorten the period to see the full result.",
        "ko": "표를 {rows}행까지만 표시했습니다. ETF 수나 기간을 줄이면 전체 결과를 볼 수 있습니다.",
    },
    "ask.sql": {"en": "Executed SQL", "ko": "실행한 SQL 보기"},
    "ask.auto_view": {
        "en": "Automatic view: time series → line · ranking/comparison → bar · relationship → scatter · otherwise → table",
        "ko": "자동 표시: 시계열 → 선 차트 · 순위/비교 → 막대 차트 · 관계 → 산점도 · 그 외 → 표",
    },
    "ask.placeholder": {
        "en": "e.g. How volatile was TLT over the past year?",
        "ko": "예: 최근 1년 TLT 변동성은?",
    },
    "ask.spinner": {"en": "Checking the data...", "ko": "데이터를 확인하는 중..."},
    "ask.quota_error": {
        "en": "Today's free AI quota has been exhausted. Please try again tomorrow.",
        "ko": "오늘 사용할 수 있는 무료 AI 질문 횟수를 모두 썼습니다. 내일 다시 시도해주세요.",
    },
    "ask.provider_error": {
        "en": "The AI provider is temporarily unavailable after trying the fallback model. Please try again in a few minutes. Tables and the other dashboard pages remain available.",
        "ko": "AI 제공자가 일시적으로 응답하지 않습니다. 예비 모델까지 확인했으니 몇 분 뒤 다시 시도해주세요. 표와 다른 대시보드 화면은 계속 사용할 수 있습니다.",
    },
    "ask.schema_error": {
        "en": "The question does not match the current warehouse schema. Please ask the administrator to check it.",
        "ko": "질문과 현재 데이터 표의 구조가 맞지 않습니다. 관리자에게 확인을 요청해주세요.",
    },
    "ask.generic_error": {
        "en": "An error occurred while processing the question. Please try again later.",
        "ko": "질문을 처리하는 중 오류가 생겼습니다. 잠시 후 다시 시도해주세요.",
    },
    "ask.table_reason": {
        "en": "A table is more appropriate for this result. ({reason})",
        "ko": "이 결과는 차트보다 표가 알맞습니다. ({reason})",
    },
    "ask.table_auto": {
        "en": "A table was selected automatically for this result shape.",
        "ko": "결과 모양에 따라 표를 자동으로 선택했습니다.",
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
