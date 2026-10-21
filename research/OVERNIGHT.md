# Overnight returns, stock by stock: the first short-term edge that survives (small) costs

_October 2026. Code: `research/overnight.py`. Tables: [`output/overnight.md`](output/overnight.md). Universe = the
750 largest US companies at each quarter-end (point-in-time), price over $10, $20M a day traded;
daily Yahoo prices, **survivors-only**. Research, not advice._

## The question

Across the market, most of the gain arrives **overnight**, between one day's close and the next
day's open (research/SWING_EDGES.md). Trading that on SPY fails: two trades a day cost more than it
earns. But Lou, Polk & Skouras (2019) found the split is **persistent stock by stock**: the stocks
that earned the most overnight in the past keep doing so. We tested whether that holds, and whether
the strongest names can be traded profitably.

## 1. It's widespread

Over 2014-2026, among 819 stocks with 3+ years in the universe:
- **The median stock made +10.1% a year overnight and +3.7% during the day.**
- **Overnight beat daytime for 69% of stocks.**
- **The top names** (picked with hindsight, so descriptive only) are mostly the period's big
  winners: BE, CEG, VRT, FIX, NVDA, AMD, AXON, APP, LITE (+54% to +101% a year overnight).
- **Some stocks lose overnight and earn in the day,** e.g. MRNA, RBLX, ABNB, GME.

## 2. It persists (out of sample)

Each month, stocks were ranked by their average overnight return over the previous 12 months, and
the **next** month was measured:

| Past-overnight tenth | Next month overnight /yr | Next month daytime /yr |
|---|---|---|
| 1 (weakest) | +3.1% | +11.6% |
| 5 | +8.3% | +3.1% |
| 10 (strongest) | **+24.0%** | −3.0% |

- **The strongest tenth beat the weakest by 7.3 basis points a night** (t = 6.4), in **82% of 150
  months**, and about equally in both halves (6.8 and 7.7).
- **There's a "tug of war":** the overnight winners give some back during the day (−5.6 bp a day,
  t = −3.0). Holding them around the clock captures only part of the overnight edge.
- **This is the strongest, most consistent pattern in all our research so far.**

## 3. Trading it

The 20 strongest past overnight earners, re-picked monthly, held **only overnight**: buy at the
close, sell at the next open, every day.

| | Return/yr | Sharpe | Worst drop | 2014-19 | 2020-26 |
|---|---|---|---|---|---|
| Zero cost | 27.7% | 1.18 | −36% | 21.0% (1.54) | 33.5% (1.13) |
| **0.02% each way** | **15.5%** | **0.70** | −36% | 9.4% (0.72) | 20.7% (0.74) |
| 0.05% each way | −0.7% | −0.02 | −58% | | |
| Same 20 held day and night | 19.9% | 0.66 | −47% | 7.3% | 31.3% |
| Average stock | 12.6% | 0.62 | −39% | | |
| SPY overnight only, 0.02% | −1.5% | −0.25 | | | |

**Robustness** (overnight only):

| Variant | 0.02% each way | Break-even cost each way |
|---|---|---|
| 20 stocks, 12 months (base) | 15.5% | 0.045% |
| 10 stocks | 18.1% | 0.049% |
| 50 stocks | 11.8% | 0.038% |
| 6-month look-back | 12.3% | 0.039% |
| 3-month look-back | 7.3% | 0.030% |

- **It works in every variant at 0.02%, and a longer look-back is better.** The pattern is robust,
  not one lucky setting.
- **Everything hinges on the cost.** It trades 20 stocks twice a day, about 10,000 orders a year,
  so each 0.01% per trade is worth about 5% a year. Below about 0.02% it beats the market; above
  about 0.045% it loses.
- **Why low costs may be possible:** the trades would use the official **closing and opening
  auctions** (market-on-close and market-on-open orders, which Alpaca supports). Those fill at the
  same official prices this test uses, without crossing a bid-ask spread. A $100k account is far
  too small to move an auction.
  - What's left is mainly the SEC fee on sales (about 0.003%) and any gap between Yahoo's "open"
    and the true opening-auction price.
  - That's plausible, but **unproven**.

## Caveats

- **Survivors-only prices.** Stocks that crashed and were delisted are missing. That flatters
  the long-held strong names most.
- **The current list is extreme.** Over the past 12 months the top names (LITE, BE, SNDK, MU, MRVL,
  TSEM...) made +130% to +375% a year overnight. That's the AI-hardware run: concentrated in one
  theme and one regime.
- **Earnings land overnight.** Part of any stock's overnight return is earnings news, which is a
  gamble each quarter.
- **Execution risk.** Missing the closing-auction cut-off (3:50pm New York for NYSE, 3:55pm for
  Nasdaq) or an opening-auction failure would leave positions open during the day, which these
  stocks tend to lose.
- **Tax** (in a real account): every trade is short-term.
- **Paper trading won't measure the real auction cost.** Alpaca's paper fills are simulated, so a
  paper test proves the plumbing, not the cost.

## Verdict

**Promising, not proven.** It's the only short-term effect in our research that:
- is statistically strong out of sample (t = 6.4, 82% of months);
- holds up across settings and in both halves;
- survives costs, if they're about 0.02% or less per trade.

The open question is the real cost of trading through the auctions. Recorded in the register as
research (`overnight_drift`), status **promising - needs a cost test**.

**Possible next step (your decision):**
- Build it as a separate, small experimental sleeve or a second paper account.
- Send market-on-close buys at about 3:45pm and market-on-open sells before 9:28am New York.
- Log every fill against the official open and close.
- Paper trading proves the mechanics. Only a small real-money test would prove the cost, and the
  desk stays on paper unless you explicitly decide otherwise.

## Sources (accessed 2026-10-21)

- Lou, D., Polk, C. & Skouras, S. (2019), "A tug of war: overnight versus intraday expected returns", *Journal of Financial Economics* 134(1).
- Cliff, M., Cooper, M. & Gulen, H. (2008), "Return differences between trading and non-trading hours: like night and day".
- Alpaca order types (market-on-open "opg", market-on-close "cls"): https://docs.alpaca.markets/docs/orders-at-alpaca (verify cut-off times and paper-fill behaviour there).
