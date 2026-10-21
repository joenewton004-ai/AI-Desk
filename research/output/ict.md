# ICT day trading - generated tables

Rules fixed in research/ict.py before running. Universe = the 100 largest US companies at the latest quarter-end known at the time (filings assumed public 45 days after it). Costs 0.03% each way (stress 0.10%). Portfolio: 10% of the account per trade, at most 10 trades a day, cash otherwise (Sharpe above T-bills). Yahoo intraday bars, regular hours only.


## Model 1: Silver Bullet, 5-minute bars (last ~60 days only - a short sample)

59 trading days with a setup, 2026-07-28 to 2026-10-20.

| rules | trades | win rate | avg R (before costs) | per trade after costs | t-stat | at 0.10% costs | portfolio return/yr | Sharpe |
|---|---|---|---|---|---|---|---|---|
| Pure ICT (both sides, all stocks) | 2974 | 41% | +0.01 | -0.061% | -3.5 | -0.201% | -17.5% | -2.59 |
| + financial bias (long top third, short bottom third) | 959 | 41% | +0.02 | -0.068% | -2.0 | -0.208% | -23.4% | -4.75 |
| + financials, long only (top third) | 619 | 42% | +0.07 | -0.001% | -0.0 | -0.141% | +4.0% | 0.03 |
| + trend bias (long above 50-day, short below) | 1445 | 40% | -0.02 | -0.085% | -3.4 | -0.225% | -22.3% | -4.00 |
| + financial and trend bias | 540 | 39% | -0.04 | -0.118% | -2.7 | -0.258% | -21.3% | -5.16 |
| Longs only (all stocks) | 1506 | 44% | +0.09 | +0.015% | 0.6 | -0.125% | -8.2% | -1.49 |
| Shorts only (all stocks) | 1468 | 38% | -0.07 | -0.139% | -5.9 | -0.279% | -32.2% | -6.43 |
| Control: same trades, coin-flip direction | 2974 | 47% | -0.02 | -0.067% | -3.8 | | | |

How trades ended (pure ICT): stop 1249, close 1242, target 483.
By quarter, per trade after costs: 2026Q3 -0.09%, 2026Q4 +0.03%.

## Model 2: Judas swing, hourly bars (~3 years)

728 trading days with a setup, 2023-11-21 to 2026-10-20.

| rules | trades | win rate | avg R (before costs) | per trade after costs | t-stat | at 0.10% costs | portfolio return/yr | Sharpe |
|---|---|---|---|---|---|---|---|---|
| Pure ICT (both sides, all stocks) | 21483 | 42% | -0.01 | -0.066% | -10.0 | -0.206% | -19.0% | -3.67 |
| + financial bias (long top third, short bottom third) | 6816 | 43% | -0.01 | -0.065% | -5.3 | -0.205% | -14.1% | -3.00 |
| + financials, long only (top third) | 3490 | 44% | +0.00 | -0.046% | -2.6 | -0.186% | -6.1% | -1.84 |
| + trend bias (long above 50-day, short below) | 9853 | 42% | -0.02 | -0.079% | -8.0 | -0.219% | -17.5% | -3.38 |
| + financial and trend bias | 3292 | 43% | -0.02 | -0.067% | -3.8 | -0.207% | -7.7% | -2.55 |
| Longs only (all stocks) | 9730 | 43% | -0.01 | -0.060% | -6.2 | -0.200% | -13.5% | -2.47 |
| Shorts only (all stocks) | 11753 | 41% | -0.01 | -0.071% | -7.8 | -0.211% | -18.7% | -3.11 |
| Control: same trades, coin-flip direction | 21483 | 47% | -0.01 | -0.070% | -10.5 | | | |

How trades ended (pure ICT): close 12131, stop 7120, target 2232.
By quarter, per trade after costs: 2023Q4 -0.09%, 2024Q1 -0.05%, 2024Q2 -0.04%, 2024Q3 -0.06%, 2024Q4 -0.08%, 2025Q1 -0.06%, 2025Q2 -0.08%, 2025Q3 -0.07%, 2025Q4 -0.05%, 2026Q1 -0.04%, 2026Q2 -0.06%, 2026Q3 -0.12%, 2026Q4 -0.16%.

SPY over the Model 1 window: +3.7% (59 days).

SPY over the Model 2 window: +75.4% (729 days).
