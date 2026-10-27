# Can the overnight sleeve trade less?

_October 2026. Code: `research/overnight_turnover.py`. Tables: [`output/overnight_turnover.md`](output/overnight_turnover.md).
Daily, 2014-04 to 2026-10, **survivors-only prices**, the live rules (12-month ranking, daily re-pick, both checks).
Research, not advice._

Costs are a percentage of the money moved, so cutting the **number of stocks** doesn't cut costs. Cutting the
**money moved** does. Most nights, 93% of tonight's 20 stocks were also last night's, yet the live sleeve sells them
all at the open and buys them back near the close.

| Version | Traded a day | Sharpe at 0.02% each way | at 0.05% | at 0.10% | Volatility | Worst drop (0.05%) |
|---|---|---|---|---|---|---|
| A: live (sell all at the open) | 1.50× the book | **1.54** | 0.76 | −0.55 | 14% | −21% |
| B: keep repeat picks through the day | **0.26×** | 0.77 | 0.69 | **0.55** | 25% | −33% |
| C: top 10, sell all | 1.50× | 1.46 | 0.80 | −0.32 | 17% | −22% |
| D: top 10, keep repeats | 0.27× | 0.83 | 0.75 | 0.63 | 28% | −34% |

Returns per year at 0.02% / 0.05% / 0.10% costs: A 26.1% / 12.6% / −6.8%; B 19.5% / 17.2% / 13.4%.

- **Fewer stocks (C) changes nothing important.** The cost per dollar is the same; it's just more concentrated.
- **Keeping repeat picks (B) cuts trading by about 83% and makes the sleeve far less sensitive to costs.**
  - From 0.02% to 0.10% costs its return falls only from 19.5% to 13.4%, while the live version goes from 26.1% to
    −6.8%.
  - The cost of that is the daytime moves. They average about zero for these stocks (−0.006% a day), but they nearly
    double the volatility (14% → 25%) and deepen the worst drop (to about −33%).
  - B stops being an "overnight" strategy. It becomes a daily-refreshed 12-month momentum portfolio that steps
    aside on the same cash nights. It's also weak in 2014-19 (Sharpe 0.06-0.32).
- **The crossover is at about 0.04-0.05% each way.** Below that the live version wins clearly (Sharpe 1.54 vs 0.77).
  Above it, keeping repeats wins: at 0.10% the live version loses money and B still makes 13% a year.

## Verdict

**Which is better depends on real trading costs, which we don't know yet.**
- On a live account with auction orders, at roughly 0.01-0.02% each way, keep the live version.
- If real costs turn out above ~0.05% each way, version B is the safer sleeve. It would need an amendment (it changes
  the sleeve's rules) and its own desk test, given its higher volatility.

The official-price line and the market-on-open test (around 2026-11-10) are the evidence to decide on. Nothing has
changed in the live rules.
