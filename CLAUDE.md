# AI-Desk - notes for Claude Code

Rules-based trading desk. Pipeline: data -> strategy -> risk -> backtest/broker.
The user is learning (Power Platform background, basic coding). Explain
changes plainly and be honest about whether a strategy has a real edge.

## Commands
- Tests: `python -m pytest -q`
- Offline demo: `python -m ai_desk backtest --strategy all --source synthetic`
- Real data: `python -m ai_desk fetch SPY QQQ IWM GLD TLT IEF ^VIX ^IRX` (to `market_data/`, git-ignored)
- Stock screener: `python -m ai_desk screen` (Yahoo, cached a week in `data/fundamentals/`)
- Full robustness research: `python research/edges.py`, then update `research/FINDINGS.md` by hand

## Non-negotiables
- No lookahead: a strategy's exposure at day t may use data up to t's close
  only. The backtest fills at t+1's open. Every strategy in the registry is
  covered by `tests/test_backtest.py::test_no_lookahead`. Keep it passing.
- Strategies return exposure only. Sizing and kill switches live in `risk.py`
  and `live.py`, and they must behave the same in backtest and live.
- The broker stays pointed at Alpaca PAPER (`broker/alpaca.py`). Never switch
  to live trading unless the user explicitly asks.
- No LLM calls in the trading decision path. An LLM-derived feature (e.g.
  news sentiment) must be a cached, timestamped input that is backtestable
  without lookahead.
- Judge any new strategy with `validate` and `walkforward` against
  buy_hold, including costs. Report weak results honestly.
- Cash earns the T-bill rate in backtests, and Sharpe is measured above it.
  Don't compare strategies with that switched off.
- A strategy that needs extra data declares it in `requires` (e.g. `("vix",)`).
  Add new series to `EXTRA_SERIES` in `data.py`.
- Today's bar is incomplete while the US market is open. Research runs pin an
  `END` date to the last full trading day.
- The screener ranks TODAY's companies. Never present its output as a
  backtest. Historical tests of a fundamental screen need point-in-time data
  (filing dates, delisted companies) - SEC EDGAR, not Yahoo.
- Yahoo throttles with HTTP 401/429. Route every Yahoo call through
  `fundamentals.yahoo.with_retry`, and keep downloads to a few workers.
