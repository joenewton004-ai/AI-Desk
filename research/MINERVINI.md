# Mark Minervini's SEPA method, as fixed rules

_October 2026. Code: `research/minervini.py`. Tables: [`output/minervini.md`](output/minervini.md). Daily, April
2014 - October 2026. Universe = the 750 largest US companies at each quarter-end (point-in-time), **survivors-only
Yahoo prices**, which flatter every rule here. Research, not advice._

## The method

Minervini calls it SEPA ("Trade Like a Stock Market Wizard", 2013; "Think & Trade Like a Champion", 2017). He
reports winning the 1997 US Investing Championship. In plain words: buy market leaders that are already in strong
uptrends and growing earnings fast, buy them as they break out of a quiet pause, and cut losses quickly. Each
part is a fixed rule here:

| Part | Rule |
|---|---|
| **Trend Template** | Above the 50, 150 and 200-day averages, stacked 50 > 150 > 200; the 200-day rising for a month; 30%+ above the 52-week low and within 25% of the high |
| **Relative strength** | IBD-style rating 70+ (top 30%), from the 3, 6, 9 and 12-month returns |
| **Growth** | Latest quarter's EPS up 25%+ and sales up 20%+ on a year earlier; optionally EPS growth accelerating. From SEC filings as first reported, used only from the day after filing |
| **Entry** | Either hold the qualifiers, or buy a breakout from a tight base on 1.5× volume (the VCP rule in `research/swing.py`) |
| **Risk rules** | 7.5% stop; stop raised to break-even once a trade is up 15% (twice the risk); then sold on a close below the 50-day average |
| **Market filter** | New buys only while SPY is above its 200-day average |
| **Book** | Up to 10 positions of 10%; idle cash earns T-bills; 0.10% cost each way |

## Results

| | Return/yr | Sharpe | Worst drop | Invested |
|---|---|---|---|---|
| A. Trend Template + RS, held while it qualifies | 11.8% | 0.45 | −48% | 99% |
| B. + earnings and sales growth | 7.0% | 0.33 | −35% | 65% |
| C. + accelerating earnings | 5.3% | 0.26 | −32% | 54% |
| D. B + his stops | 5.7% | 0.27 | −35% | 65% |
| **E. Full SEPA (growth + base breakout + stops)** | **5.2%** | **0.30** | **−24%** | 37% |
| F. E + market filter | 5.4% | 0.31 | −23% | 34% |
| G. E without the growth rules (chart only) | 1.6% | 0.07 | −41% | 91% |
| **Average large stock (equal weight)** | **12.1%** | **0.59** | −40% | 100% |
| **SPY** | **13.7%** | **0.72** | −34% | 100% |

## What it means

- **No version beats simply owning the market.** The best Sharpe is 0.45, for the Trend Template alone, against
  0.59 for the average stock and 0.72 for SPY. The full method makes 5.2% a year.
- **The full method controls risk well.** Its worst drop was −24%, against −40% for the average stock. But that's
  mostly because it sits in cash: only 37% invested on average. Its Sharpe of 0.30 shows that less risk didn't
  mean better risk-adjusted returns.
- **The growth rules matter; the chart rules don't, on their own.** Without the trading rules (section 3 of the
  tables):
  - Trend Template + RS stocks did no better than the universe the next month (+0.02%, t 0.1).
  - Adding the growth rules gave +0.45% a month, which isn't distinguishable from luck (t 0.9, about 11 stocks).
  - Growth alone, with no chart rules, gave +0.52% a month (t 2.0). That's the only hint of something real, and
    with five groups tested, a t of 2.0 is weak evidence.
  - Breakouts without the growth rules (G) earn almost nothing.
- **His win/loss shape shows up:** 36% winners averaging +23%, losers −9%. But:
  - stops averaged −9.6%, not −7.5%, because a close below the stop is sold at the next open, after the gap;
  - one year carries the record: 2024 (+61% for E). Without it, E is close to T-bills.
- **It's unstable.** E beat the average stock in 2014-19 (Sharpe 0.55 vs 0.75 is still lower), and fell to 0.24 in
  2020-26. A (the template) did the reverse.
- **Costs bite the rotation versions.** At 0.30% each way, A falls from 11.8% to 7.7% a year.
- **It overlaps with what we run.** A is a cousin of the desk's momentum sleeve (strong trend, top relative strength).
  It does worse than that sleeve's own backtest, so there's nothing here to swap in.

## What this can't capture

Minervini is a discretionary trader. He judges the quality of each base, "pivot" points, how a stock acts after
the breakout, sells into strength, adds to winners, and raises or lowers total exposure with his own read of
the market. None of that is in fixed rules, so this tests the rules he publishes, not his skill. It also can't
check his reported results.

## Verdict

**No edge as fixed rules.** The method's risk management works (shallower drops), but the return isn't there.
The one lead is that fast growth by itself (EPS +25%, sales +20%) picked stocks that did slightly better the next
month (t 2.0). Peter Lynch's growth rules (`research/LYNCH.md`) found no edge, so treat this lead with caution.
Recorded in the register as research-only (`minervini_sepa`).
