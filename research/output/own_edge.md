# Our own edge: a search across indicators, judged on years the search never saw - generated tables

Excess per week = the picks' 5-day return (next open to the open 5 days later) minus the universe's average (stocks) or the ETF's own average (ETFs). Strategy = the weekly portfolio after costs. **Stock prices are survivors-only.**

## stocks: 2014-05-15 to 2020-01-01 (search), 2020-01-01 to 2026-10-12 (holdout)

Searched 317 single buckets and 4401 pair cells on the development years.

| candidate | development: avg excess per week | t | holdout: avg excess per week | t | weeks beat | names held | strategy return/yr, Sharpe, worst | universe |
|---|---|---|---|---|---|---|---|---|
| single: intraday_20d bucket 4/10 | +0.08% | 2.6 | -0.02% | -0.5 | 50% | 50 | +6.5%, 0.42, -35% | +12.1%, 0.69, -34% |
| single: ret_1d bucket 4/10 | +0.06% | 2.4 | -0.05% | -1.1 | 47% | 50 | +4.7%, 0.34, -36% | +12.1%, 0.69, -34% |
| single: gap bucket 5/10 | +0.07% | 2.4 | -0.07% | -1.8 | 45% | 51 | +3.7%, 0.29, -33% | +12.1%, 0.69, -34% |
| single: ret_60d bucket 6/10 | +0.07% | 2.2 | -0.06% | -1.5 | 46% | 50 | +5.3%, 0.37, -34% | +12.1%, 0.69, -34% |
| single: volume_5_60 bucket 10/10 | +0.09% | 2.2 | -0.05% | -0.9 | 50% | 50 | +5.0%, 0.34, -41% | +12.1%, 0.69, -34% |
| pair: ret_10d low + ret_120d high | +0.21% | 3.1 | +0.18% | 1.6 | 55% | 39 | +17.2%, 0.77, -40% | +12.1%, 0.69, -34% |
| pair: ret_10d low + vix mid | +0.15% | 3.0 | +0.01% | 0.1 | 48% | 166 | -0.4%, -0.04, -16% | +12.1%, 0.69, -34% |
| pair: vol_ratio_5_60 mid + volume_5_60 low | +0.09% | 2.9 | +0.01% | 0.2 | 52% | 59 | +7.9%, 0.47, -35% | +12.1%, 0.69, -34% |
| pair: atr_pct low + spy_ret_5d mid | +0.18% | 2.8 | -0.29% | -2.0 | 37% | 166 | +1.1%, 0.26, -10% | +12.1%, 0.69, -34% |
| pair: vs_sma5 mid + range_vs_20d high | +0.10% | 2.8 | -0.07% | -1.4 | 48% | 40 | +3.3%, 0.27, -35% | +12.1%, 0.69, -34% |
| pair: ret_10d low + ret_250d mid | +0.11% | 2.8 | +0.02% | 0.3 | 50% | 51 | +9.5%, 0.54, -37% | +12.1%, 0.69, -34% |
| pair: ret_10d low + vs_sma200 high | +0.20% | 2.7 | +0.17% | 1.3 | 55% | 33 | +15.9%, 0.70, -40% | +12.1%, 0.69, -34% |
| pair: ret_10d low + ret_60d high | +0.16% | 2.7 | +0.12% | 1.0 | 50% | 31 | +12.7%, 0.59, -40% | +12.1%, 0.69, -34% |
| pair: ret_120d high + vs_sma20 low | +0.20% | 2.7 | +0.16% | 1.4 | 56% | 35 | +16.6%, 0.74, -38% | +12.1%, 0.69, -34% |
| pair: rsi_14 mid + vix low | +0.07% | 2.6 | +0.20% | 2.2 | 83% | 167 | +1.1%, 0.40, -4% | +12.1%, 0.69, -34% |
| model (LightGBM, top 20 each week) | +0.41% | 3.8 | +0.41% | 2.4 | 55% | 18 | +27.5%, 0.86, -52% | +12.1%, 0.69, -34% |

Model holdout, average 5-day excess by score decile (1 = lowest): 1: -0.18%, 2: -0.03%, 3: -0.06%, 4: +0.03%, 5: +0.05%, 6: -0.06%, 7: +0.03%, 8: +0.02%, 9: +0.07%, 10: +0.12%
Model's most-used indicators: spy_vs_sma200 (39%), vix (8%), ret_60d (6%), ret_120d (5%), spy_ret_5d (5%), vs_52w_low (4%), vs_sma20 (4%), vol_20d (4%)

## ETFs: 1999-06-01 to 2013-01-01 (search), 2013-01-01 to 2026-10-20 (holdout)

Searched 317 single buckets and 4501 pair cells on the development years.

| candidate | development: avg excess per week | t | holdout: avg excess per week | t | weeks beat | names held | strategy return/yr, Sharpe, worst | universe |
|---|---|---|---|---|---|---|---|---|
| single: spy_vs_sma200 bucket 6/10 | +0.40% | 2.4 | -0.20% | -1.3 | 49% | 25 | -0.3%, -0.09, -11% | +8.7%, 0.77, -25% |
| single: volume_5_60 bucket 8/10 | +0.30% | 2.0 | -0.00% | -0.0 | 53% | 3 | +3.2%, 0.27, -30% | +8.7%, 0.77, -25% |
| single: spy_ret_5d bucket 2/10 | +0.47% | 1.9 | +0.47% | 1.6 | 69% | 25 | +2.1%, 0.53, -13% | +8.7%, 0.77, -25% |
| single: vs_sma20 bucket 7/10 | +0.18% | 1.9 | -0.16% | -2.1 | 48% | 3 | -1.2%, -0.04, -45% | +8.7%, 0.77, -25% |
| single: vs_sma200 bucket 6/10 | +0.15% | 1.7 | -0.05% | -0.7 | 50% | 3 | +4.5%, 0.45, -22% | +8.7%, 0.77, -25% |
| pair: ret_2d mid + rsi_14 mid | +0.28% | 2.8 | -0.03% | -0.4 | 51% | 4 | +3.3%, 0.33, -21% | +8.7%, 0.77, -25% |
| pair: spy_vs_sma200 mid + weekday mid | +0.43% | 2.4 | +0.13% | 0.8 | 58% | 25 | +1.9%, 0.52, -12% | +8.7%, 0.77, -25% |
| pair: ret_5d low + mom_12_1 low | +0.43% | 2.1 | -0.01% | -0.1 | 51% | 3 | -3.0%, 0.00, -80% | +8.7%, 0.77, -25% |
| pair: vol_ratio_5_60 low + spy_vs_sma200 mid | +0.31% | 2.1 | -0.00% | -0.0 | 54% | 9 | +1.4%, 0.26, -23% | +8.7%, 0.77, -25% |
| pair: vol_ratio_5_60 high + spy_ret_5d low | +0.53% | 2.1 | +0.28% | 1.1 | 60% | 11 | +4.3%, 0.44, -20% | +8.7%, 0.77, -25% |
| pair: vs_sma200 mid + overnight_20d low | +0.22% | 2.1 | -0.03% | -0.4 | 54% | 4 | +3.5%, 0.33, -34% | +8.7%, 0.77, -25% |
| pair: ret_20d high + range_vs_20d high | +0.27% | 2.1 | -0.08% | -0.6 | 48% | 3 | -0.0%, 0.09, -55% | +8.7%, 0.77, -25% |
| pair: mom_12_1 low + vix low | +0.28% | 2.0 | -0.16% | -1.7 | 49% | 7 | -3.7%, -0.29, -53% | +8.7%, 0.77, -25% |
| pair: vol_20d low + spy_vs_sma200 mid | +0.14% | 2.0 | -0.06% | -0.9 | 53% | 11 | +1.1%, 0.32, -13% | +8.7%, 0.77, -25% |
| pair: ret_5d low + vix low | +0.28% | 1.9 | -0.23% | -2.0 | 49% | 6 | -5.6%, -0.38, -66% | +8.7%, 0.77, -25% |
| model (LightGBM, top 3 each week) | +0.31% | 2.4 | -0.00% | -0.0 | 52% | 2 | -2.9%, 0.02, -70% | +8.7%, 0.77, -25% |

Model holdout, average 5-day excess by score decile (1 = lowest): 1: -0.06%, 2: -0.03%, 3: -0.01%, 4: +0.06%, 5: +0.13%, 6: -0.12%, 7: -0.01%, 8: +0.07%, 9: -0.01%, 10: -0.01%
Model's most-used indicators: spy_vs_sma200 (26%), vix (19%), spy_ret_5d (13%), vs_sma50 (6%), vix_chg_5d (4%), ret_20d (4%), vs_sma20 (3%), ret_250d (3%)
