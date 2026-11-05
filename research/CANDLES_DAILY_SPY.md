# Daily candlestick patterns on SPY, 1993-2026

_October 2026. Code: `research/candles_daily_spy.py`. Tables: [`output/candles_daily_spy.md`](output/candles_daily_spy.md).
Daily bars (Yahoo, adjusted) to 2026-10-28. Research, not advice._

## What was already known here

- **5-minute candles on SPY and NVDA (2016-2026):** no edge (`CANDLES.md`).
- **Hammer, bullish engulfing and reversal close as filters on RSI dips:** they add nothing (`CANDLE_RSI.md`).

This test covers what was left: the full textbook set on daily SPY bars, standing alone, bullish and bearish, from 1993.

## Set-up (fixed before running)

- **23 patterns** with standard definitions (`patterns()` in the script):
  - 10 bullish: hammer, inverted hammer, engulfing, piercing line, morning star, three white soldiers, harami,
    dragonfly doji, marubozu, tweezer bottom
  - 10 bearish: shooting star, hanging man, engulfing, dark cloud cover, evening star, three black crows, harami,
    gravestone doji, marubozu, tweezer top
  - 3 neutral: doji, inside day, outside day
- **Context, as the textbooks require:** bullish reversals only after a down week, bearish ones after an up week.
- **Measured:** from the next open over 1 and 5 trading days, against SPY's normal drift over as many days.
- **To pass:** moves the predicted way in 1993-2009 AND 2010-2026 with |t| >= 2, and the same way on QQQ, IWM and DIA.
- **Luck allowance:** 40 directional tests, so about 2 would pass by chance.

## Results: 1 of 40 passes

| pattern | per year | SPY win rate | SPY over 5 days vs normal | t | 1993-2009 / 2010-2026 | QQQ+IWM+DIA |
|---|---|---|---|---|---|---|
| **tweezer top** (bearish) | 7 | 57% | **-0.32%** | **-2.7** | -0.30% / -0.34% | -0.36% / -0.24% |
| bullish harami | 4.4 | 70% | +0.41% | 1.8 | +0.27% / +0.63% | +0.08% / +0.78% |
| bearish harami | 4.3 | 44% | -0.56% | -3.0 | -0.48% / -0.67% | **+0.05%** / -0.28% (fails) |
| hammer | 2.3 | 65% | -0.11% | -0.3 | +0.36% / -0.72% | flips |
| bullish engulfing | 2.3 | 55% | +0.17% | 0.6 | +0.61% / -0.38% | flips |
| morning star | 0.3 | 30% | -2.16% | -2.0 | wrong way (10 cases) | wrong way |
| bearish engulfing | 4.1 | 70% | +0.29% | 1.7 | wrong way | - |
| three black crows | 1.2 | 69% | +0.38% | 1.3 | wrong way | - |
| doji / inside day / outside day | 17-18 | 58-62% | -0.11% to +0.02% | -1.1 to 0.2 | nothing | nothing |

- **The famous patterns don't work on SPY.**
  - Hammers, engulfing patterns, morning and evening stars, three soldiers or crows, dojis: either nothing, or they
    flip between the two halves.
  - Several bearish patterns are followed by *rises* (bearish engulfing +0.29%, three black crows +0.38% over a week).
    That fits what the swing test found: SPY tends to bounce after a down day, whatever the candle looks like
    (`SWING_ETF.md`).
- **The one pass: a tweezer top.** After an up week, a green day and then a red day with the same high (within 0.1%).
  - SPY then lags its normal drift by 0.32% over the next 5 days (t -2.7), in both halves.
  - It also lags on QQQ (-0.46%, t -1.9) and IWM (-0.46%, t -1.9), but not on DIA (-0.02%).
  - The matching high is what matters. The same days without it show nothing (+0.03%), so it isn't just the up-week
    reversal.
- **It's not worth trading.**
  - It's one pass in 40 tests, about what luck delivers.
  - It's small: -0.32% a week is a seventh of SPY's normal weekly swing.
  - It's bearish, and the desk is long only and doesn't hold SPY, so it can't be used directly.
  - At most it's a "stay out of SPY next week" flag, to recheck on new data before trusting it.

## Verdict

Daily candlestick patterns carry no reliable signal on SPY, the same as 5-minute ones. The one pattern-like
effect that survives (tweezer top) is small, bearish and within what luck delivers across 40 tests. The pattern that
does work on SPY at this horizon is simpler and needs no candles: buy a short dip (RSI(2) < 10) while SPY is above its
200-day average (`SWING_ETF.md`). Recorded as research-only (`candles_daily_spy`).
