# TJR's model as fixed rules - generated tables

## 5m bars, 2026-08-17 to 2026-10-26 (NQ=F and ES=F, New York time)

Net of costs (NQ 0.75 points, ES 0.60 per round trip). R = the trade's risk (entry to stop).

| rules | trades | win rate | avg R (net) | t | avg R before costs | stopped out | $ per contract, total | profit factor |
|---|---|---|---|---|---|---|---|---|
| BOS, 2R | 76 | 39% | -0.05 | -0.4 | -0.02 | 54% | $-8,412 | 0.91 |
| *control: same times, random direction (20 runs)* | | | -0.08 (range -0.26 to +0.12) | | | | | |
| BOS, 3R | 76 | 36% | -0.13 | -0.9 | -0.10 | 57% | $-14,965 | 0.79 |
| BOS, opposite liquidity | 76 | 43% | +0.05 | 0.3 | +0.08 | 51% | $+1,715 | 1.09 |
| BOS, 2R, 1-hour bias | 43 | 42% | +0.03 | 0.2 | +0.05 | 56% | $+1,122 | 1.06 |
| inverse FVG, 2R | 46 | 33% | -0.18 | -1.0 | -0.15 | 59% | $-4,718 | 0.73 |
| inverse FVG, 2R, 1-hour bias | 21 | 33% | -0.14 | -0.5 | -0.12 | 67% | $-1,170 | 0.79 |

By level swept (BOS, 2R):

| level | trades | avg R (net) | win rate |
|---|---|---|---|
| Asia high | 9 | -0.37 | 22% |
| Asia low | 10 | +0.47 | 70% |
| London high | 16 | +0.70 | 69% |
| London low | 9 | -0.83 | 11% |
| overnight high | 5 | +0.16 | 40% |
| overnight low | 11 | -0.42 | 27% |
| prior day high | 9 | -0.17 | 33% |
| prior day low | 7 | -0.51 | 14% |

| instrument | trades | avg R (net) | $ per contract |
|---|---|---|---|
| ES=F | 34 | +0.03 | $-133 |
| NQ=F | 42 | -0.12 | $-8,280 |

## 1h bars, 2024-06-04 to 2026-10-26 (NQ=F and ES=F, New York time)

Net of costs (NQ 0.75 points, ES 0.60 per round trip). R = the trade's risk (entry to stop).

| rules | trades | win rate | avg R (net) | t | avg R before costs | stopped out | $ per contract, total | profit factor |
|---|---|---|---|---|---|---|---|---|
| BOS, 2R | 264 | 43% | -0.06 | -1.3 | -0.04 | 15% | $-39,235 | 0.81 |
| *control: same times, random direction (20 runs)* | | | -0.00 (range -0.07 to +0.08) | | | | | |
| BOS, 3R | 264 | 42% | -0.07 | -1.7 | -0.05 | 15% | $-44,415 | 0.76 |
| BOS, opposite liquidity | 264 | 43% | -0.06 | -1.4 | -0.04 | 15% | $-38,145 | 0.80 |
| BOS, 2R, 1-hour bias | 90 | 47% | -0.01 | -0.1 | +0.01 | 12% | $-8,438 | 0.97 |
| inverse FVG, 2R | 36 | 39% | -0.06 | -0.6 | -0.05 | 14% | $+915 | 0.77 |
| inverse FVG, 2R, 1-hour bias | 5 | 80% | +0.42 | 2.1 | +0.43 | 0% | $+5,462 | 9.78 |

By level swept (BOS, 2R):

| level | trades | avg R (net) | win rate |
|---|---|---|---|
| Asia high | 43 | -0.22 | 33% |
| Asia low | 71 | -0.04 | 45% |
| London high | 20 | +0.02 | 45% |
| London low | 27 | -0.11 | 37% |
| overnight high | 4 | +0.21 | 75% |
| overnight low | 3 | +0.18 | 67% |
| prior day high | 54 | +0.05 | 48% |
| prior day low | 42 | -0.08 | 40% |

| instrument | trades | avg R (net) | $ per contract |
|---|---|---|---|
| ES=F | 143 | -0.04 | $-11,990 |
| NQ=F | 121 | -0.07 | $-27,245 |

