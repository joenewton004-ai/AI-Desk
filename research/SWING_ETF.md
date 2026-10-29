# Swing trades up to a week on SPY or commodity ETFs

_October 2026. Code: `research/swing_etf.py`. Tables: [`output/swing_etf.md`](output/swing_etf.md). Daily bars (Yahoo,
adjusted) to 2026-10-28: SPY from 1993, QQQ/IWM/DIA from 1998-2000, GLD/SLV/USO/UNG from 2004-2007. Follows
`INTRADAY_ETF.md` (day trades: nothing works). Research, not advice._

## Set-up (fixed before running)

- **Trades:** each signal is decided at a close and bought at the next open. Held at most 5 trading days, one
  position at a time, long only.
- **Costs each way:** 0.01% (SPY family, GLD), 0.02% (SLV), 0.03% (USO), 0.05% (UNG).
- **The yardstick is holding the ETF.** SPY rises over time, so any long rule "makes money". Each trade is therefore
  measured against holding the ETF for the same number of days ("excess").
- **To pass:** the lead ETF (SPY / GLD) beats holding in both halves (1993-2009 / 2010-2026; GLD 2004-15 / 2016-26)
  with t >= 2, and the rest of its family does too.
- **Ten rules:**
  - RSI(2) dip (Connors)
  - RSI(14) dip (the desk's live rule)
  - three down days
  - weak close (IBS)
  - 10-day low
  - 20-day breakout
  - down week, up week
  - turn of the month
  - gap down

## Results

**Index ETFs: three rules pass, all versions of one idea - buy a short dip while the market is above its 200-day
average.**

| rule (SPY) | trades a year | days held | win rate | avg per trade | vs holding | t | 1993-2009 / 2010-2026 |
|---|---|---|---|---|---|---|---|
| **RSI(2) < 10, above the 200-day** | 8 | 3.0 | **73%** | **+0.51%** | +0.36% | 3.4 | +0.56% / +0.18% |
| **10-day low, above the 200-day** | 10 | 3.0 | 70% | +0.40% | +0.25% | 2.9 | +0.30% / +0.22% |
| RSI(14) < 30, above the 200-day | ~0.5 | 3.4 | 88% | +1.68% | +1.52% | 2.3 | passes, but only 16 trades in 30 years |
| three down days | 12 | 5 | 61% | +0.46% | +0.22% | 1.9 | fails (t < 2) |
| turn of the month | 12 | 7 | 65% | +0.53% | +0.19% | 1.5 | fails (t < 2) |
| down week (buy) | 25 | 5 | 61% | +0.36% | +0.12% | 1.0 | fails |
| 20-day breakout | 14 | 5 | 60% | +0.16% | -0.08% | -1.3 | worse than holding |
| up week (buy) | 27 | 5 | 55% | -0.00% | -0.24% | -2.9 | worse than holding |

**As a strategy (SPY, in the market only during trades, T-bills otherwise):**
- **RSI(2) dip:** 6.6% a year, Sharpe 0.69, worst drop -11%. Buy and hold: 10.9%, 0.52, -55%.
- **10-day low:** 6.5% a year, Sharpe 0.61, worst drop -11%.
- **The catch:** both are in the market only 10-12% of the time. Their return per year in the market is high, but
  the account sits in T-bills 90% of the time.

**Commodity ETFs: nothing passes.** Every rule's excess is within ±0.1% and flips sign between the halves. Gold,
silver, oil and gas don't snap back after short dips the way stock indexes do.

## How sturdy is the RSI(2) dip? (SPY)

| variant | trades | win rate | vs holding | t | 1993-2009 / 2010-2026 | since 2009 (after Connors published) |
|---|---|---|---|---|---|---|
| threshold 5 | 130 | 72% | +0.50% | 2.9 | +0.92% / +0.23% | +0.29% (t 1.5) |
| **threshold 10 (the rule)** | 271 | 73% | +0.36% | 3.4 | +0.56% / +0.18% | +0.24% (t 1.8) |
| threshold 15 | 406 | 71% | +0.25% | 3.3 | +0.33% / +0.18% | +0.21% (t 2.1) |
| threshold 20 | 501 | 70% | +0.15% | 2.2 | +0.24% / +0.07% | +0.11% (t 1.2) |
| no 200-day filter | 420 | 70% | +0.35% | 3.1 | +0.46% / +0.22% | +0.20% (t 1.3) |
| 3x costs | 271 | 72% | +0.32% | 3.0 | +0.52% / +0.14% | +0.20% (t 1.5) |
| hold up to 10 days | 266 | 75% | +0.39% | 3.5 | +0.66% / +0.17% | +0.23% (t 1.5) |

- **It's not a fluke of one setting.** Every threshold, a longer hold and triple costs all work.
- **It has faded.** The edge over holding is about a third of its pre-2010 size since the strategy became widely known
  (Connors & Alvarez, *Short Term Trading Strategies That Work*, 2008). Since 2009 it is still positive but only
  borderline significant (t 1.5-2.1).
- **It works best on SPY.** It's weaker on QQQ and DIA (t 0.9) and passes on IWM (t 2.2).

## Versus the NVIDIA opening buy

| | NVIDIA opening buy | SPY RSI(2) dip |
|---|---|---|
| win rate | 49% | **73%** |
| average per trade (after costs) | +0.125% | **+0.51%** |
| trades a year | ~170 | ~8 |
| holds on other instruments? | no (about 0 on 11 others) | yes on IWM, weaker on QQQ/DIA |
| hindsight risk | high (picked the stock that rose 100x) | low (SPY, a rule published in 2008) |

**Yes: a one-week horizon finds what day trading couldn't.**
- The SPY RSI(2) dip wins nearly three trades in four and makes about four times as much per trade as the NVIDIA rule.
- It holds on other index ETFs, so it isn't hindsight.
- Its size since 2010 is modest, and it trades rarely: about 8 times a year, 10% of the time in the market.

## What it would mean for the desk (not proposed yet)

- **It's the same idea the desk already trades live.** The RSI(14) dip on top-100 stocks (`CANDLE_RSI.md`) is this
  rule on single stocks, where it earns more (+1.0-1.2% a dip).
- **The spare cash is already in use.** The overnight sleeve takes every spare dollar each night. An SPY dip sleeve
  would have to share cash with it, so a desk test (like `DESK_RSI.md`) is needed before an amendment.
- **Survivors:** not an issue for ETFs. Yahoo's adjusted prices include dividends, which flatters both the rule and
  holding equally.
