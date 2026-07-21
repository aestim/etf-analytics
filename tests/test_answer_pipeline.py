"""The Ask orchestration contract, with all network and DB calls mocked."""

from types import SimpleNamespace

import pandas as pd
import pytest

import ask


@pytest.fixture(autouse=True)
def direct_pipeline(monkeypatch):
    monkeypatch.setattr(ask, "MODEL_CHAIN", ["test-model"])
    monkeypatch.setattr(ask, "_model_idx", 0)
    monkeypatch.setattr(ask, "_with_backoff", lambda fn, *args: fn(*args))


def test_answer_runs_gate_guard_and_readonly_query(monkeypatch):
    frame = pd.DataFrame({"ticker": ["SPY"], "adj_close": [650.0]})
    monkeypatch.setattr(
        ask,
        "classify",
        lambda question, model: SimpleNamespace(intent="data_query", reason=""),
    )
    monkeypatch.setattr(
        ask,
        "generate_sql",
        lambda question: ask.SqlAnswer(
            sql="SELECT ticker, adj_close FROM public_marts.mart_etf_returns",
            explanation="Latest adjusted close.",
        ),
    )
    monkeypatch.setattr(ask, "run_readonly", lambda sql: frame)

    result = ask.answer("SPY latest price")

    assert result.status == "answered"
    assert result.model == "test-model"
    assert result.explanation == "Latest adjusted close."
    assert f"LIMIT {ask.MAX_ROWS}" in result.safe_sql
    assert result.df is frame


def test_answer_stops_at_out_of_scope_gate(monkeypatch):
    monkeypatch.setattr(
        ask,
        "classify",
        lambda question, model: SimpleNamespace(intent="out_of_scope", reason="prediction"),
    )
    monkeypatch.setattr(
        ask,
        "generate_sql",
        lambda question: pytest.fail("SQL generation must not run after a refusal"),
    )

    result = ask.answer("Predict tomorrow's winner")

    assert result.status == "refused_gate"
    assert result.reason == "prediction"


def test_answer_stops_when_sql_guard_rejects_generated_sql(monkeypatch):
    monkeypatch.setattr(
        ask,
        "classify",
        lambda question, model: SimpleNamespace(intent="data_query", reason=""),
    )
    monkeypatch.setattr(
        ask,
        "generate_sql",
        lambda question: ask.SqlAnswer(sql="DROP TABLE users", explanation="bad"),
    )
    monkeypatch.setattr(
        ask,
        "run_readonly",
        lambda sql: pytest.fail("Rejected SQL must never reach the database"),
    )

    result = ask.answer("show data")

    assert result.status == "refused_guard"
    assert "only SELECT" in result.reason


def test_answer_converts_provider_failure_to_ui_safe_error(monkeypatch):
    def unavailable(question, model):
        raise ask.ProviderUnavailableError("all models unavailable")

    monkeypatch.setattr(ask, "classify", unavailable)

    result = ask.answer("SPY latest price")

    assert result.status == "error"
    assert result.error_kind == "provider_unavailable"
    assert "temporarily unavailable" in result.reason
