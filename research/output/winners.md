# What the best stocks looked like before their run - generated tables

Universe: the 750 largest US companies at each date (survivors only). Prices adjusted for splits and dividends. Winner = top 10% of the window by 5-year return.

## 1. The past 5 years: 2021-09-30 to 2026-09-30 (750 companies)

Universe median 5-year return +17%; average +56%; top decile cut-off +188%.

| symbol | multiple | sector | growth/yr | gross_margin | roic_avg | mom_12m | ret_36m | off_12m_high | size rank (1=biggest) |
|---|---|---|---|---|---|---|---|---|---|
| MU | 15.4x | Electronics | 2% | 31% | 24% | +51% | +57% | -22% | 101 |
| BE | 14.8x | Electronics | 30% | 21% | -17% | +4% | -45% | -46% | 613 |
| STX | 12.9x | Machinery & computers | -2% |  | 33% | +73% | +101% | -13% | 356 |
| LITE | 11.6x | Electronics | 12% | 45% | 11% | +11% | +39% | -12% | 638 |
| DELL | 11.2x | Machinery & computers | 6% | 31% | 2% | +54% | +93% | +0% | 102 |
| NVDA | 11.1x | Electronics | 20% | 62% | 42% | +53% | +197% | -7% | 10 |
| WDC | 10.7x | Machinery & computers | -6% | 27% | 7% | +54% | +3% | -25% | 371 |
| VRT | 10.1x | Electronics |  |  | -19% | +39% | +147% | -14% | 534 |
| ANET | 9.5x | Machinery & computers | 12% | 64% | 29% | +66% | +29% | -10% | 270 |
| VST | 8.8x | Utilities | 28% |  | 5% | -6% | -26% | -12% | 543 |
| FLEX | 8.3x | Electronics | -2% | 7% | 8% | +59% | +35% | -5% | 529 |
| AVGO | 7.9x | Electronics | 11% | 57% | 7% | +37% | +121% | -2% | 41 |
| PLTR | 7.8x | Software & business services | 35% | 68% | -1557% | +153% |  | -32% | 163 |
| HWM | 7.4x | Primary metals | -26% |  | 5% | +87% | +87% | -12% | 428 |
| MPC | 7.2x | Refining | -2% |  | 1% | +120% | -12% | +0% | 198 |
| CIEN | 6.9x | Electronics | 8% | 47% | 14% | +29% | +64% | -12% | 554 |
| EME | 6.6x | SIC 17 | 5% | 16% | 17% | +71% | +56% | -8% | 628 |
| KLAC | 6.1x | Instruments & medical devices | 20% |  | 31% | +75% | +249% | -4% | 144 |
| TRGP | 6.1x | Utilities | -2% | 29% | -2% | +256% | +3% | +0% | 473 |
| LRCX | 6.1x | Machinery & computers | 10% | 47% | 47% | +73% | +295% | -12% | 100 |
| AMD | 5.9x | Electronics | 23% | 45% | 24% | +26% | +233% | -7% | 70 |
| PWR | 5.7x | SIC 17 | 6% | 15% | 9% | +116% | +245% | +0% | 388 |
| NVT | 5.3x | Machinery & computers | -2% | 37% | 6% | +88% | +30% | -6% | 667 |
| LLY | 5.2x | Chemicals & pharma | 7% |  | 17% | +59% | +128% | -11% | 36 |
| MOG-A | 5.2x | Machinery & computers | 5% | 26% | 12% | +22% | -8% | -15% | 696 |

### Median trait: top 25 vs the whole universe, and the percentile they sat at

| feature | top25 | universe | top25_pctile |
|---|---|---|---|
| Return on capital (avg) | 0.0935 | 0.105 | 45 |
| Return on capital (worst year) | 0.0581 | 0.0614 | 49 |
| Gross margin | 0.344 | 0.385 | 41 |
| Operating margin | 0.119 | 0.108 | 55 |
| Free-cash-flow margin | 0.0862 | 0.116 | 39 |
| Revenue growth (multi-year) | 0.0657 | 0.0476 | 59 |
| Revenue growth (latest year) | 0.00378 | 0.0118 | 48 |
| Share of years revenue rose | 0.75 | 0.75 | 45 |
| Gross margin trend | 0.0132 | 0.00102 | 67 |
| Net debt / EBITDA | 1.39 | 1.27 | 52 |
| Growth vs industry peers | 0.0404 | 0 | 68 |
| Operating earnings yield (cheapness) | 0.0375 | 0.029 | 63 |
| Free-cash-flow yield (cheapness) | 0.0401 | 0.0322 | 58 |
| Earnings yield (cheapness) | 0.0336 | 0.0285 | 59 |
| 6-month price momentum | 0.0322 | 0.039 | 48 |
| 12-month price momentum | 0.587 | 0.361 | 71 |
| 3-year price return (before) | 0.608 | 0.448 | 58 |
| Closeness to 12-month high | -0.105 | -0.0866 | 41 |
| Volatility (12m) | 0.329 | 0.288 | 63 |
| Growth accelerating (latest - multi-year) | -0.0436 | -0.0412 | 49 |
| Company size (market cap) | -371 | -376 | 51 |
| Revenue size | 9.76 | 5.11 | 68 |

## 2. Does the trait raise the odds? 5-year outcomes, 31 overlapping windows starting 2014-03-31 to 2021-09-30

winner pctile = where the winners sat on this trait (50 = no different from everyone). IC = rank correlation between the trait and the later return (0 = nothing; above about 0.05 in a year-averaged t of 2+ is worth noticing). lift = chance of being a winner (or a bust) if you were in the top fifth on the trait, relative to the 10% base rate.

| label | winner_pctile | winners above 50 in | ic | IC>0 in | t (by year) | winner lift (top fifth) | bust_winner lift (top fifth) | winner lift (bottom fifth) |
|---|---|---|---|---|---|---|---|---|
| Return on capital (avg) | 54% | 71% | +0.097 | 100% | +7.1 | 1.20 | 0.81 | 0.93 |
| Return on capital (worst year) | 53% | 65% | +0.093 | 100% | +6.4 | 1.10 | 0.73 | 1.20 |
| Operating margin | 46% | 39% | +0.088 | 100% | +7.0 | 1.08 | 0.63 | 1.36 |
| Free-cash-flow margin | 56% | 55% | +0.085 | 81% | +2.6 | 1.52 | 0.63 | 0.96 |
| Company size (market cap) | 47% | 32% | +0.078 | 87% | +5.2 | 0.87 | 0.67 | 1.04 |
| Revenue size | 50% | 52% | +0.070 | 61% | +1.4 | 0.92 | 0.76 | 1.08 |
| Closeness to 12-month high | 49% | 48% | +0.058 | 81% | +1.5 | 0.99 | 0.83 | 1.14 |
| 3-year price return (before) | 53% | 78% | +0.052 | 74% | +0.9 | 1.30 | 1.22 | 1.08 |
| Revenue growth (latest year) | 59% | 81% | +0.045 | 65% | +0.8 | 1.29 | 1.44 | 0.83 |
| Share of years revenue rose | 67% | 74% | +0.042 | 74% | +1.1 | 0.78 | 1.35 | 0.78 |
| Gross margin | 56% | 55% | +0.040 | 52% | +0.5 | 1.39 | 1.01 | 0.92 |
| Operating earnings yield (cheapness) | 47% | 42% | +0.026 | 52% | +0.6 | 1.08 | 1.12 | 1.32 |
| Gross margin trend | 46% | 29% | +0.022 | 65% | +1.2 | 1.06 | 1.03 | 1.29 |
| Revenue growth (multi-year) | 60% | 97% | +0.021 | 55% | +0.4 | 1.36 | 1.54 | 0.74 |
| Growth accelerating (latest - multi-year) | 48% | 35% | +0.020 | 71% | +0.7 | 1.06 | 1.17 | 1.14 |
| 6-month price momentum | 52% | 61% | +0.017 | 65% | +0.6 | 1.16 | 1.23 | 1.02 |
| Free-cash-flow yield (cheapness) | 54% | 65% | +0.016 | 58% | +0.5 | 1.11 | 1.23 | 0.81 |
| 12-month price momentum | 53% | 71% | +0.015 | 58% | +0.4 | 1.11 | 1.31 | 1.02 |
| Earnings yield (cheapness) | 48% | 48% | +0.005 | 42% | +0.2 | 1.08 | 1.26 | 1.18 |
| Growth vs industry peers | 55% | 87% | +0.000 | 55% | -0.1 | 1.40 | 1.49 | 0.85 |
| Net debt / EBITDA | 43% | 23% | -0.069 | 19% | -2.8 | 0.79 | 1.33 | 1.35 |
| Volatility (12m) | 60% | 87% | -0.088 | 19% | -3.2 | 1.33 | 1.93 | 0.57 |

## 3. Does the trait raise the odds? 3-year outcomes, 39 overlapping windows starting 2014-03-31 to 2023-09-30

winner pctile = where the winners sat on this trait (50 = no different from everyone). IC = rank correlation between the trait and the later return (0 = nothing; above about 0.05 in a year-averaged t of 2+ is worth noticing). lift = chance of being a winner (or a bust) if you were in the top fifth on the trait, relative to the 10% base rate.

| label | winner_pctile | winners above 50 in | ic | IC>0 in | t (by year) | winner lift (top fifth) | bust_winner lift (top fifth) | winner lift (bottom fifth) |
|---|---|---|---|---|---|---|---|---|
| Return on capital (worst year) | 50% | 49% | +0.084 | 87% | +3.6 | 1.07 | 0.66 | 1.37 |
| Return on capital (avg) | 52% | 62% | +0.082 | 87% | +4.2 | 1.16 | 0.80 | 1.15 |
| Free-cash-flow margin | 52% | 54% | +0.080 | 74% | +2.4 | 1.30 | 0.65 | 1.10 |
| Operating margin | 45% | 23% | +0.079 | 85% | +3.2 | 1.02 | 0.61 | 1.41 |
| 3-year price return (before) | 55% | 54% | +0.069 | 57% | +1.2 | 1.35 | 1.31 | 1.11 |
| Company size (market cap) | 45% | 18% | +0.064 | 79% | +2.4 | 0.86 | 0.67 | 1.21 |
| Closeness to 12-month high | 48% | 38% | +0.058 | 79% | +1.7 | 0.95 | 0.84 | 1.16 |
| Revenue size | 47% | 49% | +0.057 | 56% | +1.3 | 0.92 | 0.67 | 1.16 |
| Gross margin | 54% | 64% | +0.043 | 54% | +0.6 | 1.24 | 1.01 | 0.98 |
| Share of years revenue rose | 60% | 51% | +0.036 | 54% | +0.8 | 0.94 | 1.36 | 0.86 |
| Gross margin trend | 47% | 41% | +0.035 | 82% | +3.9 | 1.06 | 1.14 | 1.13 |
| Revenue growth (latest year) | 56% | 67% | +0.025 | 49% | +0.6 | 1.30 | 1.59 | 0.98 |
| 12-month price momentum | 52% | 54% | +0.025 | 62% | +0.8 | 1.16 | 1.24 | 1.06 |
| Operating earnings yield (cheapness) | 45% | 41% | +0.023 | 46% | +0.6 | 1.01 | 1.03 | 1.40 |
| Free-cash-flow yield (cheapness) | 50% | 41% | +0.022 | 64% | +0.5 | 1.03 | 1.17 | 1.02 |
| Revenue growth (multi-year) | 59% | 85% | +0.021 | 46% | +0.5 | 1.38 | 1.55 | 0.82 |
| 6-month price momentum | 52% | 51% | +0.020 | 64% | +0.8 | 1.17 | 1.16 | 1.11 |
| Growth accelerating (latest - multi-year) | 46% | 38% | +0.007 | 56% | +0.3 | 0.97 | 1.27 | 1.25 |
| Earnings yield (cheapness) | 47% | 38% | +0.006 | 41% | +0.2 | 1.03 | 1.18 | 1.25 |
| Growth vs industry peers | 56% | 82% | -0.005 | 44% | -0.2 | 1.41 | 1.54 | 0.93 |
| Net debt / EBITDA | 44% | 26% | -0.061 | 15% | -3.6 | 0.83 | 1.25 | 1.37 |
| Volatility (12m) | 62% | 92% | -0.072 | 21% | -2.3 | 1.45 | 1.86 | 0.55 |

## 4. Does the trait raise the odds? 1-year outcomes, 47 overlapping windows starting 2014-03-31 to 2025-09-30

winner pctile = where the winners sat on this trait (50 = no different from everyone). IC = rank correlation between the trait and the later return (0 = nothing; above about 0.05 in a year-averaged t of 2+ is worth noticing). lift = chance of being a winner (or a bust) if you were in the top fifth on the trait, relative to the 10% base rate.

| label | winner_pctile | winners above 50 in | ic | IC>0 in | t (by year) | winner lift (top fifth) | bust_winner lift (top fifth) | winner lift (bottom fifth) |
|---|---|---|---|---|---|---|---|---|
| Return on capital (avg) | 48% | 45% | +0.050 | 70% | +1.9 | 1.08 | 0.89 | 1.35 |
| Return on capital (worst year) | 43% | 32% | +0.048 | 74% | +1.9 | 0.96 | 0.75 | 1.50 |
| Free-cash-flow margin | 45% | 32% | +0.043 | 64% | +1.4 | 0.97 | 0.77 | 1.26 |
| Operating margin | 41% | 15% | +0.036 | 62% | +1.5 | 0.89 | 0.74 | 1.52 |
| Gross margin trend | 53% | 62% | +0.030 | 70% | +1.9 | 1.21 | 1.14 | 1.02 |
| Revenue size | 44% | 19% | +0.027 | 62% | +1.0 | 0.84 | 0.69 | 1.27 |
| Closeness to 12-month high | 47% | 34% | +0.026 | 66% | +0.7 | 0.94 | 0.87 | 1.32 |
| Company size (market cap) | 44% | 23% | +0.026 | 68% | +0.8 | 0.80 | 0.70 | 1.28 |
| Gross margin | 51% | 55% | +0.020 | 55% | +0.4 | 1.10 | 1.06 | 1.09 |
| Free-cash-flow yield (cheapness) | 45% | 32% | +0.020 | 53% | +0.8 | 0.96 | 1.06 | 1.32 |
| Share of years revenue rose | 56% | 40% | +0.019 | 55% | +0.4 | 1.05 | 1.28 | 0.91 |
| 3-year price return (before) | 50% | 49% | +0.014 | 60% | +0.3 | 1.30 | 1.27 | 1.29 |
| 6-month price momentum | 51% | 51% | +0.013 | 62% | +0.6 | 1.31 | 1.12 | 1.21 |
| Growth accelerating (latest - multi-year) | 48% | 34% | +0.010 | 53% | +0.4 | 1.02 | 1.27 | 1.19 |
| Revenue growth (latest year) | 58% | 72% | +0.010 | 55% | +0.2 | 1.43 | 1.62 | 0.99 |
| Operating earnings yield (cheapness) | 43% | 32% | +0.005 | 43% | +0.2 | 0.98 | 1.07 | 1.55 |
| 12-month price momentum | 50% | 57% | +0.000 | 55% | -0.0 | 1.30 | 1.23 | 1.21 |
| Revenue growth (multi-year) | 59% | 77% | -0.003 | 51% | -0.1 | 1.43 | 1.64 | 0.94 |
| Earnings yield (cheapness) | 47% | 45% | -0.005 | 47% | -0.1 | 1.09 | 1.21 | 1.33 |
| Growth vs industry peers | 59% | 85% | -0.015 | 43% | -0.7 | 1.44 | 1.63 | 0.94 |
| Net debt / EBITDA | 44% | 30% | -0.026 | 43% | -0.9 | 0.95 | 1.11 | 1.32 |
| Volatility (12m) | 66% | 87% | -0.042 | 45% | -0.8 | 1.73 | 1.89 | 0.51 |

## 5. Sectors: were the winners clustered? (5-year windows)

| sector | company_windows | winner_lift | bust_lift | windows_lift_above_1 | median_annual |
|---|---|---|---|---|---|
| SIC 55 | 409 | 2.18 | 0.37 | 65% | +15.9% |
| Rubber & plastics | 270 | 1.74 | 1.63 | 77% | +11.5% |
| Apparel | 266 | 1.73 | 1.95 | 94% | +1.9% |
| General retail | 342 | 1.73 | 0.99 | 65% | +9.5% |
| Electronics | 1570 | 1.69 | 0.68 | 84% | +13.2% |
| Engineering & research | 359 | 1.62 | 0.17 | 61% | +15.7% |
| Construction | 199 | 1.46 | 0.80 | 52% | +16.4% |
| SIC 52 | 194 | 1.44 | 0.00 | 55% | +18.1% |
| Instruments & medical devices | 1591 | 1.44 | 0.72 | 58% | +11.0% |
| Misc retail | 373 | 1.42 | 2.28 | 55% | +5.8% |
| Software & business services | 2953 | 1.39 | 1.14 | 61% | +9.2% |
| Machinery & computers | 1696 | 1.39 | 0.67 | 77% | +11.8% |
| Primary metals | 295 | 1.36 | 0.85 | 45% | +8.2% |
| Wholesale (durable) | 467 | 1.24 | 0.19 | 55% | +10.5% |
| Recreation | 154 | 1.10 | 0.00 | 48% | +10.1% |
| Heavy construction | 169 | 1.01 | 1.12 | 55% | +8.0% |
| Wholesale (nondurable) | 389 | 1.00 | 1.41 | 45% | +4.5% |
| Health services | 260 | 0.88 | 1.42 | 42% | +10.6% |
| Travel services | 249 | 0.80 | 0.12 | 61% | +10.7% |
| Transport equipment | 1027 | 0.62 | 0.45 | 6% | +6.9% |
| Oil & gas | 467 | 0.56 | 4.24 | 16% | -4.3% |
| Utilities | 1605 | 0.52 | 0.48 | 23% | +8.4% |
| Metal products | 398 | 0.50 | 0.20 | 23% | +11.2% |
| Refining | 243 | 0.49 | 0.74 | 26% | +8.2% |
| Trucking | 221 | 0.41 | 0.09 | 29% | +8.8% |
| Food | 868 | 0.40 | 0.53 | 3% | +6.6% |
| Chemicals & pharma | 1934 | 0.38 | 1.19 | 0% | +5.7% |
| SIC 27 | 167 | 0.36 | 2.22 | 30% | +0.5% |
| Restaurants | 449 | 0.29 | 0.71 | 13% | +6.0% |
| Hotels | 416 | 0.22 | 0.91 | 3% | +7.0% |
| Telecom & media | 534 | 0.21 | 2.30 | 3% | -0.5% |
| Apparel retail | 237 | 0.08 | 2.24 | 0% | +0.5% |
| Airlines | 242 | 0.08 | 2.89 | 6% | -2.8% |
| Paper | 221 | 0.00 | 0.36 | 0% | +5.9% |

## 6. Out-of-sample: could a composite of these traits have picked winners in advance?

For each test window, each trait's direction is learned only from 5-year windows that had already finished before the test window began. Companies are ranked by the direction-adjusted sum of percentiles; the top decile is compared with the universe. Base rate for a winner is 10%.

| start | trained_on | features_used | hit_rate | bust_rate | picks_annual | picks_median_annual | universe_annual | universe_median_annual |
|---|---|---|---|---|---|---|---|---|
| 2019-06 | 2 | 20 | 4% | 8% | +7.7% | +8.5% | +7.7% | +7.8% |
| 2019-09 | 3 | 19 | 5% | 5% | +9.8% | +9.7% | +9.5% | +9.5% |
| 2019-12 | 4 | 17 | 8% | 3% | +9.5% | +9.6% | +7.4% | +7.3% |
| 2020-03 | 5 | 20 | 5% | 11% | +11.1% | +10.6% | +13.7% | +13.3% |
| 2020-06 | 6 | 20 | 7% | 9% | +7.7% | +7.3% | +9.6% | +9.5% |
| 2020-09 | 7 | 21 | 1% | 9% | +4.3% | +6.5% | +9.0% | +8.8% |
| 2020-12 | 8 | 21 | 5% | 13% | +1.5% | +3.7% | +5.1% | +5.9% |
| 2021-03 | 9 | 21 | 7% | 12% | +0.6% | +2.2% | +2.9% | +3.9% |
| 2021-06 | 10 | 21 | 11% | 9% | +1.0% | -1.4% | +3.6% | +3.1% |
| 2021-09 | 11 | 20 | 8% | 12% | +0.1% | -1.3% | +3.0% | +3.2% |

Average over 10 test windows (heavily overlapping - roughly 3 independent years): hit rate 6% (random = 10%), bust rate 9% (random = 10%), picks +5.4%/yr vs universe average +7.1%/yr (median pick +5.6% vs median stock +7.2%).

### The same test over 1-year runs (more windows, so a fairer test)

Winner = top decile by the next 12 months' return; test windows start every quarter from 2019-03.

| year | hit_rate | bust_rate | picks_annual | picks_median_annual | universe_annual | universe_median_annual |
|---|---|---|---|---|---|---|
| 2019.0 | 19% | 0% | +22.8% | +17.1% | +1.9% | -1.9% |
| 2020.0 | 5% | 16% | +37.1% | +34.4% | +50.8% | +41.7% |
| 2021.0 | 3% | 15% | -20.9% | -21.6% | -10.3% | -12.1% |
| 2022.0 | 8% | 6% | +15.8% | +13.4% | +13.4% | +10.7% |
| 2023.0 | 11% | 5% | +20.9% | +16.6% | +18.9% | +14.1% |
| 2024.0 | 9% | 7% | +9.9% | +7.3% | +8.7% | +4.1% |
| 2025.0 | 8% | 8% | +11.3% | +0.1% | +20.2% | +7.2% |

Average over 27 test windows (7 calendar years): hit rate 9% (random = 10%), bust rate 8%, picks +13.9% vs universe +14.6% (median pick +10.0% vs median stock +9.2%). Years where the picks beat the universe average: 4 of 7.
