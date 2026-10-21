# Swing trading: VCP breakouts, as fixed rules

_October 2026. Code: `research/swing.py`. Tables: [`output/swing.md`](output/swing.md).
Universe = the 750 largest US companies at each quarter-end (point-in-time), **survivors-only
Yahoo prices**, which flatter this. Research, not advice._

## The idea

The `vcp-screener` skill in [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills)
(MIT licence, read 2026-10-21) follows Mark Minervini's "volatility contraction pattern". In plain
words: a stock in a strong uptrend pauses, its swings get smaller and its volume quieter, then it
breaks out of the pause on heavy volume. The skill finds candidates for a person to judge. Here
every step is a fixed rule:

| Step | Rule |
|---|---|
| Trend | Above its 50/150/200-day averages, stacked in that order, the 200-day rising, within 25% of the 52-week high, 30%+ above the low |
| Pause | The last 10 days' range under half that of the 50 days before; volume below its 50-day average |
| Breakout | Close above the highest close of the previous 20 days on 1.5x average volume |
| Entry | Next day's open |
| Exits | 8% stop, close below the 50-day average, +25% target, or 40 trading days |
| Book | Up to 10 positions of 10%; idle cash in T-bills; 0.10% cost each way |

## Results (April 2014 - October 2026)

| | return/yr | Sharpe | worst drop |
|---|---|---|---|
| **VCP breakouts** | 2.8% | 0.13 | −30% |
| Random strong-trend stocks, same exits | −0.2% | −0.07 | −40% |
| Average large stock (equal weight) | 12.1% | 0.59 | −40% |
| SPY | 13.7% | 0.72 | −34% |

- **1,123 trades:** 39% winners, averaging +10.6% against −6.1% for losers. That's +0.38% per
  trade after costs, held 24 days on average.
- **It beat SPY in 4 of 13 years** and the average stock in 5.
- **Costs kill it.** At 0.30% each way, which is realistic for a fast-moving breakout bought at
  the open, it loses money (−0.7%/yr).
- **No setting rescues it.** Across every change tested (stops, targets, holding time, breakout
  length, volume, number of positions), the best is 5.6%/yr, still far below buy-and-hold.
- **The pattern does add something.** It beats random picks from the same strong-trend stocks
  (+0.38% vs +0.03% per trade), so the breakout part isn't pure noise. It just isn't enough to beat
  simply owning the market, mostly because a quarter of the trades are stopped out and the
  50-day exit cuts winners short.

## Verdict

**No edge as a rules-based strategy.** Recorded in the register as research-only (`vcp_swing`).
Running it in a second paper account would mostly measure luck: a few months gives a few dozen
trades against 1,123 here. The skill's own author uses it as a shortlist for human judgement,
which this test can't capture, so it says nothing about how good that judgement is.
