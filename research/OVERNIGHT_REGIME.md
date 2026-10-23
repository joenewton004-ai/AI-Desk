# The overnight sleeve and the fear index: when to switch, and to what

_October 2026. Code: `research/overnight_regime.py`. Tables: [`output/overnight_regime.md`](output/overnight_regime.md).
3,158 nights, April 2014 - October 2026; the 750 largest US companies, **survivors-only prices**; 0.02% per trade each
way; nights in cash earn T-bills. Research, not advice._

The question (prompted by 2026-10-22, when big tech fell and defensive stocks rose): should the overnight sleeve
switch what it holds when markets are fearful, for example into defensive stocks, using the VIX or a tech sell-off as
the signal? Every signal uses only what was known at the 3:55pm buy.

## 1. Defensive stocks don't earn overnight

| Average night, after costs | All nights | VIX above 25 | After tech lagged defensives most |
|---|---|---|---|
| **The sleeve (top 20 overnight earners)** | **+6.6 bp** | +7.0 bp | −12.7 bp |
| Low-beta top 20 | +1.2 bp | +3.1 bp | −8.3 bp |
| Defensive-industry top 20 | +1.8 bp | +4.7 bp | −7.7 bp |
| Average stock | +4.0 bp | +8.1 bp | −7.4 bp |

- **Switching to defensive stocks never pays.** On the nights the sleeve does badly, defensive stocks do badly
  too. They just earn less the rest of the time. Every "switch to the low-beta or defensive list" rule did worse
  than switching to **cash**, and most did no better than doing nothing.
- **A high VIX alone isn't a warning.** The sleeve earned *more* on average when the VIX was 20-30, because fear
  brings bigger overnight moves both ways. Cash above VIX 25 cuts the worst drop (−36% to −25%), but the Sharpe
  barely moves (0.70 to 0.77).

## 2. Two signals that do line up with bad nights

| Rule (in cash those nights) | Nights out | Return/yr | Sharpe | Worst drop | 2014-19 | 2020-26 |
|---|---|---|---|---|---|---|
| Always invested (now) | 0% | 15.5% | 0.70 | −36% | 0.72 | 0.75 |
| **SPY below its 200-day average** | 16% | 18.3% | 0.95 | −19% | 1.03 | 1.01 |
| **After tech lagged defensives most** (that day in the worst 10%) | 13% | 20.1% | 0.97 | −28% | 0.90 | 1.07 |
| **Either of the two** | 25% | 18.0% | **1.03** | **−16%** | 1.00 | 1.13 |
| SPY rule, a day later | 16% | 16.6% | 0.87 | −23% | 0.83 | 0.95 |
| Tech rule, a day later | 13% | 14.9% | 0.74 | −31% | 0.69 | 0.82 |

**SPY below its 200-day average.** In falling markets the sleeve loses overnight: −3.1 bp a night in 2014-19 and
−3.4 bp in 2020-26, against +8.5 bp otherwise. That covers 16 separate spells.
- It holds in both halves and still helps when lagged a day.
- On its own the gap is modest statistically (t −1.4); its main effect is a smaller worst drop (−19% vs −36%).
- The desk's old SPY momentum sleeve used the same kind of trend rule.

**A day when tech lagged defensives the most** (tech stocks' return minus defensive stocks', in the worst 10% of
days, threshold set from past days only). The next night averages −9.6 bp against +9.0 bp otherwise (t −2.2):
−5.7 bp in 2014-19 and −11.4 bp in 2020-26. Today, 2026-10-22, looks like one of these days.
- **It only works on the same day.** Lagged by a day, it adds nothing. Live, the desk would judge it at 3:55pm from
  prices up to then, a few minutes earlier than the close the backtest used. That's a small, real difference to watch.
- It's a known pattern: the overnight winners' gains tend to reverse the next morning after a hard selling day.

## The catches

1. **About 20 rules were tested.** With that many, a t of about 2 can happen by chance. Both signals hold in both
   halves, which helps, but neither is strong evidence alone.
2. **Survivors-only prices**, as in all the stock-level research here.
3. **Part of the gain is simply trading less.** A night in cash saves the 0.04% round trip. That's real, and the
   amendment's evidence would have to state it.
4. **The worst nights still happen.** Several of the sleeve's 15 worst nights (e.g. 2025-01-27, 2026-06-23,
   2026-09-14) came with a calm VIX and SPY above its 200-day. No signal here warns of those.

## Verdict

**Don't switch to defensive stocks; consider switching to cash.** The combined rule (cash when SPY is below its
200-day average, or on a day tech lags defensives the most) lifted the sleeve's Sharpe from 0.70 to 1.03 and cut
its worst drop from −36% to −16%, in both halves. The evidence is moderate, with a multiple-testing caveat.

**Live from 2026-10-23** (amendment 7a8b29ec, accepted by you). The checks run at the 3:55pm buy
(`python -m ai_desk overnight regime` shows tonight's verdict). The tech cut-off comes from the past 5 years of daily
closes, refreshed each evening: −1.32% on 2026-10-22, a day when tech lagged by 3.07%.
