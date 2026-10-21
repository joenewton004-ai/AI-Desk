# Leveraged S&P 500 fund on SPY signals - generated tables

Daily, 1994-01-03 to 2026-10-19. Signals at SPY's close, fills at the next open. Simulated funds: L x SPY daily, minus fees (0.89-0.91%/yr) and financing (T-bills + 0.3% on the borrowed part). 0.03% per trade. Sharpe above T-bills.

## 1. Results

| | return/yr | volatility | Sharpe | worst drop | worst year | 1994-2009 | 2010-2026 | in the market | avg leverage | trades/yr |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY buy and hold | 10.8% | 19% | 0.51 | -55% | -37% | 7.4% (0.28) | 14.0% (0.77) | 100% | 1.0x | 0.0 |
| 2x buy and hold (SSO-like) | 14.4% | 37% | 0.48 | -88% | -67% | 5.7% (0.25) | 23.1% (0.74) | 100% | 2.0x | 0.0 |
| 3x buy and hold (UPRO-like) | 14.9% | 56% | 0.49 | -98% | -85% | 0.5% (0.26) | 30.2% (0.75) | 100% | 3.0x | 0.0 |
| SPY above its 200-day (1x, the desk's old idea) | 9.3% | 12% | 0.58 | -25% | -13% | 9.9% (0.55) | 8.5% (0.61) | 77% | 1.0x | 2.9 |
| 2x, trend only | 13.8% | 24% | 0.55 | -45% | -26% | 14.1% (0.51) | 13.3% (0.58) | 77% | 2.0x | 2.9 |
| 3x, trend only | 17.4% | 37% | 0.55 | -61% | -38% | 17.1% (0.52) | 17.3% (0.58) | 77% | 3.0x | 2.9 |
| 3x, trend + vol cap | 13.7% | 23% | 0.56 | -37% | -24% | 12.5% (0.49) | 14.5% (0.61) | 77% | 2.1x | 21.4 |
| 3x, trend + VIX filter | 15.7% | 35% | 0.52 | -60% | -38% | 13.4% (0.43) | 17.5% (0.60) | 76% | 3.0x | 4.5 |
| 3x, trend + 10% stop | 16.6% | 36% | 0.54 | -69% | -53% | 14.3% (0.46) | 18.4% (0.61) | 76% | 3.0x | 2.8 |
| 2x strict (trend + vol cap + VIX + stop) | 11.6% | 19% | 0.53 | -31% | -18% | 10.5% (0.44) | 12.4% (0.61) | 76% | 1.7x | 10.0 |
| 3x strict (trend + vol cap + VIX + stop) | 12.7% | 23% | 0.53 | -37% | -24% | 11.3% (0.44) | 13.9% (0.59) | 76% | 2.1x | 22.3 |

## 2. The crashes

| episode | SPY buy and hold | 3x buy and hold (UPRO-like) | 3x, trend only | 3x strict (trend + vol cap + VIX + stop) | 2x strict (trend + vol cap + VIX + stop) |
|---|---|---|---|---|---|
| 2000-02 dot-com | -48% | -93% | -46% | -20% | -19% |
| 2008 crisis | -55% | -95% | -32% | -18% | -16% |
| 2020 Covid | -34% | -75% | -58% | -21% | -22% |
| 2022 bear | -25% | -64% | -31% | -16% | -16% |
| 2025 tariff drop | -19% | -49% | -25% | -17% | -15% |

## 3. Walk-forward: each January choose the average length and band on the past 10 years

| 3x trend | return/yr | Sharpe | worst drop |
|---|---|---|---|
| Walk-forward choice (out of sample) | 12.2% | 0.46 | -64% |
| Fixed 200-day, 1% band (same years) | 14.8% | 0.52 | -61% |

Chosen: 2004: 200d/2%; 2005: 250d/2%; 2006: 250d/2%; 2007: 250d/2%; 2008: 250d/2%; 2009: 250d/2%; 2010: 250d/2%; 2011: 250d/2%; 2012: 250d/2%; 2013: 100d/0%; 2014: 100d/0%; 2015: 200d/2%; 2016: 100d/1%; 2017: 200d/2%; 2018: 200d/2%; 2019: 100d/1%; 2020: 200d/2%; 2021: 150d/2%; 2022: 150d/2%; 2023: 200d/0%; 2024: 100d/0%; 2025: 100d/0%; 2026: 100d/0%

## 4. Does the simulation match the real funds?

Buy and hold, 2009-06-25 to 2026-10-20 (real prices include fees and financing):

| fund | real return/yr | simulated | real worst drop | simulated |
|---|---|---|---|---|
| SSO (2x) | 25.0% | 25.3% | -59% | -58% |
| UPRO (3x) | 32.7% | 33.8% | -77% | -75% |
