# A leveraged S&P 500 fund on SPY signals, with strict risk rules

_October 2026. Code: `research/leveraged.py`. Tables: [`output/leveraged.md`](output/leveraged.md). Daily, 1994-2026.
Research, not advice._

## The setup

- **Every decision is made at SPY's close and fills at the next open.**
- **The funds are simulated** from SPY's daily returns: 2× like SSO, 3× like UPRO, with daily reset, their fees
  (about 0.9% a year) and the cost of borrowing for the leverage (T-bills + 0.3%).
- **The simulation matches the real funds** since 2009:
  - SSO 25.0%/yr real vs 25.3% simulated;
  - UPRO 32.7% vs 33.8%;
  - worst drops within 2 points.

  So the 1994-2009 years, before the funds existed, are a fair estimate.

Risk rules tested, alone and together ("strict"):
- **Trend:** only hold while SPY is above its 200-day average (1% band against whipsaws).
- **Volatility cap:** leverage = 25% ÷ SPY's recent volatility, at most 2× or 3×.
- **VIX filter:** out while the VIX closes above 30.
- **10% stop:** sell if the position is down 10% from entry, and wait for SPY to make a new 20-day high
  above its 200-day average.

## Results

| | Return/yr | Sharpe | Worst drop | Worst year | 2010-2026 Sharpe |
|---|---|---|---|---|---|
| SPY buy and hold | 10.8% | 0.51 | −55% | −37% | **0.77** |
| 3× buy and hold | 14.9% | 0.49 | **−98%** | −85% | 0.75 |
| SPY above its 200-day, 1× | 9.3% | **0.58** | −25% | −13% | 0.61 |
| 3×, trend only | **17.4%** | 0.55 | −61% | −38% | 0.58 |
| 3×, trend + vol cap | 13.7% | 0.56 | −37% | −24% | 0.61 |
| **2× strict** | 11.6% | 0.53 | **−31%** | −18% | 0.61 |
| **3× strict** | 12.7% | 0.53 | −37% | −24% | 0.59 |

**In the crashes:**

| | 2000-02 | 2008 | 2020 | 2022 |
|---|---|---|---|---|
| SPY | −48% | −55% | −34% | −25% |
| 3× buy and hold | −93% | −95% | −75% | −64% |
| 3× strict | −20% | −18% | −21% | −16% |

## What it means

- **The strict rules do their job as risk management.** 3× strict made a little more than SPY (12.7% vs
  10.8%) with about two-thirds of its worst drop (−37% vs −55%), and never lost more than 21% in a crash.
  Without the rules, 3× buy and hold lost 98% at its worst; that's how leveraged funds get wiped out.
- **They don't add an edge.** Every version's Sharpe is about 0.53-0.58, only a little above SPY's 0.51.
  Leverage multiplies both return and risk, and the rules mostly trade return for safety.
- **In the last 16 years, plain SPY beat all of them on risk-adjusted terms** (Sharpe 0.77 vs 0.58-0.61).
  In a market that kept recovering fast, every exit missed part of the rebound.
- **The vol cap is the most useful single rule.** It's the one that most cuts the worst drop (−61% to −37%
  for 3×).
- **The 10% stop alone hurts:** it sold near bottoms, made the worst drop deeper (−69%) and lowered the
  return.
- **Tuning doesn't help.** Choosing the average length each year from the past 10 years did worse out of
  sample (12.2%, Sharpe 0.46) than just keeping the 200-day (14.8%, 0.52).
- **Leveraged funds also carry real-world risks this can't show:**
  - a huge gap at the open moves 3× before any rule can act;
  - the funds' swap counterparties;
  - a fund could close.

## Verdict

**A defensible way to get more return than SPY with a smaller worst drop. It's not an edge, and recent
years favoured plain buy and hold.** If you want leverage on the S&P 500, the strict 2× version
(11.6%/yr, worst drop −31%) is the most controlled. It would replace part of the desk's equity
exposure, not add to it.

Recorded in the register as research-only (`leveraged_spy`). Any live use would go through an amendment.
