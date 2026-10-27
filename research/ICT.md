# ICT day trading, with financials mixed in: is there an edge?

_October 2026. Code: `research/ict.py`. Tables: [`output/ict.md`](output/ict.md). Research, not advice._

## What ICT is

ICT ("Inner Circle Trader", Michael Huddleston) is a popular day-trading method built on
"liquidity". Obvious highs and lows have stop orders resting beyond them. Price runs those stops
(a **sweep**), then reverses sharply. The sharp move often leaves a **fair value gap (FVG)**: three
candles where the third doesn't overlap the first. You enter when price comes back into the gap,
put your stop beyond the sweep, and target the other side. Timing matters: setups are only taken
in set "kill zone" windows.

We tested two of its best-known models:
- **Silver Bullet:** an FVG between 10:00 and 11:00 New York time, after a sweep of the prior day's
  high/low or the opening range. Entry is a limit order at the gap, the stop goes beyond the sweep,
  the target is 2× the risk, and the position is closed by the end of the day.
- **Judas swing:** the first hour fakes out beyond the prior day's high or low, then closes back
  inside. Enter against the fake-out at 10:30 with a 2× risk target.

Each was tested pure, then with the company's financials mixed in. Point-in-time SEC data gave
the desk's quality score. Longs were taken only in the top third by score and shorts only in the
bottom third, so the chart sets the timing and the financials set the side. A trend filter (ICT's
"higher-timeframe bias": longs above the 50-day average, shorts below) was tested too. The rules
were fixed in the code before running.

**Limits of this test:**
- **The Silver Bullet sample is short.** Yahoo only keeps 60 days of 5-minute bars, so Model 1 is
  about 40 trading days (2,974 trades).
- **The Judas swing is on hourly bars**, about 3 years and 21,483 trades.
- **ICT's rules are discretionary.** These are community descriptions turned into fixed rules, so
  someone practising ICT would say a skilled trader filters the setups better. This tests whether
  the setups themselves have an edge.

## Results

Costs are 0.03% each way, which is cheap for large-cap stocks.

| | Trades | Win rate | Avg result before costs | Per trade after costs |
|---|---|---|---|---|
| **Silver Bullet, pure** | 2,974 | 41% | +0.01R | −0.06% (t = −3.5) |
| + financial bias | 959 | 41% | +0.02R | −0.07% |
| + financials, longs only | 619 | 42% | +0.07R | −0.00% |
| + trend bias | 1,445 | 40% | −0.02R | −0.09% |
| Coin-flip direction (control) | 2,974 | 47% | −0.02R | −0.07% |
| **Judas swing, pure** | 21,483 | 42% | −0.01R | −0.07% (t = −10.0) |
| + financial bias | 6,816 | 43% | −0.01R | −0.07% |
| + financials, longs only | 3,490 | 44% | +0.00R | −0.05% |
| + trend bias | 9,853 | 42% | −0.02R | −0.08% |
| Coin-flip direction (control) | 21,483 | 47% | −0.01R | −0.07% |

R is the trade's result as a multiple of the amount risked, so 0R means breaking even.

**What this means:**
- **Before costs, the setups break even.** About 0R per trade in both models, the same as flipping
  a coin for direction.
- **After costs, they lose.** As a portfolio (10% per trade, up to 10 a day), pure Silver Bullet
  lost about 17% a year and the Judas swing about 19%. SPY rose 75% over the Judas swing's window.
- **Financials help a little, but not enough.** Longs in strong-scoring companies were the best
  version in both models, but they only got to break-even (Silver Bullet −0.00%, t ≈ 0). That
  mostly reflects strong stocks drifting up in a rising market, not the setup.
- **The trend filter made things worse.**
- **It failed in every quarter.** The Judas swing lost money after costs in all 13 quarters
  (−0.04% to −0.16% per trade).

## Why day trading is so hard to win

- **Costs are a big share of each trade.** A typical intraday move is 0.5–1%, so 0.06% in round-trip
  costs takes a large bite, and a modest edge disappears.
- **Large caps are the most efficient stocks there are.** Obvious levels like the prior day's high
  and the opening range are watched by everyone, including high-frequency firms, so they don't
  leave a free edge.
- **What makes ICT look convincing on social media:** it's taught with hand-picked charts after
  the fact, and the rules are flexible enough that a winning trade can always be explained.

## Verdict

**No edge, with or without financials**, on 60 days and now on ten years (below). Not added to the desk; recorded as research-only
(`ict_daytrading`).

The parts that do hold up are already in the desk, on slower timeframes:
- strong financials (the quality screen);
- price strength (the momentum sleeve).

Both work over months, where costs are small next to the move.

## Re-run on ten years of 5-minute bars (October 2026)

Code: `research/ict_long.py`. Tables: [`output/ict_long.md`](output/ict_long.md).

Alpaca's market data is now reachable. The re-run keeps the same rules, universe rule, biases, costs and portfolio.
What changed:
- **Period:** January 2016 to October 2026, instead of 60 days (Silver Bullet) and 3 years (Judas swing).
- **Data:** Alpaca's consolidated 5-minute bars, split-adjusted. The Judas swing's hourly candles are built from them
  as 9:30, 10:30 and so on.
- **Coverage:** 222 of the 224 companies that were in the top 100 at some point. The two missing are OTC listings,
  and coverage is 100% of member-days.

| | Trades | Avg R before costs | After costs (0.03% each way) | t | 2016-20 | 2021-26 | Portfolio Sharpe |
|---|---|---|---|---|---|---|---|
| Silver Bullet, pure | 129,658 | +0.02 | −0.051% | −21.4 | −0.051% | −0.051% | −2.02 |
| Silver Bullet + financials, long only | 22,355 | +0.04 | −0.035% | −5.7 | | | −1.37 |
| *Silver Bullet, coin-flip direction* | 129,658 | −0.00 | −0.061% | | | | |
| Judas swing, pure | 80,366 | −0.00 | −0.053% | −15.8 | −0.059% | −0.049% | −2.70 |
| Judas swing + financial and trend bias | 11,904 | +0.00 | −0.052% | −5.6 | | | −1.52 |
| *Judas swing, coin-flip direction* | 80,366 | −0.00 | −0.062% | | | | |

- **The first test's answer holds, and is now beyond doubt.**
  - Both models lose after costs in every year from 2016 to 2026.
  - The Silver Bullet lost in 42 of 44 quarters, and the Judas swing in 39 of 44.
- **The Silver Bullet's direction call is worth about 0.01% a trade.**
  - It wins 39% of the time with 2R targets, against a coin flip's −0.061%, so +0.02R before costs.
  - With 130,000 trades that small number is real, but it's a sixth of the cost of a round trip, even at a tight
    0.03% each way.
- **The Judas swing's direction call is worth nothing:** −0.00R, the same as a coin flip.
- **The financial and trend biases don't rescue either model.**
  - Long-only Silver Bullet in high-quality companies is the least bad version (+0.04R before costs, −0.035% after).
  - Every version is negative in both halves.
- **What this can't capture:**
  - A trader's discretion: which gap "looks right", and skipping news days.
  - Futures and forex, where ICT is mostly taught.
  - Small caps. The TJR re-run on QQQ/SPY (`research/TJR.md`) found the same thing: nothing before costs.

## Sources (accessed 2026-10-21; community descriptions, not ICT's own course material)

- LuxAlgo, "ICT Silver Bullet setup": https://www.luxalgo.com/blog/ict-silver-bullet-setup-trading-methods/
- LuxAlgo concept library, Silver Bullet: https://www.luxalgo.com/library/concept/silver-bullet/
- TradingView, "What is the ICT Silver Bullet strategy": https://pl.tradingview.com/chart/EURUSD/jOkVQBxm-What-Is-the-ICT-Silver-Bullet-Strategy-and-How-Does-It-Work
- TradingView, "Mastering ICT concepts": https://pl.tradingview.com/chart/BTCUSDT.P/XrrOfC4G-Mastering-ICT-Concepts-The-Ultimate-Trading-Strategy-Guide
