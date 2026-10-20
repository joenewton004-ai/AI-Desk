# Can we spot the big winners before their run?

_October 2026. Code: `research/winners.py`. Tables: [`output/winners.md`](output/winners.md).
Educational research, not financial advice._

## The short answer

**Not from anything we can measure here.** The best stocks of the last five years
share a *story* (almost all of them sit in the AI hardware and power supply chain),
but the numbers that describe them before their run were ordinary, and traits that
look like patterns in hindsight do not pick winners in advance.

The one thing that did hold up across eight years of starting points is **quality**
(high returns on capital, high margins, strong free cash flow, low debt). It does
not find the 10-baggers. It **avoids the busts**.

## 1. The past five years (30 Sep 2021 to 30 Sep 2026)

The 25 best of the 750 largest US companies, by total return (the median company
made +17%; the top-decile cut-off was +188%):

| | |
|---|---|
| Memory and storage | MU 15.4x, STX 12.9x, WDC 10.7x |
| AI chips and equipment | NVDA 11.1x, AVGO 7.9x, AMD 5.9x, LRCX 6.1x, KLAC 6.1x |
| Networking and optics | ANET 9.5x, LITE 11.6x, CIEN 6.9x |
| Servers and electronics | DELL 11.2x, FLEX 8.3x |
| Power, cooling and electrical build-out | BE 14.8x, VRT 10.1x, VST 8.8x, EME 6.6x, PWR 5.7x, NVT 5.3x |
| Everything else | PLTR 7.8x, HWM 7.4x, MPC 7.2x, TRGP 6.1x, LLY 5.2x, MOG-A 5.2x |

So the pattern is a **theme**, which is the premise of the bottleneck sleeve. But look
at what these companies looked like on the day the five years started
(median of the 25, against the median of all 750):

| At the start | Top 25 | All 750 | Where the top 25 sat |
|---|---|---|---|
| Return on capital | 9% | 10.5% | 45th percentile |
| Gross margin | 34% | 39% | 41st |
| Free-cash-flow margin | 9% | 12% | 39th |
| Revenue growth (multi-year) | 6.6%/yr | 4.8%/yr | 59th |
| Cheapness (operating earnings yield) | 3.8% | 2.9% | 63rd |
| 12-month price momentum | +59% | +36% | 71st |
| Volatility | 33% | 29% | 63rd |

**They were not obviously high-quality businesses.** Several (MU, STX, WDC, DELL, FLEX,
MPC) were cyclical hardware makers or refiners with flat or shrinking revenue and thin
margins. What stood out was only mild: stronger prior price momentum (71st percentile),
growth and margin trend a bit better than peers (about the 67th percentile) and
higher-than-normal volatility. A screen built in 2021 for "great businesses" would
have missed most of them.

## 2. But a list of winners proves nothing

Looking only at winners ignores everyone with the same traits who did not win. So the
test is **across 31 five-year windows** (every quarter from 2014 to 2021, each with
the point-in-time fundamentals we already hold): does having the trait raise the
chance of being a top-decile winner, and does it raise the chance of being a bust?

| Trait (top fifth of the universe) | Chance of being a winner | Chance of being a bust | Consistent? |
|---|---|---|---|
| High return on capital | 1.2x the base rate | **0.8x** | Higher later return in 31 of 31 windows |
| High operating margin | 1.1x | **0.6x** | 31 of 31 |
| High free-cash-flow margin | 1.5x | **0.6x** | 25 of 31 |
| High debt (net debt / EBITDA) | 0.8x | 1.3x | Worse later return in 25 of 31 windows |
| High revenue growth | 1.4x | **1.5x** | Barely any link to later return |
| High volatility | 1.3x | **1.9x** | Worse later return in 25 of 31 |
| High 12-month momentum | 1.1x | 1.3x | No link (rank correlation +0.015) |
| Gross margin rising, growth accelerating, cheap valuation | about 1.0x-1.1x | about 1.0x-1.3x | No link |

(Base rate: 10% for a winner and 10% for a bust. Ratios are the average across windows.)

Two clean lessons:

1. **Quality cuts the bust rate by a fifth to two-fifths but barely raises the winner rate.**
   It is a way to lose less, not to find the stock that runs. This is also why the live
   quality screen beat its universe in the backtest without finding 10-baggers.
2. **Growth and volatility are lottery tickets.** Fast-growing, volatile stocks produce
   more winners (1.3-1.4x) *and* more busts (1.5-1.9x), with no better average outcome.
   Winners looked "high-growth" only because the losers with the same trait are
   invisible in a list of winners.

The 1-year and 3-year versions agree: quality is mildly helpful, growth and momentum
are not reliable (`output/winners.md` sections 3 and 4).

## 3. Sectors: the winners cluster, but only after the fact

Electronics and semiconductors had a winner rate 1.7x normal and beat it in 84% of
windows. Oil and gas, airlines, telecom and apparel retail had many busts (oil and gas
4.2x the normal bust rate). Winners come from the sector with the tailwind of the era.
That is true, and nothing in the fundamentals told us *which* sector in advance.
The only forward-looking input this suggests is the one the bottleneck sleeve uses,
following where money is already flowing, and this test cannot confirm it works.

## 4. The real test: could it have picked winners in advance?

For every test window, each trait's direction was learned **only from windows that had
already finished** before the test started, then companies were ranked on all traits
together and the top decile compared with everyone:

| Test | Top-decile hit rate (random = 10%) | Picks | Universe |
|---|---|---|---|
| 5-year, starts 2019-06 to 2021-09 | **6%** | +5.4%/yr | +7.1%/yr |
| 1-year, 27 quarterly windows 2019-2025 | **9%** | +13.9% | +14.6% |

**It failed.** The ranked picks did slightly worse than picking at random, in both
tests, and lagged most for the 2020-21 starts. A likely reason is that the quality traits
it had learned fell out of favour while the market rewarded hardware and unprofitable growth
(not tested). Whatever helps in one era can stop helping in the next.

## What this means for the desk

- **Do not expect any screen on fundamentals or price to find the next big winner.** There
  is no evidence of it here, and we shouldn't build a sleeve that promises it.
- **Quality remains the defensible edge, as a way to avoid busts.** That matches the
  quality screen sleeve (50%) and its backtest, which beat its own universe
  (17.9%/yr against 11.4%).
- **The bottleneck sleeve's honest case** is "follow the theme while it is working, and
  leave when the trend breaks", not "find it before it starts". The 100-day exit
  matters more than the entry. We will learn whether that holds from paper trading.
- **Expect the next run to look different** from the AI build-out. Past winners tell
  us about the last era, not the next.

## Limits (all of them flatter the result, and none changes the conclusion)

- **Survivors only.** Companies that went bust or were bought are missing, which
  inflates every return and understates the bust rate.
- **Only the 750 largest companies at each date.** The biggest multiples often start
  in small companies, which are not in the data. Within the universe, smaller
  companies did show both more winners and more busts.
- **Overlapping windows.** The 31 windows share most of their years, so the "31 of 31"
  counts overstate certainty. About eight independent years sit behind them.
- **Only measurable traits.** Product launches, market size, management and anything
  qualitative are invisible here.
- **One era dominates.** The last five years were one AI theme.

## Next experiments, if you want them

1. **Survivor-free universe.** Rebuild with companies that died, from SEC filings, and
   include small caps. That is the only way to test whether anything finds the real
   multi-baggers.
2. **Theme detection.** Test whether an industry's recent strength predicts which
   industries win over the next year (industry momentum), since that is the one
   forward-looking idea the bottleneck sleeve relies on.
