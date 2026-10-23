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

## Follow-up: a check on the sleeve's own picks instead of industries

_Code: `research/overnight_picks_check.py`. Tables: [`output/overnight_picks_check.md`](output/overnight_picks_check.md)._

Your point: industries change, and so does what the sleeve holds. Rather than "tech vs defensive", look at the 20
stocks the sleeve is about to buy. All of these go to cash on the flagged nights, with the cut-off set from earlier
days only:

| Check (that day's worst 10%) | Alone: Sharpe | Worst drop | With the SPY rule: Sharpe | Worst drop | 2014-19 | 2020-26 | Flagged nights: 2014-19 / 2020-26 |
|---|---|---|---|---|---|---|---|
| None | 0.70 | −36% | 0.95 | −19% | 1.03 | 1.01 | |
| A. Tech minus defensive (**live now**) | 0.96 | −29% | 1.03 | −16% | 1.00 | 1.13 | −5.7 / −10.6 bp |
| B. Picks minus the average stock | 0.81 | −34% | 1.06 | −18% | 1.03 | 1.15 | −12.6 / **+7.3** bp |
| C. Picks' own return that day | 1.02 | −26% | 1.12 | −18% | 1.15 | 1.18 | −7.4 / −11.8 bp |
| **D. Picks' return since that day's open** | **1.03** | −34% | **1.31** | **−17%** | **1.20** | **1.45** | **−12.7 / −13.9 bp** |

- **Yes: checking the picks works better than checking industries, if it's the picks' own move.** D, the picks
  falling hard during the day, flags nights that average −13.6 bp against +9.2 bp otherwise (t −2.3), about the same
  in both halves. It fits the original research: overnight winners tend to give back during the day, and a big
  give-back is followed by a bad night.
- **The picks lagging the market (B) isn't the signal.** It fails in 2020-26, where its flagged nights did *better*
  than average. What matters is the picks falling, not falling more than everything else.
- **D only overlaps half the time with the live tech check** (49%), so they're different warnings.
- **Easier to run live:** it needs only the 20 picks' open and 3:55pm prices, and no industry lists to keep current.
  Its cut-off has been stable, about −1.5% to −1.9% through the years (−1.9% using all history to 2026, −2.3% using the
  last 3 years), so live it can use a fixed −1.9%, reviewed when the research is re-run.
- **The catches:** this is the sixth variant tested on top of about 20, so the multiple-testing risk keeps growing.
  D was the variant that fits the earlier research's mechanism, and it holds in both halves; that's the best defence.
  Live judges it at 3:55pm, not at the close the backtest used. Survivors-only prices, as before.

**Live from 2026-10-23** (amendment 9b951502, accepted by you): D replaced the tech-vs-defensive check; the SPY 200-day
rule stays. Cut-off fixed at −1.9% (`overnight.PICKS_DAY_CUTOFF`).

## Follow-up: skip single fallen picks instead of the whole night?

_Code: `research/overnight_perstock.py`. Tables: [`output/overnight_perstock.md`](output/overnight_perstock.md).
On the live v2 picks (12-month return, ranked the evening before); every rule keeps the SPY 200-day rule._

| Rule | Sharpe | Worst drop | 2014-19 | 2020-26 |
|---|---|---|---|---|
| SPY rule only | 1.17 | −17% | 1.34 | 1.22 |
| **Group rule (live): all 20 out when their average is −2%+** | **1.54** | −15% | 1.43 | 1.71 |
| Per-stock: skip picks down 2%+ (their share in cash) | 1.43 | −15% | 1.54 | 1.49 |
| Per-stock: skip picks down 3%+ (in cash) | 1.42 | −15% | 1.53 | 1.48 |
| Per-stock: skip picks down 5%+ (in cash) | 1.25 | −15% | 1.40 | 1.29 |
| Per-stock, money spread over the other picks (2-8%) | 1.01-1.13 | −17% to −18% | | |
| Group rule + skip single picks down 3%+ | 1.64 | −13% | 1.58 | 1.79 |

What a single fallen pick did that night, against the other picks on the same nights (before costs):

| Down since the open | Stock-nights | That pick | The other picks | t |
|---|---|---|---|---|
| 2%+ | 11,323 | +5.0 bp | +14.1 bp | −3.7 |
| 3%+ | 6,761 | +2.6 bp | +12.0 bp | −2.7 |
| 5%+ | 2,518 | +6.9 bp | +6.3 bp | 0.1 |
| 8%+ | 620 | +24.4 bp | −2.1 bp | 1.7 |

- **The group rule beats per-stock skipping.** The warning is the picks falling *together*; one stock's bad day says
  much less about the night.
- **Spreading the skipped money over the other picks is clearly worse**: it concentrates the sleeve on fewer names.
- **A pick down 2-3% does earn less that night** (t −3.7), but still about break-even after costs, so skipping it
  mostly just holds cash. **Big single falls (5%+) tend to bounce overnight**, so skipping them costs money.
- **Both together scored best** (1.64, worst drop −13%, both halves). The gain over the live rule (+0.10) is well
  inside the noise, and it's yet another variant on top of many tested, so on its own it isn't a reason to change.
