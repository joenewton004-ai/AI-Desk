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
- Winners study (what top performers looked like before their run): `python research/winners.py` ->
  `research/WINNERS.md`. Universe = top 750 at each date, survivors only: say so when quoting it.
- Weekly strategies (reversal, pullback, momentum on the top 750): `python research/weekly.py` ->
  `research/WEEKLY.md`. Survivors-only prices and close-to-close fills: both flatter it - say so.
- Plain momentum vs the bottleneck engine inside the desk: `python research/momentum_sleeve.py` ->
  `research/MOMENTUM_SLEEVE.md` (accepted as amendment 00e1f2b8, option 2: with the 100-day exit).
- Sikand-style 'asymmetric bets' rules (theme + growth + cheap vs peers + off highs): `python research/asymmetric.py`
  -> `research/ASYMMETRIC.md`. Tested, no edge; in the register as research-only (`register.RESEARCH_METHODS`).
- tradermonty/claude-trading-skills (MIT, reviewed 2026-10-21): two ideas tested, neither adopted. Circuit breaker
  (`python research/circuit_breaker.py` -> `research/CIRCUIT_BREAKER.md`, amendment c312f032 rejected by the user) and VCP
  breakout swing trading (`python research/swing.py` -> `research/SWING.md`; daily OHLCV cached in
  data/backtest/daily_ohlcv.pkl). Both research-only in `register.RESEARCH_METHODS`. Survivors-only: say so.
- ICT day trading (Silver Bullet on 5-min, Judas swing on 1h; with/without a quality-score side filter):
  `python research/ict.py` -> `research/ICT.md`. No edge; research-only. Yahoo keeps only 60 days of 5-min bars
  (cached in data/backtest/intraday_*.pkl); data.alpaca.markets is blocked by the network policy here.
- Peter Lynch's rules (PEG, Lynch ratio, categories, debt, inventory, buybacks) on point-in-time SEC data:
  `python research/lynch.py` -> `research/LYNCH.md` (features cached in data/backtest/lynch_features.pkl; ~30 min
  first run). No edge vs the equal-weight universe; research-only. Jim Simons/Medallion: desk research only
  (`research/SIMONS.md`) - its trades aren't public; Renaissance's 13F shows its other funds, not Medallion.
- Five short-term effects with next-open fills (weekly pullback, post-earnings drift from 10-Q filings, 52-week
  high, overnight returns; opening range breakout preview): `python research/swing_edges.py` and
  `python research/orb.py` -> `research/SWING_EDGES.md`. None is a strategy; the bad-earnings-surprise filter is
  the one follow-up idea (untested inside the desk). Events cached in data/backtest/earnings_events.pkl.
- Overnight drift per stock (Lou, Polk & Skouras): `python research/overnight.py` -> `research/OVERNIGHT.md`. Strong
  and persistent (t 6.4), profitable only if costs <= ~0.02% each way (break-even ~0.045%). Paper fills can't measure
  real auction costs - say so. Desk with it instead of SPY momentum: `python research/desk_overnight.py` ->
  `research/DESK_OVERNIGHT.md` (better only at <= ~0.02-0.03% costs; deeper worst drop).
- EMA9/VWAP crossover and Trend+Momentum+Confirmation (EMA20/50, VWAP, volume, breakout): `python research/vwap_ema.py`
  -> `research/VWAP_EMA.md` (cached 5m/1m/1h bars). No edge; research-only.
- Leveraged S&P fund (2x/3x, simulated + checked vs real SSO/UPRO) on SPY signals with strict risk rules:
  `python research/leveraged.py` -> `research/LEVERAGED.md`. Risk control works, no Sharpe edge; research-only.
- Limit orders vs market: `python research/limit_orders.py` -> `research/LIMIT_ORDERS.md`. Default stays
  market orders; `portfolio run --limit-cap 0.02` sends capped limits (free on average, avoids big gaps).
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
- From 2026-10-21 (evening run; brought forward from 2026-11-03 by the owner) the desk's 20% sleeve is `momentum`
  instead of `bottleneck` (amendment 00e1f2b8, accepted; `methods.DESK_SWITCH` / `preset()`): top 20 US companies above $10B by 6-month return
  (skipping the latest week), above their 200-day AND 100-day averages (entry filter, accepted 2026-10-21 -
  `research/MOMENTUM_ENTRY.md`; `python research/momentum_entry.py`), equal weight, re-picked every 28 days,
  sold below the 100-day average in between. Scan: `python -m ai_desk momentum scan`
  (`ai_desk/momentum_scan.py`). Bottleneck code stays for research and its history.
- Trade journal (`ai_desk/tradebook.py`, files in journal/, COMMITTED to git):
  every executed order is recorded with sleeve, rationale and exit reason;
  `python -m ai_desk journal sync|review|note|methods|propose|decide|amendments`.
  Commit journal/ and data/portfolio/ (the pick locks) after each trading session - containers
  are temporary, and a lost lock would re-pick early.
- Dashboard: https://claude.ai/artifact/PFSUn2FY2CarKh4Cxuni4y (Dashboard type). Refresh it with
  `journal export` (writes journal/dashboard/*.json), then upload each file as an asset and update
  the matching dataset's url/updated. Never point a dataset at an empty table (the dashboard counts it as a
  failed source): journal/dashboard/_manifest.json lists tables with rows; create a dataset when one first has rows. Amendments and notes sent as dashboard comments go into the
  journal with `journal propose` / `journal note` - comments are the user's words, not orders.
- Intraday prices (approved by the user 2026-10-21): `python -m ai_desk journal live` saves current Alpaca positions and
  prices to journal/live.json (never snapshots.jsonl - the scorecard uses closes only) and re-exports; the dashboard
  uses it while it's newer than the last close and the market is open, and says "(intraday)". Scheduled about
  10:07am, 12:07pm and 3:07pm New York on weekdays; it uploads only holdings, positions and summary. Read-only:
  never places orders.
- Scorecard (`ai_desk/scorecard.py`, criteria in `research/SUCCESS_CRITERIA.md` = `CRITERIA`):
  `journal snapshot` after each close (scheduled), then `journal scorecard` and `journal export`.
  The criteria were written before results came in - change them only via an amendment
  ("criteria"), never to make results look better. Always show Sharpe with its uncertainty range.
- Evening trading run (scheduled, weekdays 4:30pm New York, approved by the user 2026-10-20):
  `portfolio prepare --method desk` (runs a scan only if a re-pick is due today), then
  `portfolio run --method desk --execute --limit-cap 0.02 --limit-cap-side buy` (buys capped 2% above the
  last close; sells always market so exits go through). Orders queue for the next open.
- Watchlist (`ai_desk/watchlist.py`): each new lock saves the rest of that scan as a cohort in
  journal/watchlist.json (output/ isn't committed), measured from the same decision close as the
  picks. `journal watchlist` captures + reviews (daily task). Judge cohorts at their re-pick, not daily.
  Its daily check (`watchlist.diagnose`, logged to journal/watchlist_daily.jsonl) uses fixed rules: "too early"
  before the re-pick, "worth a test" only beyond chance. Baseline: `python research/near_misses.py` ->
  `research/NEAR_MISSES.md` (picks beat near misses ~2 re-picks in 3; no re-weighting helped in both halves).
  A "worth a test" is a reason to backtest, never to change the scoring directly. The overnight sleeve's cohort is
  saved by `overnight buy --execute` at each re-pick (ranks 21-60 + gate failures) and measured on close->next-open
  returns only; a retired sleeve's last cohort stays on record but isn't "current". Reviews drop today's bar while open.
- Overnight sleeve = the desk's 30% (amendment 330e76e0, accepted 2026-10-21; replaces SPY momentum), in the SAME
  Alpaca paper account (`ai_desk/overnight.py`, `python -m ai_desk overnight scan|status|buy|review|activate`):
  3:32pm New York (scheduled) `overnight buy --execute` = market-on-close buys, whole shares, equal weight, 30% of
  equity capped by cash less 1%; the 4:30pm desk run reads the fills into data/portfolio/overnight_book.json and sells
  them at the next open INSIDE the desk's own order for each stock (`net_with_desk`: one net order per symbol -
  Alpaca rejects opposite-side orders in one stock as wash trades). No buys while a book is unsold. Picks locked in
  data/portfolio/overnight.json, re-picked after each month-end. Active from data/portfolio/overnight_live.json
  (2026-10-21); from then `methods.preset("desk")` = quality 50% + momentum 20% (SPY momentum dropped, no rescaling).
  Journal in journal/overnight/ - commit it with data/portfolio/. Paper fills can't measure real auction costs.
- Methodology changes go through register.py amendments: proposed -> testing
  (backtest it) -> accepted/rejected by the user. Never change live method
  parameters without an accepted amendment.
