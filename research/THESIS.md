# AI-Desk: strategy thesis

_October 2026. Written by Claude from this repo's research: `research/FINDINGS.md`
(market timing), `research/output/screen_backtest.md` (stock selection) and
`research/notes/2026-10-19/` (company research). Educational research, not
financial advice. No real money should follow it until the paper-trading
plan in section 7 has run its course._

---

## 1. The thesis in one paragraph

**Buy durable, high-return businesses when they're reasonably priced and
the market agrees they're working. Use one simple rule to limit the damage in
long bear markets. Let Claude do the research, but never the trading.**

The evidence supports the stock-selection part more than the market-timing
part. Over 12½ years of point-in-time data, a 25-stock quality screen beat an
equal-weighted portfolio of the same universe by about **4% a year**. The
result held across portfolio sizes, rebalance months and trading costs. It's
promising but **not proven**: the statistical confidence is moderate
(t ≈ 1.8), the sample covers one long bull market, and survivorship bias
inflates the absolute numbers. Market momentum cut drawdowns in 30 years of
index data, but in this period it lowered returns. So it belongs on the
index part of a portfolio as crash insurance, not as a filter on the stock
picks.

---

## 2. What the desk does

| layer | what it is | where in the repo |
|---|---|---|
| **Stock selection** | Rank large US companies on quality (ROIC, margins, cash conversion), growth, value, balance-sheet strength and momentum, after "great business" gates and a 10-year check on SEC filings | `ai_desk/fundamentals/` |
| **Market timing** | Hold SPY while its 12-month return is positive, otherwise T-bills | `ai_desk/strategies/momentum.py` |
| **Risk** | Position sizing, leverage cap, drawdown kill switch, stale-data and order-size guards | `ai_desk/risk.py`, `ai_desk/live.py` |
| **Research** | Claude reads filings and news for shortlisted names and writes dated, sourced notes; the numbers are generated from data, never typed | `research/notes/` |
| **Execution** | Alpaca paper trading only | `ai_desk/broker/alpaca.py` |

No LLM takes part in any buy or sell decision. Every decision is a
deterministic rule that can be backtested and audited.

---

## 3. Edge 1: quality stock selection

### Why it should work
- **Economics.** A business that earns 30% on its capital and can reinvest at
  similar rates compounds intrinsic value faster than one earning 8%. Markets
  tend to underestimate how long high returns last.
- **Research.** "Profitability" (Novy-Marx 2013) and "Quality Minus Junk"
  (Asness, Frazzini & Pedersen 2019) are among the better-documented equity
  factors. Combining quality with value and momentum is a common, published
  approach.
- **Behaviour.** Quality stocks are "boring" and seldom lottery-like, so
  speculative money tends to overlook them until the results add up.

### The point-in-time backtest (Apr 2014 – Sep 2026)
At every rebalance the screen was rebuilt using **only SEC filings that had
been filed by that date** (no later reports or restatements), that day's
prices, and the same gates, 10-year check and scoring as today's screener.

| | CAGR | volatility | Sharpe* | worst drawdown | beta |
|---|---|---|---|---|---|
| **Screen: top 25** (equal-weight, rebalanced each March) | **15.8%** | 18.6% | 0.78 | −32.7% | 1.15 |
| All companies passing the gates | 12.6% | 15.9% | 0.71 | −26.2% | 1.01 |
| Universe, equal-weight (same 750 companies) | 11.5% | 17.0% | 0.62 | −27.4% | 1.09 |
| S&P 500 (SPY) | 13.8% | 14.5% | 0.83 | −23.9% | 1.00 |

\*Sharpe measured above T-bills. 0.10% cost per trade on turnover.

**How robust is it?**
- **Rebalance month doesn't matter much.** The top 25 beat the universe whether
  rebalanced in March (+4.3%/yr), June (+4.7%), September (+4.1%) or December
  (+2.0%).
- **Portfolio size doesn't matter much.** Top 10: 18.3%/yr, top 25: 15.8%,
  top 50: 15.4%. More names give a little less return and a smoother ride,
  which is what a real effect looks like.
- **Costs barely matter.** At 5× the trading costs (0.5% a trade) it still
  earned 15.3%/yr, because it trades only once a year.
- **The ranking does the work, not the gates.** The gates alone added only
  about 0.8%/yr over the universe (t ≈ 0.7), while ranking within them added
  about 3.3%/yr. Filtering for quality avoids the worst companies; the
  combination of quality, value and momentum picks the winners.

**How confident should we be?**

| comparison | extra return | t-stat | reading |
|---|---|---|---|
| Screen vs same universe | +4.1%/yr | 1.80 | Suggestive. About a 7% chance of seeing this by luck if there were no real edge |
| Screen vs SPY | +2.4%/yr | 1.03 | Not distinguishable from luck, and achieved with more risk (beta 1.15) |

Rule of thumb: a t-stat above 2 is where evidence starts to be convincing,
and above 3 for an idea found by searching through many alternatives.

### What the backtest can't tell us
1. **Survivorship bias.** Prices come only from companies that still trade
   today, so firms that went bankrupt or were bought out are missing. This
   flatters the screen *and* the universe, which is why the fair comparison
   is screen vs universe (+4.1%), not screen vs SPY. The true edge over SPY is
   probably smaller than +2.4%.
2. **One regime.** 2014-2026 was mostly a bull market, with one fast crash
   (2020) and one bear market (2022). The screen lost **27% in 2022, worse
   than SPY's 18%**. It has never been tested in a long bear market like
   2000-02 or 2008.
3. **A recent lag.** From 2020 to 2026 the screen earned 14.5%/yr against
   SPY's 15.2%. The mega-cap tech rally favoured the cap-weighted index over
   any equal-weighted portfolio. If that continues, the screen keeps lagging.
4. **Lumpy returns.** Three years (2017 +48%, 2019 +43%, 2023 +43%) produced
   much of the outperformance. In 6 of 13 years it trailed SPY. Living
   through that takes patience.
5. **Simplifications.** Historical forward P/Es don't exist, so value used
   trailing earnings. Some companies' capital-spending data is missing from
   their filings. The universe dips into mid-caps, adding a size tilt that
   SPY doesn't have.

### What the company research added
Looking closely at today's top 10 (`research/notes/2026-10-19/`) showed what
the numbers miss:
- **Cyclical peaks look like quality** in a 4-year window. This led to the
  10-year SEC check, which now excludes the miners.
- **Biotech numbers hide expiry dates.** Incyte's main drug loses patent
  protection in 2028, and that doesn't show in any ratio.
- **"Cheap quality" always has a controversy.** Adobe and Booking face AI
  disruption; Deckers faces a slowing HOKA. The screen finds candidates. The
  investment case is whether that specific fear is overdone.

---

## 4. Edge 2: market momentum as crash insurance

From `research/FINDINGS.md`, testing SPY from 1994 to 2026 with costs and
T-bill interest:

| | CAGR | Sharpe | worst drawdown |
|---|---|---|---|
| SPY buy & hold | 10.8% | 0.51 | −55% |
| 12-month momentum on SPY | 10.6% | 0.60 | −34% |

It held up out-of-sample, across sub-periods, on other markets and at 6× the
costs. **Its value is surviving long bear markets** (2000-02, 2008), not
adding return.

**But it hurt the stock screen.** Applied to the top 25 from 2014 to 2026,
it cut return from 15.8% to 11.0% a year while barely improving the worst
drawdown (−33% → −26%). The bear markets in this period were short with
sharp rebounds: the switch sold after the drop and bought back after the
recovery (2016, 2020, 2022-23). This is the known weakness of trend rules.
They pay off in slow, deep bear markets and cost money in fast ones.

**Conclusion:** keep momentum as insurance on the **index** part of a
portfolio, where 30 years of data back it. Don't use it to switch the stock
portfolio on and off.

---

## 5. Putting it together: a proposed structure (to test, not to fund)

| portfolio, 2014-2026 | CAGR | volatility | Sharpe | worst drawdown |
|---|---|---|---|---|
| Screen top 25 only | 15.8% | 18.6% | 0.78 | −32.7% |
| SPY only | 13.8% | 14.5% | 0.83 | −23.9% |
| 50% screen + 50% SPY | 14.9% | 16.1% | 0.83 | −28.3% |
| **50% screen + 50% SPY with momentum** | **13.3%** | **14.6%** | **0.80** | **−23.2%** |

The last row is the most balanced candidate. It has SPY-like risk in this
period, keeps most of the screen's upside, and adds crash insurance that
would have mattered in 2008 (a period this backtest can't cover). Its cost:
lower return than holding SPY in a fast-recovering market.

**Proposed rules for paper trading:**
1. **50% "selection sleeve":** the screen's top 25, equal-weighted,
   re-picked every quarter (see the update below). Before buying, read the research note on each new
   name. Drop any with a known expiry date (patent cliff, contract loss) or a
   data flag.
2. **50% "index sleeve":** SPY when its 12-month return is positive,
   otherwise T-bills, checked monthly.
3. **Risk:** no position above 6% of the portfolio. The account-level kill
   switch (20% below peak) stays on.
4. **Costs and taxes:** about 25-50 trades a year. In a taxable account,
   annual rebalancing realises gains, which this backtest doesn't model.

---

## 6. What would prove this wrong (kill criteria)

Decide these *before* starting, so a bad run isn't explained away:

| signal | action |
|---|---|
| Selection sleeve trails the equal-weight universe by >10 percentage points over a rolling 3 years | Stop. The edge has probably gone, or never existed |
| Selection sleeve falls >40% from its peak | Halt and review: worse than anything in the backtest |
| Paper results differ from the backtest by >3%/yr for reasons other than market moves (fills, data errors) | Fix the machinery before continuing |
| A later data rebuild (e.g. with delisted companies) shows the edge vs universe below +1%/yr | Downgrade to "unproven", index sleeve only |

---

## 7. The plan from here

1. ~~**Build the portfolio executor.**~~ Done: `python -m ai_desk portfolio`
   (see `research/METHODS.md` and the README).
2. **Paper trade for at least 12 months.** Run both sleeves on Alpaca paper
   and log every decision to the journal.
3. **Monthly review.** Compare paper results with the backtest and the
   benchmarks, and check the kill criteria.
4. **Strengthen the evidence while waiting:**
   - add delisted companies: SEC filings exist for them, and prices could
     come from a paid source (e.g. Sharadar), to remove survivorship bias
   - extend the test back to 2009-10, when the XBRL data starts
   - test quarterly rebalancing and cap-weighting
5. **Only then** consider real money, starting small and only in a
   tax-advantaged account if possible.

---

## 7a. Update: quarterly re-picks and a 70/30 split

- **Quarterly re-picks backtest better than annual.** Same rules, re-picked
  every March, June, September and December:
  - **17.9%/yr, Sharpe 0.89**, against 15.8% and 0.78 rebalanced annually
  - still 16.8%/yr at 5× trading costs
  - the universe earned 11.4%/yr
  
  About 6 of the 25 names change each quarter. Fresher picks, especially
  momentum and the latest filings, seem to help. One caveat: this variant
  was chosen after seeing the annual result, so treat the improvement as
  likely, not proven.
- **Live allocation chosen: 70% screen / 30% SPY with momentum**
  (`--method aggressive`). In the backtest, the annual version of this split
  earned 14.4%/yr, with a −27% worst drawdown and −22% in 2022. That's more
  return and bigger drops than 50/50, with about the same Sharpe.
- **How it runs:**
  - Stock picks are locked when bought. Between quarterly re-picks only the
    SPY momentum switch can trade, and the stocks drift as in the backtest.
  - When a re-pick is due, run `python -m ai_desk screen` first. The
    executor then sells the dropouts, buys the new names and re-levels.

## 7c. Update: a bottleneck sleeve (see `research/BOTTLENECK.md`)

- **The live mix is now `--method desk`:** 50% quality screen (re-picked
  quarterly), 20% bottleneck sleeve (re-picked weekly, sold below the 200-day
  average), 30% SPY with the momentum switch.
- **Evidence is weak for the bottleneck sleeve.** Its testable part,
  money-flow rotation, didn't beat SPY with weekly re-picks (11.8%/yr,
  Sharpe 0.45, −61% worst drop). The desk with it earned 15.5%/yr (Sharpe
  0.85, −24%) vs 15.8% (0.89, −28%) for 70/30. It's kept as a 20%
  experiment because its fundamental filters (margin expansion, backlog,
  insider buying) and the theme map can't be backtested. The kill criteria
  in section 6 apply to it too.

## 7b. Methods tested since (see `research/METHODS.md`)

- **50/200 moving-average crossover:** the same crash insurance as momentum,
  with near-identical results on SPY. An acceptable alternative switch for
  the index sleeve, not an extra edge.
- **Duopoly pairs trading:** market-neutral (correlation 0.08), but only
  about 1%/yr above T-bills, and that halves with higher costs. It stays in
  research until hedge ratios, reversion tests and pair-retirement rules are
  added.
- **The executor now exists:** `python -m ai_desk portfolio plan --method thesis`
  shows the orders for the 50/50 structure against the paper account.

## 8. Bottom line

- **What's genuinely good:** a careful, point-in-time process for picking
  quality companies. Four years of Yahoo data are cross-checked against ten
  years of SEC filings, plus a sourced research note on each candidate. Over
  12½ years it beat comparable stocks by about 4% a year, robust to timing,
  size and costs.
- **What isn't proven:** that it beats simply owning the S&P 500, after
  accounting for risk, survivorship and luck.
- **The honest framing:** treat this as a **disciplined way to own a
  concentrated portfolio of great businesses**, with a realistic hope of
  modest outperformance. It is not a profit machine. Market momentum is
  insurance against the rare deep bear market, and you pay a premium for it
  in normal years.
- **What makes or breaks it:** following the rules through the years it lags
  (6 of 13 in this backtest), and stopping if the kill criteria trigger.
