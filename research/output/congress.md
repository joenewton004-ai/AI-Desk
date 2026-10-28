# Copying Congress's stock purchases (House, 2014-2026) - generated tables

3,171 electronic reports, 26,205 transactions with a ticker. Stock purchases: 10,249 events, 66% in the price cache. Median delay from trade to report: 27 days (90% within 63).

Excess = the stock minus the equal-weight universe over the same days, after 0.05% costs each way. Bought at the first open after the report was filed. **Survivors-only prices; paper reports and the Senate missing.**

| rule | hold | events | avg excess | t | beat universe | 2014-19 | 2020-26 |
|---|---|---|---|---|---|---|---|
| all | 20d | 6,680 | -0.28% | -1.0 | 47% | +0.03% | -0.35% |
| all | 60d | 6,547 | -0.76% | -0.8 | 45% | +1.08% | -1.17% |
| all | 120d | 6,362 | -2.19% | -1.7 | 44% | +1.79% | -3.11% |
| 15k+ | 20d | 1,236 | -0.27% | -0.9 | 46% | -0.57% | -0.17% |
| 15k+ | 60d | 1,216 | -0.97% | -0.6 | 45% | +0.46% | -1.48% |
| 15k+ | 120d | 1,193 | -3.01% | -1.8 | 42% | +1.46% | -4.66% |
| 50k+ | 20d | 354 | +0.33% | -0.1 | 50% | +0.48% | +0.27% |
| 50k+ | 60d | 352 | +2.23% | 0.8 | 56% | +3.55% | +1.65% |
| 50k+ | 120d | 348 | +0.63% | 0.0 | 52% | +5.14% | -1.40% |
| cluster | 20d | 1,608 | +0.13% | 0.3 | 50% | +0.69% | +0.07% |
| cluster | 60d | 1,580 | -0.03% | 0.1 | 47% | +3.62% | -0.44% |
| cluster | 120d | 1,541 | -1.31% | -0.0 | 45% | +7.03% | -2.29% |
| fresh | 20d | 1,480 | +0.05% | -1.0 | 49% | -0.44% | +0.19% |
| fresh | 60d | 1,459 | +0.78% | -0.2 | 48% | +1.64% | +0.53% |
| fresh | 120d | 1,402 | -0.41% | -0.6 | 47% | +2.29% | -1.25% |
| own | 20d | 3,365 | -0.32% | -1.4 | 46% | +0.33% | -0.45% |
| own | 60d | 3,292 | -1.12% | -1.7 | 44% | +0.92% | -1.51% |
| own | 120d | 3,162 | -2.81% | -2.3 | 41% | +1.21% | -3.63% |
| pelosi | 20d | 43 | +2.51% | 0.7 | 40% | -3.99% | +3.57% |
| pelosi | 60d | 41 | +0.17% | 0.7 | 34% | -6.02% | +1.23% |
| pelosi | 120d | 39 | +5.54% | 0.8 | 51% | -6.10% | +7.65% |
| sales | 20d | 7,091 | -0.40% | -1.4 | 48% | +0.23% | -0.49% |
| sales | 60d | 6,895 | -1.08% | -1.5 | 45% | +0.19% | -1.26% |
| sales | 120d | 6,665 | -1.92% | -2.1 | 43% | +1.71% | -2.45% |
| trade-date | 20d | 6,706 | -0.57% | -1.0 | 47% | -0.10% | -0.67% |
| trade-date | 60d | 6,630 | -1.02% | -1.0 | 45% | +0.77% | -1.42% |
| trade-date | 120d | 6,457 | -1.98% | -1.5 | 45% | +2.00% | -2.92% |

The same events against SPY instead (the cache's universe is today's big companies, so it is flattered by hindsight; SPY isn't):

- all: 20d -0.07%, 60d -0.06%, 120d -0.37%
- 50k+: 20d +0.33%, 60d +1.91%, 120d +0.23%
- cluster: 20d +0.47%, 60d +0.88%, 120d +1.16%
- pelosi: 20d +2.59%, 60d +0.11%, 120d +4.89%

Robustness: 'all' bought one day later (2nd open after the report):

- 20d: -0.37% (t -1.1), 2014-19 +0.04%, 2020-26 -0.46%
- 60d: -0.84% (t -0.9), 2014-19 +1.09%, 2020-26 -1.27%
- 120d: -2.22% (t -1.8), 2014-19 +1.79%, 2020-26 -3.14%

## Copy book: every disclosed purchase held 60 trading days, equal weight

| book | period | return/yr | Sharpe (above T-bills) | worst drop |
|---|---|---|---|---|
| copy Congress | 2014-2026 | +13.9% | 0.71 | -35% |
| equal-weight universe | 2014-2026 | +27.8% | 0.92 | -43% |
| SPY | 2014-2026 | +13.7% | 0.75 | -32% |
| copy Congress | 2014-19 | +13.6% | 0.92 | -19% |
| equal-weight universe | 2014-19 | +14.5% | 0.91 | -23% |
| SPY | 2014-19 | +12.1% | 0.88 | -19% |
| copy Congress | 2020-26 | +14.2% | 0.61 | -35% |
| equal-weight universe | 2020-26 | +40.9% | 1.02 | -43% |
| SPY | 2020-26 | +15.2% | 0.69 | -32% |
