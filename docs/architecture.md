# Architecture

## Overview

Batch pipeline that ingests ETF prices, lands raw files, loads PostgreSQL, transforms with dbt, and serves metrics to a Streamlit dashboard. Orchestration is handled by Airflow once each step runs successfully on its own.

## Components

| Component | Role | Technology |
|-----------|------|------------|
| Ingest | Pull prices from API; write raw | Python, `yfinance` |
| Raw zone | Immutable daily snapshots | `data/raw/` (local; S3 in production) |
| Warehouse | Structured tables for SQL transforms | PostgreSQL 15 |
| Transform | Clean, model, test | dbt |
| Orchestration | Schedule & dependency management | Apache Airflow 2.x |
| Presentation | Charts & comparison tables | Streamlit |

## Data flow

```mermaid
flowchart LR
  subgraph sources
    YF[Yahoo Finance API]
  end

  subgraph ingest
    PY[ingest/fetch_prices.py]
  end

  subgraph storage
    RAW[data/raw/]
    PG[(PostgreSQL)]
  end

  subgraph transform
    DBT[dbt staging & marts]
  end

  subgraph orchestration
    AF[Airflow DAG]
  end

  subgraph ui
    ST[Streamlit dashboard]
  end

  YF --> PY --> RAW
  PY --> PG
  AF --> PY
  AF --> DBT
  PG --> DBT
  DBT --> PG
  PG --> ST
```

## Layer model

| Layer | Location | Mutability | Purpose |
|-------|----------|------------|---------|
| **raw** | `data/raw/{ticker}/` | Append-only | Preserve source-shaped extracts |
| **staging** | `dbt/models/staging/` | Rebuilt on run | Types, rename, dedupe, calendar align |
| **marts** | `dbt/models/marts/` | Rebuilt on run | Analytics-ready returns & risk metrics |
| **serve** | Streamlit reads marts | Read-only | Human-facing views |

## Airflow DAG

DAG id: `etf_pipeline` (see `airflow/dags/etf_pipeline_dag.py`)

| Task | Command / operator | Depends on |
|------|-------------------|------------|
| `extract_load_raw` | Bash: `python ingest/fetch_prices.py` | — |
| `dbt_run` | Bash: `dbt deps && dbt run --profiles-dir .` (in `dbt/`) | `extract_load_raw` |
| `dbt_test` | Bash: `dbt test --profiles-dir .` (in `dbt/`) | `dbt_run` |

> **Rule:** Add tasks to the DAG only after each command succeeds manually from the CLI.

## Environments

| Environment | Raw storage | Warehouse | Orchestration |
|-------------|-------------|-----------|---------------|
| Local (this repo) | `data/raw/` | Docker Postgres | Docker Airflow |
| Production-style | S3 `s3://bucket/raw/etf/` | RDS Postgres | Managed Airflow / MWAA |

## Security & config

- Secrets via `.env` (never commit `.env`)
- See `.env.example` for variable names

## Observability (future)

- Airflow task logs
- dbt run artifacts under `dbt/target/`
- Optional: data freshness check on `mart_etf_risk_metrics.as_of_date`
