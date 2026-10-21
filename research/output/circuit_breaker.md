# Drawdown circuit breaker on the desk - generated tables

Weekly, 2014-04-11 to 2026-10-16. Desk = 50% quality screen + 20% plain momentum (100-day exit) + 30% SPY with its 12-month switch. Survivors-only prices. 0.10% per trade (stress 0.30%). Sharpe above T-bills.

| | return/yr | volatility | Sharpe | worst drop | at 3x costs | 2014-19 Sharpe | 2020-26 Sharpe | weeks halted | times tripped |
|---|---|---|---|---|---|---|---|---|---|
| Desk as it is (no breaker) | 15.8% | 17.9% | 0.80 | -31.3% | 14.9% | 0.95 | 0.74 | 0 | 0 |
| Skill defaults, freeze buys (5% week / 8% month) | 15.6% | 17.8% | 0.80 | -30.6% | 14.5% | 0.96 | 0.72 | 31 | 17 |
| Skill defaults, go to cash | 14.1% | 16.5% | 0.77 | -30.9% | 12.7% | 0.83 | 0.74 | 27 | 17 |
| Tighter, freeze (3% week / 6% month) | 15.1% | 17.5% | 0.78 | -30.6% | 14.2% | 0.96 | 0.69 | 83 | 48 |
| Tighter, go to cash | 11.8% | 15.6% | 0.67 | -28.7% | 9.3% | 0.65 | 0.69 | 64 | 53 |
| Looser, freeze (7% week / 10% month) | 15.8% | 17.8% | 0.80 | -30.6% | 14.9% | 0.95 | 0.74 | 15 | 8 |
| Looser, go to cash | 15.2% | 17.1% | 0.80 | -31.2% | 14.1% | 0.87 | 0.78 | 15 | 8 |

## When the skill's defaults tripped, and what the desk did over the next 3 months

| halted from | weeks | desk next 13 weeks (no breaker) | with freeze | with cash |
|---|---|---|---|---|
| 2015-08-28 | 1 | -0.9% | -1.5% | -6.0% |
| 2015-11-20 | 1 | -8.7% | -9.1% | -9.3% |
| 2016-01-15 | 4 | +4.3% | +4.5% | +7.6% |
| 2018-02-16 | 3 | +9.2% | +9.2% | +2.9% |
| 2018-03-30 | 1 | +11.8% | +11.8% | +10.2% |
| 2018-10-19 | 3 | -5.3% | -4.9% | -8.8% |
| 2018-12-28 | 2 | +13.4% | +13.4% | +9.1% |
| 2020-03-06 | 1 | -1.9% | -1.2% | +7.6% |
| 2020-03-20 | 3 | +8.9% | +8.6% | +18.4% |
| 2020-11-06 | 1 | +23.4% | +23.4% | +11.4% |
| 2022-01-14 | 1 | -4.1% | -4.5% | -4.9% |
| 2022-01-28 | 2 | -1.7% | -2.2% | -3.2% |
| 2022-05-06 | 1 | -3.3% | -2.8% | -5.5% |
| 2022-06-24 | 2 | +4.6% | +5.2% | +2.5% |
| 2024-04-26 | 2 | +10.8% | +9.1% | +4.8% |
| 2024-09-13 | 1 | +23.1% | +22.5% | +16.4% |
| 2025-04-04 | 2 | +9.3% | +8.0% | +18.7% |

(The cash version tripped 17 times; its dates can differ once its own returns diverge.)

## Year by year: skill defaults minus the desk as it is

| year | desk | freeze | cash |
|---|---|---|---|
| 2014 | +14.4% | +0.0% | +0.0% |
| 2015 | -0.7% | -0.5% | -5.1% |
| 2016 | +11.7% | +0.2% | +3.5% |
| 2017 | +31.4% | +0.0% | +0.0% |
| 2018 | -3.0% | +0.4% | -8.1% |
| 2019 | +33.1% | +0.0% | -1.3% |
| 2020 | +19.3% | +0.9% | -1.1% |
| 2021 | +26.6% | +0.0% | +0.0% |
| 2022 | -21.3% | +0.0% | -2.4% |
| 2023 | +35.7% | +0.0% | +0.0% |
| 2024 | +30.3% | -2.6% | -13.7% |
| 2025 | +13.8% | -1.3% | +9.8% |
| 2026 | +23.2% | +0.0% | +0.0% |

## Part 2: daily prices, adding the 2% daily limit

Same desk, same decisions (taken from the latest Friday), but held and checked day by day. Statistics are annualised from daily returns.

| | return/yr | volatility | Sharpe | worst drop | days halted | times tripped |
|---|---|---|---|---|---|---|
| Desk as it is (no breaker) | 16.4% | 18.5% | 0.81 | -33.4% | 0 | 0 |
| Skill defaults, freeze buys (2% day / 5% week / 8% month) | 15.9% | 18.2% | 0.79 | -33.4% | 258 | 102 |
| Skill defaults, go to cash | 11.1% | 16.4% | 0.61 | -35.7% | 238 | 117 |
| Daily limit only (2%), freeze | 16.3% | 18.4% | 0.81 | -33.4% | 128 | 112 |
| Daily limit only (2%), go to cash | 13.1% | 17.6% | 0.68 | -32.7% | 117 | 117 |
| Looser (3% day / 7% week / 10% month), go to cash | 15.8% | 16.8% | 0.84 | -34.2% | 106 | 40 |
