# The day-trader-skill's daily setups on the top 100 - generated tables

Excess = the setup's average minus the average of all top-100 stocks the same day (same hold, same costs). t-stats from the daily series of excess returns (5-day holds overlap: their t is divided by sqrt 5). **Survivors-only prices.**

| setup | hold | signals/yr | avg after costs | all stocks | excess | t | 2014-19 excess | 2020-26 excess |
|---|---|---|---|---|---|---|---|---|
| breakout_20d | next day | 3761 | -0.112% | -0.086% | -0.003% | -0.2 | +0.010% | -0.014% |
| breakout_20d | 5 days | 3761 | +0.023% | +0.154% | -0.072% | -1.0 | -0.052% | -0.089% |
| bull_flag | next day | 691 | -0.060% | -0.086% | +0.007% | 0.3 | -0.010% | +0.017% |
| bull_flag | 5 days | 691 | +0.157% | +0.154% | +0.015% | 0.1 | -0.086% | +0.079% |
| reclaim_ma20 | next day | 1476 | -0.112% | -0.086% | -0.002% | -0.1 | -0.000% | -0.003% |
| reclaim_ma20 | 5 days | 1476 | +0.093% | +0.154% | -0.075% | -0.7 | -0.032% | -0.110% |
| oversold | next day | 829 | +0.101% | -0.086% | -0.003% | -0.1 | -0.045% | +0.031% |
| oversold | 5 days | 829 | +0.819% | +0.154% | +0.169% | 1.0 | +0.034% | +0.282% |
| oversold_bounce | next day | 446 | -0.085% | -0.086% | -0.000% | -0.0 | +0.026% | -0.021% |
| oversold_bounce | 5 days | 446 | +0.270% | +0.154% | -0.046% | -0.2 | -0.153% | +0.038% |

For comparison, the live dip rule (above the 200-day average AND RSI 14 under 30, sold above the 5-day average) made +1.0% / +1.2% a dip in the two periods (research/CANDLE_RSI.md).
