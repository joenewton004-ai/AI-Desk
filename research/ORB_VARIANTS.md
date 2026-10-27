# Can the NVIDIA opening buy be made more profitable?

_October 2026. Code: `research/orb_variants.py`. Tables: [`output/orb_variants.md`](output/orb_variants.md). 5-minute
Alpaca bars, 2016-2026, 0.02% costs each way. Research, not advice._

**How the tweaks were judged:** a tweak only counts if it beats the base rule on NVIDIA **and** on 11 other stocks
pooled (QQQ plus the 10 largest US companies of 2016, picked without hindsight), in **both** 2016-20 and 2021-26.
Tuning to NVIDIA alone would just re-fit its past.

| Tweak (each has a reason) | NVDA net per trade | NVDA 2016-20 / 2021-26 | Other 11 pooled | Others 2016-20 / 2021-26 | Passes |
|---|---|---|---|---|---|
| Base (shadowed now) | +0.123% | +0.110% / +0.133% | −0.005% | +0.004% / −0.013% | |
| Only with the 50-day trend | +0.088% | +0.089% / +0.087% | −0.018% | | no |
| **Only on gap-up days** | **+0.155%** | +0.116% / +0.190% | **+0.014%** | +0.036% / −0.006% | **yes** |
| Only on narrow-range days | +0.111% | +0.122% / +0.102% | +0.006% | | no |
| Only breakouts before 11:00 | +0.123% | | −0.007% | | no |
| Stop at mid-range | +0.052% | | −0.046% | | no |
| Take profit at 2R | +0.103% | | −0.005% | | no |
| 30-minute range | +0.120% | | −0.007% | | no |

- **Only one tweak passes: trading on days NVIDIA opens above the previous close.** It lifts NVIDIA from +0.12% to
  +0.16% a trade, and the other stocks from about −0.01% to +0.01%.
  - That's still roughly zero for the other stocks, so the edge remains NVIDIA's, which is the hindsight problem.
  - With seven tweaks tried, one passing could be chance.
- **Tighter stops and profit targets make it worse.** Breakout gains come from the few days that run to the close.
- **The last 59 days in the shadow log:** the base rule averaged −0.18% a trade (36 trades). Gap-up days averaged
  −0.24% (24 trades). That's too few to judge either way, but it's no confirmation.

## Verdict

There's no tweak that clearly makes it profitable beyond NVIDIA's own history. The gap-up filter is now recorded in
the shadow log next to the base rule (`gap_up` column; dashboard Scorecard tab). The live numbers will show within a
few months whether either version is real. Trading it would need an amendment.
