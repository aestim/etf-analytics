"""Shared, bounded Gemini client configuration for interactive Q&A calls."""

from __future__ import annotations

import os

from google import genai


DEFAULT_REQUEST_TIMEOUT_MS = 20_000


def request_timeout_ms() -> int:
    """Return a safe request timeout even if deployment config is malformed."""
    raw = os.getenv("GEMINI_TIMEOUT_MS", str(DEFAULT_REQUEST_TIMEOUT_MS))
    try:
        return max(1_000, int(raw))
    except ValueError:
        return DEFAULT_REQUEST_TIMEOUT_MS


def new_client() -> genai.Client:
    """Build a client whose network call cannot leave the UI spinning forever.

    Retry is owned by ask._with_backoff so the SDK must make one HTTP attempt;
    otherwise nested retries can multiply the user-visible wait.
    """
    return genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options={
            "timeout": request_timeout_ms(),
            "retry_options": {"attempts": 1},
        },
    )
