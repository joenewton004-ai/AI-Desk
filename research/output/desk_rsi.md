# The desk with an RSI dip-buying overlay - generated tables

Monthly, 2014-06 to 2026-09. **Survivors-only prices.** Overlay trades: 535 signals (above SMA200, RSI(14)<30, sell above SMA5), point-in-time top 100. Sharpe above T-bills.

| desk | overlay costs | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | overlay's average weight | overlay's return/yr (desk %) |
|---|---|---|---|---|---|---|---|---|---|
| Current desk (50% quality, 20% momentum, 30% overnight) |  | 21.5% | 15.2% | 1.243 | -21.0% | 1.262 | 1.268 | 0.0% | +0.00% |
| PRIMARY: RSI dips, 3% each (max 5), funded from the overnight sleeve | 0.05% | 21.9% | 15.0% | 1.278 | -21.3% | 1.329 | 1.287 | 1.6% | +0.89% |
| PRIMARY: RSI dips, 3% each (max 5), funded from the overnight sleeve | 0.20% | 21.6% | 15.0% | 1.255 | -21.5% | 1.301 | 1.266 | 1.6% | +0.58% |
| S1: fixed 10% RSI sleeve, pro-rata (45/18/27) | 0.05% | 20.2% | 13.7% | 1.278 | -19.3% | 1.305 | 1.301 | 1.1% | +0.59% |
| S1: fixed 10% RSI sleeve, pro-rata (45/18/27) | 0.20% | 19.9% | 13.7% | 1.262 | -19.4% | 1.284 | 1.286 | 1.1% | +0.39% |
| S2: fixed 10% RSI sleeve, from quality (40/20/30) | 0.05% | 20.5% | 13.6% | 1.308 | -18.3% | 1.331 | 1.339 | 1.1% | +0.59% |
| S2: fixed 10% RSI sleeve, from quality (40/20/30) | 0.20% | 20.2% | 13.6% | 1.291 | -18.4% | 1.309 | 1.324 | 1.1% | +0.39% |
| (S1 without trades: 45/18/27 + 10% T-bills) | | 19.5% | 13.6% | 1.243 | -18.9% | 1.262 | 1.269 | | |
| (S2 without trades: 40/20/30 + 10% T-bills) | | 19.8% | 13.5% | 1.272 | -17.9% | 1.287 | 1.306 | | |
| SPY | | 13.7% | 15% | 0.82 | -24% |

## Against the decision rule (fixed before running)

| desk | overlay costs | Sharpe 2014-19: new vs current | 2020-26 | worst drop: new vs current | Sharpe gap, 90% range (block bootstrap) | better years | passes |
|---|---|---|---|---|---|---|---|
| PRIMARY: RSI dips, 3% each (max 5), funded from the overnight sleeve | 0.05% | 1.329 vs 1.262 | 1.287 vs 1.268 | -21.3% vs -21.0% | +0.035 (+0.012 to +0.069) | 8 of 13 | yes |
| PRIMARY: RSI dips, 3% each (max 5), funded from the overnight sleeve | 0.20% | 1.301 vs 1.262 | 1.266 vs 1.268 | -21.5% vs -21.0% | +0.013 (-0.012 to +0.048) | 7 of 13 | no |
| S1: fixed 10% RSI sleeve, pro-rata (45/18/27) | 0.05% | 1.305 vs 1.262 | 1.301 vs 1.268 | -19.3% vs -21.0% | +0.036 (+0.020 to +0.060) | 3 of 13 | yes |
| S1: fixed 10% RSI sleeve, pro-rata (45/18/27) | 0.20% | 1.284 vs 1.262 | 1.286 vs 1.268 | -19.4% vs -21.0% | +0.019 (+0.002 to +0.043) | 3 of 13 | yes |
| S2: fixed 10% RSI sleeve, from quality (40/20/30) | 0.05% | 1.331 vs 1.262 | 1.339 vs 1.268 | -18.3% vs -21.0% | +0.065 (+0.038 to +0.095) | 3 of 13 | yes |
| S2: fixed 10% RSI sleeve, from quality (40/20/30) | 0.20% | 1.309 vs 1.262 | 1.324 vs 1.268 | -18.4% vs -21.0% | +0.048 (+0.022 to +0.078) | 3 of 13 | yes |

Primary passes the full rule (both halves + drop + still better at 0.20%): no.

## Year by year (primary, 0.05%)

| year | current | with the overlay | difference | overlay's own contribution |
|---|---|---|---|---|
| 2014 | +10.2% | +10.1% | -0.10% | -0.11% |
| 2015 | +3.9% | +5.3% | +1.34% | +1.20% |
| 2016 | +15.7% | +16.5% | +0.83% | +1.14% |
| 2017 | +36.5% | +35.7% | -0.88% | +0.08% |
| 2018 | -0.0% | +1.4% | +1.48% | +1.27% |
| 2019 | +26.6% | +27.6% | +1.05% | +0.65% |
| 2020 | +43.9% | +45.0% | +1.08% | +0.61% |
| 2021 | +28.8% | +30.6% | +1.77% | +2.90% |
| 2022 | -15.8% | -16.3% | -0.50% | -0.83% |
| 2023 | +31.3% | +32.5% | +1.20% | +1.09% |
| 2024 | +37.5% | +36.5% | -1.01% | +1.93% |
| 2025 | +21.9% | +22.2% | +0.37% | +0.59% |
| 2026 | +40.4% | +38.9% | -1.46% | +0.45% |

Monthly correlation of the overlay's contribution with the current desk: 0.10. The market's 10 worst months: overlay +0.09% on average, current desk -6.1%.
