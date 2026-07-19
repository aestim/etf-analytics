"""qa/sql_guard.py — LLM 출력 불신 원칙이 실제로 작동하는지 검증."""

import pytest

from sql_guard import MAX_ROWS, GuardError, validate

OK = "SELECT ticker, adj_close FROM public_marts.mart_etf_returns WHERE ticker = 'TLT'"


# --- 통과해야 하는 것들 -------------------------------------------------


def test_valid_select_passes_and_gets_limit():
    out = validate(OK)
    assert f"LIMIT {MAX_ROWS}" in out


def test_small_limit_is_kept():
    out = validate(OK + " LIMIT 5")
    assert "LIMIT 5" in out


def test_oversized_limit_is_clamped():
    out = validate(OK + " LIMIT 999999")
    assert f"LIMIT {MAX_ROWS}" in out


def test_join_between_allowed_tables():
    sql = """
        SELECT r.ticker, avg(r.rolling_vol_30d) AS v
        FROM public_marts.mart_etf_risk_metrics r
        JOIN public_marts.dim_etf d ON r.ticker = d.ticker
        WHERE d.sub_class = 'treasury_long'
        GROUP BY r.ticker ORDER BY v
    """
    assert "dim_etf" in validate(sql)


def test_cte_name_is_not_mistaken_for_table():
    sql = """
        WITH recent AS (
            SELECT * FROM public_marts.mart_etf_returns
            WHERE price_date >= CURRENT_DATE - INTERVAL '30 days'
        )
        SELECT ticker, avg(daily_return) FROM recent GROUP BY ticker
    """
    validate(sql)  # GuardError가 나지 않아야 함


def test_unqualified_allowed_table_passes():
    validate("SELECT ticker FROM mart_etf_returns")


# --- 거부해야 하는 것들 -------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        "DROP TABLE public_marts.mart_etf_returns",
        "INSERT INTO public_marts.mart_etf_returns VALUES ('X', '2024-01-01', 1, 0)",
        "UPDATE public_marts.dim_etf SET name = 'x'",
        "DELETE FROM public_marts.dim_etf",
    ],
    ids=["drop", "insert", "update", "delete"],
)
def test_writes_and_ddl_rejected(bad):
    with pytest.raises(GuardError):
        validate(bad)


def test_multiple_statements_rejected():
    with pytest.raises(GuardError, match="exactly one statement"):
        validate("SELECT 1; SELECT 2")


def test_piggyback_after_select_rejected():
    with pytest.raises(GuardError):
        validate(OK + "; DROP TABLE public_marts.dim_etf")


def test_non_whitelisted_table_rejected():
    with pytest.raises(GuardError, match="table not allowed"):
        validate("SELECT * FROM raw.etf_prices")


def test_non_whitelisted_schema_rejected():
    with pytest.raises(GuardError, match="table not allowed"):
        validate("SELECT * FROM information_schema.tables")


def test_hidden_subquery_table_rejected():
    sql = """
        SELECT ticker FROM public_marts.mart_etf_returns
        WHERE ticker IN (SELECT usename FROM pg_user)
    """
    with pytest.raises(GuardError):
        validate(sql)


def test_garbage_rejected():
    with pytest.raises(GuardError):
        validate("this is not sql at all;;;")
