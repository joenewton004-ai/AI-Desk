# The green line on QQQ and the "Magnificent 7"

_November 2026. Code: `research/green_line_tech.py`. Tables: [`output/green_line_tech.md`](output/green_line_tech.md).
Follows `GREEN_LINE.md` (SPY). Same rules: signal at each close, switch at the next open, 0.05% per switch, T-bills on
cash, prices with dividends to the 2026-11-09 close. Research, not advice._

**Hindsight warning:** the Mag 7 (Apple, Microsoft, NVIDIA, Amazon, Alphabet, Meta, Tesla) are the market's biggest
winners, named in 2023 *because* they won. Any test on them flatters buy and hold. It shows how a line behaves on
stocks that rose a lot with deep falls on the way, not what it would do on the next seven.

## Buy and hold vs the 200-day simple average

| | from | hold: return/yr | Sharpe | worst drop | line: return/yr | Sharpe | worst drop | line better in both halves? |
|---|---|---|---|---|---|---|---|---|
| SPY | 1996 | 10.4% | 0.49 | −55% | 8.2% | 0.51 | −25% | no |
| **QQQ** | 2000 | 7.8% | 0.34 | **−83%** | 7.3% | 0.40 | **−51%** | no |
| Apple | 1996 | 26.4% | 0.72 | −82% | 28.6% | 0.89 | −56% | yes |
| Microsoft | 1996 | 18.1% | 0.62 | −69% | 14.2% | 0.60 | −56% | no |
| NVIDIA | 2000 | 34.0% | 0.76 | −90% | 39.2% | 0.93 | −53% | yes |
| Amazon | 1998 | 26.2% | 0.66 | −94% | 17.1% | 0.55 | −86% | no |
| Alphabet | 2005 | 19.1% | 0.67 | −65% | 15.4% | 0.67 | −34% | no |
| Meta | 2013 | 27.9% | 0.78 | −77% | 23.5% | 0.81 | −41% | no |
| Tesla | 2011 | 41.2% | 0.86 | −74% | 17.6% | 0.55 | −69% | no |
| **Mag 7 equal weight** | 2013 | **35.9%** | 1.20 | −49% | 26.3% | 1.21 | **−30%** | no (1.66/0.89 vs 1.64/0.93) |

Other line lengths (50/200-day EMA, 2% band, 10-month) tell the same story; see the tables.

## What it means

- **QQQ: the line matters more than on SPY, because QQQ's falls are deeper.** Holding QQQ from March 2000 lost 83% at
  the worst and took about 15 years to recover. The 200-day line cut that to −51% (the 10-month line to −40%) for
  about the same return, and a slightly better Sharpe (0.40 vs 0.34). It still lost half, because 2000-2002 was a
  slow fall with rallies through the line.
- **Single stocks: mixed, which is what noise looks like.** It helped Apple and NVIDIA a lot, and badly hurt Tesla
  (17.6% vs 41.2% a year: Tesla crosses its line ~11 times a year and each whipsaw sells low and buys back higher).
  Amazon still fell 86% with the line. Only 2 of 7 improved in both halves.
- **Mag 7 basket: the classic trade-off.** The worst drop falls from −49% to −30%, the return from 35.9% to 26.3% a
  year, and the Sharpe is the same (1.21 vs 1.20).
- **Bottom line, same as SPY:** a moving-average line is crash insurance. It cuts the deepest falls (most on QQQ),
  costs return, and doesn't improve return per unit of risk in a way you can rely on.

## Verdict

Not proposed for the desk. If you'd hold QQQ or big tech for the long run, a 200-day or 10-month line is a reasonable
way to avoid an 80% fall, at a cost of some return - worth it only if a fall like 2000-2002 would make you sell at the
bottom. Recorded as research-only (`green_line_tech`).
