# A drawdown circuit breaker on the desk: does stopping after losses help?

_October 2026. Code: `research/circuit_breaker.py`. Tables: [`output/circuit_breaker.md`](output/circuit_breaker.md).
Survivors-only prices (they flatter every row equally). Research, not advice._

## The idea

The `drawdown-circuit-breaker` skill in [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills)
(MIT licence, read 2026-10-21) stops new trades after the account loses too much:

| Loss | Halted until |
|---|---|
| 2% in a day | the next weekday |
| 5% in a week | next Monday |
| 8% in a month | the first day of next month |

It is aimed at hand-traded swing accounts, where a bad run can mean tilt and revenge trading.
We tested it on the desk (50% quality screen + 20% momentum + 30% SPY with its 12-month switch),
2014-2026, two ways:
- **freeze**: no new buys while halted; sells still go through (the skill's version);
- **cash**: sell everything to T-bills while halted and buy back at release.

## Results

Daily prices, all three limits:

| | return/yr | Sharpe | worst drop | days halted |
|---|---|---|---|---|
| Desk as it is | 16.4% | 0.81 | −33.4% | 0 |
| Skill defaults, freeze buys | 15.9% | 0.79 | −33.4% | 258 |
| Skill defaults, go to cash | 11.1% | 0.61 | −35.7% | 238 |
| Daily limit only, go to cash | 13.1% | 0.68 | −32.7% | 117 |
| Looser (3% / 7% / 10%), go to cash | 15.8% | 0.84 | −34.2% | 106 |

The weekly test (weekly and monthly limits only, plus tighter and looser settings) tells the same
story: freezing changes almost nothing (15.8% → 15.6%/yr), and going to cash costs 1.7%/yr. The
worst drop is about −31% in every version.

## Why it doesn't help this desk

- **Freezing does nothing here.** The desk only buys at re-picks (every 4 weeks for momentum,
  quarterly for the quality screen), so a few halted days rarely block anything.
- **Going to cash sells at the bottom.** The big loss days cluster with the big rebound days (March
  2020, April 2025), so cutting after a bad week often misses the bounce. In 2024 it cost 13.7%.
- **It doesn't cut the worst drop.** The desk's worst losses (2022) were slow grinds, not single
  bad weeks, and the breaker kept releasing and re-buying through them. The SPY sleeve's 12-month
  switch already does the slow "get out of a falling market" job.
- **The looser cash version's Sharpe (0.84 vs 0.81) is within noise:** it's one setting out of
  seven, with a worse worst drop.

## Verdict

**Rejected (your decision, 2026-10-21).** It stays in the register as research-only
(`drawdown_breaker`), and amendment `c312f032` is marked rejected with this evidence. It makes more sense for what it was built for: a hand-traded
account where a person might break their own rules after losses.
