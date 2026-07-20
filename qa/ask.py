"""
Week 2 (3/3): question → table. Assembles the whole pipeline.

    python qa/ask.py "How volatile was TLT over the past year?"

Flow:  intent gate (Week 1) → SQL generation (structured output)
       → guard (sql_guard) → execute as etf_reader (timeout) → DataFrame

Core principle: the LLM only fills in forms (JSON). Execution is done
exclusively by this code, after validation.
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

from practice_structured import classify  # reuse the Week 1 intent gate as stage 1
from schema_prompt import SCHEMA_NAME, build_schema_prompt
from sql_guard import MAX_ROWS, GuardError, validate

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# Free-tier quotas are tracked per model → on a daily (PerDay) quota error we
# switch to the next model in the chain (flash first for quality, lite as the
# fallback). Setting GEMINI_MODEL puts that model at the head of the chain.
_DEFAULT_CHAIN = "gemini-flash-latest,gemini-flash-lite-latest"
MODEL_CHAIN = [m.strip() for m in os.getenv("GEMINI_MODEL_CHAIN", _DEFAULT_CHAIN).split(",") if m.strip()]
if _override := os.getenv("GEMINI_MODEL"):
    MODEL_CHAIN = [_override] + [m for m in MODEL_CHAIN if m != _override]

_model_idx = 0


def current_model() -> str:
    return MODEL_CHAIN[_model_idx]


def _advance_model() -> bool:
    """Switch to the next model on daily-quota exhaustion. False if none left."""
    global _model_idx
    if _model_idx + 1 < len(MODEL_CHAIN):
        _model_idx += 1
        print(f"   (daily quota → switching model: {MODEL_CHAIN[_model_idx - 1]} → {current_model()})")
        return True
    return False

STATEMENT_TIMEOUT_MS = 5000  # defence layer 3: kill runaway queries


class SqlAnswer(BaseModel):
    sql: str
    explanation: str  # one or two sentences on how the SQL answers the question


# Few-shot "question → correct SQL" pairs. Their job is to teach style
# (qualified schema paths, date handling, aggregation tricks) — 2-3 suffice.
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


RETRY_WAITS = (20, 45, 90)  # exponential backoff for per-minute 429s — they clear if you wait


class DailyQuotaError(RuntimeError):
    """Daily quota exhausted — waiting won't help, stop immediately."""


def _with_backoff(fn, *args):
    """Wrapper for Gemini free-tier (429) errors.

    - Per-minute limit: wait (honouring the server-suggested retryDelay) and retry.
    - Daily limit (PerDay): retrying is pointless → switch model or raise DailyQuotaError.
    """
    for attempt, wait in enumerate((*RETRY_WAITS, None)):
        try:
            return fn(*args)
        except Exception as e:  # noqa: BLE001 — 429s are identified by message
            msg = str(e)
            if "PerDay" in msg or "per day" in msg.lower():
                if _advance_model():
                    continue  # retry immediately on the next model (quotas are per model)
                raise DailyQuotaError("daily free-tier quota exhausted for all models") from e
            if wait is None or not ("429" in msg or "RESOURCE_EXHAUSTED" in msg):
                raise
            m = re.search(r"retry(?:Delay)?\D*(\d+(?:\.\d+)?)\s*s", msg, re.IGNORECASE)
            delay = float(m.group(1)) + 1 if m else wait
            print(f"   (429 rate limit — waiting {delay:.0f}s, retry {attempt + 1}/{len(RETRY_WAITS)})")
            time.sleep(delay)


def _structured_call(system: str, contents: str, schema: type[BaseModel], _retry: bool = True):
    """Shared structured-output call — also handles parsed=None (empty/truncated)."""
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
        # Structured output is not a guarantee — on schema mismatch or a
        # truncated response, .parsed is silently None. Retry once, then
        # promote to a clear error.
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
    """Week 3: have the LLM fill a chart form for the result table (forms only, never code)."""
    from chart_spec import ChartSpec  # lazy import — the test runner works without charts

    contents = (
        f"Question: {question}\n"
        f"Columns and dtypes:\n{df.dtypes.to_string()}\n"
        f"First rows:\n{df.head(5).to_string(index=False)}"
    )
    return _structured_call(CHART_SYSTEM_PROMPT, contents, ChartSpec)


def sslmode_for(host: str) -> str:
    """Managed Postgres (Neon/Supabase) requires SSL; local Docker has none.
    Default to 'require' unless the host is local — override with POSTGRES_SSLMODE."""
    local = host in ("localhost", "127.0.0.1", "", "postgres")
    return os.getenv("POSTGRES_SSLMODE", "prefer" if local else "require")


def run_readonly(sql: str) -> pd.DataFrame:
    """Defence layers 2+3: read-only role + statement_timeout."""
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
    # NB: statement_timeout is NOT passed as a startup option — Neon's pooler
    # (pgbouncer) rejects those. Set it as SET LOCAL inside the transaction so
    # the read-only query still can't run away (defence layer 3).
    engine = create_engine(
        url,
        connect_args={"connect_timeout": 3, "sslmode": sslmode_for(host)},
    )
    with engine.begin() as conn:
        conn.exec_driver_sql(f"SET LOCAL statement_timeout = {int(STATEMENT_TIMEOUT_MS)}")
        return pd.read_sql(sql, conn)


@dataclass
class AskResult:
    """Structured result of one pipeline run — shared by the CLI, UI and test runner."""

    question: str
    status: str  # answered | refused_gate | refused_guard | error
    reason: str = ""  # refusal / error reason
    sql: str = ""  # raw SQL as generated by the LLM
    safe_sql: str = ""  # SQL actually executed, after passing the guard
    explanation: str = ""
    model: str = ""  # which model produced this answer (fallback-chain tracking)
    df: pd.DataFrame | None = field(default=None, repr=False)

    @property
    def n_rows(self) -> int | None:
        return None if self.df is None else len(self.df)


def answer(question: str) -> AskResult:
    """Run one question through the whole pipeline; return a structured result.

    Never raises (except DailyQuotaError) — the automated runner needs
    failures to be data, not crashes.
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
        raise  # waiting won't help — propagate so the runner can stop and explain how to resume
    except Exception as e:  # noqa: BLE001 — API/DB failures are data too
        return AskResult(question, "error", reason=f"{type(e).__name__}: {e}")


def ask(question: str) -> pd.DataFrame | None:
    """CLI wrapper — print answer() in a human-readable form."""
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
    """Question → table → saved chart, in one go (Week 3 deliverable)."""
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
