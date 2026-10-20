# What success looks like - written before the results

_Set 2026-10-20, the day paper trading started. Code: `ai_desk/scorecard.py`
(`CRITERIA` holds the same numbers). Change these only through an amendment
(`journal propose criteria "..."`), so we judge against what we said in
advance and not what we feel later. Educational research, not financial advice._

## The question

**Does the desk beat what we'd get for no effort (SPY), after costs, without
more risk than planned?** Making money isn't the test. In a rising market almost
everything makes money.

| Part | It's working if… | Compared with |
|---|---|---|
| Whole desk | More return per unit of risk than SPY, and a shallower worst drop | SPY |
| Quality screen (50%) | Its picks beat the average S&P 500 company | RSP (equal-weight S&P 500) |
| Bottleneck (20%) | It beats SPY after its higher trading costs, and its exits save money | SPY |
| SPY momentum (30%) | It loses less in crashes, at a small cost in rising markets | SPY |

## Three tiers, judged on different clocks

### Tier 1 - process (from week one)
The things we can actually improve.

| Metric | Target |
|---|---|
| Slippage: fill price vs that day's open, $-weighted | ≤ 10bps average once there are 20+ fills (the backtest assumes 3bps) |
| Fill vs the signal close | Information only: the overnight gap, which the backtest includes |
| Orders rejected, canceled or expired | 0 |
| Orders still waiting after the open | 0 |

### Tier 2 - behaviour (from about 3 months)
Is it doing what the backtest said it would?

| Metric | Red flag |
|---|---|
| Drawdown from the peak | Warning at −15%. The executor halts all trading at −20% until reviewed |
| Cumulative return vs the backtest's 90% range | Outside the range means investigate before changing anything |
| Desk vs SPY over 12 months | More than 10 points behind |
| Each sleeve vs its benchmark over 12 months | More than 10 points behind |
| Bottleneck: return 20 days after an exit | Above +3% on average over 10+ exits, meaning the exit sells stocks that bounce back |

The backtest's range uses the desk's 2014-2026 backtest: 16.3%/yr, volatility
16.5%, Sharpe 0.89, worst drop −23%. That backtest uses survivors-only prices
and a theme map written with hindsight, so expect less. **Landing in the lower half
of the range would be normal, not a failure.**

### Tier 3 - edge (from 1 year; trust it after 3-5)

| Metric | Target |
|---|---|
| Sharpe (above T-bills) | At least SPY's over the same period |
| Return vs SPY since launch, after costs | ≥ 0 |
| Worst drop vs SPY's | Shallower |
| Upside capture: share of SPY's up months we catch | ≥ 80% |
| Downside capture: share of SPY's down months we take | ≤ 70% |

## How much to trust a Sharpe ratio

Roughly, the true Sharpe is the measured one ± 1.645 × √((1 + ½S²) ÷ years),
90% of the time. For a measured 0.9:

| After | The true Sharpe could be |
|---|---|
| 1 year | −0.3 to 2.1 |
| 3 years | 0.2 to 1.6 |
| 5 years | 0.4 to 1.4 |

So a great or a terrible first quarter says almost nothing about the edge. The
dashboard prints this range next to the Sharpe so it's never read alone.

## Review rhythm

| When | Look at | Decide |
|---|---|---|
| Daily (automatic) | Snapshot, fills, red flags | Nothing, unless a red flag trips |
| Weekly | Tier 1 | Fix process problems (orders, slippage) |
| Quarterly (with the screen re-pick) | Tier 2, each sleeve vs its benchmark, exits | Propose amendments; test them with a backtest first |
| Yearly | Tier 3 | Keep, change or drop a sleeve |

**Rules for changing things:**
- Never change a method because of one bad month.
- Process fixes (tier 1) can happen any time.
- Method changes need a backtest *and* paper evidence pointing the same way,
  and your approval (proposed → testing → accepted/rejected).
