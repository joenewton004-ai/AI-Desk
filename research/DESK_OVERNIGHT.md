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

## How it runs (as built, one account)

You chose to run it inside the desk's own paper account: 50% quality screen, 20% momentum, 30% overnight.
- **3:32pm New York:** market-on-close buys of the 20 picks with 30% of equity. That 30% is cash during the day,
  because the shares were sold at the open.
- **4:30pm:** the desk's evening run sells those shares at the next open, inside the desk's own order for each
  stock. A stock held by both, e.g. MU in momentum and overnight, gets one net order, because Alpaca rejects
  opposite orders in one stock as possible wash trades.
- **The sale is a market order at the open**, not a market-on-open auction order. The open is what the research
  assumed, but `overnight review` measures the real fills against the official open and close.

## Verdict

**Better on paper only if trading costs come in at about 0.02% or less, with a deeper worst drop.**
Accepted by you on 2026-10-21 (amendment 330e76e0) and active from that day.
Watch `overnight review`: if fills average worse than about 0.02-0.03% per trade, the swap is losing
the desk money, and it's time for an amendment to reverse it.
