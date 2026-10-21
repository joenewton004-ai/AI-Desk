# Four swing-trading effects with realistic fills - generated tables

Daily, 2014-04-01 to 2026-10-20; universe = the 750 largest US companies at each quarter-end (point-in-time); survivors-only Yahoo prices. Decide at a close, fill at the next open. Costs per trade each way as shown. Idle cash earns T-bills; Sharpe above T-bills.

## Benchmarks

| | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | trades | |
|---|---|---|---|---|---|---|---|---|
| Equal-weight universe (always invested) | 12.1% | 19% | 0.59 | -40% | 0.75 | 0.52 |  |  |
| SPY (always invested) | 13.7% | 17% | 0.72 | -34% | 0.86 | 0.66 |  |  |

## 1. Weekly pullback and reversal, bought at Monday's open

20 positions of 5%, chosen at Friday's close, sold at the next Monday's open (5 trading days).

| | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | trades | |
|---|---|---|---|---|---|---|---|---|
| Pullback: 20 weakest weeks among strong uptrends, costs 0.02% | 11.1% | 23% | 0.49 | -54% | 0.22 | 0.65 | 10940 |  |
| Pullback: 20 weakest weeks among strong uptrends, costs 0.05% | 8.2% | 23% | 0.37 | -56% | 0.07 | 0.55 | 10940 |  |
| Pullback: 20 weakest weeks among strong uptrends, costs 0.10% | 3.6% | 23% | 0.19 | -59% | -0.19 | 0.39 | 10940 |  |
| Reversal: 20 weakest weeks, any stock, costs 0.02% | 11.0% | 31% | 0.43 | -65% | 0.18 | 0.57 | 10940 |  |
| Reversal: 20 weakest weeks, any stock, costs 0.05% | 8.2% | 31% | 0.35 | -66% | 0.05 | 0.50 | 10940 |  |
| Pullback at zero cost (for reference) | 13.1% | 23% | 0.56 | -53% | 0.32 | 0.71 | 10940 |  |

## 2. Post-earnings drift (after the 10-Q is filed)

42365 quarterly reports with a surprise measure. Buy the top fifth of surprises at the open after the filing day, hold 60 trading days; up to 30 positions.

| | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | trades | |
|---|---|---|---|---|---|---|---|---|
| Top-fifth surprises, costs 0.02% | 11.5% | 17% | 0.62 | -25% | 0.44 | 0.74 | 1388 |  |
| Top-fifth surprises, costs 0.05% | 11.3% | 17% | 0.61 | -25% | 0.42 | 0.73 | 1388 |  |
| Top-fifth surprises, costs 0.10% | 10.9% | 17% | 0.59 | -25% | 0.40 | 0.71 | 1388 |  |
| (Bottom-fifth surprises, bought - should lag) | 8.3% | 18% | 0.42 | -32% | 0.63 | 0.31 | 1339 |  |

Event study, each report's next 60 trading days (open to open) minus the average stock:

| surprise fifth | reports | excess return | t-stat |
|---|---|---|---|
| 1 (worst) | 4350 | -0.55% | -2.6 |
| 2  | 4349 | -0.63% | -3.0 |
| 3  | 4350 | -0.36% | -1.7 |
| 4  | 4349 | -0.17% | -0.8 |
| 5 (best) | 4350 | +0.11% | 0.5 |

2014-19: best fifth +0.04%, worst fifth -0.47% (spread +0.51%).

2020-26: best fifth +0.16%, worst fifth -0.60% (spread +0.77%).

## 3. 52-week high

| | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | trades | |
|---|---|---|---|---|---|---|---|---|
| Monthly: 50 stocks closest to their 52-week high, costs 0.02% | 8.8% | 13% | 0.55 | -21% | 0.37 | 0.68 | 5450 |  |
| Monthly: 50 stocks closest to their 52-week high, costs 0.05% | 8.2% | 13% | 0.51 | -21% | 0.32 | 0.65 | 5450 |  |
| (Monthly: 50 furthest from their high - should lag) | 10.2% | 27% | 0.42 | -49% | 0.36 | 0.47 | 5450 |  |
| Swing: new 52-week-high closes, hold 20 days, 20 slots, costs 0.02% | 7.5% | 17% | 0.40 | -36% | 0.56 | 0.32 | 3084 |  |
| Swing: new 52-week-high closes, hold 20 days, 20 slots, costs 0.05% | 6.7% | 17% | 0.35 | -36% | 0.50 | 0.28 | 3084 |  |

## 4. Overnight vs daytime returns

Overnight = buy at the close, sell at the next open; daytime = buy at the open, sell at the close. Both trade every day, so costs are paid twice a day.

| | gross return/yr | at 0.02% each way | at 0.05% each way | share of days positive |
|---|---|---|---|---|
| SPY overnight | +9.0% | -1.5% | -15.3% | 56% |
| SPY daytime | +4.4% | -5.6% | -18.9% | 54% |
| Average stock overnight | +9.9% | -0.7% | -14.6% | 56% |
| Average stock daytime | +5.5% | -4.6% | -18.0% | 52% |
