# A weekly strategy: what works and what doesn't

_October 2026. Code: `research/weekly.py`. Tables: [`output/weekly.md`](output/weekly.md).
Educational research, not financial advice._

## The test

Each strategy decides at Friday's close and holds for a week. The universe each week is the
750 largest US companies as listed at the latest quarter-end, known at the time. The test runs
from April 2014 to October 2026, with a 0.10% cost per trade (and a 0.30% stress test). Cash
earns T-bills. Prices are survivors-only and trades are priced at Friday's close rather than
Monday's open, so **every number below is flattered**, the loser-buying ones most of all. The
fair comparison is the equal-weight universe, which carries the same bias.

## Results

| Strategy | Return/yr | Sharpe | Worst drop | At 3× costs | Beat the average stock |
|---|---|---|---|---|---|
| Reversal: buy the 20 biggest weekly losers | 6.5% | 0.29 | −61% | −12.5% | 3 of 13 years |
| Pullback: 20 biggest losers in an uptrend | 6.5% | 0.30 | −50% | −12.1% | 4 of 13 |
| **Momentum: top 20 by 6-month return, re-picked weekly** | **19.4%** | **0.69** | −42% | 13.7% | **11 of 13** |
| Equal-weight universe (the average stock) | 11.7% | 0.58 | −39% | - | - |
| SPY | 13.7% | 0.75 | −32% | - | - |

1. **Buying last week's losers doesn't work.** Reversal and dip-buying earned about half of
   what the average stock did, with 60% drawdowns. They also collapse once costs are realistic.
   This held for every variant (10, 20 or 50 stocks; 1- or 2-week losers).
2. **Medium-term momentum does work against the average stock.** Holding the strongest stocks
   of the last 6 months beat the equal-weight universe in 11 of 13 years. It worked in both
   halves of the test (Sharpe 1.00 in 2014-19 and 0.60 in 2020-26), and it survived triple costs.

## But weekly is the wrong timeframe for it

| Momentum, top 20 | Return/yr | Sharpe | Worst drop | At 3× costs | Book traded per week |
|---|---|---|---|---|---|
| 6-month, re-picked **weekly** | 19.4% | 0.69 | −42% | 13.7% | 24% |
| 6-month, re-picked every 2 weeks | 21.8% | 0.75 | −45% | 17.6% | 17% |
| 6-month, re-picked **every 4 weeks** | **24.0%** | **0.80** | −52% | 20.8% | 13% |
| 12-month, re-picked every 4 weeks | 24.3% | 0.79 | −52% | 21.8% | 10% |
| 3-month (13 weeks), re-picked weekly | 10.9% | 0.46 | −43% | 3.8% | 32% |

- **Re-picking less often is better.** Weekly churn costs more than it adds, the same finding
  as the bottleneck study.
- **The momentum has to be measured over 6-12 months.** Three-month momentum lost to the average stock.
- **Fewer stocks gives more return and more risk.** Ten stocks did best (26-28%/yr), but with
  worst drops of 47-58%.
- **The 40-week trend filter made no difference.**

## Honest verdict

- **There's no weekly edge.** The short-term ideas that trade every week failed.
- **There is a real-looking edge in 6-12-month stock momentum,** re-picked monthly. It's one of
  the best-documented effects in finance research, and here it was consistent across years,
  settings and both halves of the period. Its return per unit of risk is only roughly SPY's,
  though: Sharpe 0.69-0.82 vs 0.75. It gets there with about twice SPY's volatility and
  drawdowns near −50%. Survivorship flatters it too, because momentum stocks that collapsed and
  delisted are missing.
- **It overlaps the bottleneck sleeve,** which is also a momentum strategy (industry money flow
  plus stock strength). In this data, plain stock momentum re-picked every 4 weeks (24.0%/yr,
  Sharpe 0.80) did better than the bottleneck's backtested flow rotation (17.0%, 0.60). That
  is worth a proper test as an amendment to the bottleneck sleeve, not a fourth sleeve.

## Possible next step (not done)

Test "plain 6-month momentum, top 20, re-picked every 4 weeks" as a replacement for the
bottleneck sleeve's price-flow engine inside the 50/20/30 desk, with walk-forward and costs, and
compare the desk's Sharpe and drawdown. If it holds up, it becomes an amendment for you to
accept or reject.
