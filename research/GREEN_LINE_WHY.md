# Why the 200-day line helped NVIDIA and Apple (and not Tesla, Amazon or Microsoft)

_November 2026. Code: `research/green_line_why.py`. Tables: [`output/green_line_why.md`](output/green_line_why.md)
(the script also writes yearly financials per company to `output/green_line_why_<SYM>.csv`, not committed). Follows `GREEN_LINE_TECH.md`. Research, not
advice._

**Read with care:** seven stocks, all picked with hindsight (today's winners). SEC's machine-readable financials start
around 2009, so the dot-com years have prices but no financials here. These are explanations after the fact, not a
rule for choosing stocks in advance.

## 1. The mechanism: the line pays only if the stock keeps falling after it crosses

What a dollar did on the days the line said "in" vs "out" (compounded, per year):

| | while in | while out | big falls (30%+) | avg days peak to trough | out-spells a year | line vs holding |
|---|---|---|---|---|---|---|
| **NVIDIA** | +56% | **−10%** | 9 | 117 | 2.4 | **better** (39% vs 34%/yr) |
| **Apple** | +40% | **−2%** | 11 | 226 | 2.0 | **better** (29% vs 26%/yr) |
| Meta | +35% | +9% | 5 | 126 | 2.5 | less return, better Sharpe |
| Alphabet | +19% | +18% | 4 | 162 | 3.3 | less return, same Sharpe |
| Microsoft | +17% | +21% | 3 | 905 | 3.8 | worse |
| Amazon | +25% | +29% | 8 | 141 | 3.9 | worse |
| Tesla | +24% | **+75%** | 11 | 139 | **5.6** | much worse |

- For NVIDIA and Apple, the days the line sat out were losing days. It dodged the middle of long collapses: NVIDIA
  2002-03 (−69% while out), 2008-09 (−61%), 2022 (−28%); Apple 2000-01 (−54%), 2008-09 (−26%).
- For Tesla, the days out were its *best* days (+75% a year): it fell hard and fast, crossed the line, then rebounded
  just as fast (2020: −61% in 20 days, then up). The line sold near the bottom and bought back higher, 5-6 times a year.
- Most out-spells end higher for every stock (83-94% are "false alarms"). The line wins only when the few right calls
  catch a long, deep fall - and NVIDIA and Apple had several.

## 2. The business behind it: cyclical hardware vs steady services

From SEC filings, fiscal years ~2009 on:

| | revenue then -> now ($bn) | growth/yr | growth swings (sd) | years revenue fell | operating margin (range) |
|---|---|---|---|---|---|
| **NVIDIA** | 4 -> 216 | 25% | **41%** | **4** (FY2009, 2010, 2014, 2020; FY2023 flat) | 25% (−3% to 62%) |
| **Apple** | 25 -> 479 | 17% | 21% | **3** (2016, 2019, 2023) | 28% (18% to 35%) |
| Meta | 2 -> 201 | 36% | 22% | 1 (2022) | 38% (11% to 52%) |
| Microsoft | 60 -> 332 | 10% | 6% | 2 (2009, 2016) | 36% (19% to 47%) |
| Alphabet | 17 -> 403 | 19% | 8% | 0 | 28% (20% to 35%) |
| Amazon | 15 -> 717 | 24% | 10% | 0 | 4% (0% to 11%) |
| Tesla | 0.1 -> 95 | 52% | 92% | 1 (2025) | −23% (−126% to 17%) |

- **NVIDIA and Apple sell physical products in cycles.** Chips go through boom-and-glut cycles: the 2008 crash,
  crypto-mining busts in 2018-19 and 2022 (FY2023 revenue flat, operating margin from 37% to 16%). iPhones go through
  upgrade cycles (revenue fell in 2016, 2019 and 2023). When a cycle turns, revenue and profits fall for several
  quarters, and the share price grinds down for months. That slow, lasting kind of fall is exactly what a 200-day
  line catches.
- **Microsoft, Alphabet and Amazon earn steadier money** (software subscriptions, ads, cloud, retail). Their revenue
  almost never fell. Their share-price falls were mostly about valuation or the whole market, and they recovered
  quickly - so the line sold and then paid more to get back in.
- **Tesla is the extreme of volatility, not of cycles.** Its revenue has grown 52% a year but swung wildly; its price
  swings even more (57% a year). Big, fast moves in both directions are what whipsaw a line.
- **Meta is in between:** one real business downturn (2022: revenue down, the "metaverse" spending) which the line
  caught (−53% avoided), plus several quick sell-offs that it didn't.

## 3. Market position today (why they're winners - not why the line worked)

| Company | Market position (dated sources, to verify) |
|---|---|
| NVIDIA | ~75-90% of AI data-centre accelerators (estimates vary by method; IDC ~81% for 2026, ~92% of units in 2025); FY2026 data-centre revenue $194bn |
| Apple | #1 in smartphones in 2025 with ~20% of global shipments (Counterpoint, Jan 2026); ~25% in Q4 2025 |
| Tesla | ~40-45% of US EV sales in 2025, down from ~80% four years earlier (Cox Automotive) |
| Amazon / Microsoft / Alphabet | Cloud: AWS ~28%, Azure ~20%, Google Cloud ~15% (Synergy, Q2 2026, via secondary reports) |

Market share explains why these companies grew, but it doesn't predict whether a trend line helps. NVIDIA and Tesla
both dominated their markets; the line helped one and hurt the other. What matters is how the business's ups and downs
show up in the price: slow multi-quarter downturns (line helps) vs sharp sell-offs that bounce back (line hurts).

## Verdict

- The line suits **cyclical businesses whose bad patches last** (chips, hardware) and hurts **steady compounders**
  (subscriptions, ads, cloud) and **very volatile stocks** (Tesla).
- That's a story told after the fact on 7 stocks. It would need a test on many cyclical vs steady companies, with
  delisted ones included, before it could be trusted. Nothing changes on the desk; research-only.

Sources (read 2026-11-10): [IDC/Silicon Analysts via commandlinux.com](https://commandlinux.com/statistics/ai-gpu-market-share-nvidia-vs-amd-vs-intel/),
[theccpress.com (IDC 92%)](https://theccpress.com/nvidia-holds-92-ai-data-center-share-amid-700b-buildout/),
[AppleInsider / Counterpoint](https://appleinsider.com/articles/26/01/12/apple-dominated-2025-smartphone-market-with-a-20-share),
[Finimize / Cox](https://finimize.com/content/teslas-share-of-us-ev-sales-falls-below-40),
[Drive Tesla Canada / Cox Q1 2025](https://driveteslacanada.ca/news/tesla-44-share-us-ev-market-q1-2025/),
[tech-insider.org / Synergy Q2 2026](https://tech-insider.org/google-cloud-15-percent-share-aws-falls-2026/).
Several are secondary sites; the figures are approximate.
