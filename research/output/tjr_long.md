# TJR's model on ten years of QQQ and SPY 5-minute bars - generated tables

2016-01-04 to 2026-10-26, Alpaca SIP bars incl. pre-market and after-hours (New York time). QQQ stands in for NQ, SPY for ES. Levels: previous session high/low, overnight high/low (Asia and London sessions don't exist for stocks). Costs 0.01% of the price each way. R = the trade's risk.

| rules | trades | win rate | avg R (net) | t | avg R before costs | stopped out | 2016-20 R | 2021-26 R | profit factor |
|---|---|---|---|---|---|---|---|---|---|
| BOS, 2R | 3,401 | 37% | -0.088 | -3.9 | +0.007 | 57% | -0.092 | -0.085 | 0.87 |
| *control: same times, random direction (20 runs)* | | | -0.087 (range -0.117 to -0.034) | | | | | | |
| BOS, 3R | 3,401 | 32% | -0.110 | -4.3 | -0.015 | 61% | -0.115 | -0.105 | 0.84 |
| BOS, opposite liquidity | 3,401 | 35% | -0.116 | -4.5 | -0.021 | 59% | -0.126 | -0.107 | 0.83 |
| BOS, 2R, 1-hour bias | 1,282 | 38% | -0.085 | -2.4 | +0.005 | 56% | -0.126 | -0.044 | 0.87 |
| inverse FVG, 2R | 2,245 | 38% | -0.062 | -2.2 | +0.040 | 58% | -0.006 | -0.112 | 0.91 |
| inverse FVG, 2R, 1-hour bias | 862 | 38% | -0.075 | -1.7 | +0.021 | 57% | -0.067 | -0.083 | 0.88 |

By instrument and level swept (BOS, 2R):

| instrument | level | trades | avg R (net) | win rate |
|---|---|---|---|---|
| QQQ | overnight high | 552 | -0.086 | 35% |
| QQQ | overnight low | 444 | -0.027 | 40% |
| QQQ | prior day high | 440 | -0.166 | 32% |
| QQQ | prior day low | 327 | -0.084 | 39% |
| SPY | overnight high | 501 | -0.088 | 37% |
| SPY | overnight low | 427 | -0.226 | 32% |
| SPY | prior day high | 401 | +0.097 | 43% |
| SPY | prior day low | 309 | -0.123 | 36% |

By year (BOS, 2R, avg R net): 2016 -0.105 (327), 2017 -0.104 (333), 2018 -0.170 (314), 2019 -0.119 (294), 2020 +0.034 (323), 2021 -0.147 (311), 2022 -0.129 (308), 2023 -0.103 (324), 2024 +0.031 (313), 2025 +0.019 (310), 2026 -0.205 (244).

Average risk per trade: 0.34% of the price; costs are 0.095 R a trade on average.
