"""qa/schema_prompt.py — the prompt is fully generated from the dbt docs."""

from schema_prompt import ALLOWED_TABLES, build_schema_prompt


def test_prompt_contains_all_allowed_tables():
    prompt = build_schema_prompt()
    for table in ALLOWED_TABLES:
        assert f"public_marts.{table}" in prompt


def test_prompt_contains_column_descriptions():
    prompt = build_schema_prompt()
    assert "rolling_vol_30d" in prompt
    assert "adj_close" in prompt
    assert "volume" in prompt


def test_prompt_contains_universe_with_new_tickers():
    prompt = build_schema_prompt()
    for ticker in ("SCHD", "VWO", "IWM", "TLT"):
        assert ticker in prompt
    assert "treasury_long" in prompt  # lets "long-term treasuries" map to sub_class
