"""
Ask — 자연어로 마트에 질문하는 채팅 페이지 (Week 4).

파이프라인은 qa/의 pytest 검증된 부품 그대로: 문지기 → SQL 생성 →
sqlglot 가드 → etf_reader 실행 → (선택) ChartSpec → 렌더러.
이 페이지는 그 부품들을 채팅 UI로 감싸기만 한다.

무료 한도 대응: 같은 질문은 캐시 재사용(에러는 캐시 안 함),
429 백오프는 qa/ask.py의 _with_backoff가 담당.
모든 질문·SQL·오류는 qa/logs/ask_ui.jsonl에 기록 (Week 5 eval 재료).
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
    "가격·수익률·변동성·드로다운의 **조회/비교/순위**를 한국어나 영어로. "
    "예측·투자 조언·백테스트 요청은 정중히 거절합니다. "
    "생성된 SQL은 sqlglot 검사 후 읽기 전용 계정으로만 실행됩니다."
)

if not warehouse_available() or not os.getenv("GEMINI_API_KEY"):
    st.warning(
        "이 페이지는 로컬 전용입니다 — Docker Postgres(마트)와 `GEMINI_API_KEY`가 필요해요.\n\n"
        "`docker compose up -d` → ingest → `dbt run` → `.env`에 키 설정 후 다시 열기."
    )
    st.stop()

from ask import DailyQuotaError, _with_backoff, answer, generate_chart_spec  # noqa: E402
from chart_spec import TABLE_FALLBACK_REASONS, validate_spec  # noqa: E402
from render import render  # noqa: E402

LOG_PATH = _ROOT / "qa" / "logs" / "ask_ui.jsonl"


@st.cache_data(ttl=3600, show_spinner=False)
def cached_answer(question: str):
    """같은 질문은 1시간 동안 API 재호출 없이 재사용. 에러는 캐시에 남기지 않는다."""
    r = answer(question)
    if r.status == "error":
        raise RuntimeError(r.reason)  # 예외는 st.cache_data가 저장하지 않음
    return r


def log_event(question: str, status: str, sql: str = "", n_rows=None, error: str = "", model: str = "") -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "question": question, "status": status,
            "sql": sql, "n_rows": n_rows, "error": error, "model": model,
        }, ensure_ascii=False) + "\n")


def show_assistant(entry: dict) -> None:
    kind = entry["kind"]
    if kind == "refusal":
        st.markdown(f"⛔ {entry['text']}\n\n_대신 조회·비교·순위 질문은 답할 수 있어요._")
    elif kind == "error":
        st.error(entry["text"])
    else:  # data
        if entry.get("explanation"):
            st.markdown(f"💬 {entry['explanation']}")
        if entry.get("fig") is not None:
            fig = entry["fig"]
            fig.update_layout(**PLOTLY_LAYOUT)
            st.plotly_chart(fig, width="stretch")
        st.dataframe(entry["df"], width="stretch", hide_index=True)
        with st.expander("실행된 SQL"):
            st.code(entry["safe_sql"], language="sql")
        if entry.get("chart_note"):
            st.caption(entry["chart_note"])


auto_chart = st.toggle("차트 자동 생성 (질문당 API 1콜 추가)", value=True)

if "chat" not in st.session_state:
    st.session_state.chat = []

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["text"])
        else:
            show_assistant(msg)

if question := st.chat_input("예: 지난 1년 TLT 변동성 어땠어?"):
    st.session_state.chat.append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"), st.spinner("생각 중..."):
        try:
            r = cached_answer(question)
        except DailyQuotaError:
            entry = {"role": "assistant", "kind": "error",
                     "text": "Gemini 일일 무료 한도 소진 — 내일 다시, 또는 GEMINI_MODEL=gemini-flash-lite-latest로 재시작."}
            log_event(question, "daily_quota")
        except Exception as e:  # noqa: BLE001
            entry = {"role": "assistant", "kind": "error", "text": f"실행 실패: {e}"}
            log_event(question, "error", error=str(e))
        else:
            if r.status in ("refused_gate", "refused_guard"):
                entry = {"role": "assistant", "kind": "refusal", "text": r.reason}
                log_event(question, r.status, sql=r.sql, model=r.model)
            else:
                fig, chart_note = None, ""
                if auto_chart and r.df is not None and not r.df.empty:
                    try:
                        spec = validate_spec(_with_backoff(generate_chart_spec, question, r.df), r.df)
                        fig = render(spec, r.df)
                        if fig is None and (why := TABLE_FALLBACK_REASONS.get("last")):
                            chart_note = f"차트 대신 표 (사유: {why})"
                    except Exception as e:  # noqa: BLE001 — 차트 실패해도 표는 산다
                        chart_note = f"차트 생성 실패, 표로 표시: {e}"
                entry = {"role": "assistant", "kind": "data", "df": r.df,
                         "explanation": r.explanation, "safe_sql": r.safe_sql,
                         "fig": fig, "chart_note": chart_note}
                log_event(question, "answered", sql=r.safe_sql, n_rows=r.n_rows, model=r.model)
        show_assistant(entry)
    st.session_state.chat.append(entry)
