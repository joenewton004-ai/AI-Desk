# Methods evaluation - generated tables

## 1. Moving-average crossover (50/200) vs alternatives, SPY 1994-2026

| | cagr | volatility | sharpe | max_drawdown | trades |
|---|---|---|---|---|---|
| buy_hold | 10.8% | 18.7% | 0.51 | -55.2% | 1 |
| sma_crossover | 10.2% | 13.9% | 0.59 | -33.7% | 31 |
| trend | 9.3% | 12.2% | 0.59 | -25.2% | 97 |
| momentum | 10.6% | 14.5% | 0.60 | -33.7% | 23 |

### Parameter sensitivity (Sharpe), SPY

| | slow 150 | slow 200 | slow 250 |
|---|---|---|---|
| fast 20 | 0.50 | 0.62 | 0.53 |
| fast 50 | 0.60 | 0.59 | 0.63 |
| fast 100 | 0.52 | 0.55 | 0.61 |

### Walk-forward (tune on 8 years, trade the next blind), SPY

| | cagr | volatility | sharpe | max_drawdown |
|---|---|---|---|---|
| sma_crossover (out-of-sample) | 7.5% | 12.5% | 0.50 | -32.1% |
| buy_hold | 8.9% | 19.0% | 0.45 | -55.2% |

### Other markets

| | cagr | volatility | sharpe | max_drawdown | trades |
|---|---|---|---|---|---|
| QQQ buy_hold | 8.1% | 26.3% | 0.36 | -83.0% | 1 |
| QQQ sma_crossover | 11.3% | 18.1% | 0.58 | -36.5% | 33 |
| IWM buy_hold | 8.2% | 23.7% | 0.38 | -58.6% | 1 |
| IWM sma_crossover | 2.5% | 16.9% | 0.13 | -49.8% | 37 |
| GLD buy_hold | 10.3% | 18.5% | 0.53 | -45.6% | 1 |
| GLD sma_crossover | 8.3% | 15.1% | 0.49 | -36.1% | 28 |
| TLT buy_hold | 3.3% | 14.3% | 0.17 | -48.4% | 1 |
| TLT sma_crossover | 2.9% | 11.1% | 0.15 | -26.9% | 44 |

## 2. Duopoly pairs trading, 2010-2026

| | cagr | volatility | sharpe | max_drawdown | trades | avg_gross_exposure | avg_net_exposure |
|---|---|---|---|---|---|---|---|
| pairs long/short (default) | 2.6% | 3.1% | 0.33 | -5.7% | 1788 | 45.3% | -0.0% |
| pairs long-only | 11.1% | 11.1% | 0.86 | -24.4% | 894 | 45.3% | 45.3% |
| buy & hold, all 12 stocks | 17.6% | 18.7% | 0.88 | -37.0% | 12 | 100.0% | 100.0% |
| SPY buy & hold | 14.0% | 17.0% | 0.76 | -33.7% | 1 | n/a | n/a |

### Correlation with the S&P 500 (daily returns)

- pairs long/short (default): 0.08
- pairs long-only: 0.73

### Each pair on its own (long/short)

| | cagr | volatility | sharpe | max_drawdown | trades | ratio drift/yr |
|---|---|---|---|---|---|---|
| V/MA | 2.9% | 4.6% | 0.31 | -7.0% | 312 | -0.8% |
| KO/PEP | 0.6% | 5.2% | -0.16 | -12.3% | 274 | 2.7% |
| HD/LOW | 2.5% | 5.6% | 0.19 | -12.6% | 300 | 1.1% |
| UPS/FDX | -0.2% | 8.4% | -0.17 | -33.2% | 260 | -4.2% |
| MCO/SPGI | 4.7% | 5.7% | 0.55 | -11.5% | 320 | 1.7% |
| BKNG/EXPE | 3.5% | 12.4% | 0.21 | -23.7% | 322 | 1.1% |

### Parameter sensitivity (Sharpe, long/short)

| | entry z 1.5 | entry z 2.0 | entry z 2.5 |
|---|---|---|---|
| lookback 20 | 0.49 | 0.38 | 0.33 |
| lookback 60 | 0.29 | 0.33 | 0.29 |
| lookback 120 | 0.23 | 0.25 | 0.23 |

### Sub-periods and costs (long/short)

| | cagr | volatility | sharpe | max_drawdown |
|---|---|---|---|---|
| 2011-2018 | 1.6% | 2.9% | 0.41 | -5.7% |
| 2019-2026 | 3.6% | 3.3% | 0.25 | -3.4% |
| costs x3 (9bps) | 2.0% | 3.1% | 0.15 | -6.1% |
