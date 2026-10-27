# Day-trading candle patterns: SPY, then NVDA, on ten years of minute bars

_October 2026. Code: `research/candles.py` (data: `research/alpaca_bars.py`). Tables: [`output/candles.md`](output/candles.md).
Research, not advice._

## Why SPY, then NVDA

SPY was the cleanest test bed in the 60-day scan of the 120 largest stocks:
- About $25bn trades a day at a one-cent spread.
- No earnings or company news.
- The smallest opening jumps, and the same behaviour across decades.

NVDA is the most liquid single company (about $24bn a day), with about 3½× SPY's daily movement.

**Data:** Alpaca's consolidated (SIP) 1-minute bars, 2016-01-04 to 2026-10-26, split-adjusted. That's about 1.06 million bars and 2,719 days per symbol, built into 5-minute candles. This is the first intraday test on the desk with years of data rather than Yahoo's 60 days.

## The rules (fixed before the first run, textbook definitions)

| Pattern | Rule |
|---|---|
| Engulfing | A candle whose body swallows the previous opposite-coloured body |
| Hammer / shooting star | A wick of 60%+ of the candle's range on one side, 15% or less on the other |
| Inside-bar breakout | A candle inside the previous one; trade a break of the previous candle's high or low within 3 candles; stop at the other side, target 2R |
| Opening-range breakout (ORB) | The first break of the first 15 or 30 minutes' high or low; stop at the other side; out at 15:55 |
| Intraday momentum | Gao, Han, Li & Zhou (2018): the direction from yesterday's close to 10:00 sets a 15:30-to-close trade |

**How the trades are taken:**
- Engulfing and hammer/shooting star only count when the candle's range is at least the median of the previous 20 candles.
- Each was tested in three contexts:
  - plain (every signal);
  - reversal: long below the day's VWAP (volume-weighted average price), short above it;
  - trend: the other way round.
- Each was also tested with two exits: hold 30 minutes, or a stop beyond the candle plus a 2R target ("R" is the risk to the stop).
- Every trade starts at the next candle's open and is out by 15:55.
- Costs: 0.01% each way on SPY, 0.02% on NVDA.

**The control ("placebo"):** the same side, time of day and exit on random other days. That shows what the market's drift and the time of day give without the pattern; the edge is what a pattern adds on top of it.

## Results

**SPY: nothing works.**
- All 32 versions lose after costs, at t −1.7 to −8.
- Before costs, every candle pattern is within ±0.01% a trade of its placebo. On a 5-minute SPY chart, engulfing candles, hammers, shooting stars and inside bars predict nothing.
- The published intraday-momentum effect is gone too: +0.000% versus its placebo, and negative after costs in both halves. The paper's sample ended before 2016; the effect has since been arbitraged away or never carried to this period.

**NVDA: the candle patterns fail the same way, but one rule looked like an edge.**

| | Trades | Net per trade | t | 2016-20 | 2021-26 | Edge vs placebo |
|---|---|---|---|---|---|---|
| ORB 15 min, long | 1,334 | **+0.151%** | 3.2 | +0.136% | +0.164% | +0.133% |
| ORB 30 min, long | 1,311 | +0.138% | 3.1 | +0.121% | +0.151% | +0.131% |
| ORB 15 min, short | 1,346 | +0.005% | 0.1 | +0.054% | −0.037% | +0.061% |

That's positive in all 11 years and in both halves. The pattern is typical of breakouts: the best 5% of trades made 150% of the total, and the rest lost.

**The check: it doesn't hold on stocks we didn't pick with hindsight.** NVDA was chosen because it's huge now, after rising about 100× since 2016, and that flatters buying strength. So the same ORB rules were run on QQQ and the 10 largest US companies at the end of 2015: AAPL, GOOGL, MSFT, BRK.B, XOM, AMZN, META, GE, JNJ and WFC. These are survivors, but they weren't picked for what happened next.

| Pooled over those 11 | Trades | Net per trade | t | Stocks with net > 0 |
|---|---|---|---|---|
| ORB 15 min, long | 14,859 | −0.002% | −0.3 | 5 of 11 |
| ORB 30 min, long | 14,596 | −0.011% | −1.4 | 3 of 11 |
| ORB 15 min, short | 14,502 | −0.040% | −4.7 | 2 of 11 |
| ORB 15 min, busy opens only, long | 793 | −0.003% | −0.1 | 6 of 11 |

"Busy opens only" keeps the days when the opening range traded at 2× its usual volume or more. It's a nod to Zarattini, Barbon & Aziz (2024), who use "stocks in play". Theirs picks the 20 busiest stocks from the whole market each day, so this isn't a faithful copy.

## What it means

- **Textbook candle patterns have no edge on 5-minute charts of liquid US stocks.** Ten years and thousands of trades per pattern show it clearly, and before costs too, so cheaper fills wouldn't fix it.
- **NVDA's opening-range breakout is a hindsight effect.** It works on the one stock that rose 100×, and not on the 11 that were the obvious choices in 2016. Buying strength in a stock that trended up all decade looks like skill in a backtest.
- **This is multiple testing in action.** 64 versions were run on SPY and NVDA, and the best one (t 3.2) was on the stock picked for its past. That's the warning sign the cross-check was there to catch.
- **It's consistent with every earlier intraday test:** ICT, TJR's model, the Cameron gap-and-go and the EMA9/VWAP crossover. Liquid stocks' intraday charts are close to random once costs are counted.

## What this can't capture

- **Discretion.** A trader reading the tape, news and the wider market isn't a fixed rule.
- **Small caps and "stocks in play"**, where the published intraday edges are. A fair test picks the most active stocks each morning from the whole market, which needs a delisted-inclusive universe. Alpaca's data includes delisted symbols only if we know their names.
- **Real fills.** Stop orders at breakouts fill worse than these bars assume, so the results here are, if anything, flattering.

## Verdict

**No edge in common candle patterns on SPY or NVDA; NVDA's opening-range breakout doesn't survive the hindsight check.** Recorded as research-only (`candle_patterns`). The useful by-product is ten years of minute bars from Alpaca, which future intraday ideas can be tested on properly.
