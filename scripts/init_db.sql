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

-- ---------------------------------------------------------------
-- Read-only role for the LLM Q&A layer (SELECT on marts only).
-- NOTE: this file only runs on a FRESH postgres volume. On an
-- existing database, apply this block manually:
--   docker compose exec -T postgres psql -U etf -d etf_analytics < scripts/init_db.sql
--
-- PASSWORD: 'etf_reader' is the LOCAL default and must match
-- QA_DB_PASSWORD in .env (see .env.example). For any non-local /
-- shared DB (Neon, Supabase, RDS): change this to a STRONG password
-- when you apply the file, and set QA_DB_PASSWORD to the same value
-- in your secrets. NEVER commit a real password to this file.
-- ---------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'etf_reader') THEN
        CREATE ROLE etf_reader
            LOGIN
            PASSWORD 'etf_reader'
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOREPLICATION;
    END IF;
END $$;

-- dbt materializes marts into the public_marts schema
CREATE SCHEMA IF NOT EXISTS public_marts;
ALTER ROLE etf_reader
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOINHERIT;
ALTER ROLE etf_reader SET default_transaction_read_only = on;
ALTER ROLE etf_reader SET search_path = pg_catalog;
GRANT CONNECT ON DATABASE etf_analytics TO etf_reader;
REVOKE ALL ON SCHEMA raw, staging, marts FROM etf_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA raw, staging, marts FROM etf_reader;
REVOKE CREATE ON SCHEMA public FROM etf_reader;
GRANT USAGE ON SCHEMA public_marts TO etf_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public_marts TO etf_reader;
-- Tables dbt (user "etf") creates later in public_marts stay readable
ALTER DEFAULT PRIVILEGES FOR ROLE etf IN SCHEMA public_marts
    GRANT SELECT ON TABLES TO etf_reader;
