# Five documented short-term effects, tested with realistic fills

_October 2026. Code: `research/swing_edges.py` (tests 1-4) and `research/orb.py` (test 5). Tables:
[`output/swing_edges.md`](output/swing_edges.md), [`output/orb.md`](output/orb.md). Universe = the 750
largest US companies at each quarter-end (point-in-time), **survivors-only Yahoo prices**. Every trade
fills at an open after the decision close. Costs per trade each way: 0.02% (large-cap spread),
0.05%, 0.10%. Research, not advice._

Benchmarks, 2014-2026: average large stock (equal weight) **12.1%/yr, Sharpe 0.59**; SPY **13.7%, 0.72**.

## 1. Weekly pullback, bought at Monday's open: no edge

The zero-cost test (research/WEEKLY.md) bought at the same Friday close it decided on: 17.3%/yr.
Buying at Monday's open instead:

| | Return/yr | Sharpe | Worst drop |
|---|---|---|---|
| At zero cost | 13.1% | 0.56 | −53% |
| At 0.02% each way | 11.1% | 0.49 | −54% |
| At 0.05% | 8.2% | 0.37 | −56% |

- **About 4% a year was the impossible Friday-close fill.** The rest goes on costs.
- **Even at almost no cost, it's worse than owning the average stock.** It matches on return but
  has a much deeper worst drop (−54% vs −40%).
- **It only works in half the history:** Sharpe 0.22 in 2014-19, 0.65 in 2020-26.

## 2. Post-earnings drift: the downside is real, the upside isn't

Measured after each 10-Q is filed (42,365 quarterly reports), the next 60 trading days compared with
the average stock:

| Earnings surprise | Excess return | t-stat |
|---|---|---|
| Worst fifth | −0.55% | −2.6 |
| 2nd | −0.63% | −3.0 |
| Middle | −0.36% | −1.7 |
| 4th | −0.17% | −0.8 |
| Best fifth | +0.11% | 0.5 |

- **It's a steady staircase,** and the gap between best and worst held in both halves (+0.51% in
  2014-19, +0.77% in 2020-26). That's the classic drift: **bad news keeps getting priced in.**
- **Good news is already in the price** by the time the 10-Q is filed (+0.11% isn't
  distinguishable from zero). Large caps react fast to good news.
- **As a strategy, buying the best surprises** made 11.5%/yr (Sharpe 0.62): no better than the
  average stock. Buying the worst made 8.3% (0.42).
- **The useful version is as a filter, not a strategy:** avoid buying a stock in the 60 days after
  a bad earnings surprise. Worth testing on the desk's two stock sleeves; see "Next" below.

## 3. 52-week high: lower risk, not higher return

| | Return/yr | Volatility | Sharpe | Worst drop |
|---|---|---|---|---|
| 50 stocks closest to their 52-week high (monthly) | 8.8% | 13% | 0.55 | −21% |
| 50 furthest from their high | 10.2% | 27% | 0.42 | −49% |
| Swing: buy new 52-week highs, hold 20 days | 7.5% | 17% | 0.40 | −36% |

- **Stocks near their high are calm stocks.** They have half the volatility and half the worst drop
  of the average stock, but a lower return, so a similar Sharpe.
- **The return edge George & Hwang found (1963-2001) didn't show up** in large caps in 2014-2026.
- **Buying new highs as a swing trade did worse than holding.**
- **The desk already uses the useful part:** the momentum sleeve requires stocks to be above
  their 200-day average.

## 4. Overnight vs daytime: real, but you can't trade it

| | Gross return/yr | At 0.02% each way |
|---|---|---|
| SPY overnight (buy the close, sell the open) | +9.0% | −1.5% |
| SPY daytime (buy the open, sell the close) | +4.4% | −5.6% |
| Average stock overnight | +9.9% | −0.7% |

- **About two-thirds of the market's gain comes overnight.** That's a well-known pattern, and it
  shows here too.
- **Trading it means two trades a day,** about 500 a year, so even a 0.02% spread costs about 10%
  a year and wipes it out.
- **For a long-term holder it doesn't matter:** you earn both halves. Lesson for the desk: don't
  sell at the close and buy back at the open.

## 5. Opening range breakout on "stocks in play": no sign of an edge (preview only)

This follows Zarattini, Barbon & Aziz (2024), as described in their paper:
- **Stocks in play:** each day, the 20 with the most unusual volume in the first 5 minutes.
- **Entry:** trade in the direction of the first 5-minute candle, entering on a break of its high or low.
- **Exits:** a stop at 10% of the stock's average daily range; otherwise out at the close.

Yahoo only has 60 days of 5-minute and about 30 days of 1-minute bars, and the stop is so tight
(about 0.26% of the price) that a bar often hits both the entry and the stop. So there are two
bounds:

| | Trades | Avg R before costs | After 0.03% each way |
|---|---|---|---|
| 1-minute bars, best case (14 days) | 199 | −0.05R | −0.28R |
| 1-minute bars, worst case | 199 | −0.28R | −0.51R |
| 5-minute bars, best case (46 days) | 749 | −0.16R | −0.39R |

- **Even the best case loses before costs.**
- **Costs are huge in "R" terms:** with a stop of 0.26%, a 0.06% round trip is about a quarter of
  the amount risked on every trade.
- **The paper's universe was about 7,000 stocks,** mostly small caps that move far more after the
  open. That isn't what we can or should trade.
- **A real verdict needs years of minute data.** Alpaca's free feed has it, but
  `data.alpaca.markets` is blocked by this environment's network settings (Allowed domains, under
  Network access).

## Verdict and next

**None of the five is worth a sleeve.** They're recorded in the register as research-only. One thing is worth a
follow-up test: the **post-earnings filter**, which skips or delays buying a stock for 60 days after a
bottom-fifth earnings surprise, in the quality screen and momentum re-picks. It costs nothing to
trade, works on the desk's slow timetable, and the effect held in both halves. If you want it, it
goes through the usual route: backtest it inside the desk, then an amendment.

## Sources (accessed 2026-10-21)

- Bernard, V. & Thomas, J. (1989), "Post-earnings-announcement drift", *Journal of Accounting Research*.
- George, T. & Hwang, C. (2004), "The 52-week high and momentum investing", *Journal of Finance*.
- Zarattini, C., Barbon, A. & Aziz, A. (2024), "A profitable day trading strategy for the U.S. equity market", SSRN 4729284.
- Overnight returns: Cliff, M., Cooper, M. & Gulen, H. (2008), "Return differences between trading and non-trading hours".
