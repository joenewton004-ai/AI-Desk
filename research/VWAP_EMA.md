# EMA9/VWAP crossover and "Trend + Momentum + Confirmation": tested

_October 2026. Code: `research/vwap_ema.py`. Tables: [`output/vwap_ema.md`](output/vwap_ema.md). Yahoo
regular-hours bars, the 100-150 largest US companies. Costs 0.03% each way. Research, not advice._

## The two strategies, as fixed rules

**A. EMA9 / VWAP crossover:** go long when the 9-bar EMA crosses above the day's VWAP; exit when it
crosses back below, or at the close. Shorts are the mirror image.

**B. Trend + Momentum + Confirmation** (long only). Buy at the next bar's open when all four are true:
- **Trend:** 20 EMA above the 50 EMA.
- **Institutional reference:** price above VWAP.
- **Volume:** at least 1.5× the average of the last 20 bars.
- **Breakout:** the close breaks the previous day's high or the opening-range high (first 15
  minutes), for the first time that day.

Stop: the recent swing low or the 20 EMA, whichever is lower. Target 2R (variant 3R); otherwise out
at the close. Also tested:
- the "first pullback" entry (a limit order back at the broken level);
- the strategy without the volume rule;
- a control that enters on random bars on the same days, with the same stop and target.

VWAP only exists intraday, so it needs intraday bars, and Yahoo keeps only 60 days of 5-minute
bars, 30 days of 1-minute bars and 3 years of hourly bars (where VWAP and EMAs are coarse).

## Results: per trade, after 0.03% each way

| | 5-min (60 days) | 1-min (30 days) | Hourly (3 years) |
|---|---|---|---|
| **A: EMA9/VWAP crossover** | −0.067% (14,996 trades, t −10.5) | −0.058% | −0.078% (t −12.5) |
| A, long only | −0.066% | −0.058% | −0.060% |
| **B: Trend + Momentum + Confirmation** | −0.107% (715 trades) | −0.137% | −0.069% (1,014 trades) |
| B, 3R target | −0.097% | −0.131% | −0.068% |
| B, without the volume rule | −0.092% | −0.084% | −0.071% |
| B, first-pullback entry | −0.150% | −0.101% | −0.123% |
| **B control: random bars, same days** | **+0.039%** | −0.025% | **+0.137%** |

**What it means:**
- **A is a coin flip that pays costs twice a day.** Before costs it averages about zero (−0.007%
  to +0.002% per trade). With about 2 trades per stock per day, the spread turns that into a steady
  loss. The crossover follows price; it doesn't predict it.
- **B loses even before costs** (−0.009% to −0.077% per trade), and every variant loses after costs.
  - The 3R target, dropping the volume rule and the pullback entry don't rescue it.
  - The hourly version (3 years) is negative in 7 of 13 quarters, with no pattern.
- **The control is the key result.** Random entry times *on the same days* did better than the
  rule's own entries, clearly so on hourly bars (+0.137% vs −0.069%). On the days when the breakout
  happens, the gain mostly comes before the rule confirms it. By the time all four conditions line
  up (trend, VWAP, volume, breakout), the move has largely happened, and the rule buys near the
  short-term top.
- **The volume rule doesn't help.** It cuts trades by two-thirds to 94% but leaves the result
  about the same.

## Verdict

**Neither has an edge.** Both are recorded in the register as research-only (`vwap_ema`). The
pattern matches every other intraday test so far (ICT, opening range breakout): indicators built
from price itself (EMAs, VWAP, breakouts) describe what has already happened. On large caps that's
priced in within minutes, and the spread is paid on every trade.

**One caveat:** the 5- and 1-minute samples are short (about 30-60 days). A proper verdict would
use years of minute data, from Alpaca once `data.alpaca.markets` is allowed in the environment's
network settings. But the hourly test covers 3 years, and nothing in the short samples points the
other way.
