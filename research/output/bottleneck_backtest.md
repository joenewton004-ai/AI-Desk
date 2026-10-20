# Bottleneck sleeve backtest - generated tables

## 1. Weekly money-flow rotation (8 stocks, re-picked weekly), 2014-2026

| | CAGR | volatility | Sharpe | max drawdown |
|---|---|---|---|---|
| Flow rotation (weekly) | 11.8% | 32.2% | 0.45 | -60.7% |
| Universe, equal-weight | 14.2% | 20.4% | 0.66 | -40.9% |
| SPY | 13.7% | 16.3% | 0.75 | -32.2% |

### Robustness

| | CAGR | volatility | Sharpe | max drawdown |
|---|---|---|---|---|
| top 4 industries | 9.0% | 29.9% | 0.37 | -58.1% |
| top 12 industries | 18.6% | 33.2% | 0.62 | -44.1% |
| 16 stocks | 10.1% | 27.1% | 0.42 | -53.0% |
| costs x3 (0.3%/trade) | 3.4% | 32.2% | 0.21 | -66.9% |
| re-pick every 4 weeks (exit rule weekly) | 13.3% | 32.4% | 0.49 | -68.0% |
| re-pick every 13 weeks (exit rule weekly) | 21.2% | 34.4% | 0.68 | -41.6% |

2014-2019: rotation 5.3%/yr vs universe 13.4% vs SPY 12.1%

2020-2026: rotation 17.9%/yr vs universe 14.9% vs SPY 15.0%

Beat SPY in 5 of 13 calendar years. Worst year: -23.5% (2018). Average weekly turnover: about 8 names held.

### Parameter grid: moving average x re-pick frequency (exit checked weekly)

Each cell: return/yr, Sharpe, worst drawdown. Then the same for 2014-2019 | 2020-2026, and the return at 3x costs.

| MA | re-pick | return/yr | Sharpe | worst drop | 2014-19 return (Sharpe) | 2020-26 return (Sharpe) | return at 3x costs |
|---|---|---|---|---|---|---|---|
| 50-day | weekly | 8.9% | 0.37 | -45% | -2.8% (-0.06) | 20.4% (0.62) | -1.9% |
| 50-day | every 2 weeks | 12.3% | 0.48 | -45% | 1.1% (0.12) | 23.2% (0.69) | 4.1% |
| 50-day | every 4 weeks | 13.5% | 0.50 | -50% | 2.6% (0.19) | 24.0% (0.69) | 7.2% |
| 100-day | weekly | 9.8% | 0.40 | -47% | 2.1% (0.16) | 17.1% (0.53) | 0.2% |
| 100-day | every 2 weeks | 17.0% | 0.60 | -46% | 9.7% (0.49) | 23.8% (0.69) | 10.2% |
| 100-day | every 4 weeks | 13.0% | 0.49 | -44% | 6.3% (0.34) | 19.3% (0.60) | 8.4% |
| 200-day | weekly | 11.8% | 0.45 | -61% | 5.3% (0.31) | 17.9% (0.55) | 3.4% |
| 200-day | every 2 weeks | 14.1% | 0.51 | -63% | 10.2% (0.51) | 17.7% (0.54) | 8.8% |
| 200-day | every 4 weeks | 13.3% | 0.49 | -68% | 6.5% (0.35) | 19.6% (0.59) | 9.6% |

For comparison: SPY 13.7%/yr (Sharpe 0.75); equal-weight universe 14.2% (0.66); 2014-19 SPY 12.1%, 2020-26 SPY 15.0%

## 2. The full desk, monthly: 50% quality screen (quarterly) + 20% flow rotation + 30% SPY momentum

| | CAGR | volatility | Sharpe | max drawdown |
|---|---|---|---|---|
| Desk 50/20/30 | 15.5% | 16.3% | 0.85 | -24.0% |
| Previous 70/30 (screen + SPY momentum) | 15.8% | 15.9% | 0.89 | -27.6% |
| Quality screen alone (quarterly) | 17.9% | 18.4% | 0.89 | -33.4% |
| Flow rotation alone | 13.3% | 30.3% | 0.51 | -58.8% |
| SPY | 13.8% | 14.5% | 0.83 | -23.9% |

Monthly correlation between the quality screen and the flow rotation: 0.48

## 3. Recent picks (last 6 weeks)

| week | top industries (SIC codes) | picks |
|---|---|---|
| 2026-09-04 | 291, 441, 809, 506 | SNDK, AGL, DELL, STX, WDC, HPE, FTNT, CLMT |
| 2026-09-11 | 291, 441, 173, 506 | AGL, SNDK, DELL, STX, HPE, CLMT, PBF, DK |
| 2026-09-18 | 291, 441, 506, 100 | AGL, CLMT, DK, MPC, FRO, CRL, FTRE, NTRA |
| 2026-09-25 | 291, 506, 441, 736 | AGL, FTRE, NTRA, CLMT, KFRC, CRL, MAN, AMN |
| 2026-10-02 | 291, 506, 441, 736 | MXL, DELL, MU, SNDK, AMD, MRVL, HPE, INTC |
| 2026-10-09 | 291, 506, 441, 736 | AGL, DELL, HPE, PBF, SNDK, MPC, FTNT, FRO |
