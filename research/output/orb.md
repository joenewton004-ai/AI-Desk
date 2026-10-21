# Opening range breakout on stocks in play - generated tables (preview)

The 100 largest US companies; Yahoo bars. Each trade risks the same amount; results in R (multiples of that risk). 'Worst case' assumes the stop came first whenever the entry bar also reached it; 'best case' only checks the stop from the next bar. The truth lies between; the finer the bars, the closer the two.


## 5-minute bars, ~60 days, worst case

46 trading days (2026-08-17 to 2026-10-20).

| | trades | win rate | avg R before costs | avg R after 0.03% each way | after 0.10% | t-stat (after 0.03%) |
|---|---|---|---|---|---|---|
| All | 752 | 6% | -0.850 | -1.076 | -1.604 | -14.2 |
| Longs | 385 | 5% | -0.874 | -1.104 | -1.641 | -11.2 |
| Shorts | 367 | 7% | -0.824 | -1.047 | -1.565 | -9.0 |
| Relative volume 2x+ | 325 | 6% | -1.041 | -1.274 | -1.818 | -12.4 |

How trades ended: stop 698, close 54. Median stop distance: 0.26% of the price.
Days with a net gain (before costs): 7% of 46.

## 5-minute bars, ~60 days, best case

46 trading days (2026-08-17 to 2026-10-20).

| | trades | win rate | avg R before costs | avg R after 0.03% each way | after 0.10% | t-stat (after 0.03%) |
|---|---|---|---|---|---|---|
| All | 749 | 15% | -0.159 | -0.385 | -0.914 | -3.3 |
| Longs | 383 | 13% | -0.216 | -0.446 | -0.982 | -2.6 |
| Shorts | 366 | 17% | -0.100 | -0.322 | -0.842 | -1.9 |
| Relative volume 2x+ | 323 | 12% | -0.300 | -0.533 | -1.078 | -2.9 |

How trades ended: stop 624, close 125. Median stop distance: 0.26% of the price.
Days with a net gain (before costs): 35% of 46.

## 1-minute bars, ~30 days, worst case

14 trading days (2026-10-01 to 2026-10-20).

| | trades | win rate | avg R before costs | avg R after 0.03% each way | after 0.10% | t-stat (after 0.03%) |
|---|---|---|---|---|---|---|
| All | 199 | 12% | -0.276 | -0.507 | -1.048 | -2.6 |
| Longs | 100 | 9% | -0.292 | -0.526 | -1.073 | -1.7 |
| Shorts | 99 | 14% | -0.259 | -0.488 | -1.022 | -2.0 |
| Relative volume 2x+ | 63 | 8% | -0.265 | -0.506 | -1.069 | -1.2 |

How trades ended: stop 173, close 26. Median stop distance: 0.26% of the price.
Days with a net gain (before costs): 36% of 14.

## 1-minute bars, ~30 days, best case

14 trading days (2026-10-01 to 2026-10-20).

| | trades | win rate | avg R before costs | avg R after 0.03% each way | after 0.10% | t-stat (after 0.03%) |
|---|---|---|---|---|---|---|
| All | 199 | 14% | -0.052 | -0.284 | -0.824 | -1.3 |
| Longs | 100 | 11% | -0.035 | -0.269 | -0.816 | -0.8 |
| Shorts | 99 | 16% | -0.069 | -0.298 | -0.832 | -1.1 |
| Relative volume 2x+ | 63 | 8% | -0.207 | -0.449 | -1.011 | -1.0 |

How trades ended: stop 169, close 30. Median stop distance: 0.26% of the price.
Days with a net gain (before costs): 43% of 14.
