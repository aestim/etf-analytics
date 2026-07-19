"""
Week 2 ③: 질문 → 표. 전체 파이프라인 조립.

    python qa/ask.py "지난 1년 TLT 변동성 어땠어?"

흐름:  문지기(Week 1) → SQL 생성(structured output) → 가드(sql_guard)
       → etf_reader로 실행(타임아웃) → DataFrame 출력

대원칙: LLM은 양식(JSON)만 채운다. 실행은 검사를 거친 이 코드가 한다.
"""

from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

from practice_structured import classify  # Week 1 문지기를 1단계 부품으로 재사용
from schema_prompt import SCHEMA_NAME, build_schema_prompt
from sql_guard import MAX_ROWS, GuardError, validate

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# 무료 한도는 모델별로 따로 계산됨 → 일일 한도(PerDay) 감지 시 체인의
# 다음 모델로 자동 전환한다 (flash 품질 우선, 소진되면 lite로 이어가기).
# GEMINI_MODEL을 지정하면 그 모델을 체인 맨 앞에 둔다.
_DEFAULT_CHAIN = "gemini-flash-latest,gemini-flash-lite-latest"
MODEL_CHAIN = [m.strip() for m in os.getenv("GEMINI_MODEL_CHAIN", _DEFAULT_CHAIN).split(",") if m.strip()]
if _override := os.getenv("GEMINI_MODEL"):
    MODEL_CHAIN = [_override] + [m for m in MODEL_CHAIN if m != _override]

_model_idx = 0


def current_model() -> str:
    return MODEL_CHAIN[_model_idx]


def _advance_model() -> bool:
    """일일 한도 소진 시 다음 모델로 전환. 더 없으면 False."""
    global _model_idx
    if _model_idx + 1 < len(MODEL_CHAIN):
        _model_idx += 1
        print(f"   (daily quota → switching model: {MODEL_CHAIN[_model_idx - 1]} → {current_model()})")
        return True
    return False

STATEMENT_TIMEOUT_MS = 5000  # 3층 방어: 폭주 쿼리 강제 종료


class SqlAnswer(BaseModel):
    sql: str
    explanation: str  # 이 SQL이 질문을 어떻게 푸는지 한두 문장 (사용자에게 표시)


# few-shot: "질문 → 정답 SQL" 모범 예시. 스타일(스키마 경로, 날짜 처리,
# 집계 요령)을 가르치는 게 목적이라 2~3개면 충분하다.
FEW_SHOTS = """
Example 1
Q: 지난 1년 TLT 변동성 어땠어?
SQL: SELECT price_date, rolling_vol_30d
     FROM public_marts.mart_etf_risk_metrics
     WHERE ticker = 'TLT' AND price_date >= CURRENT_DATE - INTERVAL '1 year'
     ORDER BY price_date

Example 2
Q: Which long-term treasury ETF had the lowest volatility this year?
SQL: SELECT r.ticker, AVG(r.rolling_vol_30d) AS avg_daily_vol
     FROM public_marts.mart_etf_risk_metrics AS r
     JOIN public_marts.dim_etf AS d ON r.ticker = d.ticker
     WHERE d.sub_class = 'treasury_long'
       AND r.price_date >= DATE_TRUNC('year', CURRENT_DATE)
     GROUP BY r.ticker
     ORDER BY avg_daily_vol ASC

Example 3
Q: 올해 수익률 좋은 ETF 5개는?
SQL: SELECT ticker, EXP(SUM(LN(1 + daily_return))) - 1 AS ytd_return
     FROM public_marts.mart_etf_returns
     WHERE price_date >= DATE_TRUNC('year', CURRENT_DATE)
       AND daily_return IS NOT NULL
     GROUP BY ticker
     ORDER BY ytd_return DESC
     LIMIT 5
"""

SQL_SYSTEM_PROMPT = f"""
You translate analytics questions (Korean or English) into a single PostgreSQL
SELECT statement over the tables below. Rules:

- Exactly ONE SELECT statement. No semicolons, comments, DDL, or writes.
- Always use fully qualified table names ({SCHEMA_NAME}.table_name).
- Relative dates from CURRENT_DATE (e.g. INTERVAL '1 year', DATE_TRUNC('year', ...)).
- Map plain-language groups (e.g. "미국 장기채", "leveraged") to dim_etf
  asset_class / sub_class values from the universe list.
- Return at most {MAX_ROWS} rows; prefer ORDER BY that makes the table readable.
- rolling_vol_30d is DAILY volatility (not annualized) — mention in explanation
  if the question says "연" or "annual".
- Write `explanation` in English regardless of the question's language
  (the UI is English-only).

Database schema:
{build_schema_prompt()}

{FEW_SHOTS}
"""


RETRY_WAITS = (20, 45, 90)  # 429(분당 한도) 지수 백오프 — 기다리면 풀린다


class DailyQuotaError(RuntimeError):
    """일일 한도 소진 — 기다려도 안 풀리므로 즉시 중단해야 한다."""


def _with_backoff(fn, *args):
    """Gemini 무료 한도(429) 대응 래퍼.

    - 분당 한도: 서버가 제안한 retryDelay(있으면)만큼 기다렸다 재시도
    - 일일 한도(PerDay): 재시도가 무의미 → DailyQuotaError로 즉시 전파
    """
    for attempt, wait in enumerate((*RETRY_WAITS, None)):
        try:
            return fn(*args)
        except Exception as e:  # noqa: BLE001 — 메시지로 429 여부 판별
            msg = str(e)
            if "PerDay" in msg or "per day" in msg.lower():
                if _advance_model():
                    continue  # 다음 모델로 즉시 재시도 (한도는 모델별로 별도)
                raise DailyQuotaError("daily free-tier quota exhausted for all models") from e
            if wait is None or not ("429" in msg or "RESOURCE_EXHAUSTED" in msg):
                raise
            m = re.search(r"retry(?:Delay)?\D*(\d+(?:\.\d+)?)\s*s", msg, re.IGNORECASE)
            delay = float(m.group(1)) + 1 if m else wait
            print(f"   (429 rate limit — waiting {delay:.0f}s, retry {attempt + 1}/{len(RETRY_WAITS)})")
            time.sleep(delay)


def _structured_call(system: str, contents: str, schema: type[BaseModel], _retry: bool = True):
    """structured output 호출 공통부 — parsed=None(빈/잘린 응답)도 처리."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
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
        # structured output도 보장이 아니다 — 스키마 불일치·잘린 응답이면
        # parsed가 조용히 None이 된다. 한 번 재시도 후 명확한 에러로 승격.
        if _retry:
            time.sleep(2)
            return _structured_call(system, contents, schema, _retry=False)
        raw = (getattr(response, "text", "") or "")[:200]
        raise ValueError(f"LLM did not return valid {schema.__name__} JSON (raw: {raw!r})")
    return response.parsed


def generate_sql(question: str) -> SqlAnswer:
    return _structured_call(SQL_SYSTEM_PROMPT, question, SqlAnswer)


CHART_SYSTEM_PROMPT = """
You pick a chart for the result table of a data question. Fill ChartSpec only.
- chart_type: "line" (time series), "bar" (category comparison/ranking),
  "scatter" (relation of two numeric columns), "table" (lists, single values, else)
- x / y must be existing column names; y must be numeric.
- group_by: column to color by (e.g. ticker) when several series share the chart, else null.
- title: short, in English (the UI is English-only).
"""


def generate_chart_spec(question: str, df: pd.DataFrame):
    """Week 3: 결과 표를 보고 차트 양식을 채우게 한다 (LLM은 코드 금지, 양식만)."""
    from chart_spec import ChartSpec  # 지연 임포트 — 러너는 차트 없이도 돌게

    contents = (
        f"Question: {question}\n"
        f"Columns and dtypes:\n{df.dtypes.to_string()}\n"
        f"First rows:\n{df.head(5).to_string(index=False)}"
    )
    return _structured_call(CHART_SYSTEM_PROMPT, contents, ChartSpec)


def run_readonly(sql: str) -> pd.DataFrame:
    """2층+3층 방어: 읽기 전용 계정 + statement_timeout."""
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL

    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("QA_DB_USER", "etf_reader"),
        password=os.getenv("QA_DB_PASSWORD", "etf_reader"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "etf_analytics"),
    )
    engine = create_engine(
        url,
        connect_args={
            "connect_timeout": 3,
            "options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS}",
        },
    )
    return pd.read_sql(sql, engine)


@dataclass
class AskResult:
    """파이프라인 한 번의 구조화된 결과 — CLI와 자동 러너(run_week2.py)가 공유."""

    question: str
    status: str  # answered | refused_gate | refused_guard | error
    reason: str = ""  # 거절/에러 사유
    sql: str = ""  # LLM이 생성한 원본 SQL
    safe_sql: str = ""  # 가드 통과 후 실행된 SQL
    explanation: str = ""
    model: str = ""  # 이 답을 만든 모델 (자동 스위칭 추적용)
    df: pd.DataFrame | None = field(default=None, repr=False)

    @property
    def n_rows(self) -> int | None:
        return None if self.df is None else len(self.df)


def answer(question: str) -> AskResult:
    """질문 하나를 파이프라인 전체에 통과시키고 결과를 구조로 반환.

    예외를 밖으로 던지지 않는다 — 자동 러너가 20개를 끊김 없이
    돌리려면 실패도 데이터여야 하기 때문.
    """
    try:
        gate = _with_backoff(lambda q: classify(q, model=current_model()), question)
        if gate.intent == "out_of_scope":
            return AskResult(question, "refused_gate", reason=gate.reason, model=current_model())

        generated = _with_backoff(generate_sql, question)
        try:
            safe_sql = validate(generated.sql)
        except GuardError as e:
            return AskResult(question, "refused_guard", reason=str(e), sql=generated.sql,
                             model=current_model())

        df = run_readonly(safe_sql)
        return AskResult(
            question, "answered",
            sql=generated.sql, safe_sql=safe_sql,
            explanation=generated.explanation, df=df, model=current_model(),
        )
    except DailyQuotaError:
        raise  # 기다려도 안 풀림 — 러너가 중단·재개 안내를 하도록 전파
    except Exception as e:  # noqa: BLE001 — API/DB 장애도 기록 대상
        return AskResult(question, "error", reason=f"{type(e).__name__}: {e}")


def ask(question: str) -> pd.DataFrame | None:
    """CLI용 — answer()를 사람이 읽는 형태로 출력."""
    r = answer(question)
    if r.status == "refused_gate":
        print(f"⛔ I can't answer that — {r.reason}")
        print("   I can answer lookups, comparisons and rankings over prices, returns, volatility and drawdown.")
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
    return r.df


def ask_with_chart(question: str) -> None:
    """질문 → 표 → 차트 저장까지 한 번에 (Week 3 산출물)."""
    df = ask(question)
    if df is None or df.empty:
        return
    from chart_spec import TABLE_FALLBACK_REASONS, validate_spec
    from render import render, save_html

    spec = validate_spec(_with_backoff(generate_chart_spec, question, df), df)
    fig = render(spec, df)
    if fig is None:
        reason = TABLE_FALLBACK_REASONS.get("last", "the model chose a table")
        print(f"\n📊 Table instead of a chart ({reason})")
        return
    path = save_html(fig, "ask")
    print(f"\n📊 Saved {spec.chart_type} chart: {path} (open in a browser)")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Natural-language question → table (+ chart with --chart)")
    p.add_argument("question", nargs="+", help="question in English or Korean")
    p.add_argument("--chart", action="store_true", help="also save a chart (one extra API call)")
    args = p.parse_args()
    q = " ".join(args.question)
    ask_with_chart(q) if args.chart else ask(q)
