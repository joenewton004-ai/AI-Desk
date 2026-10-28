# The trader-skill desk: day-trader-skill's rules alongside the desk

_October 2026. Source: [Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) (MIT,
commit 3d0f4ef, 2026-10-20; code read, not installed). Live ledger: `ai_desk/skill_desk.py`. Backtest:
`research/skill_desk.py` -> [`output/skill_desk.md`](output/skill_desk.md). Research, not advice._

## What the owner chose (2026-10-28)

- **A separate ledger.** It's a virtual $5,000 account, replayed after each close on real Alpaca 5-minute prices.
  - It sends no orders and never touches the Alpaca paper account the desk trades in.
  - Sharing that account would mix the two results: the overnight sleeve uses nearly all the cash each night and
    buys at 3:55pm, the minute the skill's trades must be flat.
- **The skill's own rules, made automatic.** The skill expects a person to say yes to each trade; here its rules
  decide. That keeps it inside the desk's rule of no AI judgement in trading decisions, and makes it testable.

## The rules (copied from the skill's code and default settings)

| step | the skill's part | rule |
|---|---|---|
| scan | trader-scanner `orb` | 15-minute opening range; a hit = the first completed 5-minute bar to close above the range high |
| entry | trader-entry | the hit's bar must close between 9:45 and 15:30; filled at the next bar's open |
| exit | trader-exit (orb defaults) | stop at the range's middle, target 2 x the risk, out by 15:55 win or lose |
| size | trader-budget | shares = $50 max loss / risk per share; at most $4,000 an order and 75% of the $5,000; 10% cash kept |
| limits | trader-risk | 3 trades a day at most, none after -$150 in a day, one trade per stock a day |

**Differences from using the skill by hand (fixed in advance):**
- **Which breakout gets taken.** When several stocks break out together, a person would choose; here it's the
  earliest, then the most traded so far.
- **The universe.** The skill scans ~5,900 stocks; here it's the desk's top 100, the only stocks with ten years of
  bars to test on.
- **The fill.** An automatic order fills at the next bar's open, not at the close it just saw.

## Backtest, 2016-2026 (top 100 at each date, survivors-only)

| rules | costs each way | trades/yr | win rate | return/yr | Sharpe (95% range) | worst drop |
|---|---|---|---|---|---|---|
| 2R target (live) | 0.02% | 710 | 40% | -9.7% | -0.59 (-1.24 to 0.05) | -73% |
| 2R target (live) | 0.05% | 670 | 39% | -26.8% | -1.87 | -97% |
| 1R target (README example) | 0.02% | 730 | 51% | -12.8% | -0.97 | -80% |
| SPY buy and hold | - | - | - | +15.0% | 0.75 | -34% |

- **Before costs the rule earns almost nothing.**
  - The average trade makes +0.03 of its risk (+$1.50 on a $50 risk).
  - Costs on a ~$3,000-4,000 order are about $1.40-2.00, so it loses after costs.
- **The full sample says the same.** Every breakout, without the account's limits, comes to 156,613 trades at -0.037%
  each after 0.02% costs (t -13). It loses in 2016-20 and in 2021-26 alike.
- **The 1R target changes the win rate, not the result.** It turns a 40% win rate into 51%, but it still loses.
- **The skill's own example says the same thing.** Its Time Machine called the worked Tesla trade "close to a coin
  flip".

## What to expect from the ledger

- **Most likely a slow loss.** Expect something like 0.5-1% of the $5,000 a month, with good and bad days mixed in.
- **First check, 2026-10-27 (not counted, before the start):** ADI and TMO hit their targets and WDC was flat at
  15:55, for +$71 in total. Single days mean little.
- **Judge it after about 3 months (~180 trades),** against the backtest's -$0.48 a trade, not day by day.
- **It doesn't change the desk.** Trading it with real orders would need its own account and an amendment.

## To verify

- **Real fills.** Live fills at a stop can be worse than the stop price in a fast market. The ledger assumes the
  stop price, so it flatters the rule slightly.
- **Small stocks.** The skill's whole-market scan includes small, volatile stocks the backtest can't cover (no
  delisted-inclusive intraday data). Small stocks usually cost more to trade, not less.
