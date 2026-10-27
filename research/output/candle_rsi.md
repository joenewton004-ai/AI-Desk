# Candles + SMA trend + RSI on daily bars - generated tables

Protocol fixed in research/candle_rsi.py before running. Long only; signal at the close, buy next open, sell at the open after the exit. Per-trade returns are after costs (ETFs 0.02%, stocks 0.05% each way). Stocks: point-in-time top 100, **survivors-only prices**.

## ETFS - development period 1993-01-01 to 2012-12-31: all 72 rules

| trend | RSI | candle | exit | trades | net/trade | win | t | days held |
|---|---|---|---|---|---|---|---|---|
| no trend filter | RSI(2)<10 | no candle | exit: close > SMA5 | 1,023 | +0.586% | 71% | 6.0 | 3.7 |
| no trend filter | RSI(2)<10 | no candle | exit: 5 days | 1,118 | +0.631% | 59% | 5.7 | 5.0 |
| above SMA200 | RSI(2)<10 | no candle | exit: close > SMA5 | 565 | +0.469% | 72% | 5.1 | 3.6 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | no candle | exit: close > SMA5 | 537 | +0.454% | 72% | 4.8 | 3.6 |
| above SMA200 | RSI(2)<10 | no candle | exit: 5 days | 588 | +0.498% | 61% | 4.6 | 5.0 |
| no trend filter | RSI(14)<30 | no candle | exit: close > SMA5 | 161 | +1.641% | 73% | 4.4 | 3.3 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | no candle | exit: 5 days | 560 | +0.491% | 60% | 4.3 | 5.0 |
| no trend filter | no RSI | hammer | exit: close > SMA5 | 1,147 | +0.209% | 65% | 3.9 | 2.2 |
| above SMA200 | no RSI | hammer | exit: close > SMA5 | 774 | +0.174% | 66% | 3.3 | 2.2 |
| above SMA200 & SMA50>SMA200 | no RSI | reversal close | exit: close > SMA5 | 1,136 | +0.142% | 64% | 3.2 | 2.2 |
| above SMA200 | RSI(14)<30 | no candle | exit: close > SMA5 | 29 | +1.787% | 79% | 3.0 | 2.9 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | no candle | exit: close > SMA5 | 29 | +1.787% | 79% | 3.0 | 2.9 |
| above SMA200 | no RSI | no candle | exit: 5 days | 2,780 | +0.138% | 57% | 2.9 | 5.0 |
| no trend filter | no RSI | no candle | exit: 5 days | 4,141 | +0.144% | 55% | 2.9 | 5.0 |
| above SMA200 | no RSI | reversal close | exit: close > SMA5 | 1,277 | +0.119% | 64% | 2.8 | 2.2 |
| above SMA200 & SMA50>SMA200 | no RSI | no candle | exit: 5 days | 2,445 | +0.133% | 57% | 2.6 | 5.0 |
| no trend filter | RSI(14)<30 | no candle | exit: 5 days | 163 | +1.118% | 56% | 2.6 | 5.0 |
| above SMA200 & SMA50>SMA200 | no RSI | hammer | exit: close > SMA5 | 689 | +0.144% | 65% | 2.5 | 2.2 |
| above SMA200 | RSI(14)<30 | no candle | exit: 5 days | 29 | +1.478% | 66% | 2.3 | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | no candle | exit: 5 days | 29 | +1.478% | 66% | 2.3 | 5.0 |
| no trend filter | no RSI | reversal close | exit: close > SMA5 | 2,019 | +0.116% | 63% | 2.3 | 2.3 |
| above SMA200 & SMA50>SMA200 | no RSI | reversal close | exit: 5 days | 944 | +0.172% | 60% | 2.1 | 5.0 |
| no trend filter | RSI(2)<10 | hammer | exit: 5 days | 58 | +0.964% | 62% | 2.0 | 5.0 |
| above SMA200 | RSI(2)<10 | hammer | exit: 5 days | 24 | +1.100% | 67% | 2.0 | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | hammer | exit: 5 days | 24 | +1.100% | 67% | 2.0 | 5.0 |
| above SMA200 | no RSI | no candle | exit: close > SMA5 | 8,226 | +0.024% | 57% | 1.6 | 1.7 |
| above SMA200 | no RSI | reversal close | exit: 5 days | 1,056 | +0.116% | 59% | 1.5 | 5.0 |
| above SMA200 & SMA50>SMA200 | no RSI | no candle | exit: close > SMA5 | 7,198 | +0.023% | 58% | 1.4 | 1.7 |
| no trend filter | no RSI | no candle | exit: close > SMA5 | 11,636 | +0.024% | 57% | 1.4 | 1.8 |
| no trend filter | RSI(14)<30 | hammer | exit: 5 days | 18 | +1.096% | 61% | 1.3 | 5.0 |
| no trend filter | RSI(14)<30 | reversal close | exit: 5 days | 20 | +1.073% | 60% | 1.2 | 5.0 |
| no trend filter | no RSI | hammer | exit: 5 days | 981 | +0.113% | 58% | 1.2 | 5.0 |
| above SMA200 | RSI(2)<10 | hammer | exit: close > SMA5 | 24 | +0.500% | 75% | 1.1 | 3.8 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | hammer | exit: close > SMA5 | 24 | +0.500% | 75% | 1.1 | 3.8 |
| no trend filter | RSI(2)<10 | hammer | exit: close > SMA5 | 58 | +0.409% | 69% | 1.1 | 3.7 |
| above SMA200 | RSI(14)<30 | reversal close | exit: close > SMA5 | 3 | +1.377% | 67% | 1.0 | 3.3 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | reversal close | exit: close > SMA5 | 3 | +1.377% | 67% | 1.0 | 3.3 |
| above SMA200 | no RSI | hammer | exit: 5 days | 652 | +0.088% | 58% | 0.9 | 5.0 |
| no trend filter | no RSI | reversal close | exit: 5 days | 1,679 | +0.070% | 56% | 0.8 | 5.0 |
| above SMA200 & SMA50>SMA200 | no RSI | hammer | exit: 5 days | 579 | +0.082% | 59% | 0.8 | 5.0 |
| no trend filter | RSI(14)<30 | bullish engulfing | exit: 5 days | 3 | +1.187% | 67% | 0.8 | 5.0 |
| no trend filter | RSI(14)<30 | bullish engulfing | exit: close > SMA5 | 3 | +0.700% | 67% | 0.7 | 2.0 |
| no trend filter | RSI(14)<30 | reversal close | exit: close > SMA5 | 22 | +0.536% | 64% | 0.6 | 2.6 |
| no trend filter | no RSI | bullish engulfing | exit: close > SMA5 | 651 | +0.033% | 59% | 0.4 | 1.9 |
| no trend filter | RSI(14)<30 | hammer | exit: close > SMA5 | 18 | +0.209% | 67% | 0.3 | 2.9 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | reversal close | exit: close > SMA5 | 32 | +0.130% | 66% | 0.3 | 3.3 |
| above SMA200 | RSI(14)<30 | reversal close | exit: 5 days | 3 | +0.064% | 33% | 0.0 | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | reversal close | exit: 5 days | 3 | +0.064% | 33% | 0.0 | 5.0 |
| above SMA200 | RSI(2)<10 | reversal close | exit: close > SMA5 | 33 | +0.014% | 64% | 0.0 | 3.4 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | reversal close | exit: 5 days | 32 | -0.022% | 56% | -0.0 | 5.0 |
| no trend filter | no RSI | bullish engulfing | exit: 5 days | 590 | -0.021% | 50% | -0.2 | 5.0 |
| no trend filter | RSI(2)<10 | reversal close | exit: close > SMA5 | 77 | -0.065% | 60% | -0.2 | 3.4 |
| above SMA200 | RSI(2)<10 | reversal close | exit: 5 days | 33 | -0.181% | 55% | -0.3 | 5.0 |
| no trend filter | RSI(2)<10 | reversal close | exit: 5 days | 78 | -0.269% | 46% | -0.6 | 5.0 |
| above SMA200 & SMA50>SMA200 | no RSI | bullish engulfing | exit: 5 days | 332 | -0.235% | 49% | -1.7 | 5.0 |
| above SMA200 | no RSI | bullish engulfing | exit: 5 days | 381 | -0.221% | 48% | -1.7 | 5.0 |
| above SMA200 & SMA50>SMA200 | no RSI | bullish engulfing | exit: close > SMA5 | 356 | -0.158% | 56% | -1.8 | 1.9 |
| above SMA200 | no RSI | bullish engulfing | exit: close > SMA5 | 410 | -0.168% | 56% | -2.1 | 1.9 |
| no trend filter | RSI(2)<10 | bullish engulfing | exit: close > SMA5 | 0 | | | | |
| no trend filter | RSI(2)<10 | bullish engulfing | exit: 5 days | 0 | | | | |
| above SMA200 | RSI(2)<10 | bullish engulfing | exit: close > SMA5 | 0 | | | | |
| above SMA200 | RSI(2)<10 | bullish engulfing | exit: 5 days | 0 | | | | |
| above SMA200 | RSI(14)<30 | hammer | exit: close > SMA5 | 1 | -0.680% | 0% | nan | 5.0 |
| above SMA200 | RSI(14)<30 | hammer | exit: 5 days | 1 | -0.680% | 0% | nan | 5.0 |
| above SMA200 | RSI(14)<30 | bullish engulfing | exit: close > SMA5 | 0 | | | | |
| above SMA200 | RSI(14)<30 | bullish engulfing | exit: 5 days | 0 | | | | |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | bullish engulfing | exit: close > SMA5 | 0 | | | | |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | bullish engulfing | exit: 5 days | 0 | | | | |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | hammer | exit: close > SMA5 | 1 | -0.680% | 0% | nan | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | hammer | exit: 5 days | 1 | -0.680% | 0% | nan | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | bullish engulfing | exit: close > SMA5 | 0 | | | | |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | bullish engulfing | exit: 5 days | 0 | | | | |

Picked for the holdout (best t-stat with a candle, 100+ trades): no trend filter, no RSI, hammer, exit: close > SMA5; above SMA200, no RSI, hammer, exit: close > SMA5; above SMA200 & SMA50>SMA200, no RSI, reversal close, exit: close > SMA5

## STOCKS - development period 2014-05-15 to 2019-12-31: all 72 rules

| trend | RSI | candle | exit | trades | net/trade | win | t | days held |
|---|---|---|---|---|---|---|---|---|
| no trend filter | RSI(14)<30 | no candle | exit: 5 days | 1,618 | +0.902% | 59% | 7.8 | 5.0 |
| no trend filter | RSI(14)<30 | no candle | exit: close > SMA5 | 1,569 | +0.687% | 65% | 7.7 | 3.6 |
| no trend filter | no RSI | no candle | exit: 5 days | 28,353 | +0.140% | 54% | 6.7 | 5.0 |
| above SMA200 | RSI(14)<30 | no candle | exit: close > SMA5 | 237 | +1.008% | 72% | 5.1 | 3.8 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | no candle | exit: close > SMA5 | 237 | +1.008% | 72% | 5.1 | 3.8 |
| no trend filter | RSI(2)<10 | no candle | exit: 5 days | 7,409 | +0.207% | 54% | 4.6 | 5.0 |
| above SMA200 | RSI(14)<30 | no candle | exit: 5 days | 244 | +0.929% | 60% | 3.8 | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | no candle | exit: 5 days | 244 | +0.929% | 60% | 3.8 | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | no candle | exit: close > SMA5 | 3,798 | +0.172% | 64% | 3.8 | 3.9 |
| above SMA200 | RSI(2)<10 | no candle | exit: close > SMA5 | 3,988 | +0.163% | 64% | 3.7 | 3.9 |
| no trend filter | RSI(14)<30 | reversal close | exit: close > SMA5 | 277 | +0.737% | 60% | 3.6 | 3.1 |
| no trend filter | RSI(2)<10 | no candle | exit: close > SMA5 | 6,656 | +0.136% | 63% | 3.5 | 4.0 |
| above SMA200 | no RSI | no candle | exit: 5 days | 20,268 | +0.076% | 53% | 3.5 | 5.0 |
| above SMA200 & SMA50>SMA200 | no RSI | no candle | exit: 5 days | 18,004 | +0.080% | 53% | 3.4 | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | no candle | exit: 5 days | 4,037 | +0.164% | 55% | 3.2 | 5.0 |
| above SMA200 | RSI(2)<10 | no candle | exit: 5 days | 4,237 | +0.151% | 55% | 3.0 | 5.0 |
| no trend filter | RSI(14)<30 | reversal close | exit: 5 days | 277 | +0.775% | 55% | 2.7 | 5.0 |
| no trend filter | no RSI | hammer | exit: 5 days | 6,065 | +0.117% | 53% | 2.5 | 5.0 |
| no trend filter | RSI(14)<30 | bullish engulfing | exit: close > SMA5 | 51 | +1.086% | 65% | 2.5 | 2.0 |
| no trend filter | no RSI | bullish engulfing | exit: 5 days | 4,462 | +0.121% | 53% | 2.4 | 5.0 |
| no trend filter | no RSI | reversal close | exit: 5 days | 10,351 | +0.081% | 52% | 2.4 | 5.0 |
| no trend filter | RSI(14)<30 | bullish engulfing | exit: 5 days | 49 | +1.894% | 51% | 2.2 | 5.0 |
| above SMA200 & SMA50>SMA200 | no RSI | hammer | exit: 5 days | 3,832 | +0.115% | 53% | 2.2 | 5.0 |
| no trend filter | no RSI | hammer | exit: close > SMA5 | 6,863 | +0.053% | 58% | 2.0 | 2.3 |
| above SMA200 | no RSI | hammer | exit: 5 days | 4,257 | +0.096% | 53% | 1.9 | 5.0 |
| no trend filter | no RSI | reversal close | exit: close > SMA5 | 12,209 | +0.029% | 59% | 1.4 | 2.3 |
| above SMA200 | RSI(14)<30 | hammer | exit: close > SMA5 | 19 | +0.514% | 63% | 1.3 | 3.5 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | hammer | exit: close > SMA5 | 19 | +0.514% | 63% | 1.3 | 3.5 |
| no trend filter | no RSI | bullish engulfing | exit: close > SMA5 | 4,897 | +0.036% | 56% | 1.2 | 1.9 |
| no trend filter | RSI(2)<10 | hammer | exit: close > SMA5 | 555 | +0.132% | 62% | 1.1 | 3.6 |
| above SMA200 | RSI(14)<30 | hammer | exit: 5 days | 19 | +0.506% | 58% | 1.0 | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | hammer | exit: 5 days | 19 | +0.506% | 58% | 1.0 | 5.0 |
| no trend filter | RSI(14)<30 | hammer | exit: close > SMA5 | 170 | +0.259% | 64% | 1.0 | 3.2 |
| above SMA200 & SMA50>SMA200 | no RSI | bullish engulfing | exit: 5 days | 2,793 | +0.040% | 53% | 0.7 | 5.0 |
| above SMA200 | RSI(2)<10 | reversal close | exit: 5 days | 378 | +0.110% | 52% | 0.7 | 5.0 |
| above SMA200 | RSI(2)<10 | hammer | exit: close > SMA5 | 295 | +0.092% | 62% | 0.6 | 3.7 |
| above SMA200 & SMA50>SMA200 | no RSI | bullish engulfing | exit: close > SMA5 | 3,057 | +0.019% | 56% | 0.6 | 1.9 |
| above SMA200 & SMA50>SMA200 | no RSI | hammer | exit: close > SMA5 | 4,394 | +0.017% | 58% | 0.6 | 2.3 |
| above SMA200 | no RSI | bullish engulfing | exit: 5 days | 3,190 | +0.021% | 52% | 0.4 | 5.0 |
| above SMA200 | RSI(14)<30 | reversal close | exit: close > SMA5 | 29 | +0.173% | 55% | 0.4 | 3.7 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | reversal close | exit: close > SMA5 | 29 | +0.173% | 55% | 0.4 | 3.7 |
| no trend filter | RSI(2)<10 | reversal close | exit: close > SMA5 | 729 | +0.043% | 61% | 0.4 | 3.7 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | hammer | exit: close > SMA5 | 279 | +0.055% | 61% | 0.4 | 3.7 |
| above SMA200 | no RSI | bullish engulfing | exit: close > SMA5 | 3,502 | +0.010% | 55% | 0.3 | 1.9 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | reversal close | exit: 5 days | 355 | +0.049% | 50% | 0.3 | 5.0 |
| above SMA200 | no RSI | hammer | exit: close > SMA5 | 4,878 | +0.007% | 58% | 0.3 | 2.3 |
| above SMA200 | RSI(2)<10 | reversal close | exit: close > SMA5 | 377 | +0.003% | 63% | 0.0 | 3.6 |
| no trend filter | RSI(2)<10 | hammer | exit: 5 days | 558 | +0.002% | 50% | 0.0 | 5.0 |
| no trend filter | RSI(2)<10 | reversal close | exit: 5 days | 738 | -0.005% | 50% | -0.0 | 5.0 |
| above SMA200 | no RSI | reversal close | exit: 5 days | 7,132 | -0.007% | 51% | -0.2 | 5.0 |
| above SMA200 | RSI(2)<10 | hammer | exit: 5 days | 296 | -0.042% | 49% | -0.2 | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | hammer | exit: 5 days | 280 | -0.065% | 49% | -0.3 | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | reversal close | exit: close > SMA5 | 354 | -0.064% | 61% | -0.4 | 3.7 |
| above SMA200 | RSI(14)<30 | reversal close | exit: 5 days | 30 | -0.244% | 37% | -0.5 | 5.0 |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | reversal close | exit: 5 days | 30 | -0.244% | 37% | -0.5 | 5.0 |
| no trend filter | RSI(2)<10 | bullish engulfing | exit: 5 days | 2 | -1.081% | 50% | -0.5 | 5.0 |
| no trend filter | RSI(2)<10 | bullish engulfing | exit: close > SMA5 | 2 | -1.558% | 50% | -0.8 | 4.5 |
| above SMA200 & SMA50>SMA200 | no RSI | reversal close | exit: 5 days | 6,436 | -0.032% | 51% | -0.8 | 5.0 |
| above SMA200 | no RSI | reversal close | exit: close > SMA5 | 8,506 | -0.018% | 58% | -0.8 | 2.3 |
| no trend filter | RSI(14)<30 | hammer | exit: 5 days | 167 | -0.325% | 51% | -0.9 | 5.0 |
| above SMA200 & SMA50>SMA200 | no RSI | reversal close | exit: close > SMA5 | 7,642 | -0.030% | 58% | -1.3 | 2.3 |
| no trend filter | no RSI | no candle | exit: close > SMA5 | 78,332 | -0.015% | 55% | -2.1 | 1.8 |
| above SMA200 & SMA50>SMA200 | no RSI | no candle | exit: close > SMA5 | 50,989 | -0.034% | 54% | -4.3 | 1.8 |
| above SMA200 | no RSI | no candle | exit: close > SMA5 | 58,060 | -0.036% | 54% | -4.9 | 1.8 |
| above SMA200 | RSI(2)<10 | bullish engulfing | exit: close > SMA5 | 0 | | | | |
| above SMA200 | RSI(2)<10 | bullish engulfing | exit: 5 days | 0 | | | | |
| above SMA200 | RSI(14)<30 | bullish engulfing | exit: close > SMA5 | 0 | | | | |
| above SMA200 | RSI(14)<30 | bullish engulfing | exit: 5 days | 0 | | | | |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | bullish engulfing | exit: close > SMA5 | 0 | | | | |
| above SMA200 & SMA50>SMA200 | RSI(2)<10 | bullish engulfing | exit: 5 days | 0 | | | | |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | bullish engulfing | exit: close > SMA5 | 0 | | | | |
| above SMA200 & SMA50>SMA200 | RSI(14)<30 | bullish engulfing | exit: 5 days | 0 | | | | |

Picked for the holdout (best t-stat with a candle, 100+ trades): no trend filter, RSI(14)<30, reversal close, exit: close > SMA5; no trend filter, RSI(14)<30, reversal close, exit: 5 days; no trend filter, no RSI, hammer, exit: 5 days

## HOLDOUT - the picked rules on data they never saw

| picked on | tested on | rule | trades | net/trade | win | t | same without the candle | strategy Sharpe | benchmark Sharpe | passes 1/2/3 |
|---|---|---|---|---|---|---|---|---|---|---|
| etf | etf | no trend filter, no RSI, hammer, exit: close > SMA5 | 1,158 | +0.048% | 62% | 0.9 | +0.046% (12,059) | 0.08 | 0.59 | no/yes/no |
| etf | stock | no trend filter, no RSI, hammer, exit: close > SMA5 | 8,025 | +0.042% | 60% | 1.0 | +0.000% (91,509) | 0.23 | 0.57 | no/yes/no |
| etf | etf | above SMA200, no RSI, hammer, exit: close > SMA5 | 947 | +0.068% | 62% | 1.7 | +0.034% (9,898) | 0.17 | 0.59 | no/yes/no |
| etf | stock | above SMA200, no RSI, hammer, exit: close > SMA5 | 5,401 | +0.051% | 61% | 1.2 | -0.021% (63,979) | 0.23 | 0.57 | no/yes/no |
| etf | etf | above SMA200 & SMA50>SMA200, no RSI, reversal close, exit: close > SMA5 | 1,441 | +0.069% | 63% | 2.0 | +0.027% (9,070) | 0.15 | 0.59 | no/yes/no |
| etf | stock | above SMA200 & SMA50>SMA200, no RSI, reversal close, exit: close > SMA5 | 8,713 | +0.018% | 60% | 0.5 | -0.021% (55,365) | 0.04 | 0.57 | no/yes/no |
| stock | etf | no trend filter, RSI(14)<30, reversal close, exit: close > SMA5 | 26 | +1.056% | 81% | 1.4 | +0.584% (157) | 0.27 | 0.59 | no/yes/no |
| stock | stock | no trend filter, RSI(14)<30, reversal close, exit: close > SMA5 | 424 | +0.726% | 68% | 2.3 | +0.697% (1,964) | 0.24 | 0.57 | yes/yes/no |
| stock | etf | no trend filter, RSI(14)<30, reversal close, exit: 5 days | 27 | +0.488% | 63% | 0.4 | +0.835% (170) | 0.09 | 0.59 | no/no/no |
| stock | stock | no trend filter, RSI(14)<30, reversal close, exit: 5 days | 431 | +0.114% | 49% | 0.3 | +0.713% (2,160) | 0.16 | 0.57 | no/no/no |
| stock | etf | no trend filter, no RSI, hammer, exit: 5 days | 1,003 | +0.116% | 57% | 1.4 | +0.209% (4,158) | 0.10 | 0.59 | no/no/no |
| stock | stock | no trend filter, no RSI, hammer, exit: 5 days | 7,201 | +0.107% | 52% | 1.7 | +0.162% (34,204) | 0.36 | 0.57 | no/no/no |

## Does a candle add anything? Holdout, every trend x RSI x exit, candle vs no candle (net per trade)

| market | trend | RSI | exit | no candle | hammer | bullish engulfing | reversal close |
|---|---|---|---|---|---|---|---|
| etf | no trend filter | no RSI | exit: close > SMA5 | +0.046% (12,059) | +0.048% (1,158) | +0.190% (521) | +0.042% (2,010) |
| etf | no trend filter | no RSI | exit: 5 days | +0.209% (4,158) | +0.116% (1,003) | +0.225% (491) | +0.079% (1,711) |
| etf | no trend filter | RSI(2)<10 | exit: close > SMA5 | +0.181% (940) | +0.011% (72) | - | +0.047% (164) |
| etf | no trend filter | RSI(2)<10 | exit: 5 days | +0.285% (1,005) | +0.274% (73) | - | +0.011% (163) |
| etf | no trend filter | RSI(14)<30 | exit: close > SMA5 | +0.584% (157) | +0.740% (14) | +1.124% (5) | +1.056% (26) |
| etf | no trend filter | RSI(14)<30 | exit: 5 days | +0.835% (170) | +0.126% (15) | +1.615% (5) | +0.488% (27) |
| etf | above SMA200 | no RSI | exit: close > SMA5 | +0.034% (9,898) | +0.068% (947) | +0.130% (409) | +0.071% (1,563) |
| etf | above SMA200 | no RSI | exit: 5 days | +0.173% (3,322) | +0.127% (808) | +0.205% (385) | +0.110% (1,310) |
| etf | above SMA200 | RSI(2)<10 | exit: close > SMA5 | +0.299% (662) | +0.322% (42) | - | +0.032% (92) |
| etf | above SMA200 | RSI(2)<10 | exit: 5 days | +0.418% (682) | +0.366% (42) | - | +0.120% (91) |
| etf | above SMA200 | RSI(14)<30 | exit: close > SMA5 | +1.323% (34) | +1.586% (2) | - | +2.256% (4) |
| etf | above SMA200 | RSI(14)<30 | exit: 5 days | +1.219% (33) | -0.106% (2) | - | +1.294% (4) |
| etf | above SMA200 & SMA50>SMA200 | no RSI | exit: close > SMA5 | +0.027% (9,070) | +0.068% (894) | +0.174% (357) | +0.069% (1,441) |
| etf | above SMA200 & SMA50>SMA200 | no RSI | exit: 5 days | +0.171% (3,066) | +0.116% (760) | +0.285% (339) | +0.112% (1,214) |
| etf | above SMA200 & SMA50>SMA200 | RSI(2)<10 | exit: close > SMA5 | +0.299% (637) | +0.395% (40) | - | +0.045% (86) |
| etf | above SMA200 & SMA50>SMA200 | RSI(2)<10 | exit: 5 days | +0.420% (656) | +0.411% (40) | - | +0.127% (85) |
| etf | above SMA200 & SMA50>SMA200 | RSI(14)<30 | exit: close > SMA5 | +1.323% (34) | +1.586% (2) | - | +2.256% (4) |
| etf | above SMA200 & SMA50>SMA200 | RSI(14)<30 | exit: 5 days | +1.219% (33) | -0.106% (2) | - | +1.294% (4) |
| stock | no trend filter | no RSI | exit: close > SMA5 | +0.000% (91,509) | +0.042% (8,025) | -0.031% (5,971) | +0.009% (15,020) |
| stock | no trend filter | no RSI | exit: 5 days | +0.162% (34,204) | +0.107% (7,201) | +0.029% (5,459) | +0.067% (12,880) |
| stock | no trend filter | RSI(2)<10 | exit: close > SMA5 | +0.368% (8,709) | +0.348% (845) | +1.454% (1) | +0.360% (1,062) |
| stock | no trend filter | RSI(2)<10 | exit: 5 days | +0.484% (9,748) | +0.441% (854) | -1.795% (1) | +0.192% (1,079) |
| stock | no trend filter | RSI(14)<30 | exit: close > SMA5 | +0.697% (1,964) | +0.529% (249) | +1.530% (59) | +0.726% (424) |
| stock | no trend filter | RSI(14)<30 | exit: 5 days | +0.713% (2,160) | +0.188% (253) | +0.340% (60) | +0.114% (431) |
| stock | above SMA200 | no RSI | exit: close > SMA5 | -0.021% (63,979) | +0.051% (5,401) | -0.070% (3,945) | +0.004% (9,818) |
| stock | above SMA200 | no RSI | exit: 5 days | +0.101% (22,925) | +0.087% (4,791) | -0.007% (3,609) | +0.025% (8,285) |
| stock | above SMA200 | RSI(2)<10 | exit: close > SMA5 | +0.373% (4,695) | +0.217% (395) | - | +0.482% (518) |
| stock | above SMA200 | RSI(2)<10 | exit: 5 days | +0.401% (5,041) | +0.269% (397) | - | +0.363% (522) |
| stock | above SMA200 | RSI(14)<30 | exit: close > SMA5 | +1.214% (298) | +2.158% (23) | -1.318% (2) | +1.432% (45) |
| stock | above SMA200 | RSI(14)<30 | exit: 5 days | +1.140% (306) | +2.496% (25) | -0.588% (2) | +0.273% (46) |
| stock | above SMA200 & SMA50>SMA200 | no RSI | exit: close > SMA5 | -0.021% (55,365) | +0.030% (4,846) | -0.073% (3,428) | +0.018% (8,713) |
| stock | above SMA200 & SMA50>SMA200 | no RSI | exit: 5 days | +0.111% (20,105) | +0.060% (4,307) | +0.028% (3,144) | +0.025% (7,354) |
| stock | above SMA200 & SMA50>SMA200 | RSI(2)<10 | exit: close > SMA5 | +0.350% (4,429) | +0.205% (376) | - | +0.459% (490) |
| stock | above SMA200 & SMA50>SMA200 | RSI(2)<10 | exit: 5 days | +0.372% (4,771) | +0.273% (378) | - | +0.326% (494) |
| stock | above SMA200 & SMA50>SMA200 | RSI(14)<30 | exit: close > SMA5 | +1.214% (298) | +2.158% (23) | -1.318% (2) | +1.432% (45) |
| stock | above SMA200 & SMA50>SMA200 | RSI(14)<30 | exit: 5 days | +1.140% (306) | +2.496% (25) | -0.588% (2) | +0.273% (46) |

## Follow-up (not pre-registered): RSI dip-buying WITHOUT a candle, as a strategy

Stocks: up to 10 positions, 10% each, T-bills on the rest; ETFs: each fund alone, averaged. Sharpe above T-bills; benchmark = equal-weight top 100 (stocks) / buy and hold (ETFs). Survivors-only stock prices.

| market | rule | period | trades | net/trade | t | time invested | strategy Sharpe | benchmark Sharpe | correlation with benchmark |
|---|---|---|---|---|---|---|---|---|---|
| etf | no trend filter, RSI(14)<30, no candle, exit: 5 days | development | 163 | +1.118% | 2.6 | 4% | 0.23 | 0.33 | 0.46 |
| etf | no trend filter, RSI(14)<30, no candle, exit: 5 days | holdout | 170 | +0.835% | 2.2 | 4% | 0.25 | 0.59 | 0.49 |
| etf | no trend filter, RSI(14)<30, no candle, exit: close > SMA5 | development | 161 | +1.641% | 4.4 | 3% | 0.38 | 0.33 | 0.41 |
| etf | no trend filter, RSI(14)<30, no candle, exit: close > SMA5 | holdout | 157 | +0.584% | 1.6 | 3% | 0.17 | 0.59 | 0.45 |
| etf | no trend filter, RSI(2)<10, no candle, exit: 5 days | development | 1,118 | +0.631% | 5.7 | 28% | 0.53 | 0.33 | 0.69 |
| etf | no trend filter, RSI(2)<10, no candle, exit: 5 days | holdout | 1,005 | +0.285% | 3.0 | 25% | 0.27 | 0.59 | 0.71 |
| etf | above SMA200, RSI(2)<10, no candle, exit: close > SMA5 | development | 565 | +0.469% | 5.1 | 10% | 0.44 | 0.33 | 0.35 |
| etf | above SMA200, RSI(2)<10, no candle, exit: close > SMA5 | holdout | 662 | +0.299% | 4.6 | 12% | 0.34 | 0.59 | 0.46 |
| etf | above SMA200, RSI(14)<30, no candle, exit: close > SMA5 | development | 29 | +1.787% | 3.0 | 0% | 0.25 | 0.33 | 0.14 |
| etf | above SMA200, RSI(14)<30, no candle, exit: close > SMA5 | holdout | 34 | +1.323% | 3.4 | 1% | 0.29 | 0.59 | 0.16 |
| stock | no trend filter, RSI(14)<30, no candle, exit: 5 days | development | 1,618 | +0.902% | 7.8 | 41% | 0.71 | 0.81 | 0.74 |
| stock | no trend filter, RSI(14)<30, no candle, exit: 5 days | holdout | 2,160 | +0.713% | 4.6 | 45% | 0.48 | 0.57 | 0.71 |
| stock | no trend filter, RSI(14)<30, no candle, exit: close > SMA5 | development | 1,569 | +0.687% | 7.7 | 30% | 0.63 | 0.81 | 0.70 |
| stock | no trend filter, RSI(14)<30, no candle, exit: close > SMA5 | holdout | 1,964 | +0.697% | 5.3 | 33% | 0.54 | 0.57 | 0.66 |
| stock | no trend filter, RSI(2)<10, no candle, exit: 5 days | development | 7,409 | +0.207% | 4.6 | 94% | 0.32 | 0.81 | 0.91 |
| stock | no trend filter, RSI(2)<10, no candle, exit: 5 days | holdout | 9,748 | +0.484% | 8.4 | 94% | 0.65 | 0.57 | 0.88 |
| stock | above SMA200, RSI(2)<10, no candle, exit: close > SMA5 | development | 3,988 | +0.163% | 3.7 | 65% | 0.15 | 0.81 | 0.79 |
| stock | above SMA200, RSI(2)<10, no candle, exit: close > SMA5 | holdout | 4,695 | +0.373% | 6.6 | 67% | 0.61 | 0.57 | 0.67 |
| stock | above SMA200, RSI(14)<30, no candle, exit: close > SMA5 | development | 237 | +1.008% | 5.1 | 6% | 0.92 | 0.81 | 0.47 |
| stock | above SMA200, RSI(14)<30, no candle, exit: close > SMA5 | holdout | 298 | +1.214% | 4.7 | 6% | 0.69 | 0.57 | 0.36 |

## Robustness of the lead: stocks above their 200-day SMA with RSI(14) below X, sell above the 5-day SMA

| RSI(14) below | cost each way | trades | net/trade | t | development | holdout | positive years |
|---|---|---|---|---|---|---|---|
| 25 | 0.05% | 85 | +1.643% | 4.8 | +0.966% | +2.336% | 12 of 13 |
| 25 | 0.10% | 85 | +1.543% | 4.5 | +0.866% | +2.236% | 12 of 13 |
| 25 | 0.20% | 85 | +1.343% | 3.9 | +0.666% | +2.036% | 11 of 13 |
| 30 | 0.05% | 535 | +1.123% | 6.7 | +1.008% | +1.214% | 11 of 13 |
| 30 | 0.10% | 535 | +1.023% | 6.1 | +0.908% | +1.114% | 10 of 13 |
| 30 | 0.20% | 535 | +0.823% | 4.9 | +0.708% | +0.914% | 10 of 13 |
| 35 | 0.05% | 2,021 | +0.600% | 7.6 | +0.602% | +0.598% | 12 of 13 |
| 35 | 0.10% | 2,021 | +0.500% | 6.3 | +0.502% | +0.498% | 11 of 13 |
| 35 | 0.20% | 2,021 | +0.300% | 3.8 | +0.302% | +0.298% | 10 of 13 |

RSI(14) < 30, 0.05% costs, by year: 2014 -0.57%, 2015 +2.83%, 2016 +1.00%, 2017 +0.04%, 2018 +1.44%, 2019 +1.05%, 2020 +3.46%, 2021 +1.65%, 2022 -0.85%, 2023 +1.03%, 2024 +1.15%, 2025 +0.62%, 2026 +0.47%. Trades by stock (top 5): AAPL 11, HD 11, LOW 11, UNP 10, AMGN 9.
Share of the total from the best 5% of trades: 46%; worst trade -27.9%, best +17.9%.
