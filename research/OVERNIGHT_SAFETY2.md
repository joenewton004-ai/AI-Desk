# Earnings-night skip and sector caps, re-tested after the 2026-10-30 loss

_October 2026. Code: `research/overnight_safety2.py`. Tables: [`output/overnight_safety2.md`](output/overnight_safety2.md).
Daily, 2014-04 to the 2026-10-30 open, the live rules and checks, **survivors-only prices**. Earnings releases: 74,878
SEC 8-K item 2.02 filings, refreshed 2026-10-30. Follows `OVERNIGHT_SAFETY.md` (data to 2026-10-20). Research, not
advice._

## Why

On the night ending at the 2026-10-30 open, the sleeve lost about $9.8k.
- **Market:** chips gapped down (SMH -5.2% at the open).
- **Earnings:** Intel, Twilio, Illumina and SanDisk all reported after Thursday's close.

The question is whether skipping earnings nights, or capping how many picks come from one sector, would have
helped - and whether it helps over 12 years.

## Rules (fixed before running)

**Versions:**
- **E swap:** skip a stock on its earnings night; the next-ranked stock takes its place.
- **E cash:** skip it and keep that slot in T-bills.
- **S4 / S3 / S2:** at most 4, 3 or 2 picks from one industry.
- **H6:** at most 6 of the 20 from computer hardware and electronics combined (chips, memory, storage, servers).
- **E cash + S3:** both together.
- **60% / 50% share:** less money overnight, the rest in T-bills.

**To adopt:** a better Sharpe than live in both 2014-19 and 2020-26, and a smaller worst drop or worst month, at both
0.02% and 0.05% costs each way.

## Results (at 0.02% costs each way)

| version | return/yr | Sharpe | 2014-19 / 2020-26 | worst drop | worst month | the Oct 30 night |
|---|---|---|---|---|---|---|
| **Live** | 25.3% | **1.49** | 1.43 / 1.63 | -15% | -11.8% | **-6.1%** |
| E swap | 21.2% | 1.32 | 1.32 / 1.43 | -15% | -11.4% | -4.3% |
| E cash | 21.4% | 1.34 | 1.32 / 1.46 | -14% | -11.2% | -3.7% |
| S4 | 23.0% | 1.42 | 1.41 / 1.54 | -14% | -10.6% | -5.3% |
| S3 | 21.8% | 1.40 | 1.43 / 1.49 | -14% | -10.2% | -5.0% |
| S2 | 19.5% | 1.34 | 1.39 / 1.40 | -15% | -10.2% | -2.8% |
| H6 (hardware cap) | 22.5% | 1.42 | 1.40 / 1.53 | -13% | -10.6% | -5.0% |
| E cash + S3 | 18.7% | 1.27 | 1.29 / 1.35 | -15% | -9.8% | -2.8% |
| **60% share** | 15.7% | **1.49** | 1.43 / 1.63 | **-9%** | **-7.1%** | -3.6% |
| **50% share** | 13.4% | **1.49** | 1.43 / 1.63 | **-8%** | **-5.8%** | -3.0% |

(At 0.05% costs every version is much weaker, with Sharpe 0.38-0.71; the ranking is the same.)

## What it means

- **Every filter would have softened that night,** cutting -6.1% to between -2.8% and -5.3%.
- **But over 12 years every one costs more than it saves.** 2-7 points of return a year, and a lower Sharpe in both
  halves. None passes the rule set in advance.
- **Earnings nights still pay on average.** Skipping them gives up more than it avoids, as found before
  (`OVERNIGHT_SAFETY.md`: a pick's earnings night averaged +1.09% vs +0.10% on other nights).
- **Sector caps barely change the worst drop (-13% to -15%).** The worst nights are market-wide gaps.
- **The only lever that cuts risk without hurting the Sharpe is how much money goes overnight.**
  - At 60%: the worst drop falls from -15% to -9%, the worst month from -11.8% to -7.1%, and the Oct 30 night would
    have been -3.6%.
  - It costs a proportional part of the return: 15.7% a year instead of 25.3%.
  - It doesn't "pass" only because its Sharpe equals live's (1.49) rather than beating it. Scaling the bet doesn't
    change the risk-adjusted result.

## Verdict

- **Don't add an earnings skip or a sector cap.** They protect against a night like Oct 30, but cost more over time
  than they save.
- **If the size of the swings is the problem, lower the overnight share** (for example to 60%; an amendment, the
  owner's decision). It halves the bad nights in exchange for a proportional part of the return.

Nothing in the live rules has changed.
