# Day trading SPY or commodity ETFs: are there better patterns than the NVIDIA opening buy?

_October 2026. Code: `research/intraday_etf.py`. Tables: [`output/intraday_etf.md`](output/intraday_etf.md). Alpaca SIP
minute bars, 2016-01-04 to 2026-10-26, ~2,715 full sessions per ETF. Research, not advice._

## The question

The owner asked for reliable day-trading patterns on SPY or commodities that beat the NVIDIA opening buy (49% wins,
+0.125% a trade, but most likely a hindsight effect: it doesn't work on other large stocks).

**Already ruled out on SPY:** candle patterns, ICT, TJR, the opening-range breakout, EMA9/VWAP crossovers
(`CANDLES.md`, `ICT.md`, `TJR.md`, `VWAP_EMA.md`).

**Tested here:** the patterns with the best published evidence, plus the common folklore ones. All rules were fixed
before running, on two families: index ETFs (SPY, QQQ, IWM, DIA) and commodity ETFs (GLD, SLV, USO, UNG).

## The rules

| rule | what it does | where it comes from |
|---|---|---|
| intraday momentum, 10am | the move from yesterday's close to 10:00 decides the last half hour (15:30 -> 16:00) | Gao, Han, Li & Zhou, *J. Financial Economics* 2018 |
| late-day momentum | the move to 15:30 decides the last half hour | Baltussen, Da & Soebhag, *JFE* 2021 (dealers' hedging) |
| gap fade | a 0.2-1% gap at the open is traded back to yesterday's close (out at 12:00 at the latest) | "gaps get filled" |
| first-hour fade | a first hour that moves 0.5%+ is faded until the close | mean reversion |
| VWAP snap-back | a stretch of a quarter of the usual daily range away from VWAP is traded back to VWAP | mean reversion |
| opening-range breakout | the NVIDIA rule: long only, and long + short | the desk's own lead |
| open -> close, long or short | the time-of-day baseline; gold is said to fall in New York hours | gold desk folklore |

- **Costs each way:** 0.01% (SPY, QQQ, IWM, DIA, GLD), 0.02% (SLV), 0.03% (USO), 0.05% (UNG).
- **To pass:** positive on SPY or GLD in both 2016-20 and 2021-26 with t >= 2, AND positive on the rest of the family
  in both halves.

## Results: nothing passes (18 of 18 fail)

| rule (lead ETF) | win rate | avg before costs | avg after costs | t | Sharpe |
|---|---|---|---|---|---|
| intraday momentum 10am (SPY) | 43% | -0.002% | -0.022% | -3.8 | -1.16 |
| late-day momentum (SPY) | 44% | +0.005% | -0.015% | -2.5 | -0.76 |
| gap fade (SPY) | 52% | -0.008% | -0.028% | -2.5 | -0.75 |
| first-hour fade (SPY) | 44% | -0.032% | -0.052% | -0.9 | -0.27 |
| VWAP snap-back (SPY) | **63%** | -0.013% | -0.033% | -4.1 | -1.28 |
| opening-range breakout, long (SPY) | 38% | +0.030% | +0.010% | 0.9 | 0.27 |
| opening-range breakout, long (QQQ) | 43% | +0.046% | +0.026% | 1.6 | 0.50 |
| VWAP snap-back (GLD) | **64%** | +0.003% | -0.017% | -2.9 | -0.89 |
| gold short open -> close (GLD) | 48% | +0.005% | -0.015% | -1.3 | -0.39 |
| gap fade (UNG) | **68%** | +0.040% | -0.060% | -1.8 | -0.55 |

## What it means

1. **These markets are efficient within the day.**
   - Before costs, every rule on every ETF averages within ±0.05% a trade of zero.
   - The two published momentum effects are no longer there after costs, or before them, in 2016-2026. Both papers
     came out in this period, and documented effects often shrink once people trade them.
2. **High win rates are easy, and worthless here.**
   - Fading stretches (VWAP snap-back, gap fades) wins 60-68% of the time on every ETF, and loses money on almost
     all of them.
   - The winners are many small moves back; the losers are the days the stretch keeps going.
   - This is the trap behind "high win rate" systems.
3. **Commodities are worse, not better.** Their ETFs cost more to trade (SLV, USO, UNG spreads), and gold's "falls in
   New York hours" is +0.005% a day before costs: nothing.
4. **The nearest miss is the same opening-range breakout, long only, on the index ETFs.**
   - It made +0.01% to +0.03% a trade after costs, positive on all four in both halves.
   - But it's weak: t 0.9 on SPY, 1.6 on QQQ, Sharpe 0.3-0.5, and it wins only 38-43% of the time.
   - It's less than the NVIDIA version, without the hindsight problem. Not worth trading at real costs; a candidate
     only if costs were near zero.

**Verdict: no day-trading pattern on SPY, its sister ETFs or commodity ETFs beats the NVIDIA opening buy on the
evidence.** The desk's best intraday-to-overnight result remains the overnight drift in stocks
(`OVERNIGHT.md`). That effect lives in the time between sessions, not inside them.

## Limits

- **Futures weren't tested.** Gold, crude and S&P futures trade nearly 24 hours, and only ~60 days of their bars are
  reachable here (`TJR.md`).
- **Ten years, eight ETFs.** A longer history might show effects that were stronger before 2016 (the papers' samples
  start in the 1990s).
- **Prices may be generous.** Fills at the minute's close assume we get that price; real fills on stops and fast moves
  are usually worse.
