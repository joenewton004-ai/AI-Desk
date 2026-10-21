# Momentum sleeve: the entry filter (picked only if above the 100-day AND 200-day average)

_October 2026. Code: `research/momentum_entry.py`. Tables: [`output/momentum_entry.md`](output/momentum_entry.md).
Monthly 2014-2026, survivors-only prices, 0.10% per trade. Research, not advice._

## The gap

The sleeve picked stocks above their **200-day** average, but sells any holding below its **100-day** average,
checked every evening, the pick day included. A stock that had a strong six months but dipped in the last few
weeks was picked and sold in the same run. That would have been 5 of the 20 on 2026-10-21 (ALAB, DELL, MRVL, MU,
PANW), and that slice would sit in cash until the next re-pick. The original backtest checked the sell rule
weekly, after the pick week, so it never saw this.

## Results

| Rule | Return/yr | Sharpe | Worst drop | Average invested |
|---|---|---|---|---|
| As backtested (sell rule from the week after the pick) | 19.7% | 0.76 | −30% | 89% |
| As the live code worked (sold on the pick day) | 17.9% | 0.71 | −33% | 86% |
| **Entry filter: above both averages to be picked** | **19.4%** | **0.75** | −31% | **92%** |

- **The live behaviour was about 1.8% a year worse than the backtest.** On average 1.4 of 20 picks went straight
  to cash, at more than half of the re-picks.
- **The entry filter recovers that:** about the same as the backtested rule, beating the live behaviour in 8 of
  13 years, and more of the sleeve stays invested.

## Decision

Accepted by the owner on 2026-10-21, from that evening's first momentum pick. `momentum_scan.rank` now has an
`above_100` column, and `passes` requires both averages. The next-ranked stocks fill the slots.
