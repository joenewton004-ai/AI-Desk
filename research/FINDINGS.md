# Edge research: findings

**Data:** daily SPY, QQQ, IWM, GLD, TLT and IEF prices, plus the VIX and
13-week T-bill yields, from Yahoo Finance (adjusted for dividends and
splits). The data runs from 1993 to 16 Oct 2026.

**Rules for every test:** each signal is computed at the close and filled
at the next day's open. Every trade costs 3bps. Cash earns the T-bill rate,
and Sharpe ratios measure return above that rate. Regenerate everything
with `python research/edges.py`; the full tables are in
[`output/report.md`](output/report.md).

> Educational research, not financial advice. Past performance, especially
> in a backtest, does not predict future returns.

## Summary

| edge | verdict | why |
|---|---|---|
| **12-month momentum** (`momentum`) | ✅ **Best candidate** | Similar return to buy & hold with a much smaller worst drop. Holds up across periods, markets, parameter settings and costs. |
| **200-day trend** (`trend`) | ✅ Works, lower return | The same crash protection as momentum, but it gives up more return and more often signals falsely. Fails on small caps (IWM). |
| RSI(2) dip-buying (`rsi_reversion`) | ⚠️ Fading | Strong in the 1990s, now weak. Expensive to trade. |
| Turn-of-month (`turn_of_month`) | ❌ Unreliable | Disappeared for a decade (2007–2016). Costs eat it. |
| VIX "fear" filter (`vix_filter`) | ❌ Rejected | Sells after the crash, then misses the rebound. Worse than buy & hold everywhere. |
| Overnight-only | ❌ Untradeable | A real effect, but it trails buy & hold even before costs. |
| Multi-asset momentum rotation | ➖ Nothing special | Doesn't beat a plain 60/40 SPY/bonds portfolio on risk-adjusted return. |

**No strategy beat buy & hold on raw return.** The edges that work are about
*surviving crashes*: they keep returns close to the market while cutting the
worst loss roughly in half. That matters in practice. It's easier to stick
with a strategy through a −34% drawdown than a −55% one, and the bot
only works if you leave it running.

## The detail

### 1. Momentum and trend: the real edge is drawdown control

SPY, 1994–2026:

| | CAGR | Sharpe (±1 s.e.) | worst drawdown | trades |
|---|---|---|---|---|
| buy & hold | 10.8% | 0.51 ± 0.19 | −55% | 1 |
| momentum | 10.6% | 0.60 ± 0.19 | −34% | 23 |
| trend | 9.3% | 0.59 ± 0.19 | −25% | 97 |

Why momentum looks real:
- **Every sub-period:** its Sharpe was 0.65, 0.56 and 0.57 in 1994–2006, 2007–2016 and 2017–2026. Its worst drawdown was −19%, −25% and −34%, against −48%, −55% and −34% for buy & hold.
- **Other markets:** on QQQ, momentum earned 10.9% a year against 8.1% for buy & hold, with a worst drop of −41% against −83%. On IWM it had a similar return with half the drawdown.
- **Parameter plateau:** every lookback from 6 to 15 months scores between 0.51 and 0.62. The good result isn't one lucky setting.
- **Cost-proof:** it trades about once every 18 months. At 18bps per trade it still earns 10.5% a year.
- **Walk-forward:** tuned on 8 years and traded blind for each following year from 2001, it scored a Sharpe of 0.51 against 0.46 for buy & hold, with a −34% worst drop against −55%. Its return was 8.4% against 9.0%.
- **Published research:** time-series momentum is documented across asset classes back to the 1880s.

The honest caveats:
- **Not statistically proven.** The Sharpe gap (0.60 vs 0.51) is well inside one standard error. The evidence for momentum is consistency across tests, not one big number.
- **Few crashes to learn from.** Only 23 trades, covering a handful of real bear markets (2000–02, 2008, 2022). One more crash would shift these numbers.
- **Weak against fast crashes.** In 2020 it fell −34%, the same as buy & hold, because the crash was over before a monthly signal could react. It also lagged in 2017–2026, when there was no long bear market to dodge.
- **Taxes.** In a taxable account, every exit realises gains. That's not modelled here.

### 2. RSI(2) dip-buying is decaying

Its Sharpe was 0.74 in 1994–2006, 0.52 in 2007–2016 and 0.22 in 2017–2026. This
is the classic pattern of an edge disappearing once it's published and widely
traded. It also makes 525 trades, so costs went from 3bps to 18bps and its return
fell from 5.5% to 3.0% a year.

### 3. Turn-of-month: real in the 1990s, then gone

It earned a 0.60 Sharpe in 1994–2006, then 0.02 over the next ten years. With
about 24 trades a year, 18bps costs take its return to 1.3%. It also fails on
QQQ and IWM.

### 4. VIX filter: a lesson in why "obvious" ideas fail

Stepping aside when fear is high sounds sensible. In practice, VIX spikes *after*
the market has already fallen, and the best rebound days come while VIX is still
high. So the filter takes the loss and then misses the recovery. It underperformed
in every period, on every market, and with every parameter setting tested.

### 5. Overnight vs intraday

Since 1994, SPY has gained about 9.9% a year overnight (close to next open) and
0.8% a year during the trading day. The effect is real. But an overnight-only
strategy still trails buy & hold's 10.9% before costs, and it needs about 500
trades a year. Not worth it.

### 6. Rotating between SPY, QQQ, IWM, gold and bonds

The rule: each month, hold the strongest one or two assets by recent return,
but only if they beat T-bills, and put the rest in IEF bonds. Results from 2005:

- The variants earned 9.5–11.6% a year, with Sharpe ratios of 0.49–0.59 and worst drops of −25% to −40%.
- SPY buy & hold earned 11.0% (Sharpe 0.55, worst drop −55%).
- A plain **60/40 SPY/IEF** portfolio had the best Sharpe of all: 0.63, with a −31% worst drop. It needs no signals.

The best variant also benefits from hindsight: we picked QQQ for the universe
knowing it would boom. Rotation doesn't earn its complexity here.

## What this means for the desk

1. **Candidate for paper trading: `momentum` on SPY**, with default settings
   (12 months, checked monthly). It's simple, cheap to run and robust. Run it
   alongside buy & hold for comparison.
2. **Measure success by drawdown, not return.** Expect it to lag in strong bull
   markets and to justify itself in long bear markets.
3. **Ideas worth testing next:**
   - Momentum with bonds (IEF) instead of cash when out of the market.
   - Momentum on a SPY + IEF mix.
   - Combining momentum's exit signal with options, such as selling put spreads only while momentum is positive.

## Not covered by these tests

- **Taxes.** Exits realise gains, which matters in a taxable account.
- **Slippage on volatile opens.** The 3bps cost assumption may be too low on days when the market opens sharply.
- **Real data quality.** Yahoo's adjusted prices for dates before 2000 can contain errors.
- **Regime change.** None of these results guarantees the future will look like 1993–2026.
