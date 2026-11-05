# One more indicator for when the overnight sleeve trades

_November 2026. Code: `research/overnight_timing.py`. Tables: [`output/overnight_timing.md`](output/overnight_timing.md).
Daily, 2014-04 to the 2026-10-30 open, the live rule with both live checks (SPY below its 200-day, picks down 2%+
since the open), **survivors-only prices**. Research, not advice._

## Why

Asked 2026-11-05: can one more indicator make the sleeve smarter about which nights to sit out? Signals tested before
(VIX level, tech vs defensive, per-stock skips, earnings nights, sector caps) were not repeated.

## The six candidates (fixed before running, nothing tuned)

| | Sit in cash when... | Idea |
|---|---|---|
| **T** | the VIX closes above the 3-month VIX (VIX3M) | fear is about *now*, not later |
| **C** | junk bonds lag Treasuries (HYG/IEF below its 50-day average) | credit stress comes first |
| **B** | under 40% of the big stocks are above their 50-day average | a weak market underneath |
| **O** | the sleeve's own last 20 nights add up to a loss | the strategy itself is in a slump |
| **V** | (sizing) money overnight = typical volatility / the last 20 nights' volatility, at most 100% | bet less when swings are big |
| **W** | it's a weekend or holiday night | more news risk over 3 days |

**To adopt:** a better Sharpe than live in both 2014-19 and 2020-26, and a smaller worst drop or worst month, at both
0.02% and 0.05% costs each way. Each signal was also run a day later; a real signal shouldn't collapse when it is.

## Results (at 0.02% costs each way)

| version | in cash / money used | return/yr | Sharpe | 2014-19 / 2020-26 | worst drop | worst month | Oct 2026 |
|---|---|---|---|---|---|---|---|
| **Live** | - | 25.3% | **1.49** | 1.43 / 1.63 | -15% | -11.8% | -11.8% |
| T VIX term structure | 2% of nights | 25.9% | 1.57 | 1.42 / 1.76 | -16% | -12.7% | -11.8% |
| C credit | 23% | 19.7% | 1.38 | 0.77 / 1.74 | -18% | -4.2% | -3.3% |
| B breadth | 8% | 22.8% | 1.44 | 1.29 / 1.62 | -14% | -10.4% | -10.4% |
| O own slump | 19% | 21.6% | 1.45 | 1.36 / 1.62 | -15% | -5.8% | -3.3% |
| V volatility target | 74% on average | 16.6% | 1.54 | 1.48 / 1.59 | -11% | -8.4% | -5.5% |
| W weekends | 16% | 19.4% | 1.31 | 1.06 / 1.53 | -16% | -13.5% | -11.7% |

At 0.05% costs everything is weaker (live Sharpe 0.71). V falls to 0.55, below live, and none of the others gets
through both halves.

## What it means

- **None passes.** Each one fails in at least one half or at the higher cost.
- **T (VIX above VIX3M) is the closest call, and the most interesting.** On the 68 nights it flags that the live
  checks didn't already skip, the sleeve averaged -5.8 bp vs +12.8 bp otherwise. But it is out only 2% of the time,
  it is no better in 2014-19 (1.42 vs 1.43), and a day later it adds nothing. It didn't flag October 2026.
- **V (volatility target) cuts the worst drop to -11%** but it is mostly "less money overnight" (74% on average). A
  fixed 60-74% share gives the same Sharpe (1.49, `OVERNIGHT_SAFETY2.md`). Its small extra gain is within noise, is
  worse in 2020-26, and turns into a loss of Sharpe at 0.05% costs.
- **C (credit) and O (own slump) would have saved October 2026** (-3.3% instead of -11.8%) and halve the worst
  month. But they cost 4-6 points of return a year and their Sharpe is lower. C is very poor in 2014-19 (0.77).
  They protect against slumps by sitting out many ordinary good nights too.
- **Weekends earn as much as other nights** (+13.3 bp vs +12.0 bp), so skipping them only loses.
- **The pattern from earlier tests holds:** the two live checks already catch the timing that can be caught. Bad
  nights that arrive in calm markets (e.g. 2026-10-30) aren't signalled by any of these.

## Catches

- Six candidates plus six lagged versions: one near-pass could easily be luck.
- The signals use the day's close. Live, the buy is at 3:55pm, a few minutes earlier, which flatters them slightly.
- Survivors-only prices, as in all the stock-level research.

## Verdict

**Don't add any of these.** If anything is followed up, it is T (VIX above VIX3M) as a shadow line, to see whether it
keeps flagging bad nights live. It would need far more flagged nights than it gets (about 5 a year) before it could
be judged. The levers that work are still the two live checks and the size of the overnight share.

Nothing in the live rules has changed.
