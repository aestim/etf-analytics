# ETF Analytics Pipeline

🔗 **Live demo:** [etf-analytics-pipeline.streamlit.app](https://etf-analytics-pipeline.streamlit.app/) — runs in demo mode (parquet snapshots, refreshed daily by CI)

Automated daily ingestion and analytics for a configurable **cross-asset ETF universe** (17 tickers by default: US large/small-cap, dividend, international developed & emerging equity, leveraged equity, Treasuries, credit, TIPS, gold, REITs). Reproducible raw → staging → mart pipeline, a multipage Streamlit app with a pytest-covered **Strategy Lab**, and an **LLM-powered natural-language Q&A layer in progress**.

## Business requirement

> Research and portfolio teams need a consistent daily view of ETF performance and risk (returns, volatility, drawdown) across asset classes without copying prices into Excel — and want to ask questions about the data in plain language.

## Features

- **Ingest** — yfinance daily prices (10-year window, one batched request for the whole universe), parquet landing zone + idempotent Postgres upsert; universe is env-driven (`ETF_TICKERS`)
- **Transform** — dbt `staging → marts` (daily returns, 30-day rolling volatility, drawdown) plus a `dim_etf` reference dimension (asset class, sub class, leverage, plain-language description) built from a seed
- **Data quality** — 20+ dbt tests including an anomaly tripwire that warns if any daily return exceeds ±75%
- **Orchestration** — Airflow DAG (`ingest → dbt run → dbt test`) and a GitHub Actions daily ingest that commits parquet snapshots
- **Dashboard** — Streamlit multipage: price/return/volatility charts with a stable 24-color palette, an interactive ticker guide, and metric tooltips backed by a shared glossary
- **Strategy Lab** — five classic strategies (buy & hold, monthly DCA, 60/40 rebalance, SMA-200 trend, simplified "infinite buying" cycle on a leveraged ETF) backtested by pure, pytest-covered functions: equity curves, drawdown view, CAGR/vol/MDD/Sharpe
- **Security** — dedicated read-only role (`etf_reader`, SELECT on marts only) for the Q&A layer
- **Demo mode** — with no database reachable, the app falls back to the parquet snapshots committed by CI and recomputes the marts in pandas, so the hosted demo needs zero infrastructure

## Roadmap — LLM Q&A layer (in progress)

Plain-language questions ("Which long-duration Treasury ETF had the lowest volatility this year?") answered against the marts:

1. **Intent gate** ✅ — Gemini structured output classifies questions into `data_query` / `out_of_scope` (predictions, investment advice, and backtest requests are refused) — see [`qa/`](qa/)
2. **Text-to-SQL** ✅ — schema prompt auto-generated from dbt docs (`schema.yml` + `dim_etf`); generated SQL is parsed with sqlglot and rejected unless it is a single SELECT on whitelisted tables, then executed as `etf_reader` with a row limit and timeout — see [`qa/ask.py`](qa/ask.py) + quota-aware test runner [`qa/run_week2.py`](qa/run_week2.py)
3. **Charts** ✅ — result shape and question type deterministically select line (time series), bar (ranking/comparison), scatter (explicit relationship), or table; pydantic validation and whitelisted plotting functions keep rendering fail-safe (`qa/ask.py --chart`)

Design principle: **the LLM emits structured JSON only — generated code is never executed, and chart selection requires no extra model call.**

## Repository layout

```text
etf-analytics/
├── docs/                   # architecture.md · data-dictionary.md · images/
├── docker-compose.yml      # Postgres + Airflow
├── ingest/                 # fetch_prices.py (env-driven universe) · transform.py
├── data/raw/               # Parquet landing zone (partitioned by ticker/date)
├── dbt/                    # staging & mart models · seeds/etf_info.csv · tests
├── airflow/dags/           # etf_pipeline DAG
├── analytics/              # Pure strategy backtest functions (Strategy Lab)
├── dashboard/              # Streamlit app (app.py · db.py · pages/1_Strategy_Lab.py)
├── qa/                     # LLM Q&A layer (WIP — intent classifier done)
└── tests/                  # pytest: transform logic + strategy backtests
```

## Quick start

### 1. Start infrastructure

```bash
cp .env.example .env        # add GEMINI_API_KEY if using the qa/ layer
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
dbt debug && dbt seed && dbt run && dbt test
cd ..
```

### 5. Run unit tests (transform + strategy logic)

```bash
pytest tests/ -v
```

### 6. Enable Airflow DAG

After ingest and dbt succeed manually, unpause `etf_pipeline` in the Airflow UI.

### 7. Streamlit app

```bash
streamlit run dashboard/app.py
```

Open http://localhost:8501 — dashboard on the home page, **Strategy Lab** in the sidebar.

## Screenshots

### Dashboard — cross-asset view

<img src="docs/images/dashboard-overview.png" alt="Dashboard: prices, cumulative returns, rolling volatility" width="850">

### Ticker guide

<img src="docs/images/ticker-guide.png" alt="Ticker guide: overview table with per-ticker detail card" width="850">

### Strategy Lab

<img src="docs/images/strategy-lab.png" alt="Strategy Lab: equity curves, drawdowns, and metrics" width="850">

### Pipeline

<img src="docs/images/airflow-dag.png" alt="Airflow etf_pipeline run, all tasks green" width="850">

<img src="docs/images/dbt-test-success.png" alt="dbt test passing, including the daily-return anomaly tripwire" width="850">

## GitHub Actions (daily ingest)

Workflow: [`.github/workflows/daily_ingest.yml`](.github/workflows/daily_ingest.yml) — fetches prices on weekdays after US close and commits parquet to `data/raw/`. If pushes fail with a 403, set **Settings → Actions → Workflow permissions → Read and write**.

### Optional: cloud warehouse (full mode online)

By default the hosted demo runs in parquet fallback ("demo mode"). To run the
full Postgres + dbt warehouse online at zero cost:

1. Create a free managed Postgres (e.g. [Neon](https://neon.tech) or [Supabase](https://supabase.com)) and apply `scripts/init_db.sql` once (creates `raw.etf_prices` and the read-only `etf_reader` role)
2. Add repo **Actions secrets**: `POSTGRES_HOST`, `POSTGRES_PASSWORD` (and `POSTGRES_PORT` / `POSTGRES_DB` / `POSTGRES_USER` if they differ from the defaults) — the daily workflow then upserts prices **and runs `dbt seed/run/test`** against the cloud warehouse
3. Add the same values to **Streamlit Cloud secrets** — the app detects the warehouse and switches out of demo mode automatically (no code change; that's the fallback design paying off)
4. Optionally add `GEMINI_API_KEY` to Streamlit secrets to enable the **Ask** page online, and set `ASK_PASSWORD` to gate it (a public LLM endpoint on a free quota is an invitation)

## Data & limitations

- Free market data (yfinance) may be delayed or revised; `adj_close` (split- and distribution-adjusted) is the primary price for all return math
- Strategy Lab uses simplified rules — no fees, taxes, or slippage; idle cash at 0%; signals lagged one day (no look-ahead)
- Not investment advice; for portfolio demonstration and education only

## License

MIT
