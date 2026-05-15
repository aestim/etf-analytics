"""
ETF pipeline DAG — enable only after each task succeeds from the CLI.

Tasks:
  1. extract_load_raw  — ingest/fetch_sgov_vgit.py
  2. dbt_run           — dbt run
  3. dbt_test          — dbt test
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {
    "owner": "etf-analytics",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Paths inside the Airflow container (see docker-compose volumes)
REPO_ROOT = "/opt/airflow"
INGEST_SCRIPT = f"{REPO_ROOT}/ingest/fetch_sgov_vgit.py"
DBT_DIR = f"{REPO_ROOT}/dbt"

with DAG(
    dag_id="etf_pipeline",
    default_args=DEFAULT_ARGS,
    description="SGOV/VGIT ingest → dbt → tests",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etf", "portfolio"],
) as dag:
    extract_load_raw = BashOperator(
        task_id="extract_load_raw",
        bash_command=f"python {INGEST_SCRIPT}",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run --profiles-dir .",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir .",
    )

    extract_load_raw >> dbt_run >> dbt_test
