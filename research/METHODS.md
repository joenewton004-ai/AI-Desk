# New methods: moving-average crossover and duopoly pairs

_October 2026. Tables come from `python research/methods.py` (full output:
[`output/methods.md`](output/methods.md)). Yahoo prices adjusted for splits
and dividends, 3bps costs, cash earning the T-bill rate, and a 0.5%/yr
borrow fee on shorts. Educational research, not financial advice._

## Summary

| method | verdict | why |
|---|---|---|
| **Moving-average crossover (50/200)** | ✅ Works, but adds nothing new | Same crash insurance as 12-month momentum, with almost identical results. It's a second way of measuring the same trend. |
| **Duopoly pairs, long/short** | ⚠️ Barely an edge | About 2.6%/yr against ~1.6%/yr T-bills. Nearly uncorrelated with stocks (0.08), but the edge is thin and costs cut it in half. |
| **Duopoly pairs, long-only** | ❌ No edge | It just holds less stock: a lower return than owning the same 12 stocks, with the same risk-adjusted return. |

## 1. Moving-average crossover

The rule: hold the market while its 50-day average is above its 200-day
average (the "golden cross"); go to cash below it.

SPY, 1994-2026:

| | CAGR | Sharpe | worst drawdown | trades |
|---|---|---|---|---|
| Buy & hold | 10.8% | 0.51 | −55% | 1 |
| **50/200 crossover** | 10.2% | 0.59 | −34% | 31 |
| Price vs 200-day (`trend`) | 9.3% | 0.59 | −25% | 97 |
| 12-month momentum | 10.6% | 0.60 | −34% | 23 |

- **Robust settings:** every fast/slow combination tested scores a Sharpe of
  0.50-0.63. That's a plateau, not a lucky peak.
- **Walk-forward (tuned on 8 years, traded blind):** Sharpe 0.50 vs 0.45 for
  buy & hold, a worst drop of −32% vs −55%, but a lower return (7.5% vs
  8.9%/yr).
- **Other markets:** it helped on QQQ (11.3% vs 8.1%/yr, worst drop −37% vs
  −83%) but failed badly on small caps (IWM: 2.5% vs 8.2%/yr). On gold and
  bonds it cut drawdowns but also returns.

**Verdict:** a genuine but familiar edge, the same "sit out long bear
markets" insurance as momentum. On SPY the two give nearly identical
results, so running both doesn't diversify anything. Use it as an
alternative switch for the index sleeve if you prefer it; QQQ is where it
looked best.

## 2. Duopoly pairs trading

The idea: two companies that share a market (Visa/Mastercard, Coke/Pepsi,
Home Depot/Lowe's, UPS/FedEx, Moody's/S&P Global, Booking/Expedia) are
driven by the same forces. When their price gap stretches more than 2
standard deviations from its 60-day norm, short the leader, buy the laggard,
and wait for the gap to close.

2011-2026:

| | CAGR | volatility | Sharpe | worst drawdown | correlation with SPY |
|---|---|---|---|---|---|
| **Pairs long/short** | 2.6% | 3.1% | 0.33 | −5.7% | 0.08 |
| Pairs long-only | 11.1% | 11.1% | 0.86 | −24% | 0.73 |
| Buy & hold, same 12 stocks | 17.6% | 18.7% | 0.88 | −37% | n/a |
| SPY | 14.0% | 17.0% | 0.76 | −34% | 1.00 |

**Long/short:**
- It is genuinely market-neutral: correlation with the S&P 500 is 0.08, and
  the worst drop was only 6%.
- **But the return is mostly cash interest.** On average 55% of the account
  sits in cash earning T-bills (about 1.6%/yr over this period). The trading
  itself added roughly 1%/yr.
- **Fragile:** tripling costs halves the Sharpe (0.33 → 0.15). It's
  sensitive to settings (0.23-0.49 across the grid), and it was weaker in
  2019-2026 (Sharpe 0.25).
- **Pairs that drift apart lose money.** UPS/FedEx lost (−0.2%/yr, with a
  −33% drawdown) because UPS steadily fell behind FedEx, about 4%/yr. A
  "duopoly" can stop behaving like one, and then the gap keeps widening
  instead of closing. KO/PEP was also negative on a risk-adjusted basis.
- **Hindsight:** these pairs were chosen because they're duopolies *today*.

**Long-only:** it doesn't add an edge. It holds about 45% of the account in
the 12 stocks on average, so it earns less than owning them (11.1% vs
17.6%) with the same Sharpe. The "timing" adds nothing beyond holding less.

**Verdict:** as built, pairs trading isn't worth real capital. A small
long/short sleeve could be justified *only* as a diversifier, since it barely
moves with the market. That needs a stronger version first:
- hedge ratios estimated by regression instead of 1:1 dollars
- a check that each pair actually reverts (a cointegration test) before trading it
- a stop that retires a pair once its gap keeps widening (UPS/FedEx)

## What this changes in the thesis

Nothing structural. The 50/50 structure in [`THESIS.md`](THESIS.md) (quality
screen + SPY with a trend switch) stays. The crossover is an acceptable
alternative switch for the index sleeve. Pairs stay in research until the
stronger version above has been tested.

## How to run them

```bash
python -m ai_desk portfolio backtest --method sma_crossover --param symbols=SPY,QQQ
python -m ai_desk portfolio backtest --method pairs --param pairs=V/MA,MCO/SPGI --split 2019-01-01
python -m ai_desk portfolio backtest --method sma_crossover:0.5 --method index_momentum:0.5
python -m ai_desk portfolio plan --method thesis                # dry run vs your Alpaca paper account
python -m ai_desk portfolio run  --method thesis --execute      # send the orders (paper only)
```
