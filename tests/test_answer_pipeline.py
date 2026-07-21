"""The Ask orchestration contract, with all network and DB calls mocked."""

import pandas as pd
import pytest

import ask


@pytest.fixture(autouse=True)
def direct_pipeline(monkeypatch):
    calls = []

    def call_directly(fn, *args):
        calls.append(fn)
        return fn(*args)

    monkeypatch.setattr(ask, "MODEL_CHAIN", ["test-model"])
    monkeypatch.setattr(ask, "_model_idx", 0)
    monkeypatch.setattr(ask, "_with_backoff", call_directly)
    return calls


def test_answer_routes_and_generates_sql_in_one_model_call(monkeypatch, direct_pipeline):
    frame = pd.DataFrame({"ticker": ["SPY"], "adj_close": [650.0]})
    monkeypatch.setattr(
        ask,
        "generate_sql",
        lambda question: ask.SqlAnswer(
            intent="data_query",
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
    assert len(direct_pipeline) == 1


def test_answer_stops_at_out_of_scope_route(monkeypatch):
    monkeypatch.setattr(
        ask,
        "generate_sql",
        lambda question: ask.SqlAnswer(
            intent="out_of_scope",
            sql="",
            explanation="Predictions are outside the warehouse scope.",
        ),
    )
    monkeypatch.setattr(ask, "run_readonly", lambda sql: pytest.fail("A refusal must not run SQL"))

    result = ask.answer("Predict tomorrow's winner")

    assert result.status == "refused_gate"
    assert result.reason == "Predictions are outside the warehouse scope."


def test_answer_stops_when_sql_guard_rejects_generated_sql(monkeypatch):
    monkeypatch.setattr(
        ask,
        "generate_sql",
        lambda question: ask.SqlAnswer(
            intent="data_query",
            sql="DROP TABLE users",
            explanation="bad",
        ),
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
    def unavailable(question):
        raise ask.ProviderUnavailableError("all models unavailable")

    monkeypatch.setattr(ask, "generate_sql", unavailable)

    result = ask.answer("SPY latest price")

    assert result.status == "error"
    assert result.error_kind == "provider_unavailable"
    assert "temporarily unavailable" in result.reason


def test_answer_adds_executed_correlation_summary(monkeypatch):
    frame = pd.DataFrame(
        {
            "ticker": ["SPY", "QQQ"],
            "leverage": [1.0, 2.0],
            "avg_annualized_vol_30d": [0.15, 0.27],
            "correlation": [0.72, 0.72],
        }
    )
    monkeypatch.setattr(
        ask,
        "generate_sql",
        lambda question: ask.SqlAnswer(
            intent="data_query",
            sql="SELECT ticker, leverage FROM public_marts.dim_etf",
            explanation="Uses the trailing one-year period.",
        ),
    )
    monkeypatch.setattr(ask, "run_readonly", lambda sql: frame)

    result = ask.answer("레버리지와 변동성의 상관관계는?")

    assert "Pearson correlation: 0.72" in result.explanation
    assert "does not establish causation" in result.explanation
