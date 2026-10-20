# Index rotation vs the SPY momentum sleeve - generated tables

2004-06 to 2026-10-19, 3bps costs, cash at T-bills, Sharpe above T-bills.

## 1. Full period

| | cagr | volatility | sharpe | max_drawdown | trades |
|---|---|---|---|---|---|
| Live sleeve: SPY + 12-month switch | 9.4% | 14.4% | 0.58 | -33.7% | 17 |
| Rotation, all 6, top 1 | 12.0% | 20.9% | 0.56 | -29.3% | 143 |
| Rotation, all 6, top 2 | 11.6% | 18.0% | 0.60 | -30.9% | 204 |
| Rotation, all 6, top 3 | 11.0% | 16.8% | 0.60 | -32.7% | 225 |
| Rotation, US only (4), top 1 | 10.6% | 18.5% | 0.54 | -28.6% | 133 |
| Rotation, US only (4), top 2 | 10.8% | 16.5% | 0.60 | -30.9% | 142 |
| Rotation, ex-QQQ (5), top 2 | 8.9% | 17.2% | 0.48 | -38.3% | 192 |
| Each index with its own switch, equal 1/6 | 8.6% | 13.9% | 0.54 | -29.8% | 128 |
| SPY buy & hold | 11.0% | 18.7% | 0.56 | -55.2% | 1 |
| All 6 buy & hold, equal weight | 10.3% | 20.1% | 0.50 | -55.9% | 6 |

## 2. Three eras: return/yr (Sharpe) and worst drop

| | 2004-2012 | 2013-2019 | 2020-2026 |
|---|---|---|---|
| Live sleeve: SPY + 12-month switch | 5.7% (0.35), -25% | 12.0% (0.94), -19% | 11.1% (0.52), -34% |
| Rotation, all 6, top 1 | 12.8% (0.57), -29% | 9.1% (0.57), -23% | 13.1% (0.53), -29% |
| Rotation, all 6, top 2 | 13.2% (0.65), -24% | 8.9% (0.62), -22% | 11.6% (0.51), -31% |
| Rotation, all 6, top 3 | 11.2% (0.59), -22% | 9.7% (0.71), -20% | 11.5% (0.52), -33% |
| Rotation, US only (4), top 1 | 8.6% (0.46), -25% | 13.0% (0.79), -23% | 10.0% (0.42), -29% |
| Rotation, US only (4), top 2 | 9.7% (0.55), -20% | 10.8% (0.75), -22% | 11.8% (0.53), -31% |
| Rotation, ex-QQQ (5), top 2 | 11.2% (0.57), -24% | 6.1% (0.46), -21% | 8.5% (0.38), -35% |
| Each index with its own switch, equal 1/6 | 8.3% (0.49), -24% | 8.0% (0.72), -16% | 9.1% (0.46), -29% |
| SPY buy & hold | 4.9% (0.25), -55% | 14.2% (1.04), -19% | 15.1% (0.66), -34% |
| All 6 buy & hold, equal weight | 7.5% (0.35), -56% | 11.2% (0.79), -19% | 12.2% (0.54), -34% |

## 3. Sensitivity: lookback x top N (all 6) - return/yr, Sharpe, worst drop

| lookback | top 1 | top 2 | top 3 |
|---|---|---|---|
| 6 months | 9.7%, 0.47, -29% | 8.6%, 0.46, -31% | 8.7%, 0.50, -31% |
| 9 months | 9.1%, 0.44, -29% | 8.6%, 0.46, -33% | 8.1%, 0.45, -35% |
| 12 months | 12.0%, 0.56, -29% | 11.6%, 0.60, -31% | 11.0%, 0.60, -33% |

## 4. Costs: 3x trading costs (9bps)

| | cagr | volatility | sharpe | max_drawdown | trades |
|---|---|---|---|---|---|
| Live sleeve: SPY + 12-month switch | 9.4% | 14.4% | 0.57 | -33.7% | 17 |
| Rotation, all 6, top 1 | 11.5% | 20.9% | 0.54 | -29.6% | 143 |
| Rotation, all 6, top 2 | 11.3% | 18.0% | 0.59 | -30.9% | 204 |

## 5. Walk-forward: pick the setting on past data only, then trade it

Every January from 2010, choose the best Sharpe among the 9 grid settings on all data so far, and hold that setting for the year. Stitched out-of-sample result:

| | cagr | volatility | sharpe | max_drawdown |
|---|---|---|---|---|
| Walk-forward rotation (out of sample) | 8.3% | 18.0% | 0.45 | -30.9% |
| Live sleeve, same years | 10.2% | 15.5% | 0.61 | -33.7% |

Settings chosen: 2010: 9m top 1; 2011: 9m top 1; 2012: 12m top 2; 2013: 12m top 2; 2014: 12m top 2; 2015: 12m top 2; 2016: 12m top 2; 2017: 12m top 2; 2018: 12m top 2; 2019: 12m top 2; 2020: 12m top 2; 2021: 12m top 2; 2022: 12m top 2; 2023: 12m top 2; 2024: 12m top 2; 2025: 12m top 2; 2026: 12m top 2

## 6. What the top-1 rotation actually held (share of months)

QQQ 38% | EEM 26% | IWM 13% | cash 9% | EFA 5% | DIA 5% | SPY 4%

Top 2: QQQ 57% | EEM 35% | SPY 25% | IWM 23% | EFA 22% | DIA 15% | fully in cash 9%

Top 1 changed holding 76 times in 269 months.

## 7. In the desk (monthly, 2014-04 to 2026-09): 50% screen + 20% flow rotation + 30% index sleeve

| | cagr | volatility | sharpe | max_drawdown |
|---|---|---|---|---|
| Desk with live sleeve | 16.3% | 16.5% | 0.89 | -23.0% |
| Desk with rotation, all 6, top 1 | 16.7% | 17.5% | 0.86 | -23.9% |
| Desk with rotation, all 6, top 2 | 16.2% | 17.1% | 0.86 | -23.7% |
| Desk with rotation, us only (4), top 2 | 16.3% | 17.1% | 0.86 | -23.7% |

Monthly correlation with the quality screen: Live sleeve: SPY + 12- 0.71, Rotation, all 6, top 1 0.71, Rotation, all 6, top 2 0.74, Rotation, US only (4), 0.77

## 8. Avoid the worst: hold all but the weakest, tilt toward the leaders

Same absolute rule: an index with negative momentum is never held. 'Rank-weighted': with 4 slots the leader gets 40%, then 30%, 20%, 10%. '3/6/12m' ranks on the average of 3-, 6- and 12-month returns.

| | cagr | volatility | sharpe | max_drawdown | trades |
|---|---|---|---|---|---|
| Live sleeve: SPY + 12-month switch | 9.4% | 14.4% | 0.58 | -33.7% | 17 |
| Rotation, all 6, top 2 | 11.6% | 18.0% | 0.60 | -30.9% | 204 |
| SPY buy & hold | 11.0% | 18.7% | 0.56 | -55.2% | 1 |
| Drop worst 1 (hold 5), equal | 9.1% | 14.9% | 0.54 | -34.9% | 187 |
| Drop worst 2 (hold 4), equal | 9.6% | 15.8% | 0.55 | -34.3% | 210 |
| Drop worst 3 (hold 3), equal | 11.0% | 16.8% | 0.60 | -32.7% | 225 |
| Drop worst 2, rank-weighted | 10.7% | 16.8% | 0.58 | -31.9% | 532 |
| Drop worst 1, rank-weighted | 10.2% | 16.1% | 0.57 | -32.2% | 610 |
| Top 2, rank-weighted | 11.8% | 18.7% | 0.59 | -29.9% | 286 |
| Drop worst 2, equal, 3/6/12m | 8.9% | 15.6% | 0.51 | -35.6% | 288 |
| Drop worst 2, rank-weighted, 3/6/12m | 9.8% | 16.6% | 0.54 | -32.7% | 610 |
| Top 2, equal, 3/6/12m | 9.9% | 17.7% | 0.52 | -31.7% | 242 |

### By era: return/yr (Sharpe), worst drop

| | 2004-2012 | 2013-2019 | 2020-2026 |
|---|---|---|---|
| Live sleeve: SPY + 12-month switch | 5.7% (0.35), -25% | 12.0% (0.94), -19% | 11.1% (0.52), -34% |
| Rotation, all 6, top 2 | 13.2% (0.65), -24% | 8.9% (0.62), -22% | 11.6% (0.51), -31% |
| SPY buy & hold | 4.9% (0.25), -55% | 14.2% (1.04), -19% | 15.1% (0.66), -34% |
| Drop worst 1 (hold 5), equal | 8.7% (0.50), -22% | 8.8% (0.72), -19% | 9.3% (0.44), -33% |
| Drop worst 2 (hold 4), equal | 10.1% (0.56), -22% | 8.6% (0.66), -21% | 9.4% (0.43), -33% |
| Drop worst 3 (hold 3), equal | 11.2% (0.59), -22% | 9.7% (0.71), -20% | 11.5% (0.52), -33% |
| Drop worst 2, rank-weighted | 11.4% (0.60), -21% | 9.1% (0.66), -21% | 10.9% (0.49), -32% |
| Drop worst 1, rank-weighted | 10.5% (0.57), -20% | 9.0% (0.68), -20% | 10.4% (0.48), -32% |
| Top 2, rank-weighted | 13.2% (0.63), -24% | 9.0% (0.61), -22% | 12.2% (0.52), -30% |
| Drop worst 2, equal, 3/6/12m | 9.8% (0.56), -18% | 7.2% (0.57), -21% | 8.9% (0.41), -33% |
| Drop worst 2, rank-weighted, 3/6/12m | 11.2% (0.60), -21% | 7.0% (0.52), -21% | 10.4% (0.48), -32% |
| Top 2, equal, 3/6/12m | 12.3% (0.61), -24% | 5.3% (0.39), -21% | 11.4% (0.51), -31% |

### Robustness of the 'drop worst 2' family

| | cagr | volatility | sharpe | max_drawdown | trades |
|---|---|---|---|---|---|
| Drop worst 2, equal - 6m returns | 8.1% | 14.9% | 0.48 | -32.5% | 328 |
| Drop worst 2, equal - 9m returns | 7.9% | 15.4% | 0.46 | -34.5% | 276 |
| Drop worst 2, equal - without QQQ (hold 3 of 5) | 7.8% | 15.8% | 0.45 | -40.8% | 197 |
| Drop worst 2, rank - 6m returns | 8.6% | 16.0% | 0.49 | -31.4% | 670 |
| Drop worst 2, rank - 9m returns | 8.3% | 16.4% | 0.46 | -33.5% | 601 |
| Drop worst 2, rank - without QQQ | 8.4% | 16.7% | 0.46 | -39.5% | 391 |
| Drop worst 2, rank-weighted - 3x costs | 10.5% | 16.8% | 0.57 | -31.9% | 532 |

### Walk-forward across these 9 variants and the live sleeve

| | cagr | volatility | sharpe | max_drawdown |
|---|---|---|---|---|
| Walk-forward pick (out of sample) | 8.0% | 17.8% | 0.44 | -32.7% |
| Live sleeve, same years | 10.2% | 15.5% | 0.61 | -33.7% |

Chosen: 2010: Top 2, equal, 3/6/12m; 2011: Top 2, equal, 3/6/12m; 2012: Top 2, rank-weighted; 2013: Top 2, rank-weighted; 2014: Drop worst 3 (hold 3), equal; 2015: Top 2, rank-weighted; 2016: Top 2, rank-weighted; 2017: Drop worst 3 (hold 3), equal; 2018: Drop worst 3 (hold 3), equal; 2019: Drop worst 3 (hold 3), equal; 2020: Drop worst 3 (hold 3), equal; 2021: Top 2, rank-weighted; 2022: Top 2, rank-weighted; 2023: Top 2, rank-weighted; 2024: Top 2, rank-weighted; 2025: Top 2, rank-weighted; 2026: Top 2, rank-weighted

### In the desk (monthly, 2014-04 to 2026-09)

| | cagr | volatility | sharpe | max_drawdown |
|---|---|---|---|---|
| Desk with live sleeve | 16.3% | 16.5% | 0.89 | -23.0% |
| Desk with drop worst 2 (hold 4), equal | 15.6% | 16.8% | 0.84 | -23.1% |
| Desk with drop worst 2, rank-weighted | 16.0% | 16.9% | 0.85 | -23.2% |
| Desk with drop worst 2, rank-weighted, 3/6/12m | 15.5% | 16.8% | 0.84 | -23.3% |

Monthly correlation with the quality screen: Live sleeve: SPY + 12- 0.71, Drop worst 2 (hold 4), 0.76, Drop worst 2, rank-wei 0.73
