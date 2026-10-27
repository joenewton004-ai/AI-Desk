# Candle patterns on 5-minute bars - generated tables

Alpaca SIP minute bars (split-adjusted) -> 5-minute candles; entry at the next candle's open; out by 15:55. 'Placebo' = the same side, time of day and exit on random other days (gross, average of 20 runs): the bar to beat. 'Edge' = gross minus placebo. Net = after costs both ways. Halves split at 2021-01-01. Returns are per trade, in %.

## SPY: 2016-01-04 to 2026-10-26, 2,719 days, 0.01% cost each way

| rule | side | trades | per year | win rate (net) | gross | placebo | edge | net | t (net) | 2016-20 net | 2021-26 net | avg R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| engulfing, plain, 30 min | long | 4,577 | 424 | 45% | -0.002% | +0.002% | -0.004% | -0.022% | -7.1 | -0.024% | -0.020% |  |
| engulfing, plain, 30 min | short | 4,776 | 442 | 39% | -0.003% | -0.001% | -0.001% | -0.023% | -7.5 | -0.019% | -0.027% |  |
| engulfing, plain, stop/2R | long | 4,249 | 393 | 34% | -0.001% | +0.001% | -0.002% | -0.021% | -5.8 | -0.021% | -0.021% | -0.01 |
| engulfing, plain, stop/2R | short | 4,411 | 408 | 31% | -0.007% | -0.002% | -0.005% | -0.027% | -8.1 | -0.022% | -0.031% | -0.07 |
| engulfing, reversal, 30 min | long | 2,237 | 207 | 47% | -0.006% | +0.003% | -0.009% | -0.026% | -5.3 | -0.022% | -0.029% |  |
| engulfing, reversal, 30 min | short | 2,604 | 241 | 38% | -0.003% | -0.002% | -0.001% | -0.023% | -6.1 | -0.021% | -0.026% |  |
| engulfing, reversal, stop/2R | long | 2,191 | 203 | 33% | -0.005% | +0.002% | -0.007% | -0.025% | -4.9 | -0.026% | -0.025% | -0.04 |
| engulfing, reversal, stop/2R | short | 2,540 | 235 | 31% | -0.010% | -0.004% | -0.006% | -0.030% | -8.2 | -0.034% | -0.026% | -0.09 |
| engulfing, trend, 30 min | long | 3,195 | 296 | 45% | +0.000% | +0.001% | -0.001% | -0.020% | -5.7 | -0.025% | -0.014% |  |
| engulfing, trend, 30 min | short | 2,937 | 272 | 41% | -0.001% | -0.001% | +0.001% | -0.021% | -4.9 | -0.018% | -0.023% |  |
| engulfing, trend, stop/2R | long | 2,995 | 277 | 34% | +0.002% | +0.002% | +0.000% | -0.018% | -4.4 | -0.016% | -0.021% | +0.00 |
| engulfing, trend, stop/2R | short | 2,804 | 260 | 32% | -0.002% | -0.004% | +0.002% | -0.022% | -4.7 | -0.012% | -0.031% | -0.05 |
| hammer / shooting star, plain, 30 min | long | 2,235 | 207 | 47% | +0.003% | +0.001% | +0.002% | -0.017% | -4.0 | -0.025% | -0.012% |  |
| hammer / shooting star, plain, 30 min | short | 1,575 | 146 | 40% | -0.008% | -0.005% | -0.004% | -0.028% | -5.1 | -0.017% | -0.040% |  |
| hammer / shooting star, plain, stop/2R | long | 2,309 | 214 | 33% | -0.004% | +0.001% | -0.005% | -0.024% | -6.2 | -0.026% | -0.022% | -0.01 |
| hammer / shooting star, plain, stop/2R | short | 1,604 | 149 | 33% | -0.005% | -0.003% | -0.002% | -0.025% | -4.7 | -0.019% | -0.032% | -0.03 |
| hammer / shooting star, reversal, 30 min | long | 1,245 | 115 | 48% | +0.003% | +0.001% | +0.001% | -0.017% | -2.7 | -0.019% | -0.015% |  |
| hammer / shooting star, reversal, 30 min | short | 927 | 86 | 39% | -0.011% | -0.001% | -0.010% | -0.031% | -4.7 | -0.020% | -0.044% |  |
| hammer / shooting star, reversal, stop/2R | long | 1,303 | 121 | 32% | -0.008% | +0.001% | -0.009% | -0.028% | -5.3 | -0.028% | -0.028% | -0.04 |
| hammer / shooting star, reversal, stop/2R | short | 931 | 86 | 32% | -0.004% | -0.004% | +0.000% | -0.024% | -4.1 | -0.015% | -0.034% | -0.05 |
| hammer / shooting star, trend, 30 min | long | 1,143 | 106 | 46% | +0.004% | +0.003% | +0.001% | -0.016% | -3.0 | -0.029% | -0.008% |  |
| hammer / shooting star, trend, 30 min | short | 783 | 73 | 42% | +0.001% | +0.001% | +0.000% | -0.019% | -2.2 | -0.008% | -0.028% |  |
| hammer / shooting star, trend, stop/2R | long | 1,147 | 106 | 35% | +0.002% | +0.000% | +0.002% | -0.018% | -3.5 | -0.024% | -0.014% | +0.03 |
| hammer / shooting star, trend, stop/2R | short | 806 | 75 | 33% | -0.006% | -0.005% | -0.001% | -0.026% | -2.9 | -0.022% | -0.029% | -0.04 |
| inside-bar breakout, stop/2R | long | 5,459 | 505 | 36% | +0.005% | +0.002% | +0.003% | -0.015% | -4.1 | -0.015% | -0.014% | +0.05 |
| inside-bar breakout, stop/2R | short | 4,926 | 456 | 33% | +0.001% | -0.002% | +0.003% | -0.019% | -5.0 | -0.022% | -0.017% | -0.02 |
| opening range 15 min, to the close | long | 1,358 | 126 | 38% | +0.032% | +0.010% | +0.021% | +0.012% | 0.8 | +0.004% | +0.018% | +0.12 |
| opening range 15 min, to the close | short | 1,337 | 124 | 31% | -0.012% | -0.001% | -0.010% | -0.032% | -1.9 | -0.052% | -0.013% | -0.00 |
| opening range 30 min, to the close | long | 1,448 | 134 | 44% | +0.009% | +0.008% | +0.001% | -0.011% | -0.8 | -0.027% | +0.003% | +0.07 |
| opening range 30 min, to the close | short | 1,253 | 116 | 37% | +0.018% | +0.001% | +0.017% | -0.002% | -0.1 | -0.021% | +0.013% | +0.07 |
| intraday momentum (Gao et al.), 15:30 to close | long | 1,507 | 140 | 42% | -0.007% | -0.007% | +0.000% | -0.027% | -3.9 | -0.020% | -0.032% |  |
| intraday momentum (Gao et al.), 15:30 to close | short | 1,206 | 112 | 44% | +0.003% | +0.005% | -0.003% | -0.017% | -1.7 | -0.015% | -0.019% |  |

## NVDA: 2016-01-04 to 2026-10-26, 2,719 days, 0.02% cost each way

| rule | side | trades | per year | win rate (net) | gross | placebo | edge | net | t (net) | 2016-20 net | 2021-26 net | avg R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| engulfing, plain, 30 min | long | 4,199 | 388 | 45% | -0.008% | +0.005% | -0.013% | -0.048% | -5.9 | -0.068% | -0.030% |  |
| engulfing, plain, 30 min | short | 4,360 | 403 | 44% | -0.003% | -0.001% | -0.002% | -0.043% | -5.5 | -0.036% | -0.049% |  |
| engulfing, plain, stop/2R | long | 3,817 | 353 | 33% | -0.006% | +0.002% | -0.008% | -0.046% | -4.6 | -0.052% | -0.040% | -0.04 |
| engulfing, plain, stop/2R | short | 3,883 | 359 | 34% | -0.002% | +0.001% | -0.002% | -0.042% | -4.3 | -0.039% | -0.044% | -0.01 |
| engulfing, reversal, 30 min | long | 2,124 | 197 | 45% | -0.024% | +0.002% | -0.026% | -0.064% | -5.5 | -0.074% | -0.055% |  |
| engulfing, reversal, 30 min | short | 2,361 | 218 | 45% | -0.009% | -0.005% | -0.004% | -0.049% | -4.9 | -0.036% | -0.060% |  |
| engulfing, reversal, stop/2R | long | 2,031 | 188 | 32% | -0.035% | +0.006% | -0.041% | -0.075% | -5.7 | -0.077% | -0.073% | -0.08 |
| engulfing, reversal, stop/2R | short | 2,253 | 208 | 34% | -0.011% | -0.003% | -0.008% | -0.051% | -4.7 | -0.062% | -0.041% | -0.01 |
| engulfing, trend, 30 min | long | 2,783 | 258 | 45% | +0.006% | +0.005% | +0.001% | -0.034% | -3.6 | -0.060% | -0.013% |  |
| engulfing, trend, 30 min | short | 2,679 | 248 | 43% | +0.001% | -0.004% | +0.005% | -0.039% | -3.7 | -0.025% | -0.050% |  |
| engulfing, trend, stop/2R | long | 2,563 | 237 | 35% | +0.013% | +0.002% | +0.011% | -0.027% | -2.3 | -0.036% | -0.019% | +0.01 |
| engulfing, trend, stop/2R | short | 2,531 | 234 | 34% | +0.004% | +0.006% | -0.001% | -0.036% | -2.8 | -0.021% | -0.048% | +0.01 |
| hammer / shooting star, plain, 30 min | long | 1,724 | 159 | 46% | +0.012% | +0.002% | +0.010% | -0.028% | -2.4 | -0.035% | -0.022% |  |
| hammer / shooting star, plain, 30 min | short | 1,373 | 127 | 45% | +0.007% | -0.003% | +0.010% | -0.033% | -2.4 | -0.036% | -0.030% |  |
| hammer / shooting star, plain, stop/2R | long | 1,826 | 169 | 33% | -0.008% | -0.002% | -0.006% | -0.048% | -4.4 | -0.045% | -0.051% | -0.03 |
| hammer / shooting star, plain, stop/2R | short | 1,439 | 133 | 33% | -0.013% | +0.005% | -0.018% | -0.053% | -4.3 | -0.049% | -0.059% | -0.04 |
| hammer / shooting star, reversal, 30 min | long | 895 | 83 | 48% | +0.006% | +0.003% | +0.003% | -0.034% | -2.0 | -0.033% | -0.034% |  |
| hammer / shooting star, reversal, 30 min | short | 759 | 70 | 44% | -0.024% | -0.002% | -0.022% | -0.064% | -3.3 | -0.056% | -0.075% |  |
| hammer / shooting star, reversal, stop/2R | long | 930 | 86 | 34% | -0.011% | -0.005% | -0.006% | -0.051% | -3.2 | -0.037% | -0.063% | -0.01 |
| hammer / shooting star, reversal, stop/2R | short | 779 | 72 | 33% | -0.010% | +0.002% | -0.012% | -0.050% | -3.2 | -0.036% | -0.070% | -0.02 |
| hammer / shooting star, trend, 30 min | long | 951 | 88 | 45% | +0.017% | -0.002% | +0.019% | -0.023% | -1.5 | -0.034% | -0.012% |  |
| hammer / shooting star, trend, 30 min | short | 719 | 67 | 44% | +0.032% | +0.005% | +0.027% | -0.008% | -0.4 | -0.004% | -0.014% |  |
| hammer / shooting star, trend, stop/2R | long | 993 | 92 | 33% | -0.008% | -0.007% | -0.001% | -0.048% | -3.5 | -0.051% | -0.045% | -0.05 |
| hammer / shooting star, trend, stop/2R | short | 748 | 69 | 31% | -0.018% | -0.001% | -0.017% | -0.058% | -3.2 | -0.061% | -0.054% | -0.08 |
| inside-bar breakout, stop/2R | long | 4,940 | 457 | 37% | +0.030% | +0.008% | +0.022% | -0.010% | -0.9 | -0.018% | -0.003% | +0.04 |
| inside-bar breakout, stop/2R | short | 5,000 | 463 | 35% | +0.010% | +0.002% | +0.007% | -0.030% | -2.6 | -0.023% | -0.037% | +0.01 |
| opening range 15 min, to the close | long | 1,334 | 123 | 49% | +0.191% | +0.058% | +0.133% | +0.151% | 3.2 | +0.136% | +0.164% | +0.13 |
| opening range 15 min, to the close | short | 1,346 | 125 | 45% | +0.045% | -0.016% | +0.061% | +0.005% | 0.1 | +0.054% | -0.037% | +0.04 |
| opening range 30 min, to the close | long | 1,311 | 121 | 53% | +0.178% | +0.047% | +0.131% | +0.138% | 3.1 | +0.121% | +0.151% | +0.11 |
| opening range 30 min, to the close | short | 1,282 | 119 | 47% | +0.061% | -0.017% | +0.077% | +0.021% | 0.4 | +0.068% | -0.018% | +0.04 |
| intraday momentum (Gao et al.), 15:30 to close | long | 1,474 | 136 | 50% | +0.012% | +0.014% | -0.002% | -0.028% | -1.9 | +0.002% | -0.055% |  |
| intraday momentum (Gao et al.), 15:30 to close | short | 1,229 | 114 | 44% | -0.018% | -0.017% | -0.001% | -0.058% | -3.0 | -0.042% | -0.071% |  |

## Opening-range breakout check: QQQ and the 10 largest US companies at the start of 2016

NVDA was picked because it is huge NOW (it rose ~100x since 2016), which can flatter buying strength. These were the largest companies by market value at the end of 2015 (all still listed - survivors, but not picked for what happened next). Cost 0.02% each way. 'Busy opens' = only days when the opening range traded 2x+ its usual volume (Zarattini, Barbon & Aziz 2024's 'stocks in play' idea; known at 9:45/10:00).

| stock | rule | side | trades | net | t | 2016-20 | 2021-26 | edge vs placebo |
|---|---|---|---|---|---|---|---|---|
| QQQ | ORB 15 min | long | 1,404 | +0.010% | 0.5 | -0.011% | +0.028% | +0.023% |
| QQQ | ORB 15 min | short | 1,301 | -0.035% | -1.6 | -0.074% | -0.001% | +0.011% |
| QQQ | ORB 15 min, busy opens | long | 47 | +0.126% | 0.7 | -0.138% | +0.817% | +0.201% |
| QQQ | ORB 15 min, busy opens | short | 46 | -0.064% | -0.4 | -0.079% | -0.044% | +0.079% |
| QQQ | ORB 30 min | long | 1,458 | -0.003% | -0.2 | -0.045% | +0.035% | +0.022% |
| QQQ | ORB 30 min | short | 1,241 | -0.019% | -0.8 | -0.059% | +0.013% | +0.012% |
| QQQ | ORB 30 min, busy opens | long | 41 | +0.029% | 0.2 | -0.184% | +0.544% | +0.143% |
| QQQ | ORB 30 min, busy opens | short | 39 | +0.008% | 0.0 | -0.030% | +0.069% | +0.000% |
| AAPL | ORB 15 min | long | 1,384 | +0.037% | 1.3 | +0.019% | +0.054% | +0.032% |
| AAPL | ORB 15 min | short | 1,280 | -0.060% | -2.1 | -0.031% | -0.084% | +0.014% |
| AAPL | ORB 15 min, busy opens | long | 71 | +0.244% | 1.4 | +0.287% | +0.213% | +0.327% |
| AAPL | ORB 15 min, busy opens | short | 78 | -0.031% | -0.2 | +0.326% | -0.370% | +0.087% |
| AAPL | ORB 30 min | long | 1,343 | +0.022% | 0.8 | -0.023% | +0.059% | +0.055% |
| AAPL | ORB 30 min | short | 1,246 | -0.040% | -1.4 | -0.030% | -0.049% | -0.006% |
| AAPL | ORB 30 min, busy opens | long | 65 | +0.297% | 1.8 | +0.357% | +0.259% | +0.307% |
| AAPL | ORB 30 min, busy opens | short | 62 | +0.067% | 0.5 | +0.338% | -0.222% | +0.043% |
| GOOGL | ORB 15 min | long | 1,364 | -0.028% | -1.1 | -0.038% | -0.020% | -0.021% |
| GOOGL | ORB 15 min | short | 1,302 | -0.032% | -1.1 | -0.053% | -0.013% | +0.047% |
| GOOGL | ORB 15 min, busy opens | long | 80 | -0.178% | -1.2 | -0.482% | +0.004% | -0.060% |
| GOOGL | ORB 15 min, busy opens | short | 89 | -0.223% | -1.8 | -0.053% | -0.396% | -0.087% |
| GOOGL | ORB 30 min | long | 1,320 | -0.018% | -0.7 | -0.035% | -0.003% | +0.011% |
| GOOGL | ORB 30 min | short | 1,263 | -0.051% | -1.7 | -0.084% | -0.022% | +0.007% |
| GOOGL | ORB 30 min, busy opens | long | 64 | -0.303% | -1.9 | -0.324% | -0.285% | -0.204% |
| GOOGL | ORB 30 min, busy opens | short | 72 | -0.269% | -1.9 | -0.133% | -0.377% | -0.226% |
| MSFT | ORB 15 min | long | 1,338 | +0.029% | 1.1 | +0.036% | +0.024% | +0.044% |
| MSFT | ORB 15 min | short | 1,340 | -0.066% | -2.5 | -0.096% | -0.039% | +0.025% |
| MSFT | ORB 15 min, busy opens | long | 70 | +0.093% | 0.6 | +0.025% | +0.145% | +0.126% |
| MSFT | ORB 15 min, busy opens | short | 83 | +0.031% | 0.3 | -0.067% | +0.142% | +0.153% |
| MSFT | ORB 30 min | long | 1,339 | -0.009% | -0.4 | -0.028% | +0.007% | +0.010% |
| MSFT | ORB 30 min | short | 1,261 | -0.060% | -2.2 | -0.085% | -0.039% | +0.017% |
| MSFT | ORB 30 min, busy opens | long | 67 | -0.013% | -0.1 | -0.160% | +0.121% | -0.023% |
| MSFT | ORB 30 min, busy opens | short | 73 | -0.053% | -0.5 | -0.188% | +0.086% | +0.028% |
| BRK.B | ORB 15 min | long | 1,325 | -0.020% | -1.1 | +0.000% | -0.036% | -0.001% |
| BRK.B | ORB 15 min | short | 1,363 | -0.089% | -4.7 | -0.101% | -0.077% | -0.016% |
| BRK.B | ORB 15 min, busy opens | long | 68 | -0.036% | -0.3 | -0.049% | -0.025% | +0.040% |
| BRK.B | ORB 15 min, busy opens | short | 82 | -0.069% | -0.8 | -0.233% | +0.079% | -0.008% |
| BRK.B | ORB 30 min | long | 1,320 | -0.044% | -2.5 | -0.022% | -0.063% | -0.019% |
| BRK.B | ORB 30 min | short | 1,308 | -0.083% | -4.3 | -0.080% | -0.086% | -0.025% |
| BRK.B | ORB 30 min, busy opens | long | 58 | -0.129% | -1.0 | -0.169% | -0.086% | -0.071% |
| BRK.B | ORB 30 min, busy opens | short | 72 | -0.035% | -0.3 | -0.144% | +0.052% | +0.102% |
| XOM | ORB 15 min | long | 1,381 | -0.042% | -1.6 | -0.019% | -0.060% | +0.001% |
| XOM | ORB 15 min | short | 1,300 | -0.048% | -1.7 | -0.047% | -0.049% | -0.007% |
| XOM | ORB 15 min, busy opens | long | 57 | -0.269% | -1.9 | -0.252% | -0.285% | -0.306% |
| XOM | ORB 15 min, busy opens | short | 86 | -0.132% | -1.2 | -0.216% | -0.026% | -0.142% |
| XOM | ORB 30 min | long | 1,337 | -0.055% | -2.1 | -0.023% | -0.079% | -0.005% |
| XOM | ORB 30 min | short | 1,269 | -0.052% | -2.0 | -0.027% | -0.077% | +0.006% |
| XOM | ORB 30 min, busy opens | long | 55 | -0.212% | -1.5 | -0.182% | -0.243% | -0.201% |
| XOM | ORB 30 min, busy opens | short | 69 | -0.188% | -1.3 | -0.411% | +0.041% | -0.103% |
| AMZN | ORB 15 min | long | 1,312 | +0.029% | 0.9 | +0.075% | -0.009% | +0.066% |
| AMZN | ORB 15 min | short | 1,364 | +0.037% | 1.2 | +0.052% | +0.024% | +0.065% |
| AMZN | ORB 15 min, busy opens | long | 65 | +0.156% | 0.8 | -0.083% | +0.279% | +0.146% |
| AMZN | ORB 15 min, busy opens | short | 64 | -0.037% | -0.2 | +0.080% | -0.161% | +0.009% |
| AMZN | ORB 30 min | long | 1,287 | +0.047% | 1.6 | +0.099% | +0.004% | +0.099% |
| AMZN | ORB 30 min | short | 1,312 | +0.042% | 1.4 | +0.043% | +0.041% | +0.087% |
| AMZN | ORB 30 min, busy opens | long | 62 | +0.181% | 1.1 | +0.121% | +0.219% | +0.186% |
| AMZN | ORB 30 min, busy opens | short | 56 | +0.025% | 0.1 | +0.110% | -0.054% | +0.088% |
| META | ORB 15 min | long | 1,355 | -0.003% | -0.1 | +0.014% | -0.018% | +0.024% |
| META | ORB 15 min | short | 1,323 | -0.044% | -1.2 | -0.084% | -0.009% | -0.009% |
| META | ORB 15 min, busy opens | long | 73 | -0.184% | -0.9 | +0.012% | -0.320% | -0.004% |
| META | ORB 15 min, busy opens | short | 91 | +0.084% | 0.5 | +0.376% | -0.168% | +0.093% |
| META | ORB 30 min | long | 1,299 | -0.001% | -0.0 | -0.034% | +0.029% | +0.064% |
| META | ORB 30 min | short | 1,295 | -0.041% | -1.2 | -0.068% | -0.019% | +0.031% |
| META | ORB 30 min, busy opens | long | 65 | -0.279% | -1.5 | -0.253% | -0.301% | -0.092% |
| META | ORB 30 min, busy opens | short | 76 | +0.036% | 0.2 | +0.330% | -0.242% | +0.050% |
| GE | ORB 15 min | long | 1,332 | +0.012% | 0.3 | +0.008% | +0.015% | +0.037% |
| GE | ORB 15 min | short | 1,297 | +0.022% | 0.6 | +0.073% | -0.025% | +0.053% |
| GE | ORB 15 min, busy opens | long | 94 | +0.023% | 0.1 | -0.013% | +0.054% | +0.057% |
| GE | ORB 15 min, busy opens | short | 112 | +0.042% | 0.3 | +0.305% | -0.230% | +0.169% |
| GE | ORB 30 min | long | 1,274 | +0.001% | 0.0 | -0.011% | +0.011% | +0.060% |
| GE | ORB 30 min | short | 1,253 | +0.017% | 0.5 | +0.066% | -0.026% | +0.022% |
| GE | ORB 30 min, busy opens | long | 78 | -0.037% | -0.2 | -0.110% | +0.040% | -0.009% |
| GE | ORB 30 min, busy opens | short | 89 | +0.026% | 0.1 | +0.176% | -0.109% | -0.012% |
| JNJ | ORB 15 min | long | 1,287 | -0.015% | -0.8 | -0.036% | +0.002% | -0.007% |
| JNJ | ORB 15 min | short | 1,345 | -0.115% | -5.7 | -0.092% | -0.135% | -0.040% |
| JNJ | ORB 15 min, busy opens | long | 82 | +0.045% | 0.5 | -0.062% | +0.142% | +0.009% |
| JNJ | ORB 15 min, busy opens | short | 108 | +0.096% | 0.9 | +0.216% | -0.016% | +0.175% |
| JNJ | ORB 30 min | long | 1,285 | -0.028% | -1.5 | -0.052% | -0.009% | -0.015% |
| JNJ | ORB 30 min | short | 1,247 | -0.109% | -5.3 | -0.100% | -0.118% | -0.025% |
| JNJ | ORB 30 min, busy opens | long | 69 | -0.051% | -0.6 | -0.306% | +0.114% | -0.061% |
| JNJ | ORB 30 min, busy opens | short | 99 | +0.031% | 0.3 | +0.007% | +0.054% | +0.105% |
| WFC | ORB 15 min | long | 1,377 | -0.035% | -1.2 | -0.065% | -0.011% | -0.004% |
| WFC | ORB 15 min | short | 1,287 | -0.012% | -0.4 | -0.029% | +0.005% | +0.017% |
| WFC | ORB 15 min, busy opens | long | 86 | -0.036% | -0.2 | -0.164% | +0.126% | +0.008% |
| WFC | ORB 15 min, busy opens | short | 106 | -0.236% | -1.5 | -0.378% | -0.142% | -0.169% |
| WFC | ORB 30 min | long | 1,334 | -0.037% | -1.3 | -0.062% | -0.017% | -0.002% |
| WFC | ORB 30 min | short | 1,256 | -0.034% | -1.1 | -0.039% | -0.031% | -0.006% |
| WFC | ORB 30 min, busy opens | long | 67 | +0.029% | 0.1 | -0.264% | +0.330% | +0.083% |
| WFC | ORB 30 min, busy opens | short | 82 | -0.272% | -1.5 | -0.450% | -0.126% | -0.245% |

**Pooled across these 11 (equal weight per trade):**

| rule | side | trades | net | t | 2016-20 | 2021-26 | stocks with net > 0 |
|---|---|---|---|---|---|---|---|
| ORB 15 min | long | 14,859 | -0.002% | -0.3 | -0.002% | -0.003% | 5 of 11 |
| ORB 15 min | short | 14,502 | -0.040% | -4.7 | -0.044% | -0.037% | 2 of 11 |
| ORB 15 min, busy opens | long | 793 | -0.003% | -0.1 | -0.084% | +0.065% | 6 of 11 |
| ORB 15 min, busy opens | short | 945 | -0.047% | -1.1 | +0.036% | -0.127% | 4 of 11 |
| ORB 30 min | long | 14,596 | -0.011% | -1.4 | -0.022% | -0.002% | 3 of 11 |
| ORB 30 min | short | 13,951 | -0.039% | -4.6 | -0.042% | -0.037% | 2 of 11 |
| ORB 30 min, busy opens | long | 691 | -0.044% | -0.8 | -0.145% | +0.048% | 4 of 11 |
| ORB 30 min, busy opens | short | 789 | -0.060% | -1.3 | -0.036% | -0.082% | 6 of 11 |
