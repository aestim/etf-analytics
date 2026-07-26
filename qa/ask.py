"""
Week 2 (3/3): question → table. Assembles the whole pipeline.

    python qa/ask.py "How volatile was TLT over the past year?"

Flow:  scope routing + SQL generation (normally one structured-output call)
       → guard (one bounded correction only for documented-column mismatch)
       → execute as etf_reader (timeout) → DataFrame

Core principle: the LLM only fills in forms (JSON). Execution is done
exclusively by this code, after validation.
"""

from __future__ import annotations

import os
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from google.genai import errors as genai_errors
from httpx import TimeoutException
from pydantic import BaseModel

from gemini_runtime import new_client
from presentation import correlation_summary
from schema_prompt import SCHEMA_NAME, build_schema_prompt
from sql_guard import MAX_ROWS, GuardError, SchemaGuardError, validate

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# Model aliases such as `gemini-flash-latest` can be hot-swapped to a new
# release. Pin stable IDs so Q&A behaviour and availability do not silently
# change underneath the deployed app. Lite handles the routine structured
# SQL work; Flash remains the higher-quality fallback.
_DEFAULT_CHAIN = "gemini-3.1-flash-lite,gemini-3.5-flash"
MODEL_CHAIN = [
    m.strip()
    for m in os.getenv("GEMINI_MODEL_CHAIN", _DEFAULT_CHAIN).split(",")
    if m.strip()
]
if _override := os.getenv("GEMINI_MODEL"):
    _override = _override.strip()
    MODEL_CHAIN = [_override] + [m for m in MODEL_CHAIN if m != _override]

if not MODEL_CHAIN:
    raise ValueError("GEMINI_MODEL_CHAIN must contain at least one model ID")

_model_idx = 0


def current_model() -> str:
    return MODEL_CHAIN[_model_idx]


def _advance_model() -> bool:
    """Switch to the next configured model. False if none remains."""
    global _model_idx
    if _model_idx + 1 < len(MODEL_CHAIN):
        _model_idx += 1
        print(
            f"   (switching model: {MODEL_CHAIN[_model_idx - 1]} → {current_model()})"
        )
        return True
    return False


STATEMENT_TIMEOUT_MS = 5000  # defence layer 3: kill runaway queries
SAFE_SEARCH_PATH = "pg_catalog"


class SqlAnswer(BaseModel):
    intent: Literal["data_query", "concept_question", "out_of_scope"]
    sql: str
    explanation: str  # query method, concept answer, or concise refusal reason


DEFAULT_RETURN_LOOKBACK = "1 year"
MIN_DEFAULT_RETURN_OBSERVATIONS = 200
DEFAULT_RELATIONSHIP_LOOKBACK = "1 year"
MIN_RELATIONSHIP_OBSERVATIONS = 200
MAX_HISTORICAL_LOOKBACK_YEARS = 10
MIN_OBSERVATIONS_PER_YEAR = 200

_ENGLISH_HISTORICAL_YEARS = re.compile(
    r"\b(?:over\s+(?:the\s+)?past|past|last)\s+(\d+)\s+years?\b",
    re.IGNORECASE,
)
_KOREAN_HISTORICAL_YEARS = re.compile(r"(?:지난|최근)\s*(\d+)\s*년")
_ENGLISH_METRIC_YEARS = re.compile(
    r"\b(\d+)[ -]years?\s+(?:cagr|return|performance|volatility|history|lookback)\b",
    re.IGNORECASE,
)
_KOREAN_METRIC_YEARS = re.compile(
    r"(\d+)\s*년(?:간)?\s*(?:cagr|수익|성과|변동성|데이터)",
    re.IGNORECASE,
)
_ENGLISH_IN_YEARS = re.compile(r"\bin\s+(\d+)\s+years?\b", re.IGNORECASE)
_FUTURE_CUES = re.compile(
    r"\b(?:will|future|forecast|predict|prediction|from now)\b|(?:앞으로|미래|\d+\s*년\s*후)",
    re.IGNORECASE,
)


def historical_lookback_years(question: str) -> int | None:
    """Return an explicitly historical N-year lookback, not a future horizon."""
    if _FUTURE_CUES.search(question):
        return None
    for pattern in (
        _ENGLISH_HISTORICAL_YEARS,
        _KOREAN_HISTORICAL_YEARS,
        _ENGLISH_METRIC_YEARS,
        _KOREAN_METRIC_YEARS,
    ):
        if match := pattern.search(question):
            return int(match.group(1))
    # Users often write "in 10 years" to mean "using a 10-year window" in an
    # analytics UI. Treat it as historical unless explicit forecast language
    # makes the future meaning clear.
    if match := _ENGLISH_IN_YEARS.search(question):
        return int(match.group(1))
    return None


def _question_with_period_context(question: str) -> str:
    years = historical_lookback_years(question)
    if years is None:
        return question
    minimum = years * MIN_OBSERVATIONS_PER_YEAR
    return (
        f"{question}\n\n"
        "Parsed request context (follow this exactly): the user explicitly requested "
        f"a trailing historical {years}-year window, not a future prediction. This "
        f"overrides the default lookback. Require at least {minimum} paired trading-day "
        "observations per ticker for a full-period comparison."
    )


# Few-shot "question → correct SQL" pairs. Their job is to teach style
# (qualified schema paths, date handling, aggregation tricks).
FEW_SHOTS = f"""
Example 1
Q: 지난 1년 TLT 변동성 어땠어?
Intent: data_query
SQL: WITH period_prices AS (
         SELECT ticker, price_date, adj_close
         FROM public_marts.mart_etf_returns
         WHERE ticker = 'TLT'
           AND price_date >= CURRENT_DATE - INTERVAL '1 year'
     ),
     period_rows AS (
         SELECT *,
                adj_close / LAG(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                ) - 1 AS period_daily_return
         FROM period_prices
     )
     SELECT ticker,
            MIN(price_date) AS period_start,
            MAX(price_date) AS period_end,
            COUNT(*) AS price_observations,
            COUNT(period_daily_return) AS return_observations,
            STDDEV_SAMP(period_daily_return) * SQRT(252)
                AS period_annualized_volatility
     FROM period_rows
     GROUP BY ticker

Example 2
Q: Which long-term treasury ETF had the lowest volatility this year?
Intent: data_query
SQL: WITH period_prices AS (
         SELECT p.ticker, p.price_date, p.adj_close
         FROM public_marts.mart_etf_returns AS p
         JOIN public_marts.dim_etf AS d ON p.ticker = d.ticker
         WHERE d.sub_class = 'treasury_long'
           AND p.price_date >= DATE_TRUNC('year', CURRENT_DATE)
     ),
     period_rows AS (
         SELECT *,
                adj_close / LAG(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                ) - 1 AS period_daily_return
         FROM period_prices
     )
     SELECT ticker,
            MIN(price_date) AS period_start,
            MAX(price_date) AS period_end,
            COUNT(*) AS price_observations,
            COUNT(period_daily_return) AS return_observations,
            STDDEV_SAMP(period_daily_return) * SQRT(252)
                AS period_annualized_volatility
     FROM period_rows
     GROUP BY ticker
     ORDER BY period_annualized_volatility ASC

Example 3
Q: 올해 수익률 좋은 ETF 5개는?
Intent: data_query
SQL: WITH period_rows AS (
         SELECT ticker,
                price_date,
                FIRST_VALUE(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                ) AS first_price,
                LAST_VALUE(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                ) AS last_price
         FROM public_marts.mart_etf_returns
         WHERE price_date >= DATE_TRUNC('year', CURRENT_DATE)
     )
     SELECT ticker,
            MIN(price_date) AS period_start,
            MAX(price_date) AS period_end,
            COUNT(*) AS price_observations,
            COUNT(*) - 1 AS return_observations,
            MAX(last_price / first_price - 1) AS ytd_return
     FROM period_rows
     GROUP BY ticker
     ORDER BY ytd_return DESC
     LIMIT 5

Example 4
Q: 가장 수익률 높은 ETF 3개 보여줘
Intent: data_query
SQL: WITH period_rows AS (
         SELECT ticker,
                price_date,
                FIRST_VALUE(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                ) AS first_price,
                LAST_VALUE(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                ) AS last_price
         FROM public_marts.mart_etf_returns
         WHERE price_date >= CURRENT_DATE - INTERVAL '{DEFAULT_RETURN_LOOKBACK}'
     )
     SELECT ticker,
            MIN(price_date) AS period_start,
            MAX(price_date) AS period_end,
            COUNT(*) AS price_observations,
            COUNT(*) - 1 AS return_observations,
            MAX(last_price / first_price - 1) AS cumulative_return
     FROM period_rows
     GROUP BY ticker
     HAVING COUNT(*) - 1 >= {MIN_DEFAULT_RETURN_OBSERVATIONS}
     ORDER BY cumulative_return DESC
     LIMIT 3

Example 5
Q: 레버리지 배수와 연환산 변동성의 상관관계는?
Intent: data_query
SQL: WITH period_prices AS (
         SELECT p.ticker, p.price_date, p.adj_close,
                d.leverage::double precision AS leverage
         FROM public_marts.mart_etf_returns AS p
         JOIN public_marts.dim_etf AS d ON p.ticker = d.ticker
         WHERE p.price_date >= CURRENT_DATE - INTERVAL '{DEFAULT_RELATIONSHIP_LOOKBACK}'
     ),
     period_rows AS (
         SELECT *,
                adj_close / LAG(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                ) - 1 AS period_daily_return
         FROM period_prices
     ),
     per_etf AS (
         SELECT ticker,
                leverage,
                STDDEV_SAMP(period_daily_return) * SQRT(252)
                    AS period_annualized_volatility,
                MIN(price_date) AS period_start,
                MAX(price_date) AS period_end,
                COUNT(*) AS price_observations,
                COUNT(period_daily_return) AS return_observations
         FROM period_rows
         GROUP BY ticker, leverage
         HAVING COUNT(period_daily_return) >= {MIN_RELATIONSHIP_OBSERVATIONS}
     )
     SELECT *,
            'the current ETF warehouse universe including leveraged funds'
                AS universe_scope,
            CORR(leverage, period_annualized_volatility) OVER () AS correlation
     FROM per_etf
     ORDER BY leverage, ticker

Example 6
Q: 거래량과 변동성 사이에 관계가 있나?
Intent: data_query
SQL: WITH period_prices AS (
         SELECT p.ticker, p.price_date, p.adj_close, p.volume
         FROM public_marts.mart_etf_returns AS p
         JOIN public_marts.dim_etf AS d ON p.ticker = d.ticker
         WHERE p.price_date >= CURRENT_DATE - INTERVAL '{DEFAULT_RELATIONSHIP_LOOKBACK}'
           AND d.leverage = 1
           AND p.volume IS NOT NULL
     ),
     period_rows AS (
         SELECT *,
                adj_close / LAG(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                ) - 1 AS period_daily_return
         FROM period_prices
     ),
     per_etf AS (
         SELECT ticker,
                AVG(p.volume * p.adj_close)::double precision AS avg_daily_dollar_volume,
                STDDEV_SAMP(period_daily_return) * SQRT(252)
                    AS period_annualized_volatility,
                MIN(price_date) AS period_start,
                MAX(price_date) AS period_end,
                COUNT(*) AS price_observations,
                COUNT(period_daily_return) AS return_observations
         FROM period_rows AS p
         GROUP BY ticker
         HAVING COUNT(period_daily_return) >= {MIN_RELATIONSHIP_OBSERVATIONS}
     )
     SELECT *,
            'the current unleveraged ETF subset (leverage = 1)' AS universe_scope,
            CORR(LN(NULLIF(avg_daily_dollar_volume, 0)),
                 period_annualized_volatility) OVER () AS correlation
     FROM per_etf
     ORDER BY avg_daily_dollar_volume, ticker

Example 7
Q: How do return performance and volatility move together across ETFs?
Intent: data_query
SQL: WITH period_prices AS (
         SELECT p.ticker, p.price_date, p.adj_close
         FROM public_marts.mart_etf_returns AS p
         JOIN public_marts.dim_etf AS d ON p.ticker = d.ticker
         WHERE p.price_date >= CURRENT_DATE - INTERVAL '{DEFAULT_RELATIONSHIP_LOOKBACK}'
           AND d.leverage = 1
     ),
     period_rows AS (
         SELECT *,
                FIRST_VALUE(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                ) AS first_price,
                LAST_VALUE(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                ) AS last_price,
                adj_close / LAG(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                ) - 1 AS period_daily_return
         FROM period_prices
     ),
     per_etf AS (
         SELECT ticker,
                MAX(last_price / first_price - 1) AS cumulative_return,
                STDDEV_SAMP(period_daily_return) * SQRT(252)
                    AS period_annualized_volatility,
                MIN(price_date) AS period_start,
                MAX(price_date) AS period_end,
                COUNT(*) AS price_observations,
                COUNT(period_daily_return) AS return_observations
         FROM period_rows
         GROUP BY ticker
         HAVING COUNT(period_daily_return) >= {MIN_RELATIONSHIP_OBSERVATIONS}
     )
     SELECT *,
            'the current unleveraged ETF subset (leverage = 1)' AS universe_scope,
            CORR(cumulative_return, period_annualized_volatility) OVER () AS correlation
     FROM per_etf
     ORDER BY cumulative_return DESC

Example 8
Q: Over the past 10 years, have ETFs with higher average trading volume
   generally had higher annualized volatility?
Intent: data_query
SQL: WITH period_prices AS (
         SELECT p.ticker, p.price_date, p.adj_close, p.volume
         FROM public_marts.mart_etf_returns AS p
         JOIN public_marts.dim_etf AS d ON p.ticker = d.ticker
         WHERE p.price_date >= CURRENT_DATE - INTERVAL '10 years'
           AND d.leverage = 1
           AND p.volume IS NOT NULL
     ),
     period_rows AS (
         SELECT *,
                adj_close / LAG(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                ) - 1 AS period_daily_return
         FROM period_prices
     ),
     per_etf AS (
         SELECT ticker,
                AVG(p.volume * p.adj_close)::double precision AS avg_daily_dollar_volume,
                STDDEV_SAMP(period_daily_return) * SQRT(252)
                    AS period_annualized_volatility,
                MIN(price_date) AS period_start,
                MAX(price_date) AS period_end,
                COUNT(*) AS price_observations,
                COUNT(period_daily_return) AS return_observations
         FROM period_rows AS p
         GROUP BY ticker
         HAVING COUNT(period_daily_return) >= 2000
     )
     SELECT *,
            'the current unleveraged ETF subset (leverage = 1)' AS universe_scope,
            CORR(LN(NULLIF(avg_daily_dollar_volume, 0)),
                 period_annualized_volatility) OVER () AS correlation
     FROM per_etf
     ORDER BY avg_daily_dollar_volume, ticker

Example 9
Q: Among unleveraged ETFs, what is the relationship between 10-year CAGR
   and annualized volatility?
Intent: data_query
SQL: WITH period_prices AS (
         SELECT p.ticker, p.price_date, p.adj_close
         FROM public_marts.mart_etf_returns AS p
         JOIN public_marts.dim_etf AS d ON p.ticker = d.ticker
         WHERE p.price_date >= CURRENT_DATE - INTERVAL '10 years'
           AND d.leverage = 1
     ),
     period_rows AS (
         SELECT *,
                FIRST_VALUE(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                ) AS first_price,
                LAST_VALUE(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                ) AS last_price,
                adj_close / LAG(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                ) - 1 AS period_daily_return
         FROM period_prices
     ),
     per_etf AS (
         SELECT ticker,
                POWER(
                    MAX(last_price / first_price),
                    365.25 / NULLIF(MAX(price_date) - MIN(price_date), 0)
                ) - 1
                    AS cagr,
                STDDEV_SAMP(period_daily_return) * SQRT(252)
                    AS period_annualized_volatility,
                MIN(price_date) AS period_start,
                MAX(price_date) AS period_end,
                COUNT(*) AS price_observations,
                COUNT(period_daily_return) AS return_observations
         FROM period_rows
         GROUP BY ticker
         HAVING COUNT(period_daily_return) >= 2000
     )
     SELECT *,
            'the current unleveraged ETF subset (leverage = 1)' AS universe_scope,
            CORR(cagr, period_annualized_volatility) OVER () AS correlation
     FROM per_etf
     ORDER BY cagr DESC, ticker

Example 10
Q: 지난 1년 SPY 최대 낙폭은?
Intent: data_query
SQL: WITH period_prices AS (
         SELECT ticker, price_date, adj_close
         FROM public_marts.mart_etf_returns
         WHERE ticker = 'SPY'
           AND price_date >= CURRENT_DATE - INTERVAL '1 year'
     ),
     period_rows AS (
         SELECT *,
                MAX(adj_close) OVER (
                    PARTITION BY ticker ORDER BY price_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS period_peak
         FROM period_prices
     )
     SELECT ticker,
            MIN(price_date) AS period_start,
            MAX(price_date) AS period_end,
            COUNT(*) AS price_observations,
            COUNT(*) - 1 AS return_observations,
            MIN(adj_close / period_peak - 1) AS period_max_drawdown
     FROM period_rows
     GROUP BY ticker

Example 11
Q: 양의 상관관계가 뭐야?
Intent: concept_question
SQL: ""
Explanation: 양의 상관관계는 두 값이 대체로 같은 방향으로 움직이는 관계입니다.
             한 값이 높을 때 다른 값도 높은 경향이 있지만, 이것만으로 한 값이
             다른 값의 원인이라고 판단할 수는 없습니다.

Example 12
Q: Why do bond prices generally fall when interest rates rise?
Intent: concept_question
SQL: ""
Explanation: Existing bonds become less attractive when new bonds offer higher
             interest payments, so their market prices generally fall to compete.
             Longer-term bonds are usually more sensitive, but not every bond ETF
             moves by the same amount.

Example 13
Q: TQQQ 지금 사도 돼?
Intent: out_of_scope
SQL: ""
Explanation: 특정 ETF의 매수 여부를 정하는 개인 투자 조언은 제공하지 않습니다.
"""

SQL_SYSTEM_PROMPT = f"""
You route ETF questions and, when supported, translate them into one PostgreSQL
SELECT statement over the tables below. Fill every SqlAnswer field. Rules:

- intent="concept_question" for stable, general educational questions about
  ETF, investing, finance, or basic economics that do not require current facts
  or warehouse data. Examples include definitions, how a metric works, or why
  bond prices generally respond to interest rates. Set sql="". Write a concise,
  beginner-friendly answer in the user's language: explain the idea first, add
  one concrete example, and mention an important limitation when useful. Do not
  give personal advice, a forecast, or pretend that a general relationship
  explains a specific historical event.
- intent="data_query" for descriptive lookups, aggregations, rankings,
  comparisons, time series, and relationship/correlation analysis over the
  documented warehouse. A ticker does NOT need to be named: analysis across
  the ETF universe is supported and is not "theoretical".
- intent="out_of_scope" for predictions, personal investment advice, current
  facts outside the documented data, explanations of a specific historical
  move's cause, path-dependent simulations/backtests, legal or tax advice, or
  requested data fields absent from the documented schema. General educational
  "why" questions belong to concept_question, not out_of_scope. For a refusal,
  set sql="" and give the exact reason in the user's language.
- For data_query, set sql to exactly ONE SELECT statement (WITH ... SELECT is
  allowed). No semicolons, comments, DDL, or writes.

- Always use fully qualified table names ({SCHEMA_NAME}.table_name).
- In a join, qualify every source column with the alias of the table that
  actually owns that column. Never copy a metric onto another table alias.
- Relative dates from CURRENT_DATE (e.g. INTERVAL '1 year', DATE_TRUNC('year', ...)).
- The documented marts contain up to {MAX_HISTORICAL_LOOKBACK_YEARS} years of
  history. An explicit historical period such as "over the past 10 years",
  "last 5 years", or "지난 10년" overrides every 1-year default and is in scope.
  Never claim that the dataset only supports one year. For an explicit N-year
  comparison, require at least N × {MIN_OBSERVATIONS_PER_YEAR} paired observations
  per ticker (for example, 2,000 for 10 years).
- In this analytics UI, an otherwise descriptive "in N years" means a trailing
  historical N-year window. If the question adds an explicit future cue such as
  "will", "from now", "future", "앞으로", or "N년 후", it is a prediction and
  must be refused for that reason. Never claim the warehouse has only one year.
- Map plain-language groups (e.g. "미국 장기채", "leveraged") to dim_etf
  asset_class / sub_class values from the universe list.
- Return at most {MAX_ROWS} rows; prefer ORDER BY that makes the table readable.
- The Metric Contract in the database-schema section is authoritative. For an
  aggregated requested-period metric, filter adjusted prices first and only
  then calculate LAG returns and the running period peak. Never average a
  rolling-volatility column to represent period volatility, and never take
  MIN(drawdown) from the risk mart to represent period maximum drawdown.
- If a return/performance ranking omits a period, use the trailing
  {DEFAULT_RETURN_LOOKBACK}; this is a DEFAULT LOOKBACK, not a ban on explicit
  shorter periods such as today, MTD or 3 months.
- For that default trailing-{DEFAULT_RETURN_LOOKBACK} ranking, return ticker,
  period_start, period_end, price_observations, return_observations, and
  last in-window adjusted price / first in-window adjusted price - 1. Require
  at least {MIN_DEFAULT_RETURN_OBSERVATIONS} in-window returns so ETFs with
  incomplete history are not ranked against full-period observations.
- rolling_vol_30d and annualized_vol_30d are only for an as-of snapshot or a
  rolling time series. A requested-period volatility is
  STDDEV_SAMP(period_daily_return) * SQRT(252), where period_daily_return is
  recomputed after filtering adjusted prices to the requested dates.
- For liquidity comparisons across ETFs, plain "volume" / "거래량" means daily
  dollar volume (`volume * adj_close`), not share count, because ETF share prices
  differ. Return `AVG(volume * adj_close)::double precision AS
  avg_daily_dollar_volume`. Use `LN(NULLIF(avg_daily_dollar_volume, 0))` inside
  CORR to reduce scale skew while returning the raw dollar value for display.
  Only use share volume when the user explicitly asks for shares/contracts.
- For performance windows of 2 years or longer, or when the user asks for an
  annualized long-term return, use CAGR rather than raw cumulative return:
  `POWER(last_in_window_price / first_in_window_price,
   365.25 / NULLIF(period_end - period_start, 0)) - 1 AS cagr`.
  Keep cumulative_return for sub-2-year windows or when explicitly requested.
- If a relationship/correlation question omits a period, use the trailing
  {DEFAULT_RELATIONSHIP_LOOKBACK}. Build one comparable row per ticker with
  both requested numeric measures, period_start, period_end,
  price_observations and return_observations;
  require at least {MIN_RELATIONSHIP_OBSERVATIONS} paired observations.
  Include the Pearson coefficient as `correlation` using CORR(...) OVER () so
  the same result supports a scatter plot and an exact numeric answer.
- For a generic cross-ETF relationship, join dim_etf and default to
  `leverage = 1` so QLD/TQQQ do not dominate an ordinary return-risk or
  liquidity-risk relationship. Do not apply that filter when leverage itself
  is a requested metric, when the user asks specifically about leveraged ETFs,
  or when the user explicitly says to include leveraged funds/all ETFs.
- Every relationship result must return a string `universe_scope` column:
  `the current unleveraged ETF subset (leverage = 1)` for the default filter,
  or `the current ETF warehouse universe including leveraged funds` when all
  leverage levels are intentionally included. This scope is part of the answer.
- Cross-ETF relationship questions are descriptive data queries. Do not reject
  them merely because no specific ticker is named.
- Write `explanation` in the same language as the user's question (Korean or
  English). State the applied period explicitly and use plain language before
  technical terms.

Database schema:
{build_schema_prompt()}

{FEW_SHOTS}
"""

SQL_REPAIR_SYSTEM_PROMPT = f"""
{SQL_SYSTEM_PROMPT}

Correction task: the first SQL attempt was read-only but failed documented
column validation. Return intent="data_query" and a corrected SQL statement
for the original question. Fix table aliases or column references using only
the documented schema. Do not broaden the question, invent columns, or reuse
the rejected reference. The corrected SQL will pass through the full safety
guard again before execution.
"""


RATE_LIMIT_WAITS = (2, 5)  # keep interactive requests bounded before model failover
RATE_LIMIT_MAX_SERVER_WAIT = 5.0
UNAVAILABLE_WAITS = (1, 2, 4)  # 503 capacity errors: retry briefly, then fail over
RETRY_JITTER_SECONDS = 1.0
DEADLINE_STATUS_CODES = {408, 504}
TRANSIENT_SERVICE_STATUS_CODES = {500, 502, 503}


class DailyQuotaError(RuntimeError):
    """Daily quota exhausted — waiting won't help, stop immediately."""


class ProviderUnavailableError(RuntimeError):
    """Every configured model stayed unavailable after bounded retries."""


class WarehouseSchemaError(RuntimeError):
    """The deployed database marts lag behind the application schema."""


class DataUnavailableError(RuntimeError):
    """The question needs warehouse data, but only concept answers are available."""


def _sleep_with_jitter(base_delay: float) -> float:
    """Sleep with small jitter so concurrent clients do not retry in lockstep."""
    delay = base_delay + random.uniform(0, RETRY_JITTER_SECONDS)
    time.sleep(delay)
    return delay


def _api_status_code(exc: Exception) -> int | None:
    """Return a Gemini HTTP status without relying only on error prose.

    Tests and some proxy layers may wrap the SDK exception, so retain a
    conservative message fallback for statuses handled below.
    """
    if isinstance(exc, genai_errors.APIError):
        return exc.code
    msg = str(exc)
    upper_msg = msg.upper()
    status_names = {
        408: "REQUEST_TIMEOUT",
        429: "RESOURCE_EXHAUSTED",
        500: "INTERNAL",
        502: "BAD_GATEWAY",
        503: "UNAVAILABLE",
        504: "DEADLINE_EXCEEDED",
    }
    for code, status_name in status_names.items():
        if re.search(rf"(?:^|\D){code}(?:\D|$)", msg) and status_name in upper_msg:
            return code
    return None


def _is_timeout(exc: Exception) -> bool:
    """Recognize SDK/network timeouts without matching unrelated error text."""
    return isinstance(exc, (TimeoutException, TimeoutError))


def _with_backoff(fn, *args):
    """Call an LLM function with bounded retry and model failover.

    - Per-minute 429: wait briefly, then fail over instead of blocking the UI.
    - Daily quota: switch model immediately; waiting cannot help.
    - Transient 5xx: make a few short, jittered retries, then switch model.
    - Network timeout/504: the request already waited 20s, so fail over immediately.

    The model pointer is intentionally retained after a failover: a provider
    that is unavailable now is unlikely to recover during the same Streamlit
    session, and repeatedly returning to it would make every question slow.
    """
    rate_attempt = 0
    unavailable_attempt = 0
    while True:
        try:
            return fn(*args)
        except Exception as e:  # noqa: BLE001 — 429s are identified by message
            msg = str(e)
            status_code = _api_status_code(e)
            if "PerDay" in msg or "per day" in msg.lower():
                if _advance_model():
                    rate_attempt = unavailable_attempt = 0
                    continue  # retry immediately on the next model (quotas are per model)
                raise DailyQuotaError(
                    "daily free-tier quota exhausted for all models"
                ) from e

            if _is_timeout(e) or status_code in DEADLINE_STATUS_CODES:
                if _advance_model():
                    rate_attempt = unavailable_attempt = 0
                    continue
                raise ProviderUnavailableError(
                    "all configured LLM models timed out"
                ) from e

            if status_code in TRANSIENT_SERVICE_STATUS_CODES:
                if unavailable_attempt < len(UNAVAILABLE_WAITS):
                    delay = _sleep_with_jitter(UNAVAILABLE_WAITS[unavailable_attempt])
                    unavailable_attempt += 1
                    print(
                        f"   (model unavailable — waiting {delay:.1f}s, "
                        f"retry {unavailable_attempt}/{len(UNAVAILABLE_WAITS)})"
                    )
                    continue
                if _advance_model():
                    rate_attempt = unavailable_attempt = 0
                    continue
                raise ProviderUnavailableError(
                    "all configured LLM models are temporarily unavailable"
                ) from e

            if status_code != 429:
                raise
            if rate_attempt >= len(RATE_LIMIT_WAITS):
                if _advance_model():
                    rate_attempt = unavailable_attempt = 0
                    continue
                raise ProviderUnavailableError(
                    "all configured LLM models are temporarily rate-limited"
                ) from e
            m = re.search(r"retry(?:Delay)?\D*(\d+(?:\.\d+)?)\s*s", msg, re.IGNORECASE)
            suggested_delay = (
                float(m.group(1)) + 1 if m else RATE_LIMIT_WAITS[rate_attempt]
            )
            base_delay = min(suggested_delay, RATE_LIMIT_MAX_SERVER_WAIT)
            delay = _sleep_with_jitter(base_delay)
            rate_attempt += 1
            print(
                f"   (429 rate limit — waiting {delay:.1f}s, retry {rate_attempt}/{len(RATE_LIMIT_WAITS)})"
            )


def _structured_call(
    system: str, contents: str, schema: type[BaseModel], _retry: bool = True
):
    """Shared structured-output call — also handles parsed=None (empty/truncated)."""
    with new_client() as client:
        response = client.models.generate_content(
            model=current_model(),
            contents=contents,
            config={
                "system_instruction": system,
                "response_mime_type": "application/json",
                "response_schema": schema,
            },
        )
    if response.parsed is None:
        # Structured output is not a guarantee — on schema mismatch or a
        # truncated response, .parsed is silently None. Retry once, then
        # promote to a clear error.
        if _retry:
            time.sleep(2)
            return _structured_call(system, contents, schema, _retry=False)
        raw = (getattr(response, "text", "") or "")[:200]
        raise ValueError(
            f"LLM did not return valid {schema.__name__} JSON (raw: {raw!r})"
        )
    return response.parsed


def generate_sql(question: str) -> SqlAnswer:
    return _structured_call(
        SQL_SYSTEM_PROMPT,
        _question_with_period_context(question),
        SqlAnswer,
    )


def repair_sql(question: str, failed_sql: str, validation_error: str) -> SqlAnswer:
    contents = (
        f"Original question:\n{question}\n\n"
        f"Rejected SQL:\n{failed_sql}\n\n"
        f"Validator feedback:\n{validation_error}"
    )
    return _structured_call(SQL_REPAIR_SYSTEM_PROMPT, contents, SqlAnswer)


def sslmode_for(host: str) -> str:
    """Managed Postgres (Neon/Supabase) requires SSL; local Docker has none.
    Default to 'require' unless the host is local — override with POSTGRES_SSLMODE."""
    local = host in ("localhost", "127.0.0.1", "", "postgres")
    return os.getenv("POSTGRES_SSLMODE", "prefer" if local else "require")


def _reader_engine():
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL

    host = os.getenv("POSTGRES_HOST", "localhost")
    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("QA_DB_USER", "etf_reader"),
        password=os.getenv("QA_DB_PASSWORD", "etf_reader"),
        host=host,
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "etf_analytics"),
    )
    return create_engine(
        url, connect_args={"connect_timeout": 3, "sslmode": sslmode_for(host)}
    )


def reader_ping() -> tuple[bool, str]:
    """Verify the read-only role can actually connect — surfaces a password
    mismatch between init_db.sql and QA_DB_PASSWORD early and clearly."""
    try:
        with _reader_engine().connect() as conn:
            conn.exec_driver_sql("select 1")
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, str(e).splitlines()[0]


def run_readonly(sql: str) -> pd.DataFrame:
    """Execute validated SQL with database-enforced read-only safeguards."""

    # Keep settings transaction-local for pooled connections. READ ONLY must be
    # the first SQL command in this transaction; PostgreSQL will reject it after
    # a query has already run.
    with _reader_engine().begin() as conn:
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        conn.exec_driver_sql(f"SET LOCAL search_path = {SAFE_SEARCH_PATH}")
        conn.exec_driver_sql(
            f"SET LOCAL statement_timeout = {int(STATEMENT_TIMEOUT_MS)}"
        )
        return pd.read_sql(sql, conn)


def _postgres_error_code(exc: Exception) -> str:
    """Extract a PostgreSQL SQLSTATE from SQLAlchemy/psycopg wrappers."""
    for candidate in (exc, getattr(exc, "orig", None), getattr(exc, "__cause__", None)):
        if candidate is None:
            continue
        if code := getattr(candidate, "pgcode", None) or getattr(
            candidate, "sqlstate", None
        ):
            return str(code)
    return ""


@dataclass
class AskResult:
    """Structured result of one pipeline run — shared by the CLI, UI and test runner."""

    question: str
    status: str  # explained | answered | refused_gate | refused_guard | error
    reason: str = ""  # refusal / error reason
    sql: str = ""  # raw SQL as generated by the LLM
    safe_sql: str = ""  # SQL actually executed, after passing the guard
    explanation: str = ""
    model: str = ""  # which model produced this answer (fallback-chain tracking)
    error_kind: str = (
        ""  # provider_unavailable | data_unavailable | warehouse_schema | other
    )
    df: pd.DataFrame | None = field(default=None, repr=False)

    @property
    def n_rows(self) -> int | None:
        return None if self.df is None else len(self.df)

    @property
    def truncated(self) -> bool:
        """Result hit the guard's row cap — likely cut short, so warn the user."""
        return self.df is not None and len(self.df) >= MAX_ROWS


def answer(question: str, *, execute_data: bool = True) -> AskResult:
    """Run one question through the whole pipeline; return a structured result.

    ``execute_data=False`` still allows Gemini concept explanations and safe
    refusals, but prevents a data query when the warehouse is unavailable.
    Never raises (except DailyQuotaError) — the automated runner needs
    failures to be data, not crashes.
    """
    try:
        generated = _with_backoff(generate_sql, question)
        if generated.intent == "concept_question":
            return AskResult(
                question,
                "explained",
                explanation=generated.explanation,
                model=current_model(),
            )
        if generated.intent == "out_of_scope":
            return AskResult(
                question,
                "refused_gate",
                reason=generated.explanation,
                model=current_model(),
            )
        if not execute_data:
            return AskResult(
                question,
                "error",
                reason="Historical data is currently unavailable.",
                sql=generated.sql,
                model=current_model(),
                error_kind="data_unavailable",
            )
        try:
            safe_sql = validate(generated.sql)
        except SchemaGuardError as first_error:
            repaired = _with_backoff(
                repair_sql,
                question,
                generated.sql,
                str(first_error),
            )
            if repaired.intent != "data_query":
                return AskResult(
                    question,
                    "refused_guard",
                    reason="Generated SQL could not be matched to the documented columns.",
                    sql=generated.sql,
                    model=current_model(),
                )
            generated = repaired
            try:
                safe_sql = validate(generated.sql)
            except GuardError as second_error:
                return AskResult(
                    question,
                    "refused_guard",
                    reason=f"Corrected SQL still failed validation: {second_error}",
                    sql=generated.sql,
                    model=current_model(),
                )
        except GuardError as e:
            return AskResult(
                question,
                "refused_guard",
                reason=str(e),
                sql=generated.sql,
                model=current_model(),
            )

        try:
            df = run_readonly(safe_sql)
        except Exception as e:  # noqa: BLE001 — distinguish deploy drift from query failures
            if _postgres_error_code(e) in {"42703", "42P01"}:
                return AskResult(
                    question,
                    "error",
                    reason=(
                        "The app's data tables need to be updated. "
                        "Refresh the cloud data, then try the question again."
                    ),
                    sql=generated.sql,
                    safe_sql=safe_sql,
                    model=current_model(),
                    error_kind="warehouse_schema",
                )
            raise
        explanation = generated.explanation
        if summary := correlation_summary(df, question):
            explanation = summary
        return AskResult(
            question,
            "answered",
            sql=generated.sql,
            safe_sql=safe_sql,
            explanation=explanation,
            df=df,
            model=current_model(),
        )
    except DailyQuotaError:
        raise  # waiting won't help — propagate so the runner can stop and explain how to resume
    except ProviderUnavailableError:
        return AskResult(
            question,
            "error",
            reason="The LLM provider is temporarily unavailable. Please try again in a few minutes.",
            model=current_model(),
            error_kind="provider_unavailable",
        )
    except Exception as e:  # noqa: BLE001 — API/DB failures are data too
        return AskResult(question, "error", reason=f"{type(e).__name__}: {e}")


def ask(question: str) -> pd.DataFrame | None:
    """CLI wrapper — print answer() in a human-readable form."""
    r = answer(question)
    if r.status == "explained":
        print(f"💡 {r.explanation}")
    elif r.status == "refused_gate":
        print(f"⛔ I can't answer that — {r.reason}")
        print(
            "   I can answer lookups, comparisons and rankings over prices, returns, volatility and drawdown."
        )
    elif r.status == "refused_guard":
        print(f"⛔ Generated SQL rejected by the safety guard: {r.reason}")
        print(f"   (rejected SQL: {r.sql})")
    elif r.status == "error":
        print(f"💥 Failed: {r.reason}")
    else:
        print(f"💬 {r.explanation}")
        print(f"🔍 SQL: {r.safe_sql}\n")
        if r.df is None or r.df.empty:
            print("(0 rows — no data matches the filters)")
        else:
            print(r.df.to_string(index=False))
            if r.truncated:
                print(
                    f"\n⚠️  Capped at {MAX_ROWS} rows — the result may be cut short. "
                    "Narrow the tickers or date range for the full series."
                )
    return r.df


def ask_with_chart(question: str) -> None:
    """Question → table → saved chart, in one go (Week 3 deliverable)."""
    df = ask(question)
    if df is None or df.empty:
        return
    from chart_spec import TABLE_FALLBACK_REASONS, auto_chart_spec, validate_spec
    from render import render, save_html

    spec = validate_spec(auto_chart_spec(question, df), df)
    fig = render(spec, df)
    if fig is None:
        reason = TABLE_FALLBACK_REASONS.get(
            "last", "the automatic selector chose a table"
        )
        print(f"\n📊 Table instead of a chart ({reason})")
        return
    path = save_html(fig, "ask")
    print(f"\n📊 Saved {spec.chart_type} chart: {path} (open in a browser)")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(
        description="Natural-language question → table (+ chart with --chart)"
    )
    p.add_argument("question", nargs="+", help="question in English or Korean")
    p.add_argument(
        "--chart", action="store_true", help="also save an automatically selected chart"
    )
    args = p.parse_args()
    q = " ".join(args.question)
    ask_with_chart(q) if args.chart else ask(q)
