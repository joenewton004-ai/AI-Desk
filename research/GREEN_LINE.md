# The "big green line": hold the S&P 500 above a moving average

_October 2026. Code: `research/green_line.py`. Tables: [`output/green_line.md`](output/green_line.md). Research, not advice._

## Where it comes from

The Instagram account [@pb_ema](https://www.instagram.com/pb_ema) posts a rule it attributes to Charlie Munger. Buy the
S&P 500 while it's above the green line and sell when it falls below. The reel compares that with buy and hold over
50 years. The green line is a moving average from a free TradingView indicator the account calls "PB EMA".

We couldn't open Instagram from here. The rule comes from a third-party transcript of the reel
([creatorhouse.app](https://creatorhouse.app/video/DdZquhPPHo8), read 2026-10-27), so the exact wording and the
line's length aren't verified. Nothing we found shows Munger used or endorsed this rule; his public views were the
opposite of market timing. A different TradingView script called
[PlayBit EMA ("PB-EMA")](https://vn.tradingview.com/script/lkbAbJ3M-PlayBit-EMA) is a Bitcoin indicator and probably
unrelated. Other "green line" systems use other lengths, for example
[Above The Green Line](https://abovethegreenline.com/stocks/spxa50r/) uses a 250-day average. To verify: the reel's
own line length and its 50-year numbers.

## The test

Every common length was tested, because the reel's isn't known:
- Exponential averages (EMA) of 50, 100, 200 and 250 days.
- The 200-day simple average (SMA).
- The 10-month simple average, checked only at month-ends.
- The 200-day EMA with a 2% band: switch only once the close is 2% past the line, to cut false alarms.

The rules are the same for every version:
- The signal comes from each day's close, and the switch happens at the next day's open.
- Each switch costs 0.05%.
- Cash earns T-bills, and Sharpe is measured above T-bills.

**SPY with dividends, 1994-2026:**

| Green line | Return/yr | Sharpe | Worst drop | Sharpe to mid-2010 | Sharpe after | Time in the market | Switches/yr | 2008 | 2022 |
|---|---|---|---|---|---|---|---|---|---|
| Buy and hold | 10.8% | 0.51 | −55% | 0.28 | 0.80 | 100% | 0 | −37% | −18% |
| 50-day EMA | 7.4% | 0.48 | −28% | 0.34 | 0.63 | 71% | 18.5 | −9% | −13% |
| 200-day EMA | 8.3% | 0.51 | −28% | 0.36 | 0.66 | 79% | 7.5 | −6% | −24% |
| 200-day SMA | 8.6% | 0.53 | −25% | 0.35 | 0.73 | 77% | 6.6 | −3% | −12% |
| 200-day EMA, 2% band | 8.3% | 0.50 | −29% | 0.49 | 0.51 | 79% | 2.0 | −6% | −25% |
| 10-month SMA (month-ends) | 9.6% | **0.59** | **−24%** | 0.62 | 0.56 | 78% | 1.4 | +2% | −21% |

**The S&P 500 index, 1970-2026.** This series has prices only, so it leaves out about 2% a year of dividends from
buy and hold, while cash still earns its full T-bill rate. That flatters the line, and the reel's 50-year chart
likely has the same bias:

| Green line | Return/yr | Sharpe | Worst drop | 1987 | 2008 |
|---|---|---|---|---|---|
| Buy and hold (no dividends) | 8.1% | 0.28 | −57% | +2% | −38% |
| 200-day EMA | 8.3% | 0.38 | −24% | +25% | −1% |
| 200-day SMA | 8.2% | 0.36 | −24% | +25% | +1% |
| 200-day EMA, 2% band | 8.6% | 0.40 | −23% | +18% | −2% |

## What it means

- **The claim that it avoids crashes holds up.** Every version roughly halves the worst drop: about −25% instead of
  −55%. It was mostly in cash for 2002 and 2008, and in 1987 the 200-day line was out before the crash.
- **It doesn't make more money with dividends counted.**
  - On SPY, every line earns 1-3% a year less than holding, with about the same Sharpe (0.48-0.59 vs 0.51).
  - On the index it looks better (8.3% vs 8.1%), but only because the index ignores the dividends you give up
    while in cash.
- **The best length changes with the period.** The 10-month line was the best overall, but it won before 2010 and
  lost after. The 200-day SMA did the reverse. That's what noise looks like, not a dependable edge.
- **It can still miss a whole fall.** In 2022 the decline was slow, with rallies through the line. The 200-day EMA
  lost −24%, worse than holding (−18%), because each rally pulled it back in.
- **Faster lines whipsaw.** The 50-day EMA switched about 18 times a year and earned the least.
- **The desk already uses it.** The overnight sleeve goes to cash when SPY is below its 200-day average (amendment
  7a8b29ec). The old SPY-momentum sleeve and the Soros trend test (`research/SOROS.md`) are versions of the same idea.

## Verdict

**This is insurance, not an edge.** A moving-average rule on the S&P 500 cuts the worst drop roughly in half, for
1-3% a year less return and about the same Sharpe. It's worth it if a 50% fall would make you sell at the bottom,
but it won't beat holding. Recorded as research-only (`green_line`).
