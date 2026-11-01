# Studio - launch lineup (10 videos)

Every number below is copied from the named write-up in `research/`. Re-check the source before recording - if a
write-up is re-run, its numbers change and the script must change with it. Educational content, not financial advice.

Ranked by likely appeal: famous name x size of the surprise x how clean the result is.

---

## 1. ICT Silver Bullet - 10 years, 129,658 trades  (SCRIPTED: EP01)

- **Title:** I Tested ICT's Silver Bullet on 129,658 Trades
- **Thumbnail:** 129,658 TRADES. VERDICT?
- **Hook:** "One of the most popular day-trading setups on YouTube. Ten years of data. A hundred and thirty thousand trades. It did no better than flipping a coin for direction."
- **Key result:** 2016-2026, Alpaca 5-min bars, top 100 US companies. Silver Bullet: 129,658 trades, +0.02R before
  costs, -0.051% per trade after 0.03% each way (t -21.4), lost in 42 of 44 quarters; portfolio -11.4%/yr. Judas
  swing: 80,366 trades, -0.00R before costs, -0.053% after, lost in 39 of 44 quarters. Coin-flip direction control
  -0.061% / -0.062%. Source: `research/ICT.md`, `research/output/ict_long.md`.
- **Caveats:** community descriptions turned into fixed rules (not ICT's own course material); no trader discretion;
  tested on large US stocks, not futures/forex where ICT is mostly taught; no small caps.

## 2. The "big green line" - insurance, not an edge

- **Title:** The Instagram 'Green Line' Rule: Does It Beat Buy and Hold?
- **Thumbnail:** HALF THE CRASH
- **Hook:** "A rule doing the rounds on Instagram says: own the S&P 500 above one line, sell below it. It really does cut the worst crash roughly in half - and it still loses to doing nothing."
- **Key result:** SPY with dividends, 1994-2026: buy and hold 10.8%/yr, Sharpe 0.51, worst -55%; 200-day SMA 8.6%,
  0.53, -25%; 10-month SMA 9.6%, 0.59, -24%. Every version earns 1-3%/yr less; in 2022 the 200-day EMA lost -24% vs
  -18% for holding. On the price-only index (no dividends) the line looks better - a flattering bias. Source: `research/GREEN_LINE.md`.
- **Caveats:** the reel's exact line length wasn't verified (from a third-party transcript). Nothing found shows
  Charlie Munger used or endorsed it - say so, don't attribute it to him. Best length changes with the period.

## 3. Copying Congress (and Nancy Pelosi)

- **Title:** I Copied Every Stock Congress Bought for 12 Years
- **Thumbnail:** COPY CONGRESS?
- **Hook:** "Apps promise you can copy what politicians buy. We read 5,966 House trade reports. Copying them beat the S&P 500 by two-tenths of a percent a year."
- **Key result:** buying at the open after the filing date, holding 60 days: copy book 13.9%/yr, Sharpe 0.71, worst
  -35% vs SPY 13.7%, 0.75, -32% (2014-2026). No rule beyond t 1. Pelosi: 41 events, +0.17% vs universe over 60
  days (t 0.7); her 2014-19 trades lagged by 6%. Sales did no worse than purchases. Source: `research/CONGRESS.md`.
- **Caveats:** House only (Senate not reachable); ~40% of 2014-19 reports are paper scans and missing; survivors-only
  prices; tests the stock, not Pelosi's call options. Don't imply anyone traded illegally.

## 4. TJR's model - 10 years on QQQ/SPY

- **Title:** TJR's Strategy, Backtested on 10 Years of Data
- **Thumbnail:** SWEEP. BREAK. LOSE?
- **Hook:** "Liquidity sweep, break of structure, enter. Before costs, it made 0.007 of a unit of risk per trade - effectively zero."
- **Key result:** QQQ/SPY 5-min incl. pre-market, 2016-2026: break of structure 2R, 3,401 trades, +0.007R before costs,
  -0.088R after (t -3.9) - the same as random-direction trades at the same times (-0.087R). Only 3 of 11 years
  positive. First test on NQ/ES (~49 days, 76 trades) inside the random range. Source: `research/TJR.md`.
- **Caveats:** his rulebook isn't public - this is the community version; QQQ/SPY aren't NQ/ES futures (no
  Asia/London levels); no discretion. Income figures quoted online are unverified - don't repeat them as fact.

## 5. Candle patterns on 10 years of minute bars

- **Title:** Engulfing, Hammer, Inside Bar: 10 Years of Data Says...
- **Thumbnail:** CANDLES DON'T WORK?
- **Hook:** "We tested 32 versions of the most famous candle patterns on 10 years of S&P 500 minute bars. All 32 lost money after costs."
- **Key result:** SPY 2016-2026: all 32 versions lose after costs (t -1.7 to -8); before costs every pattern is
  within +/-0.01% of its random placebo. NVDA's 15-min opening-range breakout looked great (+0.151%/trade, t 3.2) but
  on QQQ + the 10 largest companies of end-2015 it made -0.002% (t -0.3). Source: `research/CANDLES.md`.
- **Caveats:** textbook definitions, no discretion; large liquid stocks only; the hindsight check stocks are survivors
  too. Great "how backtests fool you" segment (NVDA picked because it rose ~100x).

## 6. Mark Minervini's SEPA as fixed rules

- **Title:** Minervini's SEPA Method: 12 Years of Fixed-Rule Backtest
- **Thumbnail:** ONE YEAR DID IT
- **Hook:** "Mark Minervini's rules cut losses fast and the drawdowns really were smaller. But one year - 2024 - carried the whole record."
- **Key result:** full SEPA 5.2%/yr, Sharpe 0.30, worst -24% (37% invested) vs average large stock 12.1%/0.59 and SPY
  13.7%/0.72 (2014-2026). Trading it his way (pivot buys, intraday stops) 6.3%. Without 2024, every version is
  close to T-bills. Growth alone hint: +0.52%/month, t 2.0 (weak). Source: `research/MINERVINI.md`.
- **Caveats:** survivors-only prices; only the 750 largest companies (his leaders are often smaller/recent listings);
  his discretion isn't in the rules. His 1997 and 2021 contest results are verified - say so fairly.

## 7. Leveraged S&P 500 (3x) with strict risk rules

- **Title:** 3x S&P 500 Buy and Hold Fell 98%. Can Rules Fix It?
- **Thumbnail:** -98% → -37%
- **Hook:** "Hold a 3x S&P 500 fund through every crash since 1994 and at the worst point you'd have lost 98%."
- **Key result:** 1994-2026 simulated (matches real SSO/UPRO since 2009 closely): 3x buy and hold 14.9%/yr, worst -98%;
  3x strict 12.7%, worst -37%; SPY 10.8%, -55%. Sharpes all ~0.49-0.58. Since 2010 plain SPY beat them all on
  risk-adjusted terms (0.77 vs 0.58-0.61). Source: `research/LEVERAGED.md`.
- **Caveats:** simulated before 2009; gap risk, swap counterparties, fund closure not modelled. Not an edge.

## 8. Peter Lynch's PEG rules on point-in-time SEC data

- **Title:** Peter Lynch's PEG Rule Doesn't Work Anymore. Here's Why.
- **Thumbnail:** PEG < 1 = ?
- **Hook:** "Peter Lynch made about 29% a year at Magellan. We turned his famous ratios into rules and ran them for 12 years. Every one trailed the average stock."
- **Key result:** 2014-2026: PEG under 1 10.6%/yr, Sharpe 0.53 vs average large stock 11.5%/0.61, SPY 13.8%/0.83.
  PEG under 1 on its own: -0.07% a quarter vs the average stock. Cheapest 25 by P/E worst row (8.1%). Source: `research/LYNCH.md`.
- **Caveats:** survivors-only prices; past growth used instead of his forecasts; his research process ("buy what you
  know", company visits) isn't testable. Framing: his edge was the research, not the ratios.

## 9. The overnight effect - where the market's gains actually happen

- **Title:** Most of the Stock Market's Gains Happen While It's Closed
- **Thumbnail:** THE NIGHT SHIFT
- **Hook:** "About two-thirds of the market's gain comes between the close and the next open. So why can't you just trade the night?"
- **Key result:** SPY overnight +9.0%/yr gross vs daytime +4.4%; at 0.02% each way overnight -1.5% (`SWING_EDGES.md`).
  Stock-by-stock version (Lou, Polk & Skouras): strongest tenth beat weakest by 7.3 bp a night, t 6.4, 82% of 150
  months; top 20 overnight-only 27.7%/yr at zero cost, 15.5% at 0.02%, -0.7% at 0.05%; break-even ~0.045%. Source: `research/OVERNIGHT.md`.
- **Caveats:** survivors-only; everything hinges on costs, which paper fills can't measure; current list is concentrated
  in the AI-hardware run; earnings land overnight. "Promising, not proven" - never present as a money machine.

## 10. George Soros - the part a rule can copy

- **Title:** Can You Copy George Soros? We Tested His Core Idea
- **Thumbnail:** -9% vs -51%
- **Hook:** "You can't copy Soros's trades. But the skeleton of macro trading - follow each market's trend - had a worst drop of 9% while the S&P fell 51%."
- **Key result:** 9 ETFs, monthly 2006-2026: long-only trend 7.3%/yr, Sharpe 0.79, worst -9% (2008: -1%) vs SPY 11.1%,
  0.67, -51%; 60/40 8.2%, 0.72, -29%. Long/short version +25% in 2008 but Sharpe 0.40 overall. Source: `research/SOROS.md`.
- **Caveats:** risk control, not higher return; no currencies, leverage or judgement - this is not his skill; his
  reported records come from profiles, not audited fund records.

---

## Reserves

- **Ross Cameron gap-and-go (large caps)** - gap up 4%+ bought at the open: -0.13%/trade after 0.10% each way over
  20,676 trades; the only winner needs hindsight volume (+1.54%). `research/CAMERON.md`. Caveats: no small-cap
  history, which is his actual turf. If the FTC 2022 settlement is mentioned, quote it exactly as the write-up does
  ($3m refunds, no admission, FTC didn't allege his own results were false) - or leave it out.
- **EMA9/VWAP crossover** - -0.067%/trade on 14,996 trades; random entries on the same days did better.
  `research/VWAP_EMA.md`. Caveat: 30-60 day minute samples (hourly 3 years).
- **Jim Simons / Medallion** - explainer, no backtest (trades aren't public); 50.75% win rate, 66%/yr before fees
  (disputed estimate). `research/SIMONS.md`.
- **Weekly dip-buying vs momentum** - `research/WEEKLY.md` (close-to-close fills + survivors: flattered).

## Channel-wide rules for scripts

1. Only numbers from the write-ups; quote them as written (e.g. -0.051%, not "about -0.05%" unless the file says "about").
2. Always say: rules tested are fixed-rule versions of public descriptions; discretion isn't tested.
3. Say "survivors-only prices" whenever the source says it.
4. Never say a named person lies or scams; describe their public rules and published claims.
5. One-line disclaimer in every video and description: *"Educational research, not financial advice. I'm not a financial adviser; past results don't predict future ones."*
