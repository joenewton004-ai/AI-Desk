# Checks on the stock model from research/own_edge.py - generated tables

Holdout 2020-2026: 341 weeks, average excess +0.40% a week (t 2.3); after 0.05% costs each way +0.34% (average turnover 129% of the book a week). **Survivors-only prices.**

## 1. Year by year

| year | weeks | excess a week | t | weeks beat |
|---|---|---|---|---|
| 2020 | 51 | +0.45% | 0.7 | 55% |
| 2021 | 50 | +0.06% | 0.2 | 44% |
| 2022 | 51 | +0.40% | 0.7 | 51% |
| 2023 | 50 | +0.07% | 0.3 | 52% |
| 2024 | 50 | +0.72% | 2.6 | 66% |
| 2025 | 50 | +0.73% | 1.9 | 58% |
| 2026 | 39 | +0.38% | 0.6 | 54% |

## 2. What it buys (average rank of the picks, 0 = lowest in the 500, 1 = highest; 0.5 = typical)

| indicator | picks' average rank |
|---|---|
| vol_20d | 0.74 |
| atr_pct | 0.76 |
| ret_5d | 0.30 |
| ret_20d | 0.34 |
| ret_60d | 0.50 |
| ret_250d | 0.61 |
| vs_52w_high | 0.33 |
| vs_52w_low | 0.71 |
| vs_sma200 | 0.59 |
| volume_5_60 | 0.48 |
| rsi_14 | 0.33 |
| overnight_20d | 0.45 |

## 3. When it earns (SPY vs its 200-day average at the pick)

- SPY above its 200-day: 276 weeks, +0.25% a week (t 1.5)
- SPY below its 200-day: 65 weeks, +1.03% a week (t 2.0)

## 4. Without the market-wide indicators

Stock-only indicators: holdout +0.24% a week (t 1.3), after costs +0.19%.

## 5. Walk-forward (retrained each January on every earlier year)

| year | excess a week | t |
|---|---|---|
| 2020 | +0.45% | 0.7 |
| 2021 | +0.21% | 0.6 |
| 2022 | -0.89% | -1.2 |
| 2023 | +0.16% | 0.5 |
| 2024 | +0.67% | nan |
| 2025 | +0.67% | 1.9 |
| 2026 | +1.32% | 1.5 |

Walk-forward 2020-2026: +0.32% a week (t 1.5), after 0.05% costs +0.21%.

## 6. Costs

- 0.05% each way: +0.34% a week (+19.2% a year above the universe)
- 0.10% each way: +0.27% a week (+15.2% a year above the universe)
- 0.20% each way: +0.14% a week (+7.7% a year above the universe)

## 7. Stocks far below their 52-week high (where survivors-only prices flatter most)

- picks 40%+ below their 52-week high: 1,424 (22% of picks), average excess +0.36%
- the other picks: 4,910, average excess +0.38%
- share of the model's total excess from the deep fallers: 22%

## 8. Extra market exposure (beta)

- The picks' excess rises +0.53 for every 1.00 the universe moves in a week (they swing ~1.53x the average stock).
- Part of the +0.40% a week that is just that: +0.14% (the universe averaged +0.27% a week in 2020-2026).
- What's left (alpha): +0.26% a week, t 1.7, before costs.
- Up weeks: picks +1.18% vs the universe; down weeks -0.63%.
