"""qa/schema_prompt.py — dbt 문서에서 프롬프트가 온전히 생성되는지."""

from schema_prompt import ALLOWED_TABLES, build_schema_prompt


def test_prompt_contains_all_allowed_tables():
    prompt = build_schema_prompt()
    for table in ALLOWED_TABLES:
        assert f"public_marts.{table}" in prompt


def test_prompt_contains_column_descriptions():
    prompt = build_schema_prompt()
    assert "rolling_vol_30d" in prompt
    assert "adj_close" in prompt


def test_prompt_contains_universe_with_new_tickers():
    prompt = build_schema_prompt()
    for ticker in ("SCHD", "VWO", "IWM", "TLT"):
        assert ticker in prompt
    assert "treasury_long" in prompt  # '미국 장기채' → sub_class 매핑 재료
