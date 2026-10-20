# Would limit orders cut our trading costs?

_October 2026. Code: `research/limit_orders.py`. Tables: [`output/limit_orders.md`](output/limit_orders.md).
Educational research, not financial advice._

## Short answer

**No, not on average.** We simulated every stock-day for our 34 holdings over two years
(16,932 orders each way). Limit orders did not beat a plain market order at the open.
They save money only on the days the stock moves our way. On the days they miss, the
stock has usually run away, and buying later costs 1.1-1.8% more. Those misses cancel
the savings.

The one useful version is a **wide safety cap**: a limit 1-2% beyond the last close. It
costs nothing on average (−0.4 to +0.9bps) and fills 94-98% of the time. It also means
we never chase a stock that jumps sharply overnight (for example on earnings): the order
waits and is re-planned the next day.

## Buy orders (sells mirror these closely)

| Style | Fill rate | Average cost vs the open | When it misses |
|---|---|---|---|
| Market at the open | 100% | 0 (baseline) | - |
| Limit at last close +0% | 80% | +4.9bps (worse) | +126bps |
| Limit at last close +0.5% | 90% | +2.1bps | +142bps |
| **Limit at last close +1%** | 94% | +0.9bps | +146bps |
| **Limit at last close +2%** | 98% | −0.4bps | +133bps |
| Passive limit 0.25% below the open | 85% | +4.0bps | +166bps |
| Passive limit 1% below the open | 51% | +2.5bps | +111bps |

(1bp = 0.01%. Positive = we paid more. "When it misses" is the cost of buying later instead.)

## What our 10.9bps "slippage" really was

Our first 34 market orders filled at 9:32-9:33am, two to three minutes after the open.
Against the official opening price they ranged from −49 to +151bps (median +9, and 15 of the
34 were *below* the open), with a standard error of about 9bps. That is mostly the
price moving in the first minutes, plus Alpaca's paper-trading fill simulation. One
morning can't show a cost problem, and no order type fixes noise.

## Recommendation

1. **Keep market orders as the default.** There's no evidence limits are cheaper.
2. **Optionally switch on a 2% safety cap:** `portfolio run --execute --limit-cap 0.02`.
   It's free insurance against chasing a big gap. An order that doesn't fill expires at the
   close and is re-planned on the next run.
3. **Keep measuring.** Judge slippage after 20+ fills over several different days, not one
   morning. The scorecard does this, and each fill now records its order type.

Limits of this test: daily bars don't show the order of trades within a day or our place in
the queue. To be conservative, a limit counts as filled only if the price traded 2bps
through it. That still slightly flatters limit orders.
