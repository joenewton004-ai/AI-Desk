# TJR's trading method, quantified and tested

_October 2026. Code: `research/tjr.py`. Tables: [`output/tjr.md`](output/tjr.md). Research, not advice._

## What he does and trades

TJR (TJR Trades) is a social-media day trader and educator. **His own rulebook isn't public**; this is what the
sources agree on, all of them third-party write-ups and community TradingView scripts:

| | |
|---|---|
| **Instruments** | US index futures: Nasdaq-100 E-mini (**NQ**) and S&P 500 E-mini (**ES**) |
| **When** | The New York open, roughly 9:30-11:00am New York |
| **Style** | ICT-style "smart money" day trading: in and out the same day |
| **Liquidity** | Prior day high/low, session highs/lows (Asia, London, New York), the overnight high/low, equal highs/lows |
| **Setup** | Price **sweeps** a liquidity level (trades through it and snaps back), **shifts structure** the other way (a break of structure, or an "inverse fair value gap"), then he enters, often on a pullback |
| **Risk** | Stop beyond the sweep's extreme; target the liquidity on the other side; risk kept constant in "R" (units of the stop distance); rules written before the open |
| **Timeframes** | Bias from 1-hour or 15-minute charts; entries on 1-5-minute charts |

Unverified: income figures quoted in transcript summaries (e.g. "$156,000 in a month"). Much of his business is
education and a trading community, which doesn't prove the trading itself. Sources:
[forex.in.rs](https://www.forex.in.rs/tjr-trader-strategy/),
[snappchart.app](https://www.snappchart.app/blog/beginner-playbook/tjr-ict-trading-strategy),
[transcript summary](https://sozai.app/transcript/path-to-profitability-tjr-strategy/),
[TradingView: TJR v4 Strategy](https://it.tradingview.com/script/xXrbltSH-TJR-v4-Strategy/),
[TradingView: TJR Seek and Destroy](https://es.tradingview.com/script/9yqF7p26-TJR-SEEK-AND-DESTROY),
[TradingView: TJR Strategy Indicator](https://kr.tradingview.com/script/IYLMKdC6-TJR-Strategy-Indicator/)
(read 2026-10-26; some pages only via search snippets).

## The test

Each part above as a fixed rule, on NQ and ES futures:
- **Liquidity:** the previous session's high/low, the Asia (8pm-midnight) and London (2-5am) highs/lows, and the overnight high/low.
- **Sweep:** a bar between 9:30 and 11:00 trades through a level and closes back inside.
- **Confirmation:** within 30 minutes, a close past the 3-bar swing before the sweep (break of structure), or through the move's latest fair value gap (inverse FVG).
- **The trade:** enter at the next bar's open, stop beyond the sweep, target 2R / 3R / the opposite liquidity. Optional 1-hour 50-period trend filter. One trade per instrument per day.
- **Costs:** 1 tick slippage each way plus commission.
- **Control:** the same trades in a random direction.

### 5-minute bars (Aug 17 - Oct 26, 2026: about 49 trading days, all Yahoo keeps)

| Rules | Trades | Win rate | Avg R after costs | t | $ per contract |
|---|---|---|---|---|---|
| Break of structure, 2R | 76 | 39% | −0.05 | −0.4 | −$8,412 |
| Break of structure, 3R | 76 | 36% | −0.13 | −0.9 | −$14,965 |
| **Break of structure, opposite liquidity** | 76 | 43% | **+0.05** | 0.3 | +$1,715 |
| Break of structure, 2R, with 1-hour bias | 43 | 42% | +0.03 | 0.2 | +$1,122 |
| Inverse FVG, 2R | 46 | 33% | −0.18 | −1.0 | −$4,718 |
| *Random direction, same times (20 runs)* | | | *−0.08 (−0.26 to +0.12)* | | |

### Hourly bars (June 2024 - Oct 2026: a coarse version; hourly bars blur the sweep and the exits)

| Rules | Trades | Avg R after costs | t |
|---|---|---|---|
| Break of structure, 2R | 264 | −0.06 | −1.3 |
| Break of structure, 2R, with 1-hour bias | 90 | −0.01 | −0.1 |
| *Random direction (20 runs)* | | *−0.00 (−0.07 to +0.08)* | |

## What it means

- **No edge in the rules.** Every version lands between −0.18R and +0.05R a trade after costs, inside the range
  random-direction trades produced at the same times (−0.26R to +0.12R).
- **It's the same result as the ICT test** (`research/ICT.md`: Silver Bullet and Judas swing were coin flips). TJR's
  model is a close relative.
- **The per-level breakdown looks tempting but is noise.** London highs +0.70R over 16 trades, London lows −0.83R
  over 9; in the 2-year hourly data the pattern doesn't repeat.
- **Costs matter less here than in the stock tests.** Futures are cheap to trade (about 0.02R a trade), so the
  problem isn't costs: the setups don't predict direction.

## What this can't capture

- **His rules aren't published.** These are the community's version, made precise.
- **Discretion is invisible to a test.** That includes which sweep counts, whether the structure shift looked
  "clean", and skipping days with news. That judgement may well be his skill, but rules can't test it.
- **The data is thin.** 49 days of 5-minute bars is about 76 trades; even a real +0.2R edge would struggle to show up.
  The 2-year version uses hourly bars, which his method doesn't. **Since re-run on ten years (below).**
- **Yahoo's NQ=F/ES=F are continuous front-month series**, so there are small jumps at contract rolls.

## Re-run on ten years of 5-minute bars (October 2026)

Code: `research/tjr_long.py`. Tables: [`output/tjr_long.md`](output/tjr_long.md).

Alpaca's market data, now reachable, has no futures. It does have 5-minute bars for QQQ and SPY from January 2016 to
October 2026, including pre-market (from 4am) and after-hours (to 8pm). QQQ tracks the Nasdaq-100, as NQ does, and SPY
tracks the S&P 500, as ES does.

The rules are the same as the first test, except:
- **Liquidity levels:** the previous session's high and low, and the overnight high and low (after-hours plus
  pre-market). US stocks don't trade in the Asia or London sessions, so those levels are dropped.
- **Costs:** 0.01% of the price each way.

| Rules | Trades | Win rate | Avg R after costs | t | Avg R before costs | 2016-20 | 2021-26 |
|---|---|---|---|---|---|---|---|
| Break of structure, 2R | 3,401 | 37% | −0.088 | −3.9 | +0.007 | −0.092 | −0.085 |
| Break of structure, 3R | 3,401 | 32% | −0.110 | −4.3 | −0.015 | −0.115 | −0.105 |
| Break of structure, opposite liquidity | 3,401 | 35% | −0.116 | −4.5 | −0.021 | −0.126 | −0.107 |
| Break of structure, 2R, 1-hour bias | 1,282 | 38% | −0.085 | −2.4 | +0.005 | −0.126 | −0.044 |
| Inverse FVG, 2R | 2,245 | 38% | −0.062 | −2.2 | +0.040 | −0.006 | −0.112 |
| Inverse FVG, 2R, 1-hour bias | 862 | 38% | −0.075 | −1.7 | +0.021 | −0.067 | −0.083 |
| *Random direction, same times (20 runs)* | | | *−0.087 (−0.117 to −0.034)* | | | | |

- **With 45× more trades the answer is clearer: no edge.** Before costs, every version is within a few hundredths
  of an R of zero. The main rule (+0.007R before costs) loses exactly as much as random-direction trades at the same
  times.
- **Costs decide the result.** The stops are tight, about 0.34% of the price, so 0.01% each way costs about 0.1R a
  trade. On futures it would be cheaper, roughly 0.02-0.04R, but zero minus a smaller cost is still below zero.
- **Only 3 of 11 years were positive** (2020, 2024 and 2025, each a few hundredths of an R), and no level swept
  holds up. The best of the eight level-and-instrument cells (SPY prior-day high, +0.10R over 401 trades) is the kind
  of result that turns up by chance among that many.
- **What this can't capture:**
  - QQQ/SPY aren't NQ/ES. The futures trade overnight, so the Asia and London levels he uses exist only there.
  - His discretion.

## Verdict

**No edge in TJR's model as fixed rules**, now on ten years of data as well as the original 49 days, and consistent
with the ICT test. It's recorded in the register as research-only
(`tjr_model`). It doesn't fit the desk either: the desk trades stocks once a day on Alpaca paper, not futures intraday.
