"""
ETF pipeline DAG — enable only after each task succeeds from the CLI.

Tasks:
  1. extract_load_raw  — ingest/fetch_prices.py
  2. dbt_run           — dbt run
  3. dbt_test          — dbt test
"""

from __future__ import annotations

import os
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

REPO_ROOT = "/opt/airflow"
INGEST_SCRIPT = f"{REPO_ROOT}/ingest/fetch_prices.py"
DBT_DIR = f"{REPO_ROOT}/dbt"
DBT_BIN = "/home/airflow/.local/bin/dbt"

# Postgres service name inside docker-compose network
PIPELINE_ENV = {
    "PATH": "/home/airflow/.local/bin:/usr/local/bin:/usr/bin:/bin",
    "POSTGRES_HOST": os.environ.get("POSTGRES_HOST", "postgres"),
    "POSTGRES_PORT": os.environ.get("POSTGRES_PORT", "5432"),
    "POSTGRES_USER": os.environ.get("POSTGRES_USER", "etf"),
    "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", "etf"),
    "POSTGRES_DB": os.environ.get("POSTGRES_DB", "etf_analytics"),
    "RAW_DATA_DIR": os.environ.get("RAW_DATA_DIR", f"{REPO_ROOT}/data/raw"),
    # The canonical CLI default is a full backfill. A daily scheduler must
    # override it so routine runs stay incremental.
    "FETCH_PERIOD": os.environ.get("FETCH_PERIOD", "1mo"),
    "ETF_TICKERS": os.environ.get("ETF_TICKERS", ""),
}

with DAG(
    dag_id="etf_pipeline",
    default_args=DEFAULT_ARGS,
    description="ETF universe ingest → dbt run → dbt test",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etf", "portfolio"],
) as dag:
    extract_load_raw = BashOperator(
        task_id="extract_load_raw",
        bash_command=f"python {INGEST_SCRIPT}",
        env=PIPELINE_ENV,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && {DBT_BIN} deps && {DBT_BIN} run --profiles-dir .",
        env=PIPELINE_ENV,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && {DBT_BIN} test --profiles-dir .",
        env=PIPELINE_ENV,
    )

    extract_load_raw >> dbt_run >> dbt_test
