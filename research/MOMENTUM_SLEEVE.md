# Should plain momentum replace the bottleneck sleeve's engine?

_October 2026. Code: `research/momentum_sleeve.py`. Tables:
[`output/momentum_sleeve.md`](output/momentum_sleeve.md). Educational research, not financial advice._

## What was compared

The bottleneck sleeve's backtestable part is an **industry money-flow rotation**. It holds 8
stocks from the hottest industries, requires a price above the 100-day average, sells below it
and re-picks every 2 weeks (`research/BOTTLENECK.md`). The live sleeve adds a theme map and
fundamental fingerprints on top, which can't be backtested point-in-time.

The challenger is **plain momentum**: the 20 large companies with the best 6-month return
(skipping the latest week), above their 40-week average, re-picked every 4 weeks
(`research/WEEKLY.md`).

Both use the same weekly prices, 0.10% per trade, cash at T-bills and the same survivors-only
bias. The test runs April 2014 to September 2026.

## The sleeve on its own

| Engine | Return/yr | Sharpe | Worst drop | At 3× costs | 2014-19 Sharpe | 2020-26 Sharpe |
|---|---|---|---|---|---|---|
| Current: industry flow rotation | 17.8% | 0.63 | −45% | 11.0% | 0.50 | 0.72 |
| **Plain momentum, top 20, every 4 weeks** | **25.4%** | **0.86** | −41% | **22.1%** | **1.06** | **0.82** |
| Plain momentum + the live 100-day exit | 19.8% | 0.76 | **−30%** | 15.4% | 1.06 | 0.67 |
| Plain momentum, same stock pool as the current engine | 29.0% | 0.86 | −43% | 25.6% | 0.82 | 0.92 |
| Plain momentum, top 10 | 32.7% | 0.94 | −47% | 29.1% | 0.98 | 0.98 |

Plain momentum beat the current engine in **every version and both halves of the test**. It
also holds up much better with higher costs, because it trades about half as often.

## Inside the desk (50% quality screen + 20% sleeve + 30% SPY momentum)

| Desk with | Return/yr | Sharpe | Worst drop |
|---|---|---|---|
| Current engine | 16.3% | 0.88 | −22.8% |
| **Plain momentum, top 20** | **17.6%** | **0.94** | −25.1% |
| Plain momentum + the live 100-day exit | 16.5% | 0.92 | −24.2% |
| Plain momentum, top 10 | 19.3% | 1.00 | −23.4% |

- **Consistent:** the plain-momentum desk did better in 10 of 13 calendar years and in 65% of
  rolling 3-year windows. The losing years were 2021, 2022 and 2025.
- **Walk-forward:** each January it chose the engine with the better record so far. It picked
  plain momentum every year: 19.7%/yr (Sharpe 0.97) against 18.5% (0.91) for the current engine
  over the same years.
- **Modest at desk level:** about +1.3%/yr and +0.06 Sharpe, with a slightly deeper worst
  drop. The sleeve is only 20% of the desk. A Sharpe difference that small is inside the noise
  of a 12-year test, so treat it as "consistently a bit better", not proof.

## What it would mean

Swapping the engine would make the sleeve simpler and better-tested. Its picks would come from
price strength alone, with no theme map, fundamental gates or insider score. Those parts of
today's sleeve have never been backtested, and the winners study (`research/WINNERS.md`) found
no fundamental trait that picks the big winners in advance. It would also stop being a
"bottleneck" sleeve in spirit: it would follow whatever is strongest, which today is mostly the
same energy and AI-hardware names.

## Options (an amendment for you to decide)

1. **Replace the engine with plain momentum, top 20, re-picked every 4 weeks.** This is the best
   tested option.
2. **The same, keeping the 100-day sell rule between re-picks.** A bit less return, but a much
   smaller worst drop for the sleeve (−30% vs −41%).
3. **Keep the current bottleneck sleeve,** and judge it on paper against this as a benchmark.

Top 10 did best but holds very few stocks. Top 20 is the more robust choice. Either way, the
other 80% of the desk is unchanged.
