# Our own edge with shorting - generated tables

Short book excess = how much its names did vs the universe (negative = good for a short). Long/short = each leg 100% of equity, after costs and borrow (0.5%/yr; stress 2%/yr); T-bills on the cash on top. Alpha = what's left after removing what the book earns from the market moving. **Stock prices are survivors-only: the short side is shown worse than it was, the long side better.**

## Stocks: 2014-2019 search, 2020-2026 holdout

Searched 317 single buckets and 4401 pair cells for names that lag.

### Short books (names lagging the universe; negative = a good short)

| short candidate | search years: excess a week | t | holdout: excess a week | t | weeks it worked | names |
|---|---|---|---|---|---|---|
| single: vs_sma20 bucket 10/10 | -0.16% | -2.7 | -0.11% | -0.8 | 52% | 20 |
| single: gap bucket 2/10 | -0.10% | -2.5 | -0.00% | -0.0 | 46% | 20 |
| single: volume_5_60 bucket 6/10 | -0.06% | -2.5 | -0.17% | -2.5 | 57% | 20 |
| single: vol_ratio_5_60 bucket 3/10 | -0.08% | -2.4 | -0.08% | -1.0 | 52% | 20 |
| single: volume_5_60 bucket 4/10 | -0.06% | -2.2 | -0.06% | -0.8 | 52% | 20 |
| pair: gap low + intraday_20d high | -0.18% | -4.1 | -0.04% | -0.4 | 49% | 20 |
| pair: vs_sma20 high + gap low | -0.18% | -3.8 | -0.07% | -0.6 | 52% | 20 |
| pair: vol_ratio_5_60 low + gap low | -0.15% | -3.6 | +0.02% | 0.2 | 51% | 20 |
| pair: ret_10d high + gap low | -0.16% | -3.6 | -0.04% | -0.3 | 50% | 20 |
| pair: volume_5_60 mid + overnight_20d high | -0.12% | -3.5 | -0.04% | -0.4 | 55% | 20 |
| pair: ret_20d high + gap low | -0.17% | -3.5 | -0.07% | -0.6 | 52% | 20 |
| pair: gap low + vs_spy_20d high | -0.17% | -3.5 | -0.07% | -0.6 | 52% | 20 |
| pair: rsi_14 high + gap low | -0.16% | -3.4 | -0.12% | -1.2 | 54% | 20 |
| pair: vs_sma5 high + gap low | -0.15% | -3.3 | -0.00% | -0.0 | 49% | 19 |
| pair: range_vs_20d mid + spy_vs_sma200 high | -0.07% | -3.2 | -0.27% | -2.1 | 54% | 20 |
| model's bottom 20 | - | - | -0.11% | -0.8 | 52% | 20 |

### Long/short books (holdout 2020-2026)

| book | return/yr (incl. T-bills) | Sharpe above T-bills | worst drop | market exposure (beta) | alpha a week | alpha t | at 2% borrow: return/yr |
|---|---|---|---|---|---|---|---|
| model: long top 20 / short bottom 20 | +17.7% | 0.59 | -30% | +0.46 | +0.24% | 1.1 | +15.9% |
| pullback long / short 'single: volume_5_60 bucket 6/10' | +14.8% | 0.60 | -27% | +0.21 | +0.21% | 1.3 | +13.1% |
| model long top 20 only (for comparison, vs the universe) | +18.9% | 0.75 | -26% | +0.53 | +0.20% | 1.3 | +18.9% |

### The model long/short, walk-forward (retrained each January on every earlier year)

| year | long/short a week | t |
|---|---|---|
| 2020 | +0.21% | 0.3 |
| 2021 | +0.33% | 0.6 |
| 2022 | -0.18% | -0.4 |
| 2023 | -0.11% | -0.3 |
| 2024 | +0.00% | nan |
| 2025 | +0.60% | 1.1 |
| 2026 | +1.84% | 1.5 |

Walk-forward 2020-2026: +0.33% a week (t 1.4); +16.2% a year incl. T-bills, Sharpe 0.55, worst -33%, beta +0.34, alpha +0.24% a week (t 1.1).

## ETFs: cross-asset long top 3 / short bottom 3 (model trained 1999-2012, holdout 2013-2026)

- Long leg vs the ETFs' average: -0.02% a week (t -0.2); short leg -0.30% (t -1.5; negative = good).
- Long/short: +0.18% a week (t 1.0); +5.5% a year incl. T-bills, Sharpe 0.27, worst -70%, beta +0.13, alpha +0.16% (t 0.9).
