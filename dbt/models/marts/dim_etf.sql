-- Ticker reference dimension, sourced from the etf_info seed.
-- Joins to mart_etf_returns / mart_etf_risk_metrics on ticker.

select
    upper(ticker) as ticker,
    name,
    asset_class,
    sub_class,
    leverage,
    description
from {{ ref('etf_info') }}
