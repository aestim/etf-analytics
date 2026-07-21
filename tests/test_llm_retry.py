"""Retry/failover logic is deterministic under mocks; never call Gemini here."""

import pytest
from google.genai import errors as genai_errors

import ask


@pytest.fixture(autouse=True)
def reset_model_chain(monkeypatch):
    """Each test gets a fresh two-model chain and no real waiting."""
    monkeypatch.setattr(ask, "MODEL_CHAIN", ["primary", "fallback"])
    monkeypatch.setattr(ask, "_model_idx", 0)
    monkeypatch.setattr(ask.random, "uniform", lambda _low, _high: 0.0)
    sleeps = []
    monkeypatch.setattr(ask.time, "sleep", sleeps.append)
    return sleeps


def test_503_retries_then_fails_over(reset_model_chain):
    calls = []

    def call():
        calls.append(ask.current_model())
        if ask.current_model() == "primary":
            raise RuntimeError("503 UNAVAILABLE: model is overloaded")
        return "ok"

    assert ask._with_backoff(call) == "ok"
    assert calls == ["primary", "primary", "primary", "primary", "fallback"]
    assert reset_model_chain == [1.0, 2.0, 4.0]
    assert ask.current_model() == "fallback"


def test_503_all_models_returns_clear_error(reset_model_chain):
    def call():
        raise RuntimeError("503 UNAVAILABLE: model is overloaded")

    with pytest.raises(ask.ProviderUnavailableError, match="all configured"):
        ask._with_backoff(call)
    # Three bounded retries per model; no infinite retry loop.
    assert reset_model_chain == [1.0, 2.0, 4.0, 1.0, 2.0, 4.0]


def test_typed_503_server_error_is_retried(reset_model_chain):
    calls = []

    def call():
        calls.append(ask.current_model())
        if ask.current_model() == "primary":
            raise genai_errors.ServerError(
                503,
                {"error": {"code": 503, "message": "capacity", "status": "UNAVAILABLE"}},
            )
        return "ok"

    assert ask._with_backoff(call) == "ok"
    assert calls == ["primary", "primary", "primary", "primary", "fallback"]


def test_unavailable_word_without_503_is_not_retried(reset_model_chain):
    with pytest.raises(RuntimeError, match="database unavailable"):
        ask._with_backoff(lambda: (_ for _ in ()).throw(RuntimeError("database unavailable")))
    assert reset_model_chain == []


def test_timeout_fails_over_immediately(reset_model_chain):
    calls = []

    def call():
        calls.append(ask.current_model())
        if ask.current_model() == "primary":
            raise TimeoutError("request timed out")
        return "ok"

    assert ask._with_backoff(call) == "ok"
    assert calls == ["primary", "fallback"]
    assert reset_model_chain == []


def test_all_models_timeout_returns_clear_error(reset_model_chain):
    with pytest.raises(ask.ProviderUnavailableError, match="timed out"):
        ask._with_backoff(lambda: (_ for _ in ()).throw(TimeoutError()))
    assert reset_model_chain == []


def test_504_deadline_fails_over_immediately(reset_model_chain):
    calls = []

    def call():
        calls.append(ask.current_model())
        if ask.current_model() == "primary":
            raise genai_errors.ServerError(
                504,
                {
                    "error": {
                        "code": 504,
                        "message": "Deadline expired before operation could complete.",
                        "status": "DEADLINE_EXCEEDED",
                    }
                },
            )
        return "ok"

    assert ask._with_backoff(call) == "ok"
    assert calls == ["primary", "fallback"]
    assert reset_model_chain == []


def test_wrapped_504_deadline_is_recognized(reset_model_chain):
    calls = []

    def call():
        calls.append(ask.current_model())
        if ask.current_model() == "primary":
            raise RuntimeError("504 DEADLINE_EXCEEDED: operation timed out")
        return "ok"

    assert ask._with_backoff(call) == "ok"
    assert calls == ["primary", "fallback"]
    assert reset_model_chain == []


def test_429_retries_briefly_then_fails_over(reset_model_chain):
    calls = []

    def call():
        calls.append(ask.current_model())
        if ask.current_model() == "primary":
            raise RuntimeError("429 RESOURCE_EXHAUSTED: retry later")
        return "ok"

    assert ask._with_backoff(call) == "ok"
    assert calls == ["primary", "primary", "primary", "fallback"]
    assert reset_model_chain == [2.0, 5.0]


def test_429_server_delay_is_capped(reset_model_chain):
    attempts = 0

    def call():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED: retryDelay 59s")
        return "ok"

    assert ask._with_backoff(call) == "ok"
    assert reset_model_chain == [5.0]


def test_daily_quota_fails_over_without_wait(reset_model_chain):
    calls = []

    def call():
        calls.append(ask.current_model())
        if ask.current_model() == "primary":
            raise RuntimeError("429 RESOURCE_EXHAUSTED: PerDay quota reached")
        return "ok"

    assert ask._with_backoff(call) == "ok"
    assert calls == ["primary", "fallback"]
    assert reset_model_chain == []
