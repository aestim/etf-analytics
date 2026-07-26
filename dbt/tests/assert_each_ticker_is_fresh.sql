-- Global MAX(as_of_date) can hide one stalled ticker behind healthy peers.
-- Compare every ticker present in the mart with its own newest risk row.
-- Ingest itself fails if a configured ticker returns no rows.
with latest_by_ticker as (
    select
        ticker,
        max(as_of_date) as latest_as_of_date
    from {{ ref('mart_etf_risk_metrics') }}
    group by ticker
)

select ticker, latest_as_of_date
from latest_by_ticker
where latest_as_of_date is null
   or latest_as_of_date < current_date - interval '7 days'
