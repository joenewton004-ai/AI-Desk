# Our own edge with shorting

_October 2026. Code: `research/short_edge.py` (reuses `own_edge.py`'s data, ~35 indicators, protocol and model).
Tables: [`output/short_edge.md`](output/short_edge.md). Research, not advice._

## The question

Can shorting give the desk an edge of its own? Two ways it could:
- **Short books:** find the stocks that lag.
- **Long/short books:** pair the desk's best longs with shorts. That could cancel the market exposure that inflated
  the long-only model in `OWN_EDGE.md`, where a third of its return was beta.

## Set-up (fixed before running)

- **Same search as `OWN_EDGE.md`:** top-500 stocks 2014-2019 and 25 ETFs 1999-2012, 5-day horizon, ~35 indicators,
  3 x 3 pairs, LightGBM. This time it looked for what lags.
- **Holdout, once:** stocks 2020-2026, ETFs 2013-2026. On the shortlist:
  - the 5 worst singles and 10 worst pairs as short books (20 names each);
  - the model's top 20 long / bottom 20 short;
  - the pullback long ("fell over 10 days + strong over 120 days") against the best short book;
  - the model long/short retrained each January (walk-forward);
  - ETFs: long the model's top 3 / short its bottom 3.
- **Costs:** 0.05% each way per leg (ETFs 0.02%), borrow 0.5% a year (stress 2%). Cash and short collateral earn
  T-bills.
- **Judged on:** return, Sharpe, worst drop, and **alpha**: what's left after removing what a book earns from the
  market moving.
- **Survivors-only prices.** Failed and delisted companies are missing, and they are the best shorts of all. So the
  short side here is shown **worse** than reality, the long side better.

## Results

**Short books: the search's best shorts fade, like its best longs did.**

| short book (20 names) | search years: vs the 500, a week | t | holdout | t |
|---|---|---|---|---|
| gapped down + strong last 20 days' daytime moves | -0.18% | -4.1 | -0.04% | -0.4 |
| above the 20-day + gapped down | -0.18% | -3.8 | -0.07% | -0.6 |
| strong 10 days + gapped down | -0.16% | -3.6 | -0.04% | -0.3 |
| in the top 10% above the 20-day average | -0.16% | -2.7 | -0.11% | -0.8 |
| volume ratio in its middle (6th) decile | -0.06% | -2.5 | -0.17% | -2.5 |
| the model's bottom 20 | - | - | -0.11% | -0.8 |

- **The strongest pattern in the search fades to about zero.** It was "a stock that ran up then gapped down at the
  open" (t -3.3 to -4.1 over many variants).
- **The two cells that held are nonsense.** A middling volume reading, and "a normal-range day while SPY is above its
  200-day". These are what a 1-in-20 lucky pass looks like among ~4,700 searched cells.

**Long/short books (holdout 2020-2026):**

| book | return/yr | Sharpe | worst drop | market exposure (beta) | alpha a week | alpha t |
|---|---|---|---|---|---|---|
| model: long top 20 / short bottom 20 | 17.7% | 0.59 | -30% | 0.46 | +0.24% | 1.1 |
| same, walk-forward (retrained yearly) | 16.2% | 0.55 | -33% | 0.34 | +0.24% | 1.1 |
| pullback long / short the volume cell | 14.8% | 0.60 | -27% | 0.21 | +0.21% | 1.3 |
| model long only (for comparison) | 18.9% | 0.75 | -26% | 0.53 | +0.20% | 1.3 |
| ETFs: long top 3 / short bottom 3 | 5.5% | 0.27 | **-70%** | 0.13 | +0.16% | 0.9 |

- **Adding shorts lowers the Sharpe** (0.75 → 0.59). The short leg costs more than it earns.
- **It doesn't remove the market exposure.** The model's longs are volatile stocks and its shorts are quiet ones, so
  even a dollar-neutral book still moves 0.3-0.5x with the market. True beta-neutral sizing would need even bigger
  shorts on the quiet names.
- **The walk-forward version lost money in 2022 and 2023.** In 2024 it made no trades: its scores came out tied, which
  I haven't dug into.
- **ETF long/short is the worst:** Sharpe 0.27, worst drop -70%. The long side lost to the average ETF, and a crisis
  (2020's oil crash) hits a 3-ETF book hard.
- **Borrow at 2% instead of 0.5%** costs another ~2% a year.

## Verdict

**Shorting doesn't create an edge here.**
- The stock-picking signal in this data is small and mostly on the long side: pullbacks in long-term winners.
- Shorts add costs, a borrow fee and the risk of sharp squeezes, without adding alpha. No book's alpha is significant
  (t 0.9-1.3).
- With the earlier SPY tests (`SPY_SHORT.md`), shorting is now ruled out at index, ETF and stock level.

The desk stays long only. The survivorship caveat is real: complete data, including the companies that failed, might
show a better short side. That data isn't available here.
