# ETF Analytics Pipeline

Automated daily ingestion and analytics for a configurable cross-asset ETF universe (US/intl equity, Treasuries, credit, TIPS, gold, REITs — set via `ETF_TICKERS`). Replaces manual spreadsheet downloads with a reproducible raw → staging → mart pipeline and a Streamlit dashboard.

## Business requirement

> Research and portfolio teams need a consistent daily view of ETF performance and risk (returns, volatility, drawdown) across asset classes without copying prices into Excel.

## Scope

| Item | Choice |
|------|--------|
| Tickers | Env-driven (`ETF_TICKERS`) — default: 14 cross-asset ETFs (equity·leveraged equity·Treasury·credit·TIPS·gold·REIT) |
| Frequency | Daily (trading days) |
| Source | Yahoo Finance via `yfinance` (portfolio / educational use; not for production trading) |
| Storage | Local `data/raw/` (S3-compatible layout documented in [architecture](docs/architecture.md)) |
| Warehouse | PostgreSQL (local via Docker) |
| Transform | dbt (`staging` → `marts`) |
| Orchestration | Apache Airflow |
| UI | Streamlit |

## Repository layout

```text
etf-analytics/
├── README.md
├── docs/
│   ├── architecture.md
│   └── data-dictionary.md
├── docker-compose.yml
├── ingest/                 # Extract & load raw
├── data/raw/               # Local raw landing zone
├── dbt/                    # Staging & mart models
├── airflow/dags/           # Pipeline DAG (wire after tasks work standalone)
├── analytics/              # Pure strategy backtest functions (Strategy Lab)
├── dashboard/              # Streamlit app (multipage: dashboard + Strategy Lab)
└── tests/                  # Python unit tests for transform logic
```

## Prerequisites

- Docker & Docker Compose
- Python **3.10–3.12** for dbt (3.14 is not supported by dbt yet)
- [dbt-core](https://docs.getdbt.com/) + `dbt-postgres` (after Postgres is up)
- If port **5432** is already used locally, this project maps Postgres to **5433** (see `.env.example`)

## Quick start

### 1. Start infrastructure

```bash
cp .env.example .env
docker compose up -d
```

Wait until Airflow UI is available at http://localhost:8080 (default credentials in `.env.example`).

### 2. Install dependencies (one venv at repo root)

```bash
python -m venv .venv          # skip if .venv already exists
source .venv/bin/activate
pip install -r ingest/requirements.txt -r dashboard/requirements.txt -r requirements-dev.txt
```

### 3. Run ingest (verify raw files)

```bash
python ingest/fetch_prices.py
ls -la data/raw/
```

### 4. Run dbt

```bash
cd dbt
cp profiles.yml.example profiles.yml   # edit if needed
dbt debug && dbt run && dbt test
cd ..
```

### 5. Run unit tests (transform + strategy logic)

```bash
pytest tests/ -v
```

### 6. Enable Airflow DAG

After ingest and dbt succeed manually, unpause `etf_pipeline` in the Airflow UI.

### 7. Streamlit dashboard

```bash
streamlit run dashboard/app.py
```

Open http://localhost:8501 — compare ETFs across the configured universe.

The **Strategy Lab** page backtests representative strategies (buy & hold, monthly DCA, 60/40 quarterly rebalance, SMA-200 trend, and a simplified "infinite buying" cycle on a leveraged ETF) using pytest-covered pure functions in `analytics/strategies.py`. Simplified rules, no fees/slippage — educational illustration, not investment advice.

## Screenshots (portfolio demo)

Put PNG files in [`docs/images/`](docs/images/) (see [capture guide](docs/images/README.md)).

### 1. Streamlit dashboard

| View | Metrics |
|------|---------|
| **30-day rolling volatility** | Risk comparison |
| **Latest snapshot** | Most recent vol & drawdown per ticker |
| **Adjusted close** | Price level over ~3 years |
| **Cumulative return** | Compounded daily returns |

![30-day rolling volatility and latest snapshot](docs/images/dashboard-volatility-snapshot.png)

![Adjusted close and cumulative return — SGOV vs VGIT](docs/images/dashboard-prices-returns.png)

### 2. Apache Airflow

DAG `etf_pipeline` (ingest → dbt run → dbt test). Save capture as `docs/images/airflow-dag.png`.

![Airflow DAG etf_pipeline](docs/images/airflow-dag.png)

### 3. dbt tests

All project tests passing after `dbt run`. Save terminal capture as `docs/images/dbt-test-success.png`.

![dbt test — 12/12 passed](docs/images/dbt-test-success.png)

## Development order (recommended)

1. Document (`README`, `architecture`, `data-dictionary`) — done at init
2. Ingest script → confirm `data/raw/` files
3. dbt staging models → `dbt test`
4. dbt mart models
5. Airflow DAG (glue only; each task already works alone)
6. Streamlit dashboard

## GitHub Actions (daily ingest)

Workflow: [`.github/workflows/daily_ingest.yml`](.github/workflows/daily_ingest.yml) — fetches prices and commits parquet to `data/raw/`.

If `git push` fails with **403 Permission denied to github-actions[bot]**:

1. Repo **Settings** → **Actions** → **General**
2. **Workflow permissions** → **Read and write permissions**
3. Save, then re-run the workflow (**Actions** → **Daily ETF ingest** → **Run workflow**)

## Limitations

- Free market data may be delayed or revised; document as-of dates in mart tables.
- Not investment advice; for portfolio demonstration only.

## License

MIT (add your name in a follow-up commit if needed).
