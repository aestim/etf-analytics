"""qa/sql_guard.py — verify the never-trust-LLM-output principle actually holds."""

import pytest

from sql_guard import ALLOWED_FUNCTIONS, MAX_ROWS, GuardError, SchemaGuardError, validate

OK = "SELECT ticker, adj_close FROM public_marts.mart_etf_returns WHERE ticker = 'TLT'"


# --- must pass ------------------------------------------------------------


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


def test_period_metric_functions_are_allowlisted():
    sql = """
        SELECT ticker,
               STDDEV_SAMP(daily_return) * SQRT(252) AS period_vol,
               MIN(price_date) AS period_start,
               COUNT(*) AS price_observations
        FROM public_marts.mart_etf_returns
        GROUP BY ticker
    """

    assert {"STDDEV_SAMP", "SQRT", "MIN", "COUNT"} <= ALLOWED_FUNCTIONS
    validate(sql)


def test_cte_name_is_not_mistaken_for_table():
    sql = """
        WITH recent AS (
            SELECT * FROM public_marts.mart_etf_returns
            WHERE price_date >= CURRENT_DATE - INTERVAL '30 days'
        )
        SELECT ticker, avg(daily_return) FROM recent GROUP BY ticker
    """
    validate(sql)  # must not raise GuardError


def test_unqualified_table_is_rejected_for_safe_search_path():
    with pytest.raises(GuardError, match="table not allowed"):
        validate("SELECT ticker FROM mart_etf_returns")


def test_only_pg_catalog_may_explicitly_qualify_an_allowlisted_function():
    validate(
        "SELECT pg_catalog.avg(leverage) FROM public_marts.dim_etf"
    )

    with pytest.raises(GuardError, match="function schema not allowed"):
        validate(
            "SELECT public_marts.avg(leverage) FROM public_marts.dim_etf"
        )


def test_wrong_join_alias_column_is_rejected_before_database_execution():
    sql = """
        SELECT r.ticker, AVG(r.annualized_vol_30d)
        FROM public_marts.mart_etf_returns AS r
        JOIN public_marts.mart_etf_risk_metrics AS m
          ON r.ticker = m.ticker AND r.price_date = m.price_date
        GROUP BY r.ticker
    """

    with pytest.raises(SchemaGuardError, match="column validation failed"):
        validate(sql)


# --- must reject ----------------------------------------------------------


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


@pytest.mark.parametrize(
    "bad",
    [
        "SELECT 1",
        "SELECT CURRENT_DATE",
        "WITH constants AS (SELECT 1 AS value) SELECT value FROM constants",
    ],
)
def test_select_without_an_allowed_table_is_rejected(bad):
    with pytest.raises(GuardError, match="at least one allowed mart table"):
        validate(bad)


@pytest.mark.parametrize(
    "function_call",
    [
        "pg_sleep(1)",
        "pg_notify('channel', 'message')",
        "lo_create(0)",
        "pg_catalog.pg_sleep(1)",
    ],
)
def test_side_effect_and_delay_functions_are_rejected(function_call):
    sql = f"SELECT {function_call} FROM public_marts.dim_etf"

    with pytest.raises(GuardError, match="function not allowed"):
        validate(sql)


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
