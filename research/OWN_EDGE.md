# Our own edge: a search across ~35 indicators, judged on years the search never saw

_October 2026. Code: `research/own_edge.py` (search + one holdout test) and `research/own_edge_checks.py`
(diagnostics on the one survivor). Tables: [`output/own_edge.md`](output/own_edge.md),
[`output/own_edge_checks.md`](output/own_edge_checks.md). Research, not advice._

## What the owner asked

"Analyse the patterns yourself rather than using known patterns. Any indicators, any combination, any stock, ETF,
index or commodity."

## How (and why this way)

Search a few thousand indicator combinations on the same data and some will look brilliant by luck alone. That's how
most "custom edges" are found, and why they fail with real money. So the search was split:

1. **Two universes, held to a 5-day horizon** (bought at the next open, out at the open 5 trading days later):
   - **Stocks:** the 500 largest US companies at each date (SEC market values, 45-day lag), 2014-2026. Judged
     against the average of the 500 that week. **Prices are survivors-only.**
   - **25 ETFs:** indexes, 9 sectors, Treasuries, high yield, gold, silver, oil, gas, broad commodities, REITs, the
     dollar, foreign markets. Judged against holding each ETF. Back to 1999.
2. **~35 indicators** at each close, from data up to that close only:
   - returns over 1 day to 12 months, RSI(2)/(14)
   - distance from the 5/20/50/200-day averages, volatility and its change, ATR
   - volume surges, where the close sits in the day's range, today's range vs normal
   - distance from the 52-week high and low, the opening gap, overnight vs daytime returns, strength vs SPY
   - the market's state: SPY vs its 200-day, SPY's week, the VIX and its change; weekday, month end
3. **Search on development years only** (stocks 2014-2019, ETFs 1999-2012):
   - each indicator in 10 buckets (317 tests);
   - every pair in 3 x 3 buckets (4,401 stock / 4,501 ETF tests);
   - a machine-learning model (LightGBM, gradient-boosted trees) on all of them at once.
4. **Holdout, run once** (stocks 2020-2026, ETFs 2013-2026) on a fixed shortlist: the 5 best singles, the 10 best
   pairs and the model. Each was run as a weekly portfolio after costs (0.05% each way for stocks, 0.02% for ETFs).

## Results

**The luck trap, seen directly.** Every one of the 5 best single indicators collapsed in the holdout. On stocks they
went from +0.06-0.09% a week (t 2.2-2.6) to between -0.07% and -0.02%; on ETFs, the same. Most pair winners did too.
This is what a large search produces, and why the holdout matters.

**ETFs: nothing survives.**
- The model went from +0.31% a week in the search years to 0.00% in the holdout.
- The one lean, "buy everything after SPY has had a bad week" (+0.47% a week, t 1.6), is the SPY dip effect already
  found in `SWING_ETF.md`.

**Stocks: one idea survives as a family, and the model finds the same thing.**

| what held up in 2020-2026 | holdout excess a week | t | as a weekly portfolio | universe |
|---|---|---|---|---|
| fell over 10 days + strong over 120 days | +0.18% | 1.6 | 17.2%/yr, Sharpe 0.77, worst -40% | 12.1%, 0.69, -34% |
| fell over 10 days + above the 200-day | +0.17% | 1.3 | 15.9%, 0.70, -40% | |
| strong over 120 days + below the 20-day | +0.16% | 1.4 | 16.6%, 0.74, -38% | |
| fell over 10 days + strong over 60 days | +0.12% | 1.0 | 12.7%, 0.59, -40% | |
| **the model (top 20 a week)** | **+0.41%** | **2.4** | **27.5%, 0.86, -52%** | |

**What the model is, once taken apart** (`own_edge_checks.md`):
- **What it buys:** high-volatility stocks (around the 75th percentile) that have pulled back over a week or a month
  (around the 30th) while still in a longer uptrend (the 60th percentile over 12 months, above their 200-day). That's
  the "pullback in a winner" family, plus volatility.
- **It earns mostly after the market has fallen:** +1.03% a week when SPY was below its 200-day, +0.25% when above.
- **A third of it is just extra market exposure.**
  - The picks move about 1.5x the average stock, so they beat the average in rising weeks (+1.18%) and lag in
    falling ones (-0.63%).
  - With 2020-2026 rising, that alone gives +0.14% of the +0.40% a week.
  - What's left is about +0.26% a week, t 1.7: not significant.
- **Realistic retraining shrinks it further.** Retrained each January on all earlier years, the way it would really
  run: +0.32% a week (t 1.5), or +0.21% after costs. 2022 lost 0.89% a week.
- **Its stock-specific part is small.** Without the market-state indicators it earns +0.24% a week (t 1.3).
- **It trades a lot.** About 130% of the book changes each week; at 0.20% costs each way only +0.14% a week remains.
- **Survivors-only prices don't drive it more than usual.** Stocks 40%+ below their highs give 22% of its gain, in
  line with their share of picks. But all the stock results carry the survivors' flattery.

## Verdict

**No new edge.** The search, the pairs and the model all point back to one idea the desk already trades: **a short
pullback in a stock that is in a longer uptrend**. The live RSI-dip rule on the top-100 stocks is the cleaner version
(`CANDLE_RSI.md`: +1.0-1.2% a dip, both periods).

The model adds market timing (buy volatile names after selloffs) and extra market exposure. Neither is reliable once
measured properly (alpha t 1.7; walk-forward t 1.5).

Nothing is proposed for the desk. The useful by-products:
- a reusable search pipeline that separates discovery from testing;
- direct evidence that single-indicator "edges" found by searching don't survive.

## Limits

- **Survivors-only stock prices.** Companies that failed or were taken over are missing, which flatters
  dip-buying. Delisted-inclusive data isn't available here.
- **One horizon (5 days) and one model setting.** Trying more horizons or tunings on the holdout would re-open the
  luck trap, so they weren't.
- **Futures and single commodities beyond the ETFs weren't searched.**
