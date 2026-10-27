# ICT day trading on ten years of Alpaca bars - generated tables

Same rules as research/ict.py. 2016-01-04 to 2026-10-26, 2,719 trading days. Universe: the 100 largest US companies at the latest known quarter-end; 222 of 224 companies have Alpaca bars, covering 100% of member-days. Missing: ABLZF, LKNCY. Costs 0.03% each way (stress 0.10%). Portfolio: 10% per trade, at most 10 trades a day, T-bills otherwise.


## Model 1: Silver Bullet, 5-minute bars

2718 trading days with a setup, 2016-01-04 to 2026-10-26.

| rules | trades | win rate | avg R (before costs) | per trade after costs | t-stat | at 0.10% costs | portfolio return/yr | Sharpe |
|---|---|---|---|---|---|---|---|---|
| Pure ICT (both sides, all stocks) | 129658 | 39% | +0.02 | -0.051% | -21.4 | -0.191% | -11.4% | -2.02 |
| + financial bias (long top third, short bottom third) | 40702 | 40% | +0.03 | -0.044% | -9.9 | -0.184% | -10.5% | -2.14 |
| + financials, long only (top third) | 22355 | 41% | +0.04 | -0.035% | -5.7 | -0.175% | -6.1% | -1.37 |
| + trend bias (long above 50-day, short below) | 61495 | 39% | +0.01 | -0.058% | -17.0 | -0.198% | -11.9% | -2.24 |
| + financial and trend bias | 20144 | 40% | +0.03 | -0.047% | -7.6 | -0.187% | -7.8% | -1.96 |
| Longs only (all stocks) | 61443 | 40% | +0.03 | -0.040% | -11.2 | -0.180% | -9.2% | -1.56 |
| Shorts only (all stocks) | 68215 | 38% | +0.01 | -0.060% | -19.3 | -0.200% | -13.8% | -2.39 |
| Control: same trades, coin-flip direction | 129658 | 48% | -0.00 | -0.061% | -25.8 | | | |

How trades ended (pure ICT): stop 62056, close 42177, target 25425.
By quarter, per trade after costs: 2016Q1 -0.03%, 2016Q2 -0.06%, 2016Q3 -0.04%, 2016Q4 -0.04%, 2017Q1 -0.03%, 2017Q2 -0.06%, 2017Q3 -0.07%, 2017Q4 -0.06%, 2018Q1 -0.08%, 2018Q2 -0.03%, 2018Q3 -0.05%, 2018Q4 -0.09%, 2019Q1 -0.05%, 2019Q2 -0.07%, 2019Q3 -0.07%, 2019Q4 -0.05%, 2020Q1 -0.08%, 2020Q2 -0.01%, 2020Q3 -0.01%, 2020Q4 -0.03%, 2021Q1 -0.04%, 2021Q2 -0.04%, 2021Q3 -0.06%, 2021Q4 -0.06%, 2022Q1 -0.06%, 2022Q2 -0.03%, 2022Q3 -0.04%, 2022Q4 +0.02%, 2023Q1 -0.07%, 2023Q2 -0.02%, 2023Q3 -0.04%, 2023Q4 -0.08%, 2024Q1 -0.05%, 2024Q2 -0.05%, 2024Q3 -0.09%, 2024Q4 -0.06%, 2025Q1 +0.02%, 2025Q2 -0.07%, 2025Q3 -0.09%, 2025Q4 -0.05%, 2026Q1 -0.06%, 2026Q2 -0.08%, 2026Q3 -0.06%, 2026Q4 -0.01%.

Silver Bullet (pure) - per trade after costs: 2016-20 -0.051% (59,111 trades), 2021-26 -0.051% (70,547). By year: 2016 -0.043%, 2017 -0.059%, 2018 -0.064%, 2019 -0.059%, 2020 -0.033%, 2021 -0.050%, 2022 -0.029%, 2023 -0.053%, 2024 -0.062%, 2025 -0.047%, 2026 -0.064%.

## Model 2: Judas swing, hourly bars

2718 trading days with a setup, 2016-01-04 to 2026-10-26.

| rules | trades | win rate | avg R (before costs) | per trade after costs | t-stat | at 0.10% costs | portfolio return/yr | Sharpe |
|---|---|---|---|---|---|---|---|---|
| Pure ICT (both sides, all stocks) | 80366 | 42% | -0.00 | -0.053% | -15.8 | -0.193% | -16.2% | -2.70 |
| + financial bias (long top third, short bottom third) | 24826 | 42% | +0.00 | -0.052% | -8.0 | -0.192% | -10.5% | -1.93 |
| + financials, long only (top third) | 13051 | 43% | +0.01 | -0.052% | -5.9 | -0.192% | -5.8% | -1.34 |
| + trend bias (long above 50-day, short below) | 36788 | 42% | +0.00 | -0.057% | -11.2 | -0.197% | -13.5% | -2.36 |
| + financial and trend bias | 11904 | 43% | +0.00 | -0.052% | -5.6 | -0.192% | -5.3% | -1.52 |
| Longs only (all stocks) | 36150 | 43% | +0.00 | -0.054% | -10.6 | -0.194% | -10.8% | -1.81 |
| Shorts only (all stocks) | 44216 | 41% | -0.01 | -0.053% | -11.8 | -0.193% | -12.6% | -2.01 |
| Control: same trades, coin-flip direction | 80366 | 47% | -0.00 | -0.062% | -18.4 | | | |

How trades ended (pure ICT): close 43060, stop 28135, target 9171.
By quarter, per trade after costs: 2016Q1 -0.03%, 2016Q2 -0.07%, 2016Q3 -0.05%, 2016Q4 -0.06%, 2017Q1 -0.07%, 2017Q2 -0.07%, 2017Q3 -0.06%, 2017Q4 -0.08%, 2018Q1 -0.16%, 2018Q2 -0.02%, 2018Q3 -0.05%, 2018Q4 -0.13%, 2019Q1 -0.04%, 2019Q2 -0.09%, 2019Q3 -0.05%, 2019Q4 -0.01%, 2020Q1 -0.26%, 2020Q2 +0.08%, 2020Q3 +0.03%, 2020Q4 -0.01%, 2021Q1 +0.02%, 2021Q2 -0.04%, 2021Q3 -0.05%, 2021Q4 -0.07%, 2022Q1 -0.09%, 2022Q2 -0.05%, 2022Q3 +0.04%, 2022Q4 -0.01%, 2023Q1 -0.04%, 2023Q2 +0.01%, 2023Q3 -0.01%, 2023Q4 -0.08%, 2024Q1 -0.06%, 2024Q2 -0.04%, 2024Q3 -0.06%, 2024Q4 -0.08%, 2025Q1 -0.07%, 2025Q2 -0.07%, 2025Q3 -0.06%, 2025Q4 -0.05%, 2026Q1 -0.04%, 2026Q2 -0.06%, 2026Q3 -0.11%, 2026Q4 -0.17%.

Judas swing (pure) - per trade after costs: 2016-20 -0.059% (36,791 trades), 2021-26 -0.049% (43,575). By year: 2016 -0.051%, 2017 -0.069%, 2018 -0.092%, 2019 -0.048%, 2020 -0.032%, 2021 -0.037%, 2022 -0.025%, 2023 -0.031%, 2024 -0.060%, 2025 -0.063%, 2026 -0.081%.
