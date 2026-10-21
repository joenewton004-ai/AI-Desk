# Swing trading (VCP breakouts) - generated tables

Daily, 2014-04-01 to 2026-10-20; universe = the 750 largest US companies at each quarter-end (point-in-time); survivors-only Yahoo prices. Decide at the close, fill at the next open. Up to 10 positions of 10%; idle cash earns T-bills; 0.10% per trade each way. Sharpe above T-bills.

## 1. The strategy against its benchmarks

| | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | avg invested |
|---|---|---|---|---|---|---|---|
| VCP breakouts (base rules) | 2.8% | 16% | 0.13 | -30% | -0.14 | 0.30 | 86% |
| Control: random strong-trend stocks, same exits | -0.2% | 15% | -0.07 | -40% | 0.20 | -0.25 | 83% |
| Equal-weight universe (always invested) | 12.1% | 19% | 0.59 | -40% | 0.75 | 0.52 | 100% |
| SPY (always invested) | 13.7% | 17% | 0.72 | -34% | 0.86 | 0.66 | 100% |

## 2. The trades

| | trades | win rate | avg win | avg loss | per trade | profit factor | avg days held |
|---|---|---|---|---|---|---|---|
| VCP breakouts | 1123 | 39% | +10.6% | -6.1% | +0.38% | 1.10 | 24 |
| Control | 1371 | 32% | +9.8% | -4.5% | +0.03% | 1.01 | 19 |

How the VCP trades ended:

| exit | trades | avg return |
|---|---|---|
| below 50-day | 556 | -3.6% |
| stop | 194 | -10.3% |
| target | 56 | +27.9% |
| time | 317 | +9.1% |

## 3. Stress tests (the backtest-expert checklist)

Costs, then one setting at a time around the base rules. A real edge should hold up across them.

| change | return/yr | Sharpe | worst drop | trades | per trade |
|---|---|---|---|---|---|
| Base rules | 2.8% | 0.13 | -30% | 1123 | +0.38% |
| Costs 0.20% each way | 1.0% | 0.02 | -35% | 1123 | +0.18% |
| Costs 0.30% each way | -0.7% | -0.09 | -41% | 1123 | -0.02% |
| Stop 6% | 2.5% | 0.11 | -28% | 1188 | +0.32% |
| Stop 10% | 3.7% | 0.18 | -26% | 1104 | +0.49% |
| Target 15% | 4.1% | 0.21 | -29% | 1231 | +0.50% |
| Target 35% | 3.8% | 0.19 | -30% | 1105 | +0.54% |
| No target | 3.7% | 0.19 | -29% | 1089 | +0.54% |
| Max hold 20 days | 0.4% | -0.03 | -32% | 1683 | +0.08% |
| Max hold 60 days | 4.3% | 0.23 | -28% | 977 | +0.62% |
| Breakout above 50-day high | 3.4% | 0.17 | -25% | 1046 | +0.45% |
| Volume 2x average | 2.0% | 0.07 | -23% | 952 | +0.28% |
| Volume 1.2x average | 2.6% | 0.12 | -35% | 1210 | +0.35% |
| Looser base (range under 70%) | -0.2% | -0.05 | -33% | 1150 | +0.07% |
| 5 positions of 20% | 5.6% | 0.28 | -38% | 584 | +0.73% |
| 20 positions of 5% | 3.4% | 0.17 | -21% | 2083 | +0.44% |

## 4. Year by year

| year | VCP breakouts | control | equal-weight universe | SPY |
|---|---|---|---|---|
| 2014 | +9.3% | +6.8% | +7.0% | +10.8% |
| 2015 | -15.9% | -11.9% | -3.2% | +1.2% |
| 2016 | -6.7% | +5.9% | +21.8% | +12.0% |
| 2017 | +23.1% | +22.6% | +22.6% | +21.7% |
| 2018 | -21.5% | -3.3% | -8.8% | -4.6% |
| 2019 | +8.8% | -1.7% | +31.0% | +31.2% |
| 2020 | +26.9% | +12.4% | +22.5% | +18.3% |
| 2021 | +16.7% | +13.9% | +24.3% | +28.7% |
| 2022 | -12.0% | -14.6% | -15.2% | -18.2% |
| 2023 | +2.1% | -12.3% | +20.8% | +26.2% |
| 2024 | +25.5% | +1.1% | +13.7% | +24.9% |
| 2025 | -2.5% | -5.8% | +12.5% | +17.7% |
| 2026 | -3.5% | -7.7% | +13.2% | +13.3% |

VCP beat the equal-weight universe in 5 of 13 years and SPY in 4.
