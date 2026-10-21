# Minervini SEPA as fixed rules - generated tables

Daily, 2014-04-01 to 2026-10-20; universe = the 750 largest US companies at each quarter-end (point-in-time); **survivors-only Yahoo prices**. Growth figures from SEC filings as first reported, usable the day after filing (1298 of 1448 companies covered). Decide at the close, fill at the next open; up to 10 positions of 10%; idle cash earns T-bills; 0.10% per trade each way. Sharpe above T-bills.

## 1. Layer by layer

| | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | trades | invested |
|---|---|---|---|---|---|---|---|---|
| A. Trend Template + RS 70, held while it qualifies | 11.8% | 31% | 0.45 | -48% | -0.09 | 0.73 | 1240 | 99% |
| B. + EPS 25% / sales 20% growth | 7.0% | 22% | 0.33 | -35% | -0.06 | 0.48 | 1210 | 65% |
| C. + EPS accelerating | 5.3% | 19% | 0.26 | -32% | 0.16 | 0.33 | 1135 | 54% |
| D. B + his stops (7.5%, break-even at +15%, then 50-day) | 5.7% | 22% | 0.27 | -35% | -0.06 | 0.40 | 1275 | 65% |
| E. Full SEPA: B's stocks on a base breakout, his stops | 5.2% | 14% | 0.30 | -24% | 0.55 | 0.24 | 238 | 37% |
| F. E + market filter (SPY above its 200-day) | 5.4% | 13% | 0.31 | -23% | 0.55 | 0.26 | 220 | 34% |
| G. E without the growth rules (chart only) | 1.6% | 18% | 0.07 | -41% | 0.16 | 0.02 | 508 | 91% |
| Equal-weight universe | 12.1% | 19% | 0.59 | -40% | 0.75 | 0.52 |  | 100% |
| Equal-weight, companies with SEC growth data | 12.2% | 19% | 0.59 | -40% | 0.75 | 0.53 |  | 100% |
| SPY | 13.7% | 17% | 0.72 | -34% | 0.86 | 0.66 |  | 100% |

## 2. The trades

| | trades | win rate | avg win | avg loss | per trade | profit factor | avg days |
|---|---|---|---|---|---|---|---|
| A. | 1240 | 36% | +17.3% | -6.9% | +1.74% | 1.39 | 25 |
| B. | 1210 | 31% | +12.4% | -4.3% | +0.95% | 1.32 | 17 |
| C. | 1135 | 32% | +11.2% | -4.4% | +0.68% | 1.23 | 15 |
| D. | 1275 | 31% | +12.1% | -4.3% | +0.80% | 1.27 | 16 |
| E. | 238 | 36% | +23.2% | -9.3% | +2.42% | 1.41 | 49 |
| F. | 220 | 37% | +23.0% | -9.4% | +2.66% | 1.45 | 49 |
| G. | 508 | 36% | +18.0% | -9.4% | +0.57% | 1.09 | 57 |

How the full-SEPA (E) trades ended:

| exit | trades | avg return |
|---|---|---|
| below 50-day | 85 | +23.4% |
| break-even stop | 11 | -4.9% |
| stop | 142 | -9.6% |

## 3. Does the growth filter pick better stocks? (no trading rules)

Average next-month return of qualifying stocks vs all universe members, month-ends, close to close.

| group | months | avg stocks | next month | vs universe | beat universe |
|---|---|---|---|---|---|
| Trend Template + RS 70 | 149 | 121 | +1.09% | +0.02% (t 0.1) | 52% |
| + growth (SEPA screen) | 139 | 11 | +1.24% | +0.45% (t 0.9) | 54% |
| + accelerating EPS | 135 | 8 | +1.30% | +0.63% (t 1.2) | 56% |
| growth alone (no chart rules) | 149 | 37 | +1.60% | +0.52% (t 2.0) | 54% |
| RS 90+ with the template | 149 | 45 | +1.31% | +0.24% (t 0.7) | 59% |

## 4. Stress tests on the best rule-based version

Best Sharpe above: **A. Trend Template + RS 70, held while it qualifies**. Changes one at a time:

| change | return/yr | Sharpe | worst drop | trades |
|---|---|---|---|---|
| as above | 11.8% | 0.45 | -48% | 1240 |
| costs 0.20% each way | 9.7% | 0.39 | -51% | 1240 |
| costs 0.30% each way | 7.7% | 0.33 | -54% | 1240 |
| 5 positions of 20% | 13.7% | 0.48 | -56% | 614 |
| 20 positions of 5% | 13.9% | 0.55 | -37% | 2462 |
| market filter on | 13.8% | 0.52 | -42% | 1007 |

## 5. Year by year

| year | A | B | C | D | E | F | G | equal-weight | SPY |
|---|---|---|---|---|---|---|---|---|---|
| 2014 | +2% | -6% | -2% | -6% | +2% | +2% | +2% | +7% | +11% |
| 2015 | -7% | +0% | +3% | +0% | +8% | +8% | -8% | -3% | +1% |
| 2016 | -7% | -2% | -2% | -2% | -1% | -1% | -8% | +22% | +12% |
| 2017 | +22% | +15% | +11% | +15% | +12% | +12% | +28% | +23% | +22% |
| 2018 | -24% | -9% | -2% | -9% | +1% | +1% | -7% | -9% | -5% |
| 2019 | +2% | +3% | +3% | +3% | +5% | +5% | +8% | +31% | +31% |
| 2020 | +48% | +28% | +17% | +21% | +3% | -5% | +32% | +23% | +18% |
| 2021 | +26% | -5% | -3% | -5% | +7% | +7% | +12% | +24% | +29% |
| 2022 | -19% | -15% | -12% | -18% | -11% | -6% | -15% | -15% | -18% |
| 2023 | +12% | +8% | -3% | +8% | +9% | +12% | -1% | +21% | +26% |
| 2024 | +63% | +76% | +34% | +75% | +61% | +61% | +3% | +14% | +25% |
| 2025 | +19% | +5% | +4% | -0% | -11% | -10% | -4% | +13% | +18% |
| 2026 | +48% | +14% | +30% | +13% | -4% | -4% | -12% | +13% | +13% |
