# Candle patterns + SMA trend + RSI on daily bars: is there a method that works?

_October 2026. Code: `research/candle_rsi.py`. Tables: [`output/candle_rsi.md`](output/candle_rsi.md). Research, not advice._

## The question, and why daily bars

Every intraday test found that chart patterns carry almost no information and costs decide the result:
- candles on SPY and NVDA (`CANDLES.md`);
- the ICT models (`ICT.md`);
- TJR's model (`TJR.md`).

A daily bar moves about 10× more than a 5-minute one, so costs matter far less. RSI(2) dip-buying alone is known to
have faded on SPY (`FINDINGS.md`).

The question here is whether a reversal candle, on top of a moving-average trend filter and an oversold RSI, picks
better dips.

**What others found** (read 2026-10-27):
- **Thailand, SET50 stocks, 2006-2016** ([SAGE Open, 2017](https://journals.sagepub.com/doi/10.1177/2158244017736799);
  also on [EconPapers](https://econpapers.repec.org/RePEc:sae:sagope:v:7:y:2017:i:4:p:2158244017736799)): candle
  reversal patterns, with or without an RSI, Stochastic or MFI filter, mostly had returns indistinguishable from zero.
- **Caginalp & Laurent (1998)** ([paper](https://c.mql5.com/forextsd/forum/210/The%20Predictive%20Power%20of%20Price%20Patterns.pdf)):
  strong results on S&P 500 stocks, 1992-1996.
- **Later replications** found much less. A [South African study](https://open.uct.ac.za/items/fecf7820-28a7-4bf9-9919-3cab4b200b43)
  using the same method found one pattern that worked. Marshall, Young & Rose found no value on Dow stocks for
  1992-2002, but that's a secondary summary: verify it against the original.
- **Promotional backtests**, such as [Quantified Strategies on doji + RSI](https://quantifiedstrategies.substack.com/p/crush-the-markets-with-doji-candlestick),
  claim more but aren't peer-reviewed.

## The protocol (fixed in the script before any result was seen)

**The rules:** long only. A signal at day t's close buys at t+1's open, and the position is sold at the open after
the exit condition.

| Ingredient | Options |
|---|---|
| Trend (SMA) | none; close above the 200-day SMA; close above the 200-day and the 50-day above the 200-day |
| Oversold (RSI) | none; RSI(2) < 10; RSI(14) < 30 |
| Candle | none; hammer; bullish engulfing; reversal close (a lower low, then a close in the top 25% of the range) |
| Exit | the first close above the 5-day SMA (at most 10 days); hold 5 days |

That's 72 rules.

**Costs:** 0.02% each way for ETFs, 0.05% for stocks.

**Markets and periods:**

| Market | What it covers | Development | Holdout |
|---|---|---|---|
| ETFs | SPY, QQQ, IWM, DIA, EFA, EEM | to 2012 | 2013-2026 |
| Stocks | the 100 largest US companies at each date, point-in-time from SEC filings | 2014-05 to 2019 | 2020-2026 |

The stock prices are survivors-only.

**How rules were picked and judged:**
- The three best rules **with a candle** in development were picked for each market.
- Each was judged in the holdout and on the other market, against three tests:
  1. a profit with t > 2;
  2. better than the same rule without the candle;
  3. a strategy Sharpe at least the benchmark's.

## Result 1: candles add nothing

| Picked on → tested on | Rule | Holdout trades | Net per trade | t | Without the candle | Tests passed |
|---|---|---|---|---|---|---|
| ETF → ETF | hammer, exit above SMA5 | 1,158 | +0.048% | 0.9 | +0.046% | 1 of 3 |
| ETF → ETF | above SMA200, hammer | 947 | +0.068% | 1.7 | +0.034% | 1 of 3 |
| ETF → ETF | strong trend, reversal close | 1,441 | +0.069% | 2.0 | +0.027% | 1 of 3 |
| Stocks → stocks | RSI(14)<30 + reversal close, exit above SMA5 | 424 | +0.726% | 2.3 | +0.697% | 2 of 3 |
| Stocks → stocks | RSI(14)<30 + reversal close, 5 days | 431 | +0.114% | 0.3 | +0.713% | 0 of 3 |
| Stocks → stocks | hammer, 5 days | 7,201 | +0.107% | 1.7 | +0.162% | 0 of 3 |

Each rule was also run on the other market (ETF picks on stocks and stock picks on ETFs). The full table is in the
output file, and **none of the 12 holdout runs passes all three tests.**

- The one that passes two is the RSI rule. Its candle adds +0.03% a trade, which is nothing.
- Across every trend × RSI × exit combination in the holdout (the last table of the output), a candle's effect is
  mixed: as often worse as better. The bigger "improvements" rest on 2-60 trades.
- A bullish engulfing day and RSI(2) < 10 almost never coincide: an engulfing day is an up day, which lifts RSI(2).

**Verdict on candles: no. A reversal candle doesn't pick better dips on daily bars either.** That matches the Thai
study and every intraday test.

## Result 2: the RSI part does work, without the candle

These were added after seeing the results, so they weren't pre-registered. That makes them a lead, not a finding.

| Stocks (top 100) | Period | Trades | Net per trade | t | Invested | Sharpe | Equal-weight top 100 | Correlation |
|---|---|---|---|---|---|---|---|---|
| Above SMA200, RSI(14)<30, exit above SMA5 | 2014-19 | 237 | +1.01% | 5.1 | 6% | 0.92 | 0.81 | 0.47 |
| | 2020-26 | 298 | +1.21% | 4.7 | 6% | 0.69 | 0.57 | 0.36 |
| Any trend, RSI(2)<10, 5 days | 2014-19 | 7,409 | +0.21% | 4.6 | 94% | 0.32 | 0.81 | 0.91 |
| | 2020-26 | 9,748 | +0.48% | 8.4 | 94% | 0.65 | 0.57 | 0.88 |
| ETFs: above SMA200, RSI(2)<10, exit above SMA5 | 1993-2012 | 565 | +0.47% | 5.1 | 10% | 0.44 | 0.33 | 0.35 |
| | 2013-26 | 662 | +0.30% | 4.6 | 12% | 0.34 | 0.59 | 0.46 |

**The lead: a big company still above its 200-day average whose RSI(14) falls below 30. Buy the next open, sell the
open after it closes above its 5-day average** (about 4 days on average). It survives every check:

| RSI(14) below | Cost each way | Trades 2014-26 | Net per trade | t | 2014-19 | 2020-26 | Positive years |
|---|---|---|---|---|---|---|---|
| 25 | 0.05% | 85 | +1.64% | 4.8 | +0.97% | +2.34% | 12 of 13 |
| **30** | **0.05%** | **535** | **+1.12%** | **6.7** | **+1.01%** | **+1.21%** | **11 of 13** |
| 30 | 0.20% | 535 | +0.82% | 4.9 | +0.71% | +0.91% | 10 of 13 |
| 35 | 0.05% | 2,021 | +0.60% | 7.6 | +0.60% | +0.60% | 12 of 13 |

- **It isn't one lucky setting.** Thresholds of 25, 30 and 35 all work in both periods, and with 4× the costs.
- **It's spread out:**
  - The most frequent stocks are AAPL, HD and LOW (11 trades each).
  - The best 5% of trades make 46% of the total.
  - The worst single trade was −28% and the best +18%.
- **It's known, not new.** This is the short-term reversal effect (Jegadeesh 1990, Lehmann 1990) and Connors-style
  dip-buying in an uptrend. On SPY alone it faded after publication (`FINDINGS.md`). Across 100 large stocks it held
  up through 2026.

**Caveats:**
- **Survivors-only prices flatter dip-buying.** A company that kept falling and was removed is missing. The
  membership is point-in-time, and very few top-100 companies go bust, but the bias points the wrong way.
- **The holdout isn't fully clean.** The rule family was ranked 4th of 72 in development and promoted after looking
  at the holdout.
- **It's rarely invested:** about 40 trades a year, using about 6% of a 10-slot book. On its own it would sit mostly
  in T-bills. Its value would be as a small add-on that uses idle cash, with low correlation to the market.
- **Real fills at the open after a sharp drop can be worse than these bars.**

## Verdict

- **Candle patterns, with or without an SMA trend and RSI: no edge.** Recorded as research-only (`candle_rsi`).
- **RSI(14) < 30 dip-buying in big companies above their 200-day average** is the first short-term rule here that:
  - works in both periods;
  - works at nearby settings;
  - survives 4× costs.

  It's a lead for a desk-level test, not a live method. The next step would be:
  - an amendment;
  - a backtest inside the desk (using idle cash or a small slice, with the overlap with the quality and momentum
    sleeves);
  - a check on delisting-inclusive data where possible.
