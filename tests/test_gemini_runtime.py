"""Gemini client settings keep interactive calls bounded."""

import gemini_runtime


def test_request_timeout_defaults_to_20_seconds(monkeypatch):
    monkeypatch.delenv("GEMINI_TIMEOUT_MS", raising=False)
    assert gemini_runtime.request_timeout_ms() == 20_000


def test_request_timeout_has_safe_floor_and_invalid_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_TIMEOUT_MS", "10")
    assert gemini_runtime.request_timeout_ms() == 1_000

    monkeypatch.setenv("GEMINI_TIMEOUT_MS", "not-a-number")
    assert gemini_runtime.request_timeout_ms() == 20_000


def test_client_disables_nested_sdk_retries(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini_runtime.genai, "Client", fake_client)

    gemini_runtime.new_client()

    assert captured["http_options"] == {
        "timeout": 20_000,
        "retry_options": {"attempts": 1},
    }
