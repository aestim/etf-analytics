"""Shared interface copy and controls for the multipage Streamlit app."""

from __future__ import annotations

from typing import Literal

import streamlit as st

Language = Literal["en", "ko"]
DEFAULT_LANGUAGE: Language = "en"
LANGUAGE_OPTIONS = {"English": "en", "한국어": "ko"}


COPY: dict[str, dict[Language, str]] = {
    "home.subtitle": {
        "en": "Compare historical prices, returns, and risk across the default universe and ETFs you add for this session.",
        "ko": "기본 ETF와 현재 세션에 추가한 ETF의 과거 가격, 수익률, 위험을 비교합니다.",
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
    "custom.title": {
        "en": "🔎 Find and add an ETF for this session",
        "ko": "🔎 현재 세션에 추가할 ETF 찾기",
    },
    "custom.help": {
        "en": "Search by ETF name, ISIN or Yahoo Finance symbol. Yahoo results are best-effort, so choose the listing you use with your broker.",
        "ko": "ETF 이름, ISIN 또는 Yahoo Finance 종목 코드로 검색하세요. Yahoo 결과는 완전하지 않을 수 있으므로 실제 이용하는 상장 시장을 직접 선택하세요.",
    },
    "custom.input_label": {
        "en": "ETF name, ISIN or Yahoo Finance symbol",
        "ko": "ETF 이름, ISIN 또는 Yahoo Finance 종목 코드",
    },
    "custom.input_placeholder": {
        "en": "e.g. Vanguard FTSE All-World, IE00BK5BQT80 or VWCE.DE",
        "ko": "예: Vanguard FTSE All-World, IE00BK5BQT80 또는 VWCE.DE",
    },
    "custom.search": {"en": "Search", "ko": "검색"},
    "custom.searching": {
        "en": "Searching Yahoo Finance...",
        "ko": "Yahoo Finance에서 검색하는 중...",
    },
    "custom.results_for": {
        "en": "Search results for `{query}`",
        "ko": "`{query}` 검색 결과",
    },
    "custom.search_results": {
        "en": "Choose a listing",
        "ko": "상장 시장 선택",
    },
    "custom.add_selected": {
        "en": "Add selected ETF",
        "ko": "선택한 ETF 추가",
    },
    "custom.direct_fallback": {
        "en": "Yahoo returned no search candidates. You can still try the exact symbol below.",
        "ko": "Yahoo 검색 후보가 없습니다. 아래 종목 코드를 직접 조회해 볼 수 있습니다.",
    },
    "custom.try_exact_symbol": {
        "en": "Try exact symbol: {symbol}",
        "ko": "정확한 종목 코드 직접 시도: {symbol}",
    },
    "custom.invalid_query": {
        "en": "Enter an ETF name, ISIN or Yahoo Finance symbol.",
        "ko": "ETF 이름, ISIN 또는 Yahoo Finance 종목 코드를 입력하세요.",
    },
    "custom.no_results": {
        "en": "No candidates were found. Try the full fund name, an ISIN, or an exchange-suffixed Yahoo symbol.",
        "ko": "검색 후보가 없습니다. 전체 상품명, ISIN 또는 거래소 접미사가 붙은 Yahoo 종목 코드로 다시 검색하세요.",
    },
    "custom.search_unavailable": {
        "en": "Yahoo search is temporarily unavailable. If you entered an exact symbol, you may still try it below.",
        "ko": "Yahoo 검색을 일시적으로 사용할 수 없습니다. 정확한 종목 코드를 입력했다면 아래에서 직접 조회할 수 있습니다.",
    },
    "custom.verify_isin": {
        "en": "Yahoo search may not return every listing or prove an exact ISIN/share-class match. Verify the listing with your broker or issuer.",
        "ko": "Yahoo 검색은 모든 상장 시장을 반환하거나 정확한 ISIN·share class 일치를 보장하지 않습니다. 브로커나 발행사에서 확인하세요.",
    },
    "custom.verify_listing": {
        "en": "Similar names can belong to different accumulating or distributing share classes. Verify the selected listing with your broker or issuer.",
        "ko": "이름이 비슷해도 적립형·분배형 등 다른 share class일 수 있습니다. 선택한 상품을 브로커나 발행사에서 확인하세요.",
    },
    "custom.provider_type": {
        "en": "Yahoo type",
        "ko": "Yahoo 분류",
    },
    "custom.exchange_unknown": {
        "en": "Exchange unknown",
        "ko": "거래소 정보 없음",
    },
    "custom.type_unknown": {
        "en": "Unclassified",
        "ko": "분류 정보 없음",
    },
    "custom.loading": {
        "en": "Loading history for {ticker}...",
        "ko": "{ticker} 과거 데이터를 불러오는 중...",
    },
    "custom.added": {
        "en": "{ticker} is now available on Overview and Strategy Lab.",
        "ko": "{ticker}를 한눈에 보기와 투자 방법 비교에 추가했습니다.",
    },
    "custom.already_available": {
        "en": "{ticker} is already included in the standard ETF universe.",
        "ko": "{ticker}는 이미 기본 ETF 목록에 있습니다.",
    },
    "custom.duplicate": {
        "en": "{ticker} is already in this session.",
        "ko": "{ticker}는 이미 현재 세션에 있습니다.",
    },
    "custom.invalid_ticker": {
        "en": "Enter a valid Yahoo Finance symbol using letters, numbers, dots or hyphens.",
        "ko": "영문자, 숫자, 점 또는 하이픈으로 된 Yahoo Finance 종목 코드를 입력하세요.",
    },
    "custom.isin_error": {
        "en": "This looks like an ISIN. Enter the Yahoo Finance listing symbol instead; European symbols normally include an exchange suffix.",
        "ko": "ISIN으로 보입니다. Yahoo Finance의 상장 종목 코드를 입력하세요. 유럽 종목에는 보통 거래소 접미사가 붙습니다.",
    },
    "custom.unavailable": {
        "en": "No usable daily history was found for {ticker}. Check the symbol and exchange suffix.",
        "ko": "{ticker}의 일별 데이터를 찾지 못했습니다. 종목 코드와 거래소 접미사를 확인하세요.",
    },
    "custom.insufficient": {
        "en": "{ticker} has fewer than 30 usable trading days, so it was not added.",
        "ko": "{ticker}는 사용 가능한 거래일이 30일 미만이어서 추가하지 않았습니다.",
    },
    "custom.limit": {
        "en": "You can add up to 5 ETFs per session. Remove one before adding another.",
        "ko": "한 세션에 ETF를 최대 5개까지 추가할 수 있습니다. 기존 항목을 삭제한 뒤 추가하세요.",
    },
    "custom.current": {
        "en": "ETFs added in this session",
        "ko": "현재 세션에 추가된 ETF",
    },
    "custom.remove": {"en": "Remove", "ko": "삭제"},
    "custom.clear": {"en": "Remove all session ETFs", "ko": "세션 ETF 모두 삭제"},
    "custom.session_notice": {
        "en": "Session only: these symbols disappear when the session ends and are not available in Ask.",
        "ko": "세션 전용: 세션이 끝나면 사라지며 ETF 질문하기에는 포함되지 않습니다.",
    },
    "custom.currency_notice": {
        "en": "Data remains in each listing's trading currency. The app does not convert currencies or verify ETF classification, tax status, or local investor eligibility.",
        "ko": "각 상장 종목의 거래 통화를 그대로 사용합니다. 환전, ETF 상품 분류, 세금 또는 현지 투자자격은 확인하지 않습니다.",
    },
    "custom.strategy_notice": {
        "en": "Session ETFs available here: {tickers}. Their returns remain in each listing currency; no FX conversion is applied.",
        "ko": "현재 세션 ETF: {tickers}. 각 상장 통화 기준 수익률이며 환율 변환은 적용하지 않습니다.",
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
        "en": "Choose how to invest and rebalance your ETF mix, then compare it with another custom strategy and five examples. **For education only. Past results do not predict future performance.**",
        "ko": "ETF 비중과 투자 시점, 리밸런싱 여부를 정한 뒤 다른 내 전략과 예시 전략 5개를 비교하세요. **학습용 비교이며 과거 성과가 미래 수익을 보장하지 않습니다.**",
    },
    "strategy.mode_label": {
        "en": "Choose a view",
        "ko": "무엇을 볼까요?",
    },
    "strategy.mode_custom": {
        "en": "My portfolio simulation",
        "ko": "내 포트폴리오 시뮬레이션",
    },
    "strategy.mode_examples": {
        "en": "Detailed view of five examples",
        "ko": "예시 전략 5개 자세히",
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
        "en": "Infinite Buying Strategy: staged buys, sell at a 10% gain (TQQQ)",
        "ko": "무한매수법: 나눠 사고 10% 오르면 매도 (TQQQ)",
    },
    "strategy.split_short": {
        "en": "Infinite Buying · TQQQ",
        "ko": "무한매수법 · TQQQ",
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
    "simulation.intro": {
        "en": "Build one strategy by choosing ETFs, entry timing and rebalancing. The five examples appear automatically below, and you can add a second strategy of your own.",
        "ko": "ETF와 투자 시점, 리밸런싱 여부를 골라 내 전략을 만드세요. 아래에서 예시 전략 5개를 바로 비교할 수 있고 내 전략을 하나 더 추가할 수도 있습니다.",
    },
    "simulation.primary_title": {
        "en": "1. Build my strategy",
        "ko": "1. 내 전략 만들기",
    },
    "simulation.plan_title": {
        "en": "Investment method",
        "ko": "투자 방법",
    },
    "simulation.plan_method": {
        "en": "When should the money be invested?",
        "ko": "투자금을 어떻게 넣을까요?",
    },
    "simulation.plan_lump": {
        "en": "Invest all at once",
        "ko": "한 번에 투자",
    },
    "simulation.plan_staged": {
        "en": "Spread out purchases",
        "ko": "나눠서 투자",
    },
    "simulation.plan_rebalance": {
        "en": "Rebalance once a year",
        "ko": "1년에 한 번 리밸런싱",
    },
    "simulation.plan_rebalance_help": {
        "en": "At the first available trading date each year, restore the selected ETF weights. Money reserved for future staged purchases stays in cash.",
        "ko": "매년 첫 거래일에 선택한 ETF 비중으로 되돌립니다. 나중에 나눠 투자할 예정인 현금은 미리 투자하지 않습니다.",
    },
    "simulation.plan_single_etf": {
        "en": "Rebalancing is unavailable because one ETF has no allocation to restore.",
        "ko": "ETF가 1개면 다시 맞출 비중이 없어 리밸런싱을 적용하지 않습니다.",
    },
    "simulation.plan_staged_summary": {
        "en": "spread over {months} months",
        "ko": "{months}개월 나눠 투자",
    },
    "simulation.plan_yearly": {
        "en": "yearly rebalancing",
        "ko": "매년 리밸런싱",
    },
    "simulation.plan_hold": {
        "en": "no scheduled rebalancing",
        "ko": "정기 리밸런싱 안 함",
    },
    "simulation.plan_summary": {
        "en": "**{name}:** {entry} · {rebalance}",
        "ko": "**{name}:** {entry} · {rebalance}",
    },
    "simulation.my_strategy": {
        "en": "My strategy",
        "ko": "내 전략",
    },
    "simulation.add_second": {
        "en": "+ Add another strategy of my own",
        "ko": "+ 내 전략 하나 더 추가",
    },
    "simulation.second_title": {
        "en": "2. Add another strategy",
        "ko": "2. 비교할 내 전략 추가",
    },
    "simulation.second_caption": {
        "en": "It uses the same starting budget and dates, but can have different ETFs, weights and investment rules.",
        "ko": "총 투자금과 기간은 같게 두고 ETF, 비중, 투자 방법은 다르게 정할 수 있습니다.",
    },
    "simulation.second_name": {
        "en": "Strategy name",
        "ko": "전략 이름",
    },
    "simulation.second_default": {
        "en": "My strategy 2",
        "ko": "내 전략 2",
    },
    "simulation.second_name_duplicate": {
        "en": "Give the second strategy a different name.",
        "ko": "두 번째 전략에는 다른 이름을 붙여주세요.",
    },
    "simulation.remove_second": {
        "en": "Remove this strategy",
        "ko": "이 전략 삭제",
    },
    "simulation.select_etfs": {
        "en": "Choose ETFs (up to 5)",
        "ko": "ETF 선택 (최대 5개)",
    },
    "simulation.equal_weights": {
        "en": "Split equally",
        "ko": "똑같이 나누기",
    },
    "simulation.weight_label": {
        "en": "{ticker} weight (%)",
        "ko": "{ticker} 비중 (%)",
    },
    "simulation.weight_total": {
        "en": "Total weight: **{total:.1f}%**",
        "ko": "비중 합계: **{total:.1f}%**",
    },
    "simulation.weight_valid": {
        "en": "The weights add up to 100%.",
        "ko": "비중 합계가 100%입니다.",
    },
    "simulation.weight_invalid": {
        "en": "Adjust the weights to exactly 100% to see results.",
        "ko": "결과를 보려면 비중 합계를 정확히 100%로 맞춰주세요.",
    },
    "simulation.total_amount": {
        "en": "Total simulation amount ({unit})",
        "ko": "총 투자금 ({unit})",
    },
    "simulation.amount_help": {
        "en": "Every strategy in the comparison starts with the same available budget.",
        "ko": "비교하는 모든 전략은 같은 총 투자금을 가지고 시작합니다.",
    },
    "simulation.start_date": {
        "en": "Requested start date",
        "ko": "투자 시작일",
    },
    "simulation.actual_period": {
        "en": "Actual comparison period: **{start} to {end}**",
        "ko": "실제 비교 기간: **{start} ~ {end}**",
    },
    "simulation.compare_label": {
        "en": "What do you want to compare?",
        "ko": "무엇을 비교할까요?",
    },
    "simulation.compare_timing": {
        "en": "Invest all at once vs spread out purchases",
        "ko": "한 번에 투자 vs 나눠서 투자",
    },
    "simulation.compare_rebalance": {
        "en": "No rebalancing vs yearly rebalancing",
        "ko": "리밸런싱 안 함 vs 매년 리밸런싱",
    },
    "simulation.staged_months": {
        "en": "Months used to spread out purchases",
        "ko": "나눠서 투자할 기간",
    },
    "simulation.month_option": {
        "en": "{months} months",
        "ko": "{months}개월",
    },
    "simulation.lump_name": {
        "en": "Invest all at once",
        "ko": "한 번에 투자",
    },
    "simulation.staged_name": {
        "en": "Spread over {months} months",
        "ko": "{months}개월 나눠 투자",
    },
    "simulation.no_rebalance_name": {
        "en": "No rebalancing",
        "ko": "리밸런싱 안 함",
    },
    "simulation.annual_rebalance_name": {
        "en": "Rebalance yearly",
        "ko": "매년 리밸런싱",
    },
    "simulation.results": {
        "en": "My strategy results",
        "ko": "내 전략 결과",
    },
    "simulation.summary_higher": {
        "en": "Over this period, **{higher}** finished {amount} higher than **{lower}**.",
        "ko": "이 기간에는 **{higher}**의 최종 금액이 **{lower}**보다 {amount} 높았습니다.",
    },
    "simulation.summary_equal": {
        "en": "The two alternatives finished at almost the same value over this period.",
        "ko": "이 기간에는 두 방법의 최종 금액이 거의 같았습니다.",
    },
    "simulation.summary_drop": {
        "en": "The smaller historical drop was **{name}** at {drawdown}.",
        "ko": "투자 중 가장 큰 하락 폭이 더 작았던 방법은 **{name}**({drawdown})이었습니다.",
    },
    "simulation.value_chart": {
        "en": "Account value over time",
        "ko": "투자금 변화",
    },
    "simulation.metric": {"en": "Metric", "ko": "항목"},
    "simulation.value": {"en": "Value", "ko": "값"},
    "simulation.final_value": {"en": "Final value", "ko": "최종 금액"},
    "simulation.profit": {"en": "Gain or loss", "ko": "번 돈 또는 잃은 돈"},
    "simulation.total_return": {"en": "Total return", "ko": "총수익률"},
    "simulation.max_drawdown": {
        "en": "Worst drop",
        "ko": "최대 하락",
    },
    "simulation.drop_short": {
        "en": "Drop",
        "ko": "하락률",
    },
    "simulation.annualized_vol": {
        "en": "Annualized price swings",
        "ko": "연환산 가격 변동",
    },
    "simulation.insufficient_history": {
        "en": "There is not enough common price history for this selection and deployment period. Choose an earlier start date, fewer months, or different ETFs.",
        "ko": "선택한 ETF와 분할 기간에 필요한 공통 가격 데이터가 부족합니다. 시작일을 앞당기거나 기간 또는 ETF를 바꿔주세요.",
    },
    "simulation.leverage_warning": {
        "en": "Leveraged ETF selected: {tickers}. Daily leverage can create much larger losses, and long-term returns will not be an exact multiple of the index.",
        "ko": "레버리지 ETF가 포함됐습니다: {tickers}. 일간 수익을 확대하므로 손실도 훨씬 커질 수 있고, 장기 수익률은 지수의 정확한 배수가 아닙니다.",
    },
    "simulation.reference_toggle": {
        "en": "Compare my setup with the five examples",
        "ko": "내 설정을 예시 전략 5개와 비교",
    },
    "simulation.reference_title": {
        "en": "Compare strategies",
        "ko": "전략 비교",
    },
    "simulation.reference_caption": {
        "en": "Your strategy and all five examples are shown from the start. They use the same budget and dates, but the examples use different ETFs as well as different rules.",
        "ko": "내 전략과 예시 전략 5개를 처음부터 모두 보여줍니다. 총 투자금과 기간은 같지만 예시는 사용하는 ETF와 투자 규칙이 모두 다를 수 있습니다.",
    },
    "simulation.reference_select": {
        "en": "Example lines to add to the chart (up to 3)",
        "ko": "차트에 추가할 예시 전략 (최대 3개)",
    },
    "simulation.reference_unavailable": {
        "en": "The five examples cannot use this entire period because required ETF history is missing.",
        "ko": "필요한 ETF의 과거 데이터가 없어 선택한 전체 기간으로 예시 전략 5개를 비교할 수 없습니다.",
    },
    "simulation.my_staged": {
        "en": "My portfolio · {months} months",
        "ko": "내 포트폴리오 · {months}개월",
    },
    "simulation.my_rebalanced": {
        "en": "My portfolio · rebalanced",
        "ko": "내 포트폴리오 · 리밸런싱",
    },
    "simulation.assumptions_title": {
        "en": "Calculation assumptions",
        "ko": "계산에 사용한 가정",
    },
    "simulation.assumptions_body": {
        "en": "- Dividend-adjusted historical prices already reflect ETF operating expenses, dividends, and stock splits.\n- Fractional shares are allowed and idle cash earns 0%.\n- During staged entry, yearly rebalancing only adjusts money already invested; reserved cash follows the selected purchase schedule.\n- Trading fees, taxes, slippage, and currency movements are excluded.\n- This is a historical educational simulation, not a forecast or recommendation.",
        "ko": "- 배당 반영 과거 가격에는 ETF 운용보수, 배당, 주식 분할의 영향이 이미 들어 있습니다.\n- 소수점 단위 매수를 허용하고 대기 현금의 이자는 0%로 가정합니다.\n- 나눠 투자하는 동안 리밸런싱은 이미 투자된 금액에만 적용하며, 남은 현금은 정한 매수 일정에 따라 투자합니다.\n- 거래 수수료, 세금, 매수·매도 가격 차이, 환율 변동은 제외합니다.\n- 과거 데이터를 이용한 학습용 시뮬레이션이며 미래 예측이나 투자 추천이 아닙니다.",
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
