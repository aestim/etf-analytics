# Testing strategy

The project deliberately separates fast, deterministic code tests from checks
that need a live data warehouse or an external provider.

| Layer | Command / workflow | What it protects | Why it stays |
|---|---|---|---|
| Python unit and contract tests | `pytest -q` | ingest normalization/fail-loud behavior, analytics math, dashboard demo marts, Ask orchestration, SQL safety, retry/failover, chart selection/rendering | Offline, deterministic, and completes in a few seconds |
| Static error checks | `ruff check --select E9,F63,F7,F82 .` | syntax errors, undefined names, and invalid control flow, including paths a unit test may not execute | Cheap complement to runtime tests |
| dbt parse | `dbt deps && dbt parse` | model SQL, refs, macros, YAML tests, and project configuration compile correctly | No database or repository secrets required on pull requests |
| dbt data tests | scheduled `Daily ETF ingest` when `POSTGRES_HOST` is configured | nulls, uniqueness, relationships, return anomaly bounds, and mart recency against real data | These assertions require a populated warehouse and cannot be replaced by parse |
| External ingest smoke test | scheduled `Daily ETF ingest` | Yahoo returns data for every configured ticker and snapshots can be written | Network-dependent by nature, so it is kept out of pull-request pytest |

## CI policy

- `.github/workflows/test.yml` runs on pull requests, code/config pushes to `main`, and manual dispatch.
- A push that changes only `data/raw/**` is produced by the scheduled ingest and
  does not rerun pytest/dbt parse because no executable code changed.
- Superseded runs on the same branch are cancelled; both jobs have bounded timeouts.
- CI and the Airflow/daily-ingest runtime use Python 3.11.
- Gemini is always mocked in pytest. The normal scope-routing + SQL call and
  the one bounded column-repair path are covered by orchestration contracts;
  live model calls would spend quota and make
  CI depend on provider capacity, so they belong in the separately reviewed eval run.
- Pull-request CI does not connect to Postgres. The SQL guard and orchestration are
  tested offline; live dbt assertions run in the scheduled workflow when secrets exist.

## Local commands

```bash
pip install -r requirements-dev.txt
ruff check --select E9,F63,F7,F82 .
pytest -q
```

To compile dbt without a database:

```bash
pip install -r airflow/requirements.txt
cd dbt
cp profiles.yml.example profiles.yml
dbt deps
dbt parse --profiles-dir .
```

New tests should protect a distinct behavior, failure mode, or security boundary.
Do not add a second test solely to exercise the same implementation through another
name; parameterize equivalent inputs instead.
