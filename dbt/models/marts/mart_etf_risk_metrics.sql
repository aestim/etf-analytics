with returns as (
    select * from {{ ref('mart_etf_returns') }}
),

metrics as (
    select
        ticker,
        price_date,
        stddev_samp(daily_return) over (
            partition by ticker
            order by price_date
            rows between 29 preceding and current row
        ) as rolling_vol_30d,
        (adj_close / max(adj_close) over (
            partition by ticker
            order by price_date
            rows between unbounded preceding and current row
        )) - 1 as drawdown,
        price_date as as_of_date
    from returns
)

select
    ticker,
    price_date,
    rolling_vol_30d,
    -- annualize daily vol so results match how volatility is usually quoted
    rolling_vol_30d * sqrt(252) as annualized_vol_30d,
    drawdown,
    as_of_date
from metrics
