# The day-trader-skill's daily setups, tested

_October 2026. Source: [Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) ("Trader
skill v2", MIT; code read 2026-10-27, last commit 2026-10-20). Code: `research/daily_setups.py`. Tables:
[`output/daily_setups.md`](output/daily_setups.md). Research, not advice._

**What was tested:**
- **The rules:** the pack's five pre-market scan tags, defined exactly as in its `trader-scanner/scan.py`.
- **The stocks:** the 100 largest US companies at each date, 2014-2026, survivors-only prices.
- **The holds:** the next day open-to-close (the pack's day trades) and 5 days.
- **The comparison:** each setup against the average of all top-100 stocks the same day, so the market's drift
  isn't counted as skill.
- **Costs:** 0.05% each way.

| Setup | Signals a year | Excess per trade, next day | Excess per trade, 5 days | t (5 days) | 2014-19 / 2020-26 (5 days) |
|---|---|---|---|---|---|
| 20-day breakout | 3,761 | −0.003% | −0.072% | −1.0 | −0.05% / −0.09% |
| Bull flag | 691 | +0.007% | +0.015% | 0.1 | −0.09% / +0.08% |
| Reclaim the 20-day average | 1,476 | −0.002% | −0.075% | −0.7 | −0.03% / −0.11% |
| Oversold (RSI under 30) | 829 | −0.003% | +0.169% | 1.0 | +0.03% / +0.28% |
| Oversold bounce | 446 | −0.000% | −0.046% | −0.2 | −0.15% / +0.04% |

- **As day trades, none of them does anything.** Every setup is within ±0.01% of an average stock the next day.
- **Held 5 days, only "oversold" leans positive**, at +0.17% a trade. That's weak (t 1.0) and almost all from
  2020-26.
- **The desk's live dip rule is the better version of the same idea.** It adds the 200-day-average filter and sells
  on a close above the 5-day average, and made +1.0% / +1.2% a dip in the two periods (`research/CANDLE_RSI.md`).
- **Waiting for an up day first (the "bounce") throws away what edge there is.** That matches the candle tests:
  confirmation days add nothing.

**Verdict: nothing to adopt.** The pack is a well-made manual workflow, but its setups carry no edge on large stocks.
The Congress-purchase test needs `disclosures-clerk.house.gov`, which this environment's network settings block.
