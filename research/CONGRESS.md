# Copying Congress's stock purchases (House, 2014-2026)

Generated tables: `research/output/congress.md` (`python research/house_ptr.py`, then `python research/congress.py`).
Tested 2026-10-28, after the owner allowed `disclosures-clerk.house.gov` in the network settings.

## The idea

Members of Congress must report stock trades within 45 days (the STOCK Act). "Copy Congress" apps, and the
trader-pelosi helper in Jakeschincariol/day-trader-skill, buy what members bought. The popular story is that members
trade on inside knowledge. The question here is narrower: **can someone who reads the reports make money from them?**

## Data

- **Source:** the House Clerk's yearly filing indexes and every electronically filed Periodic Transaction Report, 2014-2026.
  - 5,966 reports were read; 46,371 transactions were parsed.
  - 3,171 reports hold 26,205 transactions with a ticker and sensible dates.
  - That gives 10,249 stock-purchase events; 66% of them are in our price cache (6,680 scored at 20 days).
- **The filing date is what matters.** A trade isn't public until its report is filed. The median purchase was reported
  27 days after it was made (90% within 63 - late filings happen). The test buys at the **first open after the filing date**.
- **Gaps (say these when quoting results):**
  - **Paper filings are missing.** About 2,450 of 8,415 reports are scanned images: about 40% of 2014-2019 and about 15%
    since. A script can't read them.
  - **The Senate is missing.** Its site isn't in the network settings.
  - **Some reports didn't parse.** 807 electronic reports gave no transactions.
  - **Stocks outside the cache are missing.** Older reports often have no ticker, and small companies aren't in the
    cache, so only big and mid-sized companies that still exist are scored.
  - **Prices are survivors-only.**

## Rules (fixed before running)

**Variants:**
- Every purchase.
- Purchases of $15,001+ or $50,001+ (the reports give amount bands, not exact figures).
- **Clusters:** two or more members buying the same stock within 30 days of each other's reports.
- **Fresh:** reported within 14 days of the trade.
- **Own account:** the member's own account, not their spouse's.
- **Nancy Pelosi:** her purchases, scored on the stock even when she bought call options.
- **Sales:** should do worse than the market if the trades carry information.
- **Trade-date version:** not something a copier can do; shows what the reporting delay costs.

**How each event is measured:**
- Holds of 20, 60 and 120 trading days (about 1, 3 and 6 months).
- Costs of 0.05% each way.
- Measured against the equal-weight average of the whole price cache over the same days, and against SPY.

## Results

| rule | events | vs universe, 60 days | t | vs SPY, 60 days |
|---|---|---|---|---|
| every purchase | 6,547 | -0.76% | -0.8 | -0.06% |
| $50k+ | 352 | +2.23% | 0.8 | +1.91% |
| clusters | 1,580 | -0.03% | 0.1 | +0.88% |
| fresh (within 14 days) | 1,459 | +0.78% | -0.2 | |
| member's own account | 3,292 | -1.12% | -1.7 | |
| Nancy Pelosi | 41 | +0.17% | 0.7 | +0.11% |
| sales | 6,895 | -1.08% | -1.5 | |
| trade date (can't copy) | 6,630 | -1.02% | -1.0 | |

The copy book holds every disclosed purchase for 60 days, at equal weight:

| period | copy book | SPY | cache universe |
|---|---|---|---|
| 2014-2026 | 13.9%/yr, Sharpe 0.71, worst -35% | 13.7%, 0.75, -32% | 27.8%, 0.92, -43% |
| 2014-19 | 13.6%, 0.92, -19% | 12.1%, 0.88, -19% | 14.5%, 0.91, -23% |
| 2020-26 | 14.2%, 0.61, -35% | 15.2%, 0.69, -32% | 40.9%, 1.02, -43% |

**About the "cache universe" column:** its 41%/yr in 2020-26 is hindsight. The cache holds today's big companies, so it
is full of winners. Copied picks come from the same cache, so comparing within it is fair-ish. SPY is the plainer
yardstick.

## What it means

1. **There is no edge in copying.**
   - Copying every disclosed purchase did about as well as buying SPY: 13.9% vs 13.7% a year, with a slightly lower
     Sharpe and a deeper worst drop.
   - Not one rule has a t-stat above 1.
2. **Members' own timing shows no edge either.**
   - Measured from the trade date, which a copier can't do, purchases still trail the universe (-1.02% over 60 days).
     The reporting delay isn't hiding a profit.
   - Sales did no worse than purchases (both trail the universe by about 1% over 60 days), so the trades don't
     separate winners from losers.
   - This matches the published studies since 2012 cited in `ai_desk/bottleneck/smart_money.py`, which mostly find no
     outperformance after the STOCK Act.
3. **Big purchases ($50k+) and Pelosi's trades look better, but it's noise.**
   - The $50k+ result is +2.2% (t 0.8) from 352 events.
   - Pelosi's is +0.2% (t 0.7) from 41 events, and her 2014-19 trades lagged by 6%.
   - Her well-known gains come from call options, which add leverage on mostly big tech stocks. This test scores the
     stock, not the option.
4. **Not adopted.** In the register as research-only (`congress_copy`). The desk changes nothing.

## Fixed along the way

`smart_money.congress_signals`, used by the retired bottleneck scan, counted Congress trades by their trade date. That
could "know" a trade up to 45 days before it was public. It now counts by the filing date when the file has one
(`tests/test_congress.py`).

## To verify / limits

- The paper filings and the Senate could change the picture. Neither is reachable from here.
- Amount bands are wide ($1,001-$15,000 is the most common), so "size" is rough.
- The parser was checked by hand on a sample of reports (`tests/test_congress.py` covers wrapped tickers, options and
  partial sales). About 15,500 transactions have no ticker and are not scored.
