# Limit orders vs market orders - generated tables

34 current holdings, daily bars 2024-10-19 to 2026-10-19. Cost = price paid vs that day's official open, in basis points (1bp = 0.01%); positive = worse for us. Includes what missed limit orders cost when done later.

## Buy orders

| style | orders | fill rate | avg cost | median | worst 5% | when filled | when missed |
|---|---|---|---|---|---|---|---|
| market at the open | 16,932 | 100% | +0.0 | +0.0 | +0.0 | +0.0 | +nan |
| limit at prev close +0.00% | 16,932 | 80% | +4.9 | +0.0 | +228.1 | -24.6 | +125.7 |
| limit at prev close +0.25% | 16,932 | 86% | +2.9 | +0.0 | +181.5 | -18.0 | +134.2 |
| limit at prev close +0.50% | 16,932 | 90% | +2.1 | +0.0 | +120.2 | -13.4 | +141.9 |
| limit at prev close +1.00% | 16,932 | 94% | +0.9 | +0.0 | +0.0 | -7.7 | +146.0 |
| limit at prev close +2.00% | 16,932 | 98% | -0.4 | +0.0 | +0.0 | -3.2 | +133.1 |
| passive limit 0.10% below the open | 16,932 | 92% | +5.7 | -10.0 | +118.2 | -10.0 | +183.8 |
| passive limit 0.25% below the open | 16,932 | 85% | +4.0 | -25.0 | +190.3 | -25.0 | +166.2 |
| passive limit 0.50% below the open | 16,932 | 73% | +2.4 | -50.0 | +239.1 | -50.0 | +144.3 |
| passive limit 1.00% below the open | 16,932 | 51% | +2.5 | -100.0 | +276.3 | -100.0 | +110.8 |

## Sell orders

| style | orders | fill rate | avg cost | median | worst 5% | when filled | when missed |
|---|---|---|---|---|---|---|---|
| market at the open | 16,932 | 100% | +0.0 | +0.0 | +0.0 | +0.0 | +nan |
| limit at prev close -0.00% | 16,932 | 85% | -2.4 | +0.0 | +168.7 | -22.5 | +110.7 |
| limit at prev close -0.25% | 16,932 | 90% | -2.5 | +0.0 | +103.1 | -17.0 | +123.0 |
| limit at prev close -0.50% | 16,932 | 93% | -2.3 | +0.0 | +8.5 | -12.9 | +132.5 |
| limit at prev close -1.00% | 16,932 | 96% | -0.7 | +0.0 | +0.0 | -7.5 | +154.6 |
| limit at prev close -2.00% | 16,932 | 98% | +0.7 | +0.0 | +0.0 | -3.2 | +214.4 |
| passive limit 0.10% above the open | 16,932 | 92% | +4.7 | -10.0 | +101.6 | -10.0 | +184.8 |
| passive limit 0.25% above the open | 16,932 | 86% | +1.4 | -25.0 | +178.3 | -25.0 | +167.4 |
| passive limit 0.50% above the open | 16,932 | 75% | -1.8 | -50.0 | +231.8 | -50.0 | +142.8 |
| passive limit 1.00% above the open | 16,932 | 53% | -2.5 | -100.0 | +278.4 | -100.0 | +106.3 |

## Our first fills (2026-10-20, market orders, filled 9:32-9:33am)

34 fills: average +19.2bps vs the open, median +8.9, range -49 to +151; 15 filled below the open. Standard error of the average about 9bps.

