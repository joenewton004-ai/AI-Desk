# Overnight sleeve vs the fear index - generated tables

Nights from 2014-04-01 to 2026-10-20 (3,158). The 750 largest US companies, **survivors-only prices**, 0.02% per trade each way, cash at T-bills. Signals from the close BEFORE the buy.

## 1. Average night (bp) by what the market looked like the day before

| condition (day before) | nights | sleeve (top 20) | low-beta top 20 | defensive-industry top 20 | average stock |
|---|---|---|---|---|---|
| all nights | 3,158 | +6.6 | +1.2 | +1.8 | +4.0 |
| VIX 0-15 | 1,197 | +5.0 | +1.4 | +1.5 | +2.6 |
| VIX 15-20 | 1,087 | +7.1 | +0.5 | +1.3 | +3.9 |
| VIX 20-25 | 481 | +9.1 | +0.4 | +1.2 | +4.0 |
| VIX 25-30 | 235 | +6.4 | +3.7 | +3.3 | +6.9 |
| VIX 30-+ | 158 | +7.7 | +2.3 | +6.4 | +9.8 |
| VIX fell 10%+ | 182 | +8.8 | -3.3 | -4.8 | -7.2 |
| VIX rose 10%+ | 284 | -1.2 | -4.5 | -4.8 | -0.9 |
| VIX rose 20%+ | 75 | +8.2 | -9.3 | -10.0 | +2.3 |
| SPY below its 200-day | 508 | -3.3 | -4.2 | -3.9 | -0.9 |
| SPY above its 200-day | 2,650 | +8.5 | +2.2 | +2.9 | +4.9 |
| tech lagged defensives most (worst 10% of days) | 316 | -12.7 | -8.3 | -7.7 | -7.4 |
| tech beat defensives most (best 10%) | 316 | +10.2 | +4.2 | +6.3 | +5.7 |

(Costs are already taken off: 0.04% = 4 bp a night. A row's spread is noise unless it holds across the neighbouring rows and both halves below.)

## 2. Switching rules (the whole sleeve, night by night)

| rule | nights switched | return/yr | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe |
|---|---|---|---|---|---|---|
| Always the top 20 (now) | - | 15.5% | 0.70 | -36% | 0.72 | 0.75 |
| Cash when VIX > 25 | 12% | 14.3% | 0.77 | -25% | 0.81 | 0.79 |
| Cash when VIX > 30 | 5% | 15.0% | 0.74 | -33% | 0.64 | 0.83 |
| Cash after VIX rose 15%+ | 4% | 15.1% | 0.71 | -40% | 0.95 | 0.68 |
| Cash when SPY below its 200-day | 16% | 18.3% | 0.95 | -19% | 1.03 | 1.01 |
| Low-beta list when VIX > 25 | 12% | 14.8% | 0.73 | -30% | 0.76 | 0.77 |
| Low-beta list when VIX > 20 | 28% | 11.1% | 0.60 | -30% | 0.73 | 0.58 |
| Low-beta list after VIX rose 15%+ | 4% | 14.8% | 0.69 | -37% | 0.85 | 0.69 |
| Low-beta list when SPY below its 200-day | 16% | 15.6% | 0.76 | -31% | 0.84 | 0.80 |
| Defensive-industry list when VIX > 25 | 12% | 15.3% | 0.75 | -30% | 0.78 | 0.79 |
| Low-beta list after tech lagged most (worst 10%) | 13% | 17.2% | 0.82 | -34% | 0.81 | 0.89 |
| Cash after tech lagged most (worst 10%) | 13% | 20.1% | 0.97 | -28% | 0.90 | 1.07 |
| Cash when SPY below its 200-day OR after tech lagged most | 25% | 18.0% | 1.03 | -16% | 1.00 | 1.13 |
| Lagged a day more: cash when SPY below its 200-day | 16% | 16.6% | 0.87 | -23% | 0.83 | 0.95 |
| Lagged a day more: cash after tech lagged most | 13% | 14.9% | 0.74 | -31% | 0.69 | 0.82 |
| Always the low-beta list | all | 2.5% | 0.10 | -33% | -0.12 | 0.20 |
| Always the defensive-industry list | all | 3.9% | 0.22 | -32% | 0.13 | 0.27 |
| Always: at most 4 per industry | all | 14.0% | 0.65 | -36% | 0.62 | 0.72 |
| Lagged a day more: low-beta when VIX > 25 | 12% | 13.1% | 0.65 | -30% | 0.68 | 0.69 |
| Lagged a day more: cash after VIX rose 15%+ | 4% | 19.1% | 0.89 | -31% | 0.86 | 0.99 |

## 2b. Do the signals hold in both halves? (sleeve's average night, bp)

| signal (day before) | 2014-19 nights | 2014-19 | 2020-26 nights | 2020-26 | episodes (runs of 5+ days) |
|---|---|---|---|---|---|
| SPY below its 200-day | 175 | -3.1 | 333 | -3.4 | 16 |
| tech lagged defensives most (worst 10%, past threshold) | 131 | -5.7 | 284 | -11.4 | 0 |
| VIX above 25 | 45 | +0.5 | 346 | +7.0 | 18 |
| none of these | 1171 | +5.0 | 1075 | +12.1 | 131 |

Signal nights vs all other nights (Welch t):

- SPY below its 200-day: -3.3 vs +8.5 bp a night, t -1.4
- tech lagged most: -9.6 vs +9.0 bp a night, t -2.2

## 3. The worst nights for the sleeve - what the VIX said the day before

| morning | sleeve's night | VIX the day before | VIX change that day | SPY below 200-day? | low-beta list that night |
|---|---|---|---|---|---|
| 2015-08-24 | -9.1% | 28.0 | +46% | yes | -5.8% |
| 2020-03-09 | -8.1% | 41.9 | +6% | yes | -5.6% |
| 2020-03-12 | -8.5% | 53.9 | +14% | yes | -7.0% |
| 2020-03-16 | -12.6% | 57.8 | -23% | yes | -10.5% |
| 2020-03-18 | -7.6% | 75.9 | -8% | yes | -5.4% |
| 2020-06-11 | -8.3% | 27.6 | +0% | no | -1.2% |
| 2024-08-05 | -8.8% | 23.4 | +26% | no | -4.2% |
| 2025-01-27 | -6.6% | 14.8 | -1% | no | -0.7% |
| 2025-04-03 | -7.2% | 21.5 | -1% | yes | -3.0% |
| 2025-04-07 | -5.3% | 45.3 | +51% | yes | -4.2% |
| 2026-03-03 | -5.3% | 21.4 | +8% | no | -1.1% |
| 2026-06-23 | -7.3% | 17.3 | +5% | no | -0.4% |
| 2026-07-28 | -6.1% | 18.7 | +0% | no | +0.8% |
| 2026-08-18 | -5.1% | 15.2 | +7% | no | +0.2% |
| 2026-09-14 | -6.9% | 15.8 | -11% | no | -0.1% |

Of the sleeve's 50 worst nights, 20 came after a VIX close above 25 (which happened before 12% of all nights).

## 4. How often the low-beta list beat the sleeve, by VIX (nights)

| VIX the day before | low-beta better | difference (bp/night) | t |
|---|---|---|---|
| 0-20 | 46% | -5.0 | -2.6 |
| 20-25 | 46% | -8.7 | -1.6 |
| 25-+ | 50% | -3.8 | -0.6 |
