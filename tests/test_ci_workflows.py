"""CI workflows preserve the repository/warehouse ownership boundary."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_scheduled_ingest_never_writes_to_main():
    workflow = (ROOT / ".github" / "workflows" / "daily_ingest.yml").read_text(
        encoding="utf-8"
    )

    assert "contents: read" in workflow
    assert "persist-credentials: false" in workflow
    assert "${{ runner.temp }}/etf-raw" in workflow
    assert "POSTGRES_HOST and POSTGRES_PASSWORD are required" in workflow

    for forbidden in ("contents: write", "git add", "git commit", "git push"):
        assert forbidden not in workflow


def test_scheduled_ingest_uses_small_daily_and_full_monthly_windows():
    workflow = (ROOT / ".github" / "workflows" / "daily_ingest.yml").read_text(
        encoding="utf-8"
    )

    assert "cron: '0 21 * * 1-5'" in workflow
    assert "cron: '30 21 1 * *'" in workflow
    assert 'if [ "$SCHEDULE_EXPRESSION" = "30 21 1 * *" ]' in workflow
    assert 'period="1mo"' in workflow
    assert 'period="max"' in workflow
    assert "FETCH_PERIOD: ${{ steps.fetch_window.outputs.period }}" in workflow
    assert "1mo|10y|max" in workflow
    assert "\n          - max\n" in workflow


def test_airflow_daily_ingest_explicitly_overrides_full_backfill_default():
    dag = (ROOT / "airflow" / "dags" / "etf_pipeline_dag.py").read_text(
        encoding="utf-8"
    )

    assert '"FETCH_PERIOD": os.environ.get("FETCH_PERIOD", "1mo")' in dag
    assert '"ETF_TICKERS": os.environ.get("ETF_TICKERS", "")' in dag


def test_ingest_uses_one_versioned_universe_instead_of_workflow_literals():
    workflow = (ROOT / ".github" / "workflows" / "daily_ingest.yml").read_text(
        encoding="utf-8"
    )
    dag = (ROOT / "airflow" / "dags" / "etf_pipeline_dag.py").read_text(
        encoding="utf-8"
    )
    universe = (ROOT / "config" / "etf_universe.txt").read_text(encoding="utf-8")

    assert "SPY" in universe
    assert "ETF_TICKERS:" not in workflow
    assert "SGOV,VGIT,TLT" not in workflow
    assert "SGOV,VGIT,TLT" not in dag


def test_local_environment_excludes_build_bloat_and_installs_dbt():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    devcontainer = (ROOT / ".devcontainer" / "devcontainer.json").read_text(
        encoding="utf-8"
    )

    for required_pattern in (".git", ".venv", ".env", "data/raw", "dbt/target"):
        assert required_pattern in dockerignore
    assert "requirements-dev.txt" in devcontainer
    assert "airflow/requirements.txt" in devcontainer
    assert "dbt deps" in devcontainer
