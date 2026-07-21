"""
Ask — chat page for natural-language questions over the marts (Week 4).

The pipeline is exactly the pytest-covered parts from qa/: intent gate →
SQL generation → sqlglot guard → execution as etf_reader → deterministic
ChartSpec → renderer. This page only wraps those parts in a chat UI.

Free-tier handling: identical questions are served from cache (errors are
never cached); 429/503 retry and model failover live in qa/ask.py's _with_backoff.
Every question, generated SQL and error is logged to qa/logs/ask_ui.jsonl
(input for the Week 5 eval).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT / "dashboard", _ROOT / "qa"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from db import PLOTLY_LAYOUT, warehouse_available  # noqa: E402

st.set_page_config(page_title="Ask", page_icon="💬", layout="wide")
st.title("💬 Ask")
st.caption(
    "Ask **lookups, comparisons and rankings** over prices, returns, volatility "
    "and drawdown — in English or Korean. Predictions, investment advice and "
    "backtest requests are politely refused. Generated SQL is validated with "
    "sqlglot and executed by a read-only role."
)

if not warehouse_available() or not os.getenv("GEMINI_API_KEY"):
    st.warning(
        "This page runs locally only — it needs the Docker Postgres marts and a "
        "`GEMINI_API_KEY`.\n\n"
        "`docker compose up -d` → ingest → `dbt run` → set the key in `.env`, then reload."
    )
    st.stop()

# Optional gate for public deployments: set ASK_PASSWORD (Streamlit secret or
# env var) to require a password — protects the free LLM quota from strangers.
def _ask_password() -> str:
    try:
        return str(st.secrets.get("ASK_PASSWORD", "")) or os.getenv("ASK_PASSWORD", "")
    except Exception:  # no secrets.toml in local runs
        return os.getenv("ASK_PASSWORD", "")


if _pw := _ask_password():
    if st.text_input("Access password", type="password") != _pw:
        st.info("This public demo requires a password (it shares a free LLM quota).")
        st.stop()

# The qa/ pipeline pulls in google-genai etc. If those aren't installed yet
# (e.g. Streamlit Cloud hasn't reinstalled requirements after a deploy), fail
# gracefully with a clear message instead of a redacted crash page.
try:
    from ask import (  # noqa: E402
        DailyQuotaError,
        ProviderUnavailableError,
        answer,
        reader_ping,
    )
    from chart_spec import (  # noqa: E402
        TABLE_FALLBACK_REASONS,
        auto_chart_spec,
        validate_spec,
    )
    from presentation import is_percent_metric  # noqa: E402
    from render import render  # noqa: E402
    from sql_guard import MAX_ROWS  # noqa: E402
except ImportError as exc:
    st.error(
        "The Ask feature is temporarily unavailable — a dependency failed to load "
        f"({exc.name}). If you just deployed, reboot the app so it reinstalls "
        "requirements.txt (Manage app → Reboot)."
    )
    st.stop()

LOG_PATH = _ROOT / "qa" / "logs" / "ask_ui.jsonl"


@st.cache_data(ttl=300, show_spinner=False)
def _reader_ok() -> tuple[bool, str]:
    return reader_ping()


ok, why = _reader_ok()
if not ok:
    st.error(
        "The read-only account (`etf_reader`) can't connect, so queries would fail. "
        "Check that `QA_DB_PASSWORD` matches the password set in `scripts/init_db.sql`.\n\n"
        f"Details: {why}"
    )
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def cached_answer(question: str):
    """Serve identical questions from cache for an hour; never cache errors."""
    r = answer(question)
    if r.status == "error":
        if r.error_kind == "provider_unavailable":
            raise ProviderUnavailableError(r.reason)
        raise RuntimeError(r.reason)  # st.cache_data does not store exceptions
    return r


def log_event(question: str, status: str, sql: str = "", n_rows=None, error: str = "", model: str = "") -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "question": question, "status": status,
            "sql": sql, "n_rows": n_rows, "error": error, "model": model,
        }, ensure_ascii=False) + "\n")


def show_assistant(entry: dict, key: str) -> None:
    kind = entry["kind"]
    if kind == "refusal":
        st.markdown(
            f"⛔ {entry['text']}\n\n"
            "_I can answer lookups, comparisons and rankings over the warehouse instead._"
        )
    elif kind == "error":
        st.error(entry["text"])
    else:  # data
        if entry.get("explanation"):
            st.markdown(f"💬 {entry['explanation']}")
        if entry.get("fig") is not None:
            fig = entry["fig"]
            fig.update_layout(**PLOTLY_LAYOUT)
            # Unique key per message — identical charts across chat history would
            # otherwise collide on Streamlit's content-based element id.
            st.plotly_chart(fig, width="stretch", key=f"chart_{key}")
        percent_columns = {
            column: st.column_config.NumberColumn(format="percent")
            for column in entry["df"].columns
            if is_percent_metric(column)
        }
        st.dataframe(
            entry["df"],
            width="stretch",
            hide_index=True,
            key=f"df_{key}",
            column_config=percent_columns,
        )
        if entry.get("truncated"):
            st.warning(
                f"Capped at {MAX_ROWS} rows — this result may be cut short. "
                "Narrow the tickers or shorten the date range to see the full series."
            )
        with st.expander("Executed SQL"):
            st.code(entry["safe_sql"], language="sql")
        if entry.get("chart_note"):
            st.caption(entry["chart_note"])


auto_chart = st.toggle(
    "Automatically visualize suitable results",
    value=True,
    help="Uses the result shape only; it does not make an extra LLM call.",
)
st.caption(
    "Auto view: time series → line · rankings/comparisons → bar · "
    "relationships → scatter · everything else → table"
)

if "chat" not in st.session_state:
    st.session_state.chat = []

for i, msg in enumerate(st.session_state.chat):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["text"])
        else:
            show_assistant(msg, key=str(i))

if question := st.chat_input("e.g. How volatile was TLT over the past year?"):
    st.session_state.chat.append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"), st.spinner("Thinking..."):
        try:
            r = cached_answer(question)
        except DailyQuotaError:
            entry = {"role": "assistant", "kind": "error",
                     "text": "Daily free-tier quota exhausted for all models — try again tomorrow."}
            log_event(question, "daily_quota")
        except ProviderUnavailableError:
            entry = {
                "role": "assistant",
                "kind": "error",
                "text": (
                    "The LLM provider is temporarily unavailable. I tried the configured "
                    "fallback models; please try again in a few minutes."
                ),
            }
            log_event(question, "provider_unavailable")
        except Exception as e:  # noqa: BLE001
            entry = {"role": "assistant", "kind": "error", "text": f"Something went wrong: {e}"}
            log_event(question, "error", error=str(e))
        else:
            if r.status in ("refused_gate", "refused_guard"):
                entry = {"role": "assistant", "kind": "refusal", "text": r.reason}
                log_event(question, r.status, sql=r.sql, model=r.model)
            else:
                fig, chart_note = None, ""
                if auto_chart and r.df is not None and not r.df.empty:
                    try:
                        spec = validate_spec(auto_chart_spec(question, r.df), r.df)
                        fig = render(spec, r.df)
                        if fig is None:
                            if why := TABLE_FALLBACK_REASONS.get("last"):
                                chart_note = f"Showing a table instead of a chart ({why})"
                            else:
                                chart_note = "Table view selected automatically for this result."
                    except Exception as e:  # noqa: BLE001 — chart failures must not kill the table
                        chart_note = f"Chart generation failed, showing table: {e}"
                # getattr fallback: survives a stale in-memory ask.py after an
                # auto-redeploy (module cached without the newer 'truncated' prop).
                truncated = getattr(r, "truncated", None)
                if truncated is None:
                    truncated = r.df is not None and len(r.df) >= MAX_ROWS
                entry = {"role": "assistant", "kind": "data", "df": r.df,
                         "explanation": r.explanation, "safe_sql": r.safe_sql,
                         "fig": fig, "chart_note": chart_note, "truncated": truncated}
                log_event(question, "answered", sql=r.safe_sql, n_rows=r.n_rows, model=r.model)
        # key = its future index in the chat list (append-only → stable across reruns)
        show_assistant(entry, key=str(len(st.session_state.chat)))
    st.session_state.chat.append(entry)
