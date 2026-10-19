# Edge research - generated tables

## 1. Full period, SPY

| strategy | cagr | volatility | sharpe | max_drawdown | time_in_market | trades | sharpe_±1se |
|---|---|---|---|---|---|---|---|
| buy_hold | 10.8% | 18.7% | 0.51 | -55.2% | 100.0% | 1 | ±0.19 |
| trend | 9.3% | 12.2% | 0.59 | -25.2% | 76.8% | 97 | ±0.19 |
| rsi_reversion | 5.5% | 5.9% | 0.52 | -15.8% | 10.0% | 525 | ±0.19 |
| momentum | 10.6% | 14.5% | 0.60 | -33.7% | 81.3% | 23 | ±0.19 |
| vix_filter | 5.5% | 12.7% | 0.29 | -50.2% | 81.6% | 63 | ±0.18 |
| turn_of_month | 5.0% | 7.9% | 0.35 | -16.7% | 18.0% | 784 | ±0.18 |

## 2. Sub-periods (Sharpe above T-bills / CAGR / max drawdown)

| strategy | 1994-2006 | 2007-2016 | 2017-2026 |
|---|---|---|---|
| buy_hold | 0.45 / 10.7% / -48% | 0.39 / 6.9% / -55% | 0.73 / 15.1% / -34% |
| trend | 0.59 / 11.1% / -16% | 0.52 / 6.1% / -19% | 0.64 / 10.1% / -25% |
| rsi_reversion | 0.74 / 8.8% / -9% | 0.52 / 3.3% / -10% | 0.22 / 3.7% / -16% |
| momentum | 0.65 / 12.6% / -19% | 0.56 / 7.5% / -25% | 0.57 / 10.9% / -34% |
| vix_filter | 0.23 / 6.2% / -50% | 0.29 / 3.5% / -44% | 0.37 / 6.4% / -35% |
| turn_of_month | 0.60 / 8.6% / -14% | 0.02 / 0.5% / -17% | 0.34 / 4.9% / -11% |

## 3. Cost stress: CAGR at 3 / 8 / 18 bps per trade

| strategy | 3bps cagr% | 8bps cagr% | 18bps cagr% |
|---|---|---|---|
| buy_hold | 10.8% | 10.8% | 10.8% |
| trend | 9.3% | 9.1% | 8.8% |
| rsi_reversion | 5.5% | 4.7% | 3.0% |
| momentum | 10.6% | 10.6% | 10.5% |
| vix_filter | 5.5% | 5.4% | 5.2% |
| turn_of_month | 5.0% | 3.7% | 1.3% |

## 4. Same rules on other markets (Sharpe / CAGR / max drawdown)

| strategy | QQQ 2000+ | IWM 2001+ |
|---|---|---|
| buy_hold | 0.36 / 8.1% / -83% | 0.38 / 8.2% / -59% |
| trend | 0.47 / 8.6% / -48% | 0.30 / 5.3% / -32% |
| rsi_reversion | 0.30 / 4.0% / -17% | 0.45 / 4.5% / -18% |
| momentum | 0.53 / 10.9% / -41% | 0.39 / 6.9% / -36% |
| vix_filter | 0.05 / 1.1% / -85% | 0.19 / 3.6% / -46% |
| turn_of_month | 0.21 / 3.7% / -29% | 0.06 / 1.9% / -26% |

## 5. Parameter sensitivity, full period SPY (Sharpe)

A real edge shows a broad plateau; a lone peak is luck.

| trend | band=0.0 | band=0.01 | band=0.02 |
|---|---|---|---|
| lookback=100 | 0.49 | 0.49 | 0.41 |
| lookback=150 | 0.47 | 0.50 | 0.54 |
| lookback=200 | 0.54 | 0.59 | 0.65 |
| lookback=250 | 0.52 | 0.57 | 0.60 |

range: 0.41 to 0.65

| rsi_reversion | exit_sma=3 | exit_sma=5 | exit_sma=10 |
|---|---|---|---|
| entry_rsi=5 | 0.37 | 0.47 | 0.46 |
| entry_rsi=10 | 0.41 | 0.52 | 0.55 |
| entry_rsi=15 | 0.40 | 0.56 | 0.54 |

range: 0.37 to 0.56

| momentum | skip=0 | skip=21 |
|---|---|---|
| lookback=126 | 0.51 | 0.54 |
| lookback=189 | 0.56 | 0.59 |
| lookback=252 | 0.60 | 0.62 |
| lookback=315 | 0.57 | 0.58 |

range: 0.51 to 0.62

| vix_filter | enter_below=18 | enter_below=22 | enter_below=26 |
|---|---|---|---|
| exit_above=30 | 0.34 | 0.29 | 0.36 |
| exit_above=35 | 0.28 | 0.40 | 0.46 |
| exit_above=40 | 0.31 | 0.42 | 0.45 |

range: 0.28 to 0.46

| turn_of_month | days_after=2 | days_after=3 | days_after=4 |
|---|---|---|---|
| days_before=1 | 0.19 | 0.35 | 0.32 |
| days_before=2 | 0.21 | 0.35 | 0.33 |
| days_before=3 | 0.27 | 0.40 | 0.38 |

range: 0.19 to 0.40


## 6. Walk-forward: tune on 8 years, trade the next year blind, repeat

| strategy (out-of-sample) | start | cagr | volatility | sharpe | max_drawdown | param_changes |
|---|---|---|---|---|---|---|
| buy_hold | 2001-01-26 | 9.0% | 19.0% | 0.46 | -54.8% | 0 |
| trend | 2001-01-26 | 7.7% | 11.2% | 0.56 | -20.6% | 10 |
| rsi_reversion | 2001-01-26 | 3.9% | 5.7% | 0.39 | -16.3% | 8 |
| momentum | 2001-01-26 | 8.4% | 14.2% | 0.51 | -33.7% | 7 |
| vix_filter | 2001-01-26 | 5.6% | 13.7% | 0.34 | -43.3% | 8 |
| turn_of_month | 2001-01-26 | 3.9% | 9.3% | 0.26 | -28.4% | 9 |

## 7. Where do SPY's returns come from? Overnight vs intraday

| CAGR | overnight | intraday | close_to_close |
|---|---|---|---|
| 1994-2026 | 9.9% | 0.8% | 10.9% |
| 2017-2026 | 11.0% | 3.8% | 15.1% |

Almost all of SPY's gain has come overnight. But an overnight-only strategy (buy every close, sell every open) still trails buy & hold before costs, and it trades ~500 times a year: ~15%/yr of friction at 3bps per trade, ~5%/yr even at a very tight 1bp.

## 8. Multi-asset momentum rotation (SPY, QQQ, IWM, GLD, TLT; IEF as the safe asset)

| variant | start | cagr | volatility | sharpe | max_drawdown |
|---|---|---|---|---|---|
| 12m, top 1 | 2005-12-01 | 9.8% | 19.7% | 0.49 | -40.2% |
| 12m, top 2 | 2005-12-01 | 9.5% | 15.0% | 0.57 | -24.6% |
| 3/6/12m blend, top 1 | 2005-12-01 | 11.6% | 19.2% | 0.58 | -31.5% |
| 3/6/12m blend, top 2 | 2005-12-01 | 10.0% | 15.2% | 0.59 | -24.8% |
| 6m, top 2 | 2005-12-01 | 9.5% | 15.9% | 0.54 | -34.5% |
| SPY buy & hold | 2005-12-01 | 11.0% | 19.2% | 0.55 | -55.2% |
| 60/40 SPY/IEF (daily rebal.) | 2005-12-01 | 8.4% | 11.0% | 0.63 | -31.4% |
