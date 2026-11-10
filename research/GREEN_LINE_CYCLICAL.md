# Does the 200-day line repeatably help cyclical stocks and ETFs?

_November 2026. Code: `research/green_line_cyclical.py`. Tables: [`output/green_line_cyclical.md`](output/green_line_cyclical.md).
Follows `GREEN_LINE_WHY.md`, which explained after the fact why the line helped NVIDIA and Apple (cyclical businesses
whose downturns last). Research, not advice._

## The test

The idea was tested on 63 **new** names (the Mag 7 left out), grouped by sector **before** looking at any results:
- **Cyclical ETFs (10):** semis, energy, materials, industrials, consumer discretionary, banks, regional banks,
  homebuilders, transports, metals and mining.
- **Defensive ETFs (3):** staples, utilities, health care.
- **Cyclical stocks (29):** chips and hardware (Intel, AMD, Micron, Applied Materials, Lam, KLA, TI, Analog Devices,
  Cisco, HP, Western Digital, Seagate), machinery and industrials (Caterpillar, Deere, Cummins, Paccar, GE, Boeing),
  Ford, metals (Freeport, Nucor), energy (Exxon, Chevron, Schlumberger, Halliburton, Conoco), homebuilders (Lennar,
  D.R. Horton, PulteGroup).
- **Steady stocks (21):** P&G, Coca-Cola, Pepsi, J&J, Walmart, McDonald's, Colgate, Kimberly-Clark, Altria, General
  Mills, Hershey, Southern, Duke, Con Ed, AEP, Clorox, Costco, Abbott, Sysco, ADP, Paychex.

Same rule as before: hold above the 200-day average, T-bills below, switch at the next open, 0.05% a switch, prices
with dividends from 1996 (or listing) to 2026-11-09. **"Repeatable"** needed all four checks, fixed in advance:
1. The line raises the Sharpe for most cyclical stocks, in both halves of history.
2. The same for cyclical ETFs.
3. Cyclical stocks do better with the line than steady stocks do, in both halves.
4. Stocks whose revenue swings more (SEC filings) gain more from the line, beyond chance.

## Results

| group | line raised the Sharpe (all / 1st half / 2nd half) | median Sharpe change | median return/yr: hold -> line | median worst drop: hold -> line |
|---|---|---|---|---|
| Cyclical ETFs | 4 of 10 / 30% / 20% | −0.06 | 8.2% -> 4.9% | −69% -> −42% |
| Defensive ETFs | 0 of 3 | −0.34 | 8.1% -> 2.6% | −39% -> −31% |
| **Cyclical stocks** | **8 of 29** / 34% / 24% | **−0.05** | 12.9% -> 8.6% | **−86% -> −63%** |
| Steady stocks | 0 of 21 / 10% / 5% | −0.23 | 10.5% -> 4.6% | −54% -> −50% |

Where it helped: GE, Seagate, Halliburton, AMD, Micron (Sharpe up in both halves); Cisco and Cummins (one half
only). Where it hurt: Chevron, Paccar, Deere, D.R. Horton, Nucor, Analog Devices, Texas Instruments, Exxon.
Revenue swings vs the line's effect: rank correlation +0.25 (p = 0.09) - a lean, not a finding.

**Verdict: not repeatable.** Only check 3 passed. Checks 1, 2 and 4 failed.

## What it means

- **Half the story holds: the line hurts cyclicals much less than steady stocks.** On steady companies it's a clear
  loss: the Sharpe fell for all 21, and it nearly halved their return. Their dips are shallow and recover, so every
  exit is a false alarm. For Walmart, Colgate and Kimberly-Clark the line's whipsaws even made the worst drop
  *deeper* than holding (e.g. Walmart −37% -> −78% during its flat 2000-2011 decade).
- **The other half doesn't: it doesn't make cyclicals better.** Most cyclical stocks and ETFs ended with a slightly
  lower Sharpe. What the line reliably does on them is cut the worst drop (−86% to −63% for the median stock),
  for about 4 points of return a year.
- **NVIDIA and Apple were the lucky end of a wide spread,** not a rule. Even among chip stocks it's mixed: AMD and
  Micron gained, KLA, TI and Analog Devices lost.
- **Revenue swings point the right way but weakly.** Dropping two stocks whose SEC revenue figures look distorted
  (General Mills, Hershey) gives +0.30 with p = 0.04, but deciding that after seeing the result is exactly the
  overfitting the rules are there to stop - so the verdict stays "no".

## Catches

- **Survivors only.** Every name still trades today. Cyclicals that went bust (Lehman, Bethlehem Steel, many
  homebuilders and banks in 2008) are missing. A line would likely have helped on those, so the test may
  understate it - but you can't know in advance which ones will go bust.
- 63 names, one rule, about 30 years. ETF histories start in 1999-2007, so the cyclical ETFs have fewer cycles.

## Verdict

Not repeatable. The pattern is: **the 200-day line is crash insurance on cyclicals (it roughly cuts the worst drop
by a third at a cost of ~4 points a year) and a poor deal on steady companies.** It isn't a way to beat holding
cyclicals. Nothing changes on the desk; research-only (`green_line_cyclical`).
