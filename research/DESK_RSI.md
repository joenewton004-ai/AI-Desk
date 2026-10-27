# The desk with an RSI dip-buying overlay (amendment 661549dd)

_October 2026. Code: `research/desk_rsi.py`. Tables: [`output/desk_rsi.md`](output/desk_rsi.md). Research, not advice._

## What was tested

The rule comes from `research/CANDLE_RSI.md`. When one of the 100 largest US companies closes **above its 200-day
average with RSI(14) below 30**:
- buy it at the next open;
- sell at the open after it first closes above its 5-day average (at most 10 days).

On its own it made about +1.1% a trade, but it's invested only about 6% of the time, so how it's funded decides
what it's worth.

These versions were fixed in the amendment before running:

| Version | How it's funded |
|---|---|
| **Primary** | 3% of the desk per trade, at most 5 at once, borrowed from the overnight sleeve's 30% while open (the overnight sleeve buys that much less). Quality 50% and momentum 20% unchanged |
| S1 | A fixed 10% sleeve (5 slots of 2%), T-bills when idle; the other sleeves cut pro-rata (45/18/27) |
| S2 | The same 10% sleeve, taken from the quality screen (40/20/30) |

**How the other sleeves are modelled:** as they run live. The overnight sleeve uses the 12-month ranking, re-picked
daily, with both regime checks.

**The test setup:**
- Monthly, June 2014 to September 2026.
- Survivors-only prices, which flatter every sleeve, dip-buying most.
- The overlay costs 0.05% each way, with a 0.20% stress test.

**The decision rule, fixed in the amendment:** accept only if the desk's Sharpe is higher in **both** 2014-19 and
2020-26, the worst drop is no more than 1 point deeper, and it still beats the current desk at 0.20% costs.

## Results

| Desk | Overlay costs | Return/yr | Sharpe | Worst drop | 2014-19 | 2020-26 |
|---|---|---|---|---|---|---|
| Current (50% quality, 20% momentum, 30% overnight) | | 21.5% | 1.243 | −21.0% | 1.262 | 1.268 |
| **Primary: dips funded from overnight** | 0.05% | 21.9% | 1.278 | −21.3% | 1.329 | 1.287 |
| **Primary** | 0.20% | 21.6% | 1.255 | −21.5% | 1.301 | **1.266** |
| S1: fixed 10%, pro-rata | 0.05% | 20.2% | 1.278 | −19.3% | 1.305 | 1.301 |
| *S1 with plain cash instead of trades* | | 19.5% | 1.243 | −18.9% | 1.262 | 1.269 |
| S2: fixed 10%, from quality | 0.05% | 20.5% | 1.308 | −18.3% | 1.331 | 1.339 |
| *S2 with plain cash instead of trades* | | 19.8% | 1.272 | −17.9% | 1.287 | 1.306 |

- **The trades add a little, every way they're funded.** About +0.035 Sharpe and +0.6% to +0.9% a year at 0.05%
  costs. That's measured against each version's own cash baseline, since S1's and S2's other gains come from holding
  cash or less quality screen, not from the trades.
  - The primary's Sharpe gain has a 90% range of +0.012 to +0.069, so at low costs it's more than noise.
  - It helped in 8 of 13 years.
- **It's genuinely different from the rest of the desk.**
  - Its monthly correlation with the desk is 0.10.
  - In the market's 10 worst months it averaged +0.09% while the desk lost −6.1%. Dips in uptrending stocks are rare
    in a crash, because the stocks fall below their 200-day average first.
- **It's small.** It averages only 1.6% of the desk, about one position at a time. It can't change the desk much.
- **Costs eat half of it.** At 0.20% each way the primary's gain shrinks to +0.013 (range −0.012 to +0.048), and
  in 2020-26 the Sharpe is 1.266 against 1.268: no better.

## Against the decision rule

**The primary fails, narrowly.** At 0.05% it passes:
- Sharpe higher in both halves (1.329 vs 1.262; 1.287 vs 1.268);
- the worst drop only 0.3 points deeper.

At 0.20% costs its 2020-26 Sharpe is 0.002 below the current desk's. S1 and S2 pass, but most of their gain is the
cash they hold, which the desk could hold without any trades.

Costs matter more than usual here, because both ends of every trade are at the open:
- Live paper fills at the open have been 0.45-0.68% worse than the official open (amendment e43f2959's market-on-open
  A/B test is measuring this now).
- Real opening-auction costs for these stocks are probably close to 0.05%.

## Recommendation

**Reject for now, by the rule set before the test.** The overlay is real but small: about +0.6% to +0.9% a year,
with a Sharpe gain that fades at higher costs.

Worth revisiting once the market-on-open test (judged around 2026-11-10) shows what fills at the open really cost:
- If market-on-open fills are close to the official open, the overlay could be re-proposed with market-on-open entries
  and exits.
- Funding from the overnight sleeve is the version that keeps the desk's return.

The decision is the owner's: `python -m ai_desk journal decide 661549dd --status rejected|accepted "<evidence>"`.
