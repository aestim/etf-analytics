# Data Dictionary

Definitions for raw files, warehouse tables, and mart outputs. Keep in sync with `dbt/models/**/schema.yml`.

## Conventions

- **Grain**: one row per `ticker` × `price_date` unless noted
- **Timezone**: dates are `DATE` in America/New_York trading calendar (no intraday)
- **Ticker**: uppercase symbol (`SGOV`, `VGIT`)

---

## Raw (`data/raw/`)

Parquet written by ingest, partitioned as `data/raw/{ticker}/dt={YYYY-MM-DD}/prices.parquet`

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | string | ETF symbol |
| `price_date` | date | Trading session date |
| `open` | float | Open price |
| `high` | float | High price |
| `low` | float | Low price |
| `close` | float | Close price |
| `adj_close` | float | Split/dividend-adjusted close (**primary price**) |
| `volume` | bigint | Share volume |
| `_ingested_at` | timestamp | UTC load timestamp |

---

## Staging: `stg_etf_prices`

Source: raw / Postgres `raw.etf_prices` (after load). Cleans types and removes duplicate dates per ticker.

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | string | ETF symbol |
| `price_date` | date | Trading date |
| `adj_close` | numeric | Adjusted close price |
| `volume` | bigint | Volume |

**Tests:** `not_null` on keys; `unique` on (`ticker`, `price_date`).

---

## Marts

### `mart_etf_returns`

Daily simple returns from adjusted close, with volume retained for paired
descriptive analysis against risk metrics.

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | string | ETF symbol |
| `price_date` | date | Trading date |
| `adj_close` | numeric | Adjusted close |
| `volume` | bigint | Daily share volume |
| `daily_return` | numeric | \((adj\_close_t / adj\_close_{t-1}) - 1\) |

**Grain:** `ticker` × `price_date` (first row per ticker has `NULL` daily_return).

---

### `mart_etf_risk_metrics`

Rolling risk statistics (window = 30 trading days unless changed in dbt).

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | string | ETF symbol |
| `price_date` | date | As-of date |
| `rolling_vol_30d` | numeric | Sample std dev of `daily_return` over 30 days |
| `annualized_vol_30d` | numeric | `rolling_vol_30d × sqrt(252)` |
| `drawdown` | numeric | \((adj\_close / running\_max) - 1\) |
| `as_of_date` | date | Same as `price_date`; for freshness checks |

---

## Streamlit metrics (derived in app)

| Metric | Definition |
|--------|------------|
| Cumulative return | \(\prod (1 + daily\_return) - 1\) over selected range |
| Max drawdown | \(\min(drawdown)\) over range |
| Latest 30d vol | Last non-null `rolling_vol_30d` |

## Ask relationship metrics (derived in SQL)

| Metric | Definition / policy |
|--------|---------------------|
| `avg_daily_dollar_volume` | `AVG(volume × adj_close)` in USD; used instead of share count for cross-ETF liquidity comparisons |
| Dollar-volume relationship | Pearson correlation uses `LN(avg_daily_dollar_volume)` and the scatter x-axis is logarithmic because liquidity is highly skewed |
| `cagr` | `total_growth^(365.25 / calendar_days) - 1`; used for performance windows of 2 years or longer |
| Relationship period | Explicit historical period up to 10 years wins; omitted period defaults to trailing 1 year |
| Comparable history | At least 200 paired trading observations per requested year |
| Default universe | `leverage = 1`; include 2x/3x only when leverage is the metric or the question explicitly requests them |
| `correlation` | Cross-sectional Pearson coefficient over one aggregated row per ticker; descriptive for the curated warehouse universe, not a population claim |

---

## Source mapping (Yahoo → raw)

| Yahoo (`yfinance`) | Raw column |
|--------------------|------------|
| `Date` | `price_date` |
| `Open` | `open` |
| `High` | `high` |
| `Low` | `low` |
| `Close` | `close` |
| `Adj Close` | `adj_close` |
| `Volume` | `volume` |

---

## Known limitations

- Corporate actions rely on vendor-adjusted prices.
- Missing exchange holidays produce gaps; returns use previous available trading day.
- Free API rate limits may affect backfill; throttle in ingest if needed.
