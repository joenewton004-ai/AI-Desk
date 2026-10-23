# How far back to look when ranking stocks: a day, a week, a month... a year

_October 2026. Code: `research/lookbacks.py`. Tables: [`output/lookbacks.md`](output/lookbacks.md). 2014-2026, the 750
largest US companies at each quarter-end, **survivors-only prices**, T-bills on cash. Research, not advice._

The question: would the sleeves pick better stocks by ranking on a short window (yesterday, this week, 10 days, two
weeks, a month) instead of the long ones they use now?

## The overnight sleeve (top 20, held from the close to the next open)

Live: the average overnight return over 252 days (12 months), re-picked monthly. The sleeve sells everything every
morning, so re-picking daily costs nothing extra; that's tested too.

| Ranked by | 1 day | 5 days | 10 days | 21 days | 63 days | 126 days | 252 days |
|---|---|---|---|---|---|---|---|
| Average overnight return, re-picked daily (Sharpe) | 0.25 | −0.01 | −0.02 | 0.08 | 0.29 | 0.61 | **0.78** |
| Plain return, re-picked daily (Sharpe) | 0.11 | −0.39 | −0.43 | −0.52 | 0.12 | 0.63 | **0.88** |
| Average overnight return, re-picked monthly (Sharpe) | | | | 0.12 | 0.36 | 0.58 | 0.70 (live) |
| Average night after costs, overnight ranking daily (bp) | +2.6 | +0.7 | +0.6 | +1.4 | +3.0 | +5.8 | +7.3 |

- **Short windows don't work.** Ranking by the last day to the last month earns about nothing after costs (Sharpe
  −0.02 to 0.25). The overnight edge comes from stocks that rise overnight *persistently*, and that shows only over
  many months. A few good nights is mostly noise.
- **A plain short-term return is worse than nothing.** The top stocks of the last week to month lose overnight (Sharpe
  −0.39 to −0.52): last month's biggest winners tend to fall back.
- **Longer is better, all the way to 12 months.** That's the window the live sleeve already uses.
- **Two small possible improvements, both inside the noise:**
  - re-picking the same 12-month ranking every day instead of monthly: 0.78 vs 0.70;
  - ranking by the plain 12-month return instead of the overnight one: 0.88, in both halves (0.97, 0.92).

  The noise in a 12-year Sharpe is about ±0.3, so neither is proven. The plain-return version would also be a
  different strategy: momentum stocks held overnight, rather than the researched overnight effect.

## The momentum sleeve (top 20, re-picked every 4 weeks, sold below the 100-day average)

Live: the 6-month (26-week) return, skipping the latest week.

| Window | 1 week | 2 weeks | 4 weeks | 8 weeks | 13 weeks | **26 weeks (live)** | 52 weeks |
|---|---|---|---|---|---|---|---|
| Return/yr | 3.7% | 0.4% | 6.1% | 10.1% | 11.6% | **19.4%** | 17.2% |
| Sharpe | 0.18 | 0.03 | 0.28 | 0.44 | 0.49 | **0.75** | 0.68 |
| At 3× costs | −2.3% | −5.3% | 0.3% | 5.3% | 7.4% | **15.4%** | 13.2% |

- **The live 6-month window is the best one tested**, with 12 months close behind. Windows of a month or less barely
  beat cash, and lose money once costs are realistic.
- That matches decades of research on momentum. It works over 6-12 months; over a week to a month, prices tend to
  reverse instead (research/WEEKLY.md found the same for buying last week's losers).

## Verdict

**No merit in short windows for either sleeve.** The live choices (12 months for overnight, 6 months for momentum)
are at or near the best window. The only leads are small tweaks to the overnight sleeve, daily re-picking or the
plain 12-month return, and both are within the noise. Not worth an amendment on this evidence alone; worth
re-testing once the desk has its own live history.
