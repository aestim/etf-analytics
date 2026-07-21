"""
Week 2 (2/3): SQL safety layer 1 — an X-ray check without execution (sqlglot).

Principle: never trust LLM output. This file is layer 1 of a 3-layer defence:
  Layer 1 (here)     sqlglot parse: single SELECT · whitelisted tables · forced LIMIT
  Layer 2 (ask.py)   execute only as etf_reader (read-only role) — even if layer 1
                     were bypassed, writes are impossible
  Layer 3 (ask.py)   statement_timeout — kills runaway queries

Why a parse-tree check instead of string matching (e.g. searching for
"INSERT")? Strings are easy to evade ("/**/IN/**/SERT", subquery smuggling).
sqlglot understands the structure of the SQL without executing it.

Covered by tests/test_sql_guard.py.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import OptimizeError
from sqlglot.optimizer.qualify import qualify

from schema_prompt import ALLOWED_TABLES, SCHEMA_NAME, build_sqlglot_schema

# Ceiling to stop pathological full-table dumps, NOT a readability cap — a daily
# multi-year time series over a few tickers is thousands of rows (3y × 2 tickers
# ≈ 1500), and a smaller cap silently truncated those to the earliest slice.
# 10k covers ~4 tickers × 10y while still bounding runaway queries.
MAX_ROWS = 10000

# Collect only the node types that exist in the installed sqlglot version
_FORBIDDEN_NAMES = (
    "Insert", "Update", "Delete", "Drop", "Create", "Alter", "AlterTable",
    "Merge", "TruncateTable", "Grant", "Command",
)
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))


class GuardError(ValueError):
    """Rejection reason — phrased so it can be shown to the user as-is."""


class SchemaGuardError(GuardError):
    """The query is read-only but references an invalid documented column."""


def validate(sql: str) -> str:
    """Return the SQL with a guaranteed LIMIT if it passes; raise GuardError otherwise.

    Checks, in order (any failure rejects immediately):
      1. parses at all
      2. exactly one statement
      3. top level is a SELECT (SELECT INTO rejected too)
      4. no write/DDL nodes anywhere in the tree (subqueries included)
      5. every referenced table is whitelisted (CTE names exempt)
      6. referenced columns resolve against the documented mart schema
      7. LIMIT forced to MAX_ROWS when missing or larger
    """
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except sqlglot.errors.ParseError as e:
        raise GuardError(f"SQL could not be parsed: {e}") from e

    if len(statements) != 1:
        raise GuardError(f"exactly one statement required (got {len(statements)})")
    tree = statements[0]

    if not isinstance(tree, exp.Select):
        raise GuardError(f"only SELECT statements are allowed (got {tree.key.upper()})")
    if tree.args.get("into"):
        raise GuardError("SELECT INTO (table creation) is not allowed")

    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise GuardError(f"forbidden clause: {node.key.upper()}")

    cte_names = {cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name, schema = table.name, table.db
        if name in cte_names and not schema:
            continue  # names defined in a WITH clause are not real tables
        if schema not in ("", SCHEMA_NAME) or name not in ALLOWED_TABLES:
            shown = f"{schema}.{name}" if schema else name
            raise GuardError(
                f"table not allowed: {shown} (allowed: {SCHEMA_NAME}.{{{', '.join(ALLOWED_TABLES)}}})"
            )

    # Validate a copy: qualification expands stars and rewrites aliases, while
    # execution should retain the generated SQL apart from the forced LIMIT.
    try:
        qualify(
            tree.copy(),
            dialect="postgres",
            db=SCHEMA_NAME,
            schema=build_sqlglot_schema(),
            identify=False,
            quote_identifiers=False,
        )
    except OptimizeError as e:
        raise SchemaGuardError(f"column validation failed: {e}") from e

    limit = tree.args.get("limit")
    current = None
    if limit is not None and isinstance(limit.expression, exp.Literal):
        try:
            current = int(limit.expression.this)
        except (TypeError, ValueError):
            current = None
    if limit is None or current is None or current > MAX_ROWS:
        tree = tree.limit(MAX_ROWS)

    return tree.sql(dialect="postgres")
