# EMA9/VWAP crossover and Trend + Momentum + Confirmation - generated tables

Yahoo regular-hours bars, the 100-150 largest US companies. Costs 0.03% each way (stress 0.10%). 'per trade' = average return per trade; R = multiples of the risk (strategy B).


## 5-minute bars (~60 days), 2026-07-28 to 2026-10-20

| rules | trades | win rate | per trade before costs | per trade after 0.03% | after 0.10% | t-stat | avg R |
|---|---|---|---|---|---|---|---|
| A both sides | 14996 | 32% | -0.007% | -0.067% | -0.207% | -10.5 |  |
| A long only | 7533 | 32% | -0.006% | -0.066% | -0.206% | -7.1 |  |
| B base (2R) | 715 | 38% | -0.047% | -0.107% | -0.247% | -3.1 | -0.07 |
| B 3R target | 715 | 37% | -0.037% | -0.097% | -0.237% | -2.6 | -0.05 |
| B without the volume rule | 2378 | 39% | -0.032% | -0.092% | -0.232% | -4.2 | -0.05 |
| B first pullback entry | 501 | 33% | -0.090% | -0.150% | -0.290% | -4.3 | -0.12 |
| B best case (stop from the next bar) | 670 | 38% | -0.052% | -0.112% | -0.252% | -3.0 | -0.08 |
| B control: random bars | 703 | 42% | +0.099% | +0.039% | -0.101% | 1.6 | +0.19 |

A: 2.1 trades per stock per day; how they ended: cross back 8981, close 6015.
B: how trades ended: close 338, stop 293, target 84.

## 1-minute bars (~30 days), 2026-09-23 to 2026-10-20

| rules | trades | win rate | per trade before costs | per trade after 0.03% | after 0.10% | t-stat | avg R |
|---|---|---|---|---|---|---|---|
| A both sides | 5000 | 23% | +0.002% | -0.058% | -0.198% | -6.4 |  |
| A long only | 2510 | 23% | +0.002% | -0.058% | -0.198% | -4.5 |  |
| B base (2R) | 261 | 32% | -0.077% | -0.137% | -0.277% | -3.6 | -0.08 |
| B 3R target | 261 | 25% | -0.071% | -0.131% | -0.271% | -3.0 | -0.11 |
| B without the volume rule | 457 | 35% | -0.024% | -0.084% | -0.224% | -2.7 | -0.02 |
| B first pullback entry | 180 | 31% | -0.041% | -0.101% | -0.241% | -2.7 | -0.00 |
| B best case (stop from the next bar) | 261 | 32% | -0.076% | -0.136% | -0.276% | -3.6 | -0.07 |
| B control: random bars | 249 | 31% | +0.035% | -0.025% | -0.165% | -1.2 | +0.01 |

A: 2.1 trades per stock per day; how they ended: cross back 4058, close 942.
B: how trades ended: stop 163, target 67, close 31.

## Hourly bars (~3 years), 2023-11-21 to 2026-10-20

| rules | trades | win rate | per trade before costs | per trade after 0.03% | after 0.10% | t-stat | avg R |
|---|---|---|---|---|---|---|---|
| A both sides | 12439 | 42% | -0.018% | -0.078% | -0.218% | -12.5 |  |
| A long only | 6459 | 43% | +0.000% | -0.060% | -0.200% | -7.7 |  |
| B base (2R) | 1014 | 46% | -0.009% | -0.069% | -0.209% | -1.8 | +0.01 |
| B 3R target | 1014 | 46% | -0.008% | -0.068% | -0.208% | -1.8 | +0.01 |
| B without the volume rule | 15941 | 45% | -0.011% | -0.071% | -0.211% | -10.7 | -0.00 |
| B first pullback entry | 564 | 44% | -0.063% | -0.123% | -0.263% | -3.0 | -0.01 |
| B best case (stop from the next bar) | 879 | 48% | +0.011% | -0.049% | -0.189% | -1.1 | +0.02 |
| B control: random bars | 1014 | 55% | +0.197% | +0.137% | -0.003% | 4.1 | +0.20 |

A: 0.1 trades per stock per day; how they ended: close 9791, cross back 2648.
B: how trades ended: close 963, stop 48, target 3.
B by quarter, per trade after costs: 2023Q4 +0.34%, 2024Q1 +0.11%, 2024Q2 -0.11%, 2024Q3 -0.46%, 2024Q4 +0.03%, 2025Q1 -0.35%, 2025Q2 -0.08%, 2025Q3 +0.02%, 2025Q4 +0.21%, 2026Q1 -0.29%, 2026Q2 +0.33%, 2026Q3 -0.48%, 2026Q4 +0.77%.
