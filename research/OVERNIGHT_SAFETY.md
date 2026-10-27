# Can the overnight picks be made safer?

_October 2026. Code: `research/overnight_safety.py`. Tables: [`output/overnight_safety.md`](output/overnight_safety.md).
Daily, 2014-04 to 2026-10, the live rules and checks, **survivors-only prices**. Earnings release times come from SEC
8-K item 2.02 filings: 1,119 companies, read 2026-10-27. Research, not advice._

The variants were fixed before running:
- **E:** skip a stock on a night it reports earnings (the next-ranked stock takes its place).
- **V:** skip the most volatile fifth of stocks.
- **S:** at most 4 stocks from one industry.
- **N30:** hold 30 stocks instead of 20.
- **ESV:** E, S and V combined.

| Version | Return/yr | Volatility | Sharpe | Worst drop | Worst night | Worst month | 2014-19 | At 0.05% costs: Sharpe |
|---|---|---|---|---|---|---|---|---|
| **Live (top 20)** | 26.1% | 14.5% | **1.54** | −15% | −8.9% | −11.3% | 1.43 | 0.76 |
| E: skip earnings nights | 21.8% | 13.8% | 1.36 | −15% | −8.9% | −11.4% | 1.32 | 0.54 |
| V: skip the most volatile fifth | 14.3% | 8.7% | 1.35 | −11% | −4.8% | −10.3% | 0.91 | 0.04 |
| S: at most 4 per industry | 23.6% | 13.7% | 1.47 | −14% | −8.9% | −10.6% | 1.41 | 0.65 |
| N30: 30 stocks | 20.7% | 13.1% | 1.35 | −16% | −7.8% | −10.8% | 1.38 | 0.49 |
| ESV: all three | 11.3% | 8.2% | 1.11 | −14% | −4.8% | −9.1% | 0.80 | −0.29 |

Figures are at 0.02% costs each way unless marked.

## What it means

- **The worst nights aren't about which stocks were picked.**
  - The five worst nights had no earnings among the picks. They were market-wide shocks: 2024-08-05 (the yen
    carry-trade unwind), 2025-01-27 (the DeepSeek sell-off), 2026-06-23, 2026-09-14 and 2026-07-07.
  - When everything gaps down together, a different selection of momentum stocks gaps down too.
- **Earnings nights are where the sleeve makes much of its money.**
  - A pick's earnings night averaged +1.09%, against +0.10% on other nights, though it swings far more (7.6% vs
    1.7%).
  - Only 1.5% of pick-nights are earnings nights. Skipping them cut the return by 4 points a year, and the worst
    night didn't change.
- **Calmer stocks (V) halve the swings, but only by halving everything.**
  - Return falls from 26% to 14%, and the sleeve becomes fragile to costs: Sharpe 0.04 at 0.05%. Calm stocks move
    less overnight, but cost the same to trade.
  - Simply putting about 60% of the money in the live picks and 40% in T-bills gives about the same volatility
    (~8.7%) with a better Sharpe (~1.5) and a smaller worst night (~−5%).
- **An industry cap (S) and more stocks (N30) change little**, and both cost some return.

## Verdict

**None of these filters makes the picks safer for a fair price.** The sleeve's drawdowns come from the whole market
gapping at the open, and from how much of the desk is in the sleeve. They don't come from bad stock choices.

The tools that actually control a dramatic drawdown are:
1. **How much money goes overnight.** Today it's ~95% of the desk (amendment c52ce018). For example, 60% would cut
   the swings by about 40% with the same Sharpe; the rest earns T-bills.
2. **The existing cash checks:**
   - SPY below its 200-day average kept the sleeve flat through February-March 2020.
   - The picks-down-2% check covers a weak day.
3. **No borrowed money** (`research/OVERNIGHT_LEVERAGE.md`).

A lower overnight share, if wanted, would be an amendment. Nothing has changed in the live rules.
