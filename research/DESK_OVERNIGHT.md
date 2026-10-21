# The desk with the overnight sleeve instead of SPY momentum

_October 2026. Code: `research/desk_overnight.py`. Tables: [`output/desk_overnight.md`](output/desk_overnight.md).
Monthly, 2014-2026, **survivors-only prices**. Research, not advice._

The question: replace the desk's 30% SPY momentum sleeve (SPY when its 12-month return is positive,
else T-bills) with the overnight sleeve (research/OVERNIGHT.md), keeping 50% quality screen + 20%
momentum.

## The whole desk

| Desk | Return/yr | Sharpe | Worst drop | 2014-19 Sharpe | 2020-26 Sharpe |
|---|---|---|---|---|---|
| **Current (30% SPY momentum)** | **16.5%** | **0.91** | −24.2% | 1.02 | 0.86 |
| 30% overnight, zero cost | 22.2% | 1.15 | −25.0% | 1.42 | 1.08 |
| **30% overnight, 0.02% each way** | **18.6%** | **0.98** | −26.8% | 1.16 | 0.93 |
| 30% overnight, 0.03% | 16.8% | 0.89 | −27.8% | 1.04 | 0.86 |
| 30% overnight, 0.05% | 13.4% | 0.71 | −29.8% | 0.78 | 0.71 |
| 15% SPY momentum + 15% overnight (0.02%) | 17.5% | 0.95 | −25.4% | 1.10 | 0.91 |

- **At 0.02% per trade or less,** the swap adds about 2% a year and lifts the Sharpe from 0.91 to 0.98.
  It did better in 8 of 13 years.
- **The desk-level break-even is about 0.03% per trade.** Above that, the current desk is better.
  We don't know the real cost yet: Alpaca's paper fills are simulated.
- **It deepens the worst drop** from −24% to −27%. The SPY sleeve's 12-month switch sits in T-bills
  during long falls; the overnight sleeve is always invested.
  - In March 2020 it lost 20% against SPY's 12.5%.
  - In 2022 it cost the desk 2.7%.
- **It doesn't concentrate the desk further.** The overnight sleeve's monthly correlation with the
  other two (0.55-0.57) is lower than SPY momentum's (0.59-0.77). It's a different source of
  return, not more of the same.
- **The current list is narrow** (mostly AI hardware: LITE, BE, SNDK, MU, MRVL...), and some of those
  names overlap with the momentum sleeve today.

## What it would take to run

The overnight sleeve trades twice a day in auctions; the desk trades at the evening run. In one
account they'd fight over the same positions. The clean way:
- the desk's paper account holds the quality screen and momentum, scaled from 50/20 to 71/29;
- the overnight paper account (keys still to be added) holds the 30%, sized to 30/70 of the desk
  account's equity;
- the scorecard adds the two accounts together.

## Verdict

**Better on paper only if trading costs come in at about 0.02% or less, with a deeper worst drop.**
Logged as an amendment for your decision. A cautious path is to run the overnight sleeve in its
own paper account first, measure its fill costs for a few weeks, then make the swap if they come
in under about 0.02%.
