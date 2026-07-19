"""
Week 2 ②: SQL 안전장치 1층 — 실행 없이 X-ray 검사 (sqlglot).

원칙: LLM 출력은 신뢰하지 않는다. 3중 방어의 1층이 이 파일이다.
  1층 (여기)     sqlglot 파싱: 단일 SELECT · 화이트리스트 테이블 · LIMIT 강제
  2층 (ask.py)   etf_reader(읽기 전용 계정)로만 실행 — 1층이 뚫려도 쓰기 불가
  3층 (ask.py)   statement_timeout — 폭주 쿼리 강제 종료

문자열 검사(예: "INSERT"라는 단어 찾기)가 아니라 **파스 트리** 검사인
이유: 문자열은 우회가 쉽다("/**/IN/**/SERT", 서브쿼리 은닉 등).
sqlglot은 SQL을 실행하지 않고 구조를 파악한다.

Covered by tests/test_sql_guard.py.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp

from schema_prompt import ALLOWED_TABLES, SCHEMA_NAME

MAX_ROWS = 200  # 사람이 표로 읽을 양 + 실수로 전체 테이블 덤프 방지

# 버전에 따라 없는 노드도 있어 존재하는 것만 수집
_FORBIDDEN_NAMES = (
    "Insert", "Update", "Delete", "Drop", "Create", "Alter", "AlterTable",
    "Merge", "TruncateTable", "Grant", "Command",
)
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))


class GuardError(ValueError):
    """검사 탈락 사유 — 사용자에게 그대로 보여줘도 되는 문장으로 쓴다."""


def validate(sql: str) -> str:
    """검사를 통과하면 LIMIT이 보장된 SQL을 돌려주고, 아니면 GuardError.

    검사 순서 (하나라도 걸리면 즉시 거부):
      1. 파싱 가능한가
      2. 문장이 정확히 1개인가
      3. 최상위가 SELECT인가 (SELECT INTO 금지 포함)
      4. 트리 어디에도 쓰기/DDL 노드가 없는가 (서브쿼리 포함)
      5. 참조 테이블이 전부 화이트리스트인가 (CTE 이름은 예외)
      6. LIMIT이 없거나 크면 MAX_ROWS로 강제
    """
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except sqlglot.errors.ParseError as e:
        raise GuardError(f"SQL을 해석할 수 없음: {e}") from e

    if len(statements) != 1:
        raise GuardError(f"문장은 정확히 1개여야 함 (받은 것: {len(statements)}개)")
    tree = statements[0]

    if not isinstance(tree, exp.Select):
        raise GuardError(f"SELECT 문만 허용됨 (받은 것: {tree.key.upper()})")
    if tree.args.get("into"):
        raise GuardError("SELECT INTO(테이블 생성)는 허용되지 않음")

    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise GuardError(f"허용되지 않는 구문 포함: {node.key.upper()}")

    cte_names = {cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name, schema = table.name, table.db
        if name in cte_names and not schema:
            continue  # WITH 절에서 정의한 이름은 실제 테이블이 아님
        if schema not in ("", SCHEMA_NAME) or name not in ALLOWED_TABLES:
            shown = f"{schema}.{name}" if schema else name
            raise GuardError(
                f"허용되지 않은 테이블: {shown} (허용: {SCHEMA_NAME}.{{{', '.join(ALLOWED_TABLES)}}})"
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
