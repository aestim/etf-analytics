"""
Ask — chat page for natural-language questions over the marts (Week 4).

The pipeline is exactly the pytest-covered parts from qa/: one structured call
for scope routing + SQL → sqlglot guard (with one bounded column-reference
correction when needed) → execution as etf_reader → deterministic ChartSpec →
renderer. This page only wraps those parts in a chat UI.

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

from db import (  # noqa: E402
    DATAFRAME_ROW_HEIGHT,
    PLOTLY_LAYOUT,
    dataframe_width,
    warehouse_available,
)
from i18n import current_language, tr  # noqa: E402

lang = current_language()
st.title(tr("ask.title", lang))
st.caption(tr("ask.subtitle", lang))
st.caption(tr("ask.defaults", lang))
st.info(tr("ask.examples", lang))

if not warehouse_available() or not os.getenv("GEMINI_API_KEY"):
    st.warning(tr("ask.unavailable", lang))
    st.stop()


# Optional gate for public deployments: set ASK_PASSWORD (Streamlit secret or
# env var) to require a password — protects the free LLM quota from strangers.
def _ask_password() -> str:
    try:
        return str(st.secrets.get("ASK_PASSWORD", "")) or os.getenv("ASK_PASSWORD", "")
    except Exception:  # no secrets.toml in local runs
        return os.getenv("ASK_PASSWORD", "")


if _pw := _ask_password():
    if st.text_input(tr("ask.password", lang), type="password") != _pw:
        st.info(tr("ask.password_info", lang))
        st.stop()

# The qa/ pipeline pulls in google-genai etc. If those aren't installed yet
# (e.g. Streamlit Cloud hasn't reinstalled requirements after a deploy), fail
# gracefully with a clear message instead of a redacted crash page.
try:
    from ask import (  # noqa: E402
        DailyQuotaError,
        ProviderUnavailableError,
        WarehouseSchemaError,
        answer,
        reader_ping,
    )
    from chart_spec import (  # noqa: E402
        TABLE_FALLBACK_REASONS,
        auto_chart_spec,
        validate_spec,
    )
    from presentation import display_column_label, is_percent_metric  # noqa: E402
    from render import render  # noqa: E402
    from sql_guard import MAX_ROWS  # noqa: E402
except ImportError as exc:
    st.error(tr("ask.dependency_error", lang))
    with st.expander(tr("ask.admin_error", lang)):
        st.code(f"Missing dependency: {exc.name}")
    st.stop()

LOG_PATH = _ROOT / "qa" / "logs" / "ask_ui.jsonl"


@st.cache_data(ttl=300, show_spinner=False)
def _reader_ok() -> tuple[bool, str]:
    return reader_ping()


ok, why = _reader_ok()
if not ok:
    st.error(tr("ask.database_error", lang))
    with st.expander(tr("ask.admin_connection", lang)):
        st.code(why)
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def cached_answer(question: str):
    """Serve identical questions from cache for an hour; never cache errors."""
    r = answer(question)
    if r.status == "error":
        if r.error_kind == "provider_unavailable":
            raise ProviderUnavailableError(r.reason)
        if r.error_kind == "warehouse_schema":
            raise WarehouseSchemaError(r.reason)
        raise RuntimeError(r.reason)  # st.cache_data does not store exceptions
    return r


def log_event(
    question: str,
    status: str,
    sql: str = "",
    n_rows=None,
    error: str = "",
    model: str = "",
) -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "question": question,
                    "status": status,
                    "sql": sql,
                    "n_rows": n_rows,
                    "error": error,
                    "model": model,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def show_assistant(entry: dict, key: str) -> None:
    kind = entry["kind"]
    if kind == "refusal":
        st.markdown(f"⛔ {entry['text']}\n\n_{tr('ask.refusal_alternative', lang)}_")
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
        question = entry.get("question", "")
        table_columns = {
            column: (
                st.column_config.NumberColumn(
                    display_column_label(column, question), format="percent"
                )
                if is_percent_metric(column)
                else st.column_config.Column(display_column_label(column, question))
            )
            for column in entry["df"].columns
        }
        st.dataframe(
            entry["df"],
            width=dataframe_width(entry["df"]),
            row_height=DATAFRAME_ROW_HEIGHT,
            hide_index=True,
            key=f"df_{key}",
            column_config=table_columns,
        )
        if entry.get("truncated"):
            st.warning(tr("ask.truncated", lang, rows=MAX_ROWS))
        with st.expander(tr("ask.sql", lang)):
            st.code(entry["safe_sql"], language="sql")
        if entry.get("chart_note"):
            st.caption(entry["chart_note"])


st.caption(tr("ask.auto_view", lang))

if "chat" not in st.session_state:
    st.session_state.chat = []

for i, msg in enumerate(st.session_state.chat):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["text"])
        else:
            show_assistant(msg, key=str(i))

if question := st.chat_input(tr("ask.placeholder", lang)):
    st.session_state.chat.append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"), st.spinner(tr("ask.spinner", lang)):
        try:
            r = cached_answer(question)
        except DailyQuotaError:
            entry = {
                "role": "assistant",
                "kind": "error",
                "text": tr("ask.quota_error", lang),
            }
            log_event(question, "daily_quota")
        except ProviderUnavailableError:
            entry = {
                "role": "assistant",
                "kind": "error",
                "text": tr("ask.provider_error", lang),
            }
            log_event(question, "provider_unavailable")
        except WarehouseSchemaError as e:
            entry = {
                "role": "assistant",
                "kind": "error",
                "text": tr("ask.schema_error", lang),
            }
            log_event(question, "warehouse_schema", error=str(e))
        except Exception as e:  # noqa: BLE001
            entry = {
                "role": "assistant",
                "kind": "error",
                "text": tr("ask.generic_error", lang),
            }
            log_event(question, "error", error=str(e))
        else:
            if r.status in ("refused_gate", "refused_guard"):
                entry = {"role": "assistant", "kind": "refusal", "text": r.reason}
                log_event(question, r.status, sql=r.sql, model=r.model)
            else:
                fig, chart_note = None, ""
                if r.df is not None and not r.df.empty:
                    try:
                        spec = validate_spec(auto_chart_spec(question, r.df), r.df)
                        fig = render(spec, r.df)
                        if fig is None:
                            if why := TABLE_FALLBACK_REASONS.get("last"):
                                chart_note = tr("ask.table_reason", lang, reason=why)
                            else:
                                chart_note = tr("ask.table_auto", lang)
                    except Exception as e:  # noqa: BLE001 — chart failures must not kill the table
                        chart_note = tr("ask.chart_error", lang)
                        log_event(question, "chart_error", error=str(e))
                # getattr fallback: survives a stale in-memory ask.py after an
                # auto-redeploy (module cached without the newer 'truncated' prop).
                truncated = getattr(r, "truncated", None)
                if truncated is None:
                    truncated = r.df is not None and len(r.df) >= MAX_ROWS
                entry = {
                    "role": "assistant",
                    "kind": "data",
                    "df": r.df,
                    "explanation": r.explanation,
                    "safe_sql": r.safe_sql,
                    "fig": fig,
                    "chart_note": chart_note,
                    "truncated": truncated,
                    "question": question,
                }
                log_event(
                    question, "answered", sql=r.safe_sql, n_rows=r.n_rows, model=r.model
                )
        # key = its future index in the chat list (append-only → stable across reruns)
        show_assistant(entry, key=str(len(st.session_state.chat)))
    st.session_state.chat.append(entry)
