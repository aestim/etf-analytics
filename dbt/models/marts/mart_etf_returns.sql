with prices as (
    select * from {{ ref('stg_etf_prices') }}
),

returns as (
    select
        ticker,
        price_date,
        adj_close,
        volume,
        (adj_close / lag(adj_close) over (partition by ticker order by price_date)) - 1 as daily_return
    from prices
)

select * from returns
