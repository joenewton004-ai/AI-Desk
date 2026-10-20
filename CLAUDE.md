# AI-Desk - notes for Claude Code

Rules-based trading desk. Pipeline: data -> strategy -> risk -> backtest/broker.
The user is learning (Power Platform background, basic coding). Explain
changes plainly and be honest about whether a strategy has a real edge.

## Commands
- Tests: `python -m pytest -q`
- Offline demo: `python -m ai_desk backtest --strategy all --source synthetic`
- Real data: `python -m ai_desk fetch SPY QQQ IWM GLD TLT IEF ^VIX ^IRX` (to `market_data/`, git-ignored)
- Stock screener: `python -m ai_desk screen` (Yahoo, cached a week in `data/fundamentals/`; the
  10-year check reads SEC filings, cached in `data/sec/`; `--no-history` skips it)
- Full robustness research: `python research/edges.py`, then update `research/FINDINGS.md` by hand
- Bottleneck scan: `python -m ai_desk bottleneck scan [--theme-only]`; research in
  `research/BOTTLENECK.md` (`python research/bottleneck_backtest.py`)
- Portfolio methods: `python -m ai_desk portfolio backtest|plan|run --method <name>[:share]`;
  evaluation of sma_crossover/pairs in `python research/methods.py` -> `research/METHODS.md`
- Index rotation vs the SPY sleeve: `python research/index_rotation.py` -> `research/INDEX_ROTATION.md`
- Screen backtest (point-in-time SEC data): `python research/screen_backtest.py`; strategy
  write-up in `research/THESIS.md` - update its numbers if the backtest changes

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
- Research notes (`research/notes/<date>/`): numbers come from
  `research/build_notes.py` (DATA blocks), never typed by hand. Prose must
  cite dated sources and say what to verify. Notes are research, not advice.
- EDGAR: only data.sec.gov is reachable here. Ticker->CIK must be verified
  via data.sec.gov/submissions. Never put the user's email in SEC_USER_AGENT
  without asking - it comes from .env.
- The 10-year check's thresholds live in `filters.LONG_RUN_RULES`. They were
  calibrated against the 10 researched companies; if you change them, re-run
  `long_run_check` on those and explain any verdict that flips.
- SEC requests go through `edgar._get` (shared rate limit, 8/s across threads).
- Screen backtest: compare the screen with the equal-weight universe first
  (same survivorship bias), SPY second. Prices are survivors-only - always
  say so when quoting results.
- Portfolio methods (`portfolio/methods.py`) return target weights decided at
  each close; every method in METHODS needs a no-lookahead test in
  `tests/test_portfolio.py`. Order rules live in `executor.plan_orders`
  (pure, unit-tested) - keep network calls out of it.
- The executor never trades without `run --execute`, and stays on Alpaca PAPER.
- Alpaca: only paper keys (PK...) are accepted; `AlpacaPaper` refuses live
  keys (AK...). Check connectivity with `python -m ai_desk broker status`.
  Never ask the user to paste keys into chat - they go in .env or the cloud
  environment's secrets.
- quality_screen holdings are locked in data/portfolio/quality_screen.json
  when orders are sent, and re-picked every 3 months (backtested: quarterly
  beat annual). Never re-pick on a dry run; frozen positions aren't resized.
- Theme maps (`bottleneck/themes.py`) are dated, human-curated inputs - keep
  `as_of` current and never present theme results as hindsight-free.
- Insider signal = open-market purchases only (Yahoo's "purchases" include
  grants). Congress data only from data/congress/trades.csv; say when absent.
- The bottleneck sleeve re-picks every 2 weeks and exits below its 100-day average
  (the scan's --ma, stored with the picks);
  an exited stock stays out until the next re-pick (recorded in its lock).
- Trade journal (`ai_desk/tradebook.py`, files in journal/, COMMITTED to git):
  every executed order is recorded with sleeve, rationale and exit reason;
  `python -m ai_desk journal sync|review|note|methods|propose|decide|amendments`.
  Commit journal/ and data/portfolio/ (the pick locks) after each trading session - containers
  are temporary, and a lost lock would re-pick early.
- Dashboard: https://claude.ai/artifact/PFSUn2FY2CarKh4Cxuni4y (Dashboard type). Refresh it with
  `journal export` (writes journal/dashboard/*.json), then upload each file as an asset and update
  the matching dataset's url/updated. Amendments and notes sent as dashboard comments go into the
  journal with `journal propose` / `journal note` - comments are the user's words, not orders.
- Methodology changes go through register.py amendments: proposed -> testing
  (backtest it) -> accepted/rejected by the user. Never change live method
  parameters without an accepted amendment.
