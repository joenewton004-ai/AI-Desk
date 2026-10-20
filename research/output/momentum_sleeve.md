# Plain momentum vs the bottleneck sleeve's flow rotation - generated tables

Monthly, 2014-04 to 2026-09. Survivors-only prices (both engines). 0.10% per trade.

## 1. The 20% sleeve on its own

| | return/yr | volatility | Sharpe | worst drop | at 3x costs | 2014-19 Sharpe | 2020-26 Sharpe |
|---|---|---|---|---|---|---|---|
| Current: industry flow rotation (live setting) | 17.8% | 31% | 0.63 | -45% | 11.0% | 0.50 | 0.72 |
| Plain momentum: top 20, every 4 weeks | 25.4% | 29% | 0.86 | -41% | 22.1% | 1.06 | 0.82 |
| Plain momentum + live exit (below 100-day avg) | 19.8% | 26% | 0.76 | -30% | 15.4% | 1.06 | 0.67 |
| Plain momentum on the current engine's pool | 29.0% | 35% | 0.86 | -43% | 25.6% | 0.82 | 0.92 |
| Plain momentum: top 10, every 4 weeks | 32.7% | 35% | 0.94 | -47% | 29.1% | 0.98 | 0.98 |
| SPY (for reference) | 13.8% | 15% | 0.83 | -24% | | | | |

## 2. The whole desk: 50% quality screen + 20% sleeve + 30% SPY momentum

| desk with | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | corr. with screen |
|---|---|---|---|---|---|---|---|
| Current: industry flow rotation (live setting) | 16.3% | 16.7% | 0.88 | -22.8% | 0.91 | 0.88 | 0.56 |
| Plain momentum: top 20, every 4 weeks | 17.6% | 16.8% | 0.94 | -25.1% | 1.04 | 0.90 | 0.64 |
| Plain momentum + live exit (below 100-day avg) | 16.5% | 16.0% | 0.92 | -24.2% | 1.04 | 0.86 | 0.59 |
| Plain momentum on the current engine's pool | 18.7% | 17.2% | 0.98 | -22.6% | 1.00 | 0.98 | 0.53 |
| Plain momentum: top 10, every 4 weeks | 19.3% | 17.4% | 1.00 | -23.4% | 1.05 | 0.99 | 0.57 |
| (no 20% sleeve: 70% screen + 30% SPY momentum) | 15.8% | 15.9% | 0.89 | -27.6% | | | |

## 3. How consistent is the difference?

| year | desk with current engine | desk with plain momentum | difference |
|---|---|---|---|
| 2014 | +9.8% | +12.5% | +2.6% |
| 2015 | -0.4% | -0.1% | +0.3% |
| 2016 | +15.2% | +17.1% | +1.9% |
| 2017 | +31.5% | +31.9% | +0.4% |
| 2018 | -7.5% | -3.8% | +3.7% |
| 2019 | +30.8% | +33.1% | +2.3% |
| 2020 | +23.1% | +24.9% | +1.8% |
| 2021 | +33.9% | +26.4% | -7.5% |
| 2022 | -19.0% | -20.3% | -1.3% |
| 2023 | +36.0% | +39.1% | +3.0% |
| 2024 | +22.1% | +29.0% | +6.9% |
| 2025 | +20.8% | +18.0% | -2.9% |
| 2026 | +23.1% | +28.9% | +5.8% |

Plain momentum's desk did better in 10 of 13 calendar years.
Over rolling 3-year windows it did better in 65% of 115 windows.

## 4. Walk-forward: each January, keep the engine with the better desk Sharpe so far

| | return/yr | volatility | Sharpe | worst drop |
|---|---|---|---|---|
| Walk-forward choice (out of sample) | 19.7% | 18% | 0.97 | -25% |
| Always the current engine, same years | 18.5% | 18% | 0.91 | -23% |
| Always plain momentum, same years | 19.7% | 18% | 0.97 | -25% |

Chosen: 2017: plain; 2018: plain; 2019: plain; 2020: plain; 2021: plain; 2022: plain; 2023: plain; 2024: plain; 2025: plain; 2026: plain
