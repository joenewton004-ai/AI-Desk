# The desk with momentum top 10 instead of top 20

_October 2026. Code: `research/desk_top10.py`. Tables: [`output/desk_top10.md`](output/desk_top10.md). Monthly,
June 2014 - September 2026, **survivors-only prices**. Research, not advice._

The question: keep the desk at 50% quality screen + 20% momentum + 30% overnight, but hold the momentum
sleeve's **top 10** (2% of the desk each) instead of its top 20 (1% each). The live rules stay the same: above
the 200 and 100-day averages to be picked, re-picked every 4 weeks, sold below the 100-day average in between.

## The momentum sleeve on its own

| | Return/yr | Sharpe | Worst drop | At 3× costs |
|---|---|---|---|---|
| Top 20, live rules (now) | 19.4% | 0.75 | −31% | 15.4% |
| **Top 10, live rules** | **29.2%** | **0.92** | **−30%** | **24.7%** |
| Top 15, live rules | 22.6% | 0.80 | −32% | 18.3% |
| Top 10, plain (no filter, no 100-day exit) | 32.7% | 0.94 | −47% | 29.1% |

## The whole desk (overnight at 0.02% per trade)

| Momentum sleeve | Return/yr | Sharpe | Worst drop | 2014-19 | 2020-26 |
|---|---|---|---|---|---|
| Top 20, live rules (now) | 18.5% | 0.98 | −25.9% | 1.16 | 0.94 |
| **Top 10, live rules** | **20.7%** | **1.06** | **−25.6%** | **1.22** | **1.03** |
| Top 15, live rules | 19.2% | 1.00 | −26.1% | 1.19 | 0.95 |
| Top 10, plain | 21.4% | 1.05 | −26.3% | 1.19 | 1.04 |
| SPY | 13.7% | 0.82 | −24% | | |

At 0.03% overnight costs every desk drops by about 0.09 Sharpe, and the order stays the same (top 10: 0.97 vs 0.89).

## What it means

- **Top 10 is better, consistently.**
  - About +2% a year for the desk, with Sharpe 1.06 against 0.98.
  - Better in both halves of the test, and in 11 of 13 years.
  - It holds at triple momentum costs (Sharpe 1.02).
  - The worst drop doesn't get deeper (−25.6% vs −25.9%), because the 100-day exit still protects it.
- **It's more than noise, but not by much.** The return gap has a t of 3.0. The Sharpe gap is +0.08, and the
  bootstrap's 90% range is +0.02 to +0.12: positive, but small.
- **Keep the live rules.** Plain top 10 has a similar desk Sharpe (1.05), but on its own it falls 47% at worst
  against 30% with the rules.
- **Fewer stocks gives more diversification at the desk level.** Top 10's monthly correlation with the quality
  screen is lower (0.48 vs 0.57), so it adds more of what quality doesn't have.

## The catches

1. **Survivors-only prices flatter concentration most.** The biggest winners are in the data; momentum stocks
   that later collapsed or were delisted are under-represented. Ten names lean harder on those winners than twenty.
2. **We chose "10" after seeing it win.** That number came from `research/MOMENTUM_SLEEVE.md`, which tested 10 and
   20, so this isn't a fresh out-of-sample test. Top 15 sits in between (Sharpe 1.00), which is reassuring: the
   effect is smooth, not a lucky single setting.
3. **More single-stock risk.** One bad momentum stock is 2% of the desk instead of 1%. The sleeve swings more on
   its own: 31% volatility against 25%.

## Verdict

**A real but modest improvement in this backtest**, consistent across halves, years and costs. It is not yet live.
Under the desk's rules it needs an amendment (proposed → testing → your decision) before the live sleeve changes
from 20 to 10.
