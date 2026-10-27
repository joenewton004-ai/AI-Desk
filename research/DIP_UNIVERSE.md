# The RSI dip rule on wider universes (top 100 / 250 / 500 / 750)

_October 2026. Code: `research/dip_universe.py`. Tables: [`output/dip_universe.md`](output/dip_universe.md). Daily,
2014-2026, point-in-time universes from SEC snapshots. **Survivors-only prices**, which flatter dip-buying more the
further down the list you go. Research, not advice._

| Universe | Dips a year | Net per dip | 2014-19 | 2020-26 | At 0.20% costs | Worst dip | Money in dips | Desk return/yr | Desk Sharpe | Desk worst drop |
|---|---|---|---|---|---|---|---|---|---|---|
| **Top 100 (live)** | 44 | **+1.12%** | +1.01% | +1.21% | +0.82% | −28% | 5% | **27.7%** | **1.67** | **−15%** |
| Top 250 | 104 | +0.88% | +0.91% | +0.86% | +0.58% | −28% | 10% | 25.8% | 1.60 | −15% |
| Top 500 | 207 | +0.70% | +0.73% | +0.67% | +0.40% | −42% | 16% | 23.0% | 1.47 | −20% |
| Top 750 | 297 | +0.61% | +0.66% | +0.57% | +0.31% | −68% | 20% | 20.9% | 1.32 | −29% |

The desk is the live shape: dips at 10% each, at most 5, and the overnight sleeve with the rest, at 0.02% overnight
costs and 0.05% for the dips.

- **The rule works everywhere.** It's positive in both periods for every universe, with t-stats of 7-9.
- **Each dip earns less as the companies get smaller:** +1.12% for the top 100 down to +0.61% for the top 750. The
  worst single dips also get much worse: −68% in the top 750, a real falling knife.
- **For the desk, wider is worse.** More dips take money away from the overnight sleeve, which earns more per day
  invested than a smaller-company dip does. The desk's return falls from 27.7% to 20.9%, and its worst drop deepens
  from −15% to −29%.
- **The top 100 is the right list for the live desk.** No change.
