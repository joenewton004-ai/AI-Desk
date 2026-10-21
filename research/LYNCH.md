# Peter Lynch's method, quantified: does it still work?

_October 2026. Code: `research/lynch.py`. Tables: [`output/lynch.md`](output/lynch.md). Universe = the 750 largest
US companies at each quarter-end, fundamentals as **filed** by then (SEC EDGAR), **survivors-only
prices**. Research, not advice._

## His method

Peter Lynch ran Fidelity Magellan from 1977 to 1990 and made about 29% a year. His books, *One Up on
Wall Street* (1989) and *Beating the Street* (1993), mix judgement with rules a computer can check.

**Rules a computer can check (tested here):**
| Rule | Lynch's version | Here |
|---|---|---|
| PEG | P/E ÷ earnings growth rate. Under 1 attractive, under 0.5 very attractive | P/E ÷ 3-year net-income growth (%) |
| Dividend-adjusted | (growth + dividend yield) ÷ P/E: 2+ great, under 1 poor | same |
| Categories | Slow growers, stalwarts (10-12%), fast growers (20-25%); avoid the hottest | under 8%, 8-18%, 18-30%, over 30% |
| Balance sheet | Low debt; "a company with no debt can't go bankrupt" | debt/equity under 0.5, or more cash than debt |
| Inventory | Inventory growing faster than sales is a red flag | more than 5 points faster = fail |
| Buybacks | A company buying back its shares | share count not up over the year |

**Not testable:** "buy what you know", boring names, few analysts, low institutional ownership,
insider buying (we hold no history of it), and his personal research visits.

## Results (quarterly, 2014-2026, 0.10% per trade)

| | Return/yr | Sharpe | Worst drop | Beat average stock |
|---|---|---|---|---|
| PEG under 1 | 10.6% | 0.53 | −31% | 6 of 13 years |
| PEG under 0.5 | 10.5% | 0.51 | −33% | 8 of 13 |
| Lynch ratio 2+ | 10.5% | 0.51 | −34% | 7 of 13 |
| Lynch fast grower (all rules) | 10.0% | 0.47 | −33% | 6 of 13 |
| Lynch stalwart | 9.2% | 0.42 | −40% | 7 of 13 |
| Lynch composite, top 25 | 10.5% | 0.50 | −34% | 5 of 13 |
| Cheapest 25 by P/E | 8.1% | 0.36 | −47% | 5 of 13 |
| **Average large stock (equal weight)** | **11.5%** | **0.61** | −27% | |
| **SPY** | **13.8%** | **0.83** | −24% | |
| **Desk quality screen** (for comparison) | **17.9%** | **0.89** | −33% | 10 of 13 |

**Each rule on its own** (next quarter, stocks passing the rule minus the average stock):
- **PEG under 1: −0.07%** a quarter, no better than chance. It lost in 2014-19 (−0.68%) and won in
  2020-26 (+0.50%).
- **Growth categories:** fast growers −0.19% and stalwarts −0.11%, both no better than chance.
- **The balance-sheet, inventory and buyback rules were mildly positive** (+0.02% to +0.14%), but
  none is reliable (t below 1).
- **Ranking by PEG isn't a staircase.** The lowest-PEG fifth didn't beat the highest in a steady
  way, and the pattern reversed between the two halves.

## Why it doesn't work mechanically

1. **PEG is a value signal, and value has been weak.** A low PEG mostly means a low P/E. Cheap
   stocks lagged for most of 2014-2020. That's why "cheapest 25 by P/E" was the worst row, and
   why every PEG rule flips sign between the halves.
2. **Past growth isn't future growth.** Lynch used his own *forecast* of earnings growth. Here
   it's the last 3 years, because historical forecasts don't exist point-in-time. A company that
   grew fast last year often slows.
3. **His edge was the research, not the ratios.** He visited companies, tried products and found
   overlooked small and mid caps before analysts covered them. Among the 750 largest companies,
   which everyone watches, PEG is already priced in.
4. **The world changed.** In the 1980s screening for PEG was hard work. Today it's one filter on a
   free website.

## What it means for the desk

- **No new sleeve, no change to the scoring.** The desk's quality screen already uses the parts of
  Lynch that hold up:
  - balance-sheet strength (its "strength" score);
  - growth vs peers;
  - forward-earnings value, as one of five categories rather than the main signal.
- **It beat every Lynch version by about 7% a year**, mainly through quality (high returns on
  capital), which Lynch never quantified.
- **The buyback rule** ("shares not rising", +0.14% a quarter) is the most consistent Lynch idea
  here. It's already in the screen as `share_change` in the strength score, so nothing to add.
- **The honest summary:** Lynch's method was a *research process* that happened to produce ratios,
  and the ratios alone don't carry the edge.

Recorded in the register as research-only (`lynch_rules`).
