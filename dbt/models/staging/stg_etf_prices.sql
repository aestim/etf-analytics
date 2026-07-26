with source as (
    select * from {{ source('raw', 'etf_prices') }}
),

cleaned as (
    select
        upper(trim(ticker)) as ticker,
        price_date,
        adj_close::numeric as adj_close,
        volume,
        ingested_at
    from source
    where adj_close is not null
),

-- Keep the most recently ingested row per (ticker, price_date) so a re-ingest
-- with corrected vendor data deterministically wins.
deduped as (
    select
        *,
        row_number() over (
            partition by ticker, price_date
            order by ingested_at desc
        ) as rn
    from cleaned
)

select
    ticker,
    price_date,
    adj_close,
    volume
from deduped
where rn = 1
