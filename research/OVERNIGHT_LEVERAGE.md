# The overnight sleeve with borrowed money (1x, 1.5x, 2x)

_October 2026, the owner's what-if (not an amendment). Code: `research/overnight_leverage.py`. Tables:
[`output/overnight_leverage.md`](output/overnight_leverage.md). Daily, 2014-04 to 2026-10, the live rules, **survivors-only
prices**, margin interest at T-bills + 2.5%. Research, not advice._

| Leverage | Costs each way | Return/yr | Volatility | Sharpe | Worst drop | Worst night | Worst month | 2014-19 Sharpe |
|---|---|---|---|---|---|---|---|---|
| 1.0x | 0.02% | 26.1% | 14% | 1.54 | −15% | −8.9% | −11.3% | 1.43 |
| 1.5x | 0.02% | 37.9% | 22% | 1.50 | −22% | −13.3% | −16.7% | 1.35 |
| 2.0x | 0.02% | 49.9% | 29% | 1.48 | −29% | −17.7% | −21.8% | 1.31 |
| 1.0x | 0.05% | 12.6% | 14% | 0.76 | −21% | −8.9% | −12.2% | −0.03 |
| 1.5x | 0.05% | 16.3% | 22% | 0.72 | −32% | −13.4% | −18.0% | −0.11 |
| 2.0x | 0.05% | 19.5% | 29% | 0.69 | −42% | −17.9% | −23.5% | −0.15 |

- **Borrowing scales everything, but it doesn't improve it.**
  - Return, swings and losses grow with the leverage, and the Sharpe falls slightly because of the margin interest.
  - **If costs are 0.02%, 2x roughly doubles the return** (50% a year) and doubles the worst drop (−29%).
  - **If costs are 0.05%, 2x adds little return** (12.6% → 19.5%) but doubles the worst drop (−21% → −42%). In
    2014-19 the sleeve lost money before borrowing, so leverage only made those years worse.
- **The backtest's crash protection holds.** In Feb-Mar 2020 the SPY 200-day check put the sleeve in cash, so even 2x
  was about flat. The worst nights came from single-night shocks in the picks: −18% at 2x.
- **Years at 2x (0.02% costs):** +162% (2020), +125% (2024), +109% (2026 so far), but also −2% (2018), 0% (2022),
  +6% (2019) and +7% (2023). Big totals, lumpy delivery.
- **The practical limits:**
  - A US broker lends about 2x overnight, so 2x leaves no buffer; a bad night could bring a margin call.
  - 1.5x is the realistic ceiling.
  - Borrowed money also doubles the effect of the unknown: real fill costs.
- **Verdict: only worth considering once real costs are known to be near 0.02%.** It would need its own amendment.
