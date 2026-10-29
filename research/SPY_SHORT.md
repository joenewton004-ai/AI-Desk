# What if the desk shorted SPY?

_October 2026. Code: `research/spy_short.py`. Tables: [`output/spy_short.md`](output/spy_short.md). Daily bars to
2026-10-28 (SPY from 1993). Research, not advice._

## Set-up (fixed before running)

**Shorting starts behind.**
- SPY rose about 10% a year in 1993-2026.
- A short pays the dividends (the adjusted prices include them) and a borrow fee (0.5% a year assumed).
- Costs are 0.01% each way. A short rule has to make money outright, not just beat holding.

**Three uses were tested:**
1. **Short swing trades:** the mirror images of the dip rules that work long (`SWING_ETF.md`), held at most 5 days.
   - Pass: positive in 1993-2009 and 2010-2026 with t >= 2, and on QQQ/IWM/DIA too.
2. **Whole strategies on SPY:** the dip rule with and without the best short, and "long above the 200-day, short
   below" vs "long above, cash below". Cash and short collateral earn T-bills.
3. **A hedge:** the overnight sleeve (as live) with an SPY short against it each night. The hedge is sized on
   2014-2019 and applied unchanged in 2020-2026.

## 1. Short swing trades: none pass

| short rule | shorts a year | win rate | avg per short | t | 1993-2009 / 2010-2026 | QQQ+IWM+DIA |
|---|---|---|---|---|---|---|
| **rally below the 200-day** (RSI(2) > 90) | 2.6 | 64% | **+0.42%** | 1.8 | +0.54% / +0.23% | +0.39% / +0.42% |
| rally, any time (RSI(2) > 90) | 17.8 | 51% | -0.06% | -1.0 | -0.07% / -0.05% | ~0 |
| 10-day high below the 200-day | 3.2 | 40% | -0.14% | -0.5 | +0.17% / -0.69% | flips |
| three up days below the 200-day | 2.9 | 40% | +0.12% | 0.4 | +0.23% / -0.06% | flips |
| tweezer top | 7.5 | 42% | +0.03% | 0.3 | +0.06% / +0.00% | flips |

- **Shorting rallies in a rising market loses.** Rallies above the 200-day keep going: that's the trend the dip rule
  profits from.
- **The near miss:** shorting a sharp rally while SPY is already below its 200-day.
  - It's positive in both halves and on the other ETFs, but it fires only about 2.6 times a year and misses the bar
    (t 1.8).
  - It earned half as much after 2010.

## 2. Whole strategies on SPY

| strategy | 1993-2026 | 1993-2009 | 2010-2026 | worst drop | time long / short |
|---|---|---|---|---|---|
| buy and hold | 10.9%/yr, Sharpe 0.52 | 7.5%, 0.29 | 14.1%, 0.80 | -55% | 100% / 0% |
| dips, long only | 6.4%, 0.66 | 8.5%, 0.83 | 4.5%, 0.50 | -11% | 10% / 0% |
| dips + short rallies below the 200-day | 7.5%, 0.71 | 10.3%, 0.90 | 4.9%, 0.52 | -11% | 10% / 3% |
| above the 200-day long, below cash | 8.9%, 0.55 | 8.6%, 0.44 | 9.2%, 0.67 | -24% | 77% / 0% |
| above the 200-day long, below **short** | 4.2%, 0.18 | 5.8%, 0.21 | 2.7%, 0.16 | -47% | 77% / 23% |

- **Adding the short to the dip rule helps a little:** +1.1% a year and Sharpe 0.66 → 0.71, but only 0.50 → 0.52
  since 2010. It's a short that fires twice a year, from a rule that missed its own test.
- **Shorting below the 200-day instead of holding cash is clearly worse.** It halves the return, cuts the Sharpe to
  0.18 and doubles the worst drop (-47% vs -24%).
  - Bear markets have the sharpest rallies (2009, 2020, 2022), and they hit a short hard.
  - The cash version (the "green line", `GREEN_LINE.md`) is the sensible one.

## 3. Hedging the overnight sleeve: it removes most of the return

| version | 2014-2026 | 2014-2019 | 2020-2026 | worst drop |
|---|---|---|---|---|
| overnight sleeve (as live) | 26.1%/yr, Sharpe 1.54 | 13.6%, 1.43 | 37.9%, 1.71 | -15% |
| + an SPY short each night (1.21x) | 8.8%, 0.66 | -1.0%, -0.37 | 17.9%, 1.07 | -25% |

- **This is the useful finding.** The sleeve's nights move about 1.2x SPY's night. Hedged, the Sharpe falls from 1.54
  to 0.66 and 2014-2019 turns negative.
- **So most of the overnight sleeve's return is the stock market's own overnight premium,** taken with a basket of
  strong stocks, not a stock-picking edge that survives on its own.
- **That isn't a reason to stop it.** The overnight premium is well documented (Lou, Polk & Skouras), and the sleeve
  is designed to collect it.
- **It does mean** the sleeve behaves like holding the market at night, with the market's risks: its worst nights are
  market-wide gaps (`OVERNIGHT_SAFETY.md`).

## Verdict

- **Don't short SPY.** No short rule passes. Shorting below the 200-day loses badly against holding cash. The one
  near miss adds +0.02 to the dip rule's Sharpe since 2010.
- **Don't hedge the overnight sleeve.** The hedge takes away the premium the sleeve exists to earn.
- **Practical point:** shorting on Alpaca needs a margin account; the desk's executor has shorting switched off
  (`allow_short=False`).
