with source as (
    select * from {{ source('raw', 'etf_prices') }}
),

cleaned as (
    select
        upper(trim(ticker)) as ticker,
        price_date,
        adj_close::numeric as adj_close,
        volume
    from source
    where adj_close is not null
),

deduped as (
    select
        *,
        row_number() over (partition by ticker, price_date order by price_date) as rn
    from cleaned
)

select
    ticker,
    price_date,
    adj_close,
    volume
from deduped
where rn = 1
