# Metric Contract

This is the single definition used by the dashboard, natural-language Q&A, and
technical documentation. Prices are Yahoo Finance `Adj Close` values fetched
with `auto_adjust=False`. Ingest must fail if that field is unavailable; raw
`Close` must never be substituted.

## Requested-period metrics

For ticker \(i\), first filter adjusted-price observations to the inclusive
requested date window. Let \(P_0,\ldots,P_n\) be those filtered observations in
date order.

| Metric | Definition | Required coverage |
|---|---|---|
| `period_return` | \(P_n / P_0 - 1\) | at least 2 prices |
| `period_annualized_volatility` | sample standard deviation of \(P_t/P_{t-1}-1\) for \(t=1,\ldots,n\), multiplied by \(\sqrt{252}\) | at least 2 returns |
| `period_max_drawdown` | minimum of \(P_t/\max(P_0,\ldots,P_t)-1\) | at least 1 price |
| coverage | `period_start`, `period_end`, `price_observations`, and `return_observations = price_observations - 1` | always return these fields for an aggregated period metric |

Consequences:

- Recompute returns after filtering the price window. The first in-window price
  is the baseline, not a return from a price before the requested period.
- Reset the running peak at the first in-window price when computing period
  maximum drawdown.
- Do not use the average of `rolling_vol_30d` or
  `annualized_vol_30d` as period volatility.
- Do not take `MIN(drawdown)` from the rolling-risk mart as period maximum
  drawdown because that series carries peaks from before the requested window.
- A ranking must apply the same window and minimum coverage rule to every
  ticker. Rows with inadequate coverage are excluded, not compared as if full.

## Point-in-time rolling metrics

`mart_etf_risk_metrics` intentionally has different semantics:

- `rolling_vol_30d` is the trailing 30-observation sample standard deviation of
  daily returns as of each date.
- `annualized_vol_30d` is that rolling value multiplied by \(\sqrt{252}\).
- `drawdown` is the as-of decline from the highest adjusted close in all
  warehouse history available up to that date.

These fields are appropriate for an as-of risk snapshot or a rolling time
series. They are not substitutes for requested-period volatility or maximum
drawdown.
