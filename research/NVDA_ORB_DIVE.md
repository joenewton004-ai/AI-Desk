# The NVIDIA opening buy, taken apart

_October 2026. Code: `research/nvda_orb_dive.py`. Tables: [`output/nvda_orb_dive.md`](output/nvda_orb_dive.md).
Shadow log: `journal/nvda_orb.jsonl` (2026-08-04 to 2026-10-28). Research, not advice._

The question: why did the shadow trades lose (37 trades, -0.19% each, against the backtest's +0.15%), and can a
pattern raise the win rate?

## What happened on the shadow days

| result | trades | average | best run before the exit | worst dip |
|---|---|---|---|---|
| stopped at the range low | 13 | -1.01% | +0.55R | 1.12R |
| held to 3:55pm, won | 15 | +0.66% | +1.21R | 0.57R |
| held to 3:55pm, lost | 9 | -0.41% | +0.36R | 0.46R |

(R = the risk taken: entry minus stop.)

- **The losers were real failed breakouts, not stop hunts.**
  - 9 of the 13 stopped trades never got 0.4R in profit.
  - None closed the day back above its entry.
  - A wider stop or a later re-entry would not have saved them.
- **The winners were small.** Only 6 of the 24 trades held to 3:55pm got as far as +1R, and one got to +2R. Not a
  single shadow trade made +2%.
- **The stock was unusually quiet.**
  - Only 5% of the shadow days moved more than 3% from open to close, against 18% in 2016-2026.
  - The typical high-low range was 2.2% a day, against 3.1%.
- **It's bad luck, not a broken rule.** At ~1.7% swing per trade, a 37-trade average has about ±0.28% of noise.
  -0.19% is about 1.2 of those below the history, and 9% of all 37-trade stretches since 2016 were as bad.

## Why the rule makes money at all (ten years of NVDA)

- **The win rate is a coin flip:** 1,795 trades, 49% winners, +0.125% a trade after costs (t 3.2), in both halves.
- **The profit comes from rare big days.**
  - 12% of trades make +2% or more.
  - The best 10% of trades earn 2.8x the rule's whole profit; the other 90% lose money together.
- **Stops are rarely premature.** Only 8% of stopped trades had first been +1R up.

So **the win rate is not the lever**. The rule wins by staying in on the few days NVDA trends from the open. Anything
that cuts those days short raises the win rate and lowers the profit.

## Patterns tested (fixed in advance; must beat the live rule on NVDA AND 11 other stocks, in both halves)

| change | NVDA win rate | NVDA average | others' average | passes |
|---|---|---|---|---|
| live rule | 49% | +0.125% | -0.003% | - |
| take profit at +1R | **54%** | +0.073% | -0.010% | no |
| take profit at +1R, stop at the range middle | 53% | +0.003% | -0.051% | no |
| stop to break-even at +1R | 44% | +0.111% | -0.007% | no |
| out if it closes back inside the range | 18% | +0.083% | -0.015% | no |
| previous day down only | 50% | +0.172% | +0.013% | no (NVDA 2021-26 worse) |
| breakout by 10:00 only | 48% | +0.155% | -0.004% | no |
| QQQ already through its own range | 51% | +0.064% | +0.011% | no |
| gap-up days (already shadowed) | 50% | +0.155% | +0.014% | no (NVDA 2016-20 a hair worse) |
| only when the stock has been lively (20-day ranges above the year's) | 49% | +0.126% | -0.010% | no |
| no entries after 15:30 | 49% | +0.127% | -0.004% | no |

- **The only way to raise the win rate costs money.**
  - Taking profit at +1R lifts the win rate from 49% to 54% but cuts the average per trade by 40%.
  - Adding the middle stop (the trader-skill version) wipes the edge out.
- **"Previous day down" and "gap-up days" look good on NVDA but don't hold everywhere.**
  - Each beats the live rule in one half only.
  - On the other stocks they lift a rule that makes about zero to about zero.
  - The gap-up flag stays in the shadow log as before. Its earlier pass (`ORB_VARIANTS.md`) was marginal and misses by
    0.001% here.
- **Not tested as a rule: weekdays.** Mondays look best (53%, +0.24%), but with five weekdays to choose from, that's
  the kind of pattern noise produces.
- **The 3:55pm entry on 2026-10-21 is a real oddity, but harmless.**
  - The breakout came in the last bar, so it bought and sold in the same minute.
  - Blocking entries after 15:30 makes no measurable difference, so the shadow keeps matching its backtest.

## Verdict

- **No pattern raises the win rate without lowering the profit.**
- **The shadow's losses fit a quiet stock** and normal bad luck for a rule that lives on a few big days.
- **The bigger doubt remains.** The same rule makes about nothing on QQQ and the 10 largest companies of 2016.
  NVDA's +0.125% is most likely hindsight: picking the stock that went up 100x.
- **Keep it as a shadow.** Judge it after ~120 trades (about a year), not on win rate.
