-- Schemas for raw landing and dbt-managed objects
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

-- Optional: raw table populated by ingest (parquet can also stay file-only initially)
CREATE TABLE IF NOT EXISTS raw.etf_prices (
    ticker       TEXT NOT NULL,
    price_date   DATE NOT NULL,
    open         DOUBLE PRECISION,
    high         DOUBLE PRECISION,
    low          DOUBLE PRECISION,
    close        DOUBLE PRECISION,
    adj_close    DOUBLE PRECISION NOT NULL,
    volume       BIGINT,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ticker, price_date)
);
