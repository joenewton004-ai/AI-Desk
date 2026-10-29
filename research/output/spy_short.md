# What if the desk shorted SPY? - generated tables

Daily bars to 2026-10-28 (adjusted, so a short pays the dividends). Costs 0.01% each way, borrow 0.5%/yr.

## 1. Short-side swing rules (a short has to make money: the yardstick is zero)

| rule | SPY shorts/yr | days held | win rate | avg per short | t | 1993-2009 | 2010-2026 | QQQ+IWM+DIA 1st / 2nd half | passes |
|---|---|---|---|---|---|---|---|---|---|
| rally_below_200 | 2.6 | 3.3 | 64% | +0.42% | 1.8 | +0.54% | +0.23% | +0.39% / +0.42% | no |
| rally_any | 17.8 | 3.7 | 51% | -0.06% | -1.0 | -0.07% | -0.05% | -0.00% / -0.08% | no |
| ten_day_high_down | 3.2 | 5.0 | 40% | -0.14% | -0.5 | +0.17% | -0.69% | +0.15% / -0.24% | no |
| three_up_down | 2.9 | 5.0 | 40% | +0.12% | 0.4 | +0.23% | -0.06% | +0.05% / +0.33% | no |
| tweezer_top | 7.5 | 5.0 | 42% | +0.03% | 0.3 | +0.06% | +0.00% | +0.17% / -0.10% | no |

## 2. Whole strategies on SPY (the best short rule by t: rally_below_200)

| strategy | period | return/yr | Sharpe (above T-bills) | worst drop | long / short of the time |
|---|---|---|---|---|---|
| buy and hold | 1993-2026 | +10.9% | 0.52 | -55% | 100% / 0% |
| buy and hold | 1993-2009 | +7.5% | 0.29 | -55% | 100% / 0% |
| buy and hold | 2010-2026 | +14.1% | 0.80 | -32% | 100% / 0% |
| dips long only (RSI(2) < 10 above the 200-day) | 1993-2026 | +6.4% | 0.66 | -11% | 10% / 0% |
| dips long only (RSI(2) < 10 above the 200-day) | 1993-2009 | +8.5% | 0.83 | -8% | 9% / 0% |
| dips long only (RSI(2) < 10 above the 200-day) | 2010-2026 | +4.5% | 0.50 | -11% | 11% / 0% |
| dips long + rally_below_200 short | 1993-2026 | +7.5% | 0.71 | -11% | 10% / 3% |
| dips long + rally_below_200 short | 1993-2009 | +10.3% | 0.90 | -8% | 9% / 4% |
| dips long + rally_below_200 short | 2010-2026 | +4.9% | 0.52 | -11% | 11% / 3% |
| above the 200-day: long; below: cash | 1993-2026 | +8.9% | 0.55 | -24% | 77% / 0% |
| above the 200-day: long; below: cash | 1993-2009 | +8.6% | 0.44 | -22% | 70% / 0% |
| above the 200-day: long; below: cash | 2010-2026 | +9.2% | 0.67 | -24% | 84% / 0% |
| above the 200-day: long; below: SHORT | 1993-2026 | +4.2% | 0.18 | -47% | 77% / 23% |
| above the 200-day: long; below: SHORT | 1993-2009 | +5.8% | 0.21 | -35% | 70% / 30% |
| above the 200-day: long; below: SHORT | 2010-2026 | +2.7% | 0.16 | -43% | 84% / 16% |

## 3. Hedging the overnight sleeve with an SPY short each night

Beta of the sleeve's nights to SPY's night (2014-2019): 1.21. Hedge = short 1.21x SPY on each invested night, applied unchanged in 2020-2026.

| version | period | return/yr | Sharpe (above T-bills) | worst drop |
|---|---|---|---|---|
| overnight sleeve (as live) | 2014-2026 | +26.1% | 1.54 | -15% |
| overnight sleeve (as live) | 2014-2019 | +13.6% | 1.43 | -12% |
| overnight sleeve (as live) | 2020-2026 | +37.9% | 1.71 | -15% |
| overnight sleeve + SPY hedge | 2014-2026 | +8.8% | 0.66 | -25% |
| overnight sleeve + SPY hedge | 2014-2019 | -1.0% | -0.37 | -25% |
| overnight sleeve + SPY hedge | 2020-2026 | +17.9% | 1.07 | -11% |
