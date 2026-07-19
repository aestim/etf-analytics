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

from schema_prompt import ALLOWED_TABLES, SCHEMA_NAME

MAX_ROWS = 200  # human-readable table size + prevents accidental full-table dumps

# Collect only the node types that exist in the installed sqlglot version
_FORBIDDEN_NAMES = (
    "Insert", "Update", "Delete", "Drop", "Create", "Alter", "AlterTable",
    "Merge", "TruncateTable", "Grant", "Command",
)
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))


class GuardError(ValueError):
    """Rejection reason — phrased so it can be shown to the user as-is."""


def validate(sql: str) -> str:
    """Return the SQL with a guaranteed LIMIT if it passes; raise GuardError otherwise.

    Checks, in order (any failure rejects immediately):
      1. parses at all
      2. exactly one statement
      3. top level is a SELECT (SELECT INTO rejected too)
      4. no write/DDL nodes anywhere in the tree (subqueries included)
      5. every referenced table is whitelisted (CTE names exempt)
      6. LIMIT forced to MAX_ROWS when missing or larger
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
