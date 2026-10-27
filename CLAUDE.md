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
  `python research/ict.py` -> `research/ICT.md`. No edge; research-only. Re-run on 2016-2026 Alpaca 5-min bars for the
  point-in-time top 100 (`python research/ict_long.py`, after `python research/alpaca_bars.py --5min --workers=6 <names>`;
  ~2 hours of downloads): still no edge, both halves. Yahoo keeps only 60 days of 5-min bars
  (cached in data/backtest/intraday_*.pkl); years of minute bars now come from research/alpaca_bars.py.
- TJR's model (NQ/ES futures, New York-open liquidity sweep + break of structure / inverse FVG): `python research/tjr.py`
  -> `research/TJR.md` (bars cached in data/backtest/futures_intraday.pkl: 5m ~60 days, 1h 2 years). No edge; research-only.
  Re-run on QQQ/SPY 5-min bars incl. pre-market, 2016-2026 (`python research/tjr_long.py`): no edge.
- George Soros (desk research + cross-asset trend on 9 ETFs): `python research/soros.py` -> `research/SOROS.md`.
  Long-only trend: Sharpe 0.79, worst -9% vs SPY 0.67/-51% - risk control, not return. Research-only.
- Ross Cameron gap-and-go (large caps only - no small-cap history): `python research/cameron.py` -> `research/CAMERON.md`.
  Gaps lose after costs; only hindsight volume helps. Research-only.
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
- Overnight sleeve vs the fear index (VIX levels/changes, SPY 200-day, tech-vs-defensive days; defensive/low-beta lists):
  `python research/overnight_regime.py` -> `research/OVERNIGHT_REGIME.md`. Defensive lists don't earn overnight; cash
  when SPY < 200-day or on a day tech lags defensives most: Sharpe 1.03 vs 0.70 (both halves; ~20 rules tested).
  Follow-up `research/overnight_picks_check.py`: the picks' own fall since the open beats tech-vs-defensive (1.31 with
  the SPY rule) - live from 2026-10-23 (amendments 7a8b29ec + 9b951502). Per-stock skipping instead of the group rule
  (`research/overnight_perstock.py`): worse alone (1.43 vs 1.54); group + skip picks down 3%+ 1.64 (inside noise). Not live.
- EMA9/VWAP crossover and Trend+Momentum+Confirmation (EMA20/50, VWAP, volume, breakout): `python research/vwap_ema.py`
  -> `research/VWAP_EMA.md` (cached 5m/1m/1h bars). No edge; research-only.
- Leveraged S&P fund (2x/3x, simulated + checked vs real SSO/UPRO) on SPY signals with strict risk rules:
  `python research/leveraged.py` -> `research/LEVERAGED.md`. Risk control works, no Sharpe edge; research-only.
- The 'big green line' (@pb_ema on Instagram: S&P 500 above a moving average, cash below; 50-250 day EMA, 200-day SMA,
  10-month SMA): `python research/green_line.py` -> `research/GREEN_LINE.md`. Halves the worst drop, 1-3%/yr less return,
  same Sharpe on SPY with dividends (the price-only index flatters it). Research-only.
- Candle patterns on 10 years of Alpaca minute bars (SPY, NVDA; engulfing, hammer/star, inside bar, opening-range breakout,
  intraday momentum): `python research/candles.py` -> `research/CANDLES.md`. No edge; NVDA's ORB (t 3.2) fails on QQQ + the
  10 largest companies of 2016 (hindsight). Research-only. Minute bars: `python research/alpaca_bars.py SYM ...` (Alpaca SIP
  feed via the network secret for data.alpaca.markets; cached in data/backtest/alpaca_1m_<SYM>.pkl, from 2016).
- Daily candles + SMA trend + RSI (72 pre-registered rules, development/holdout, ETFs and point-in-time top-100 stocks):
  `python research/candle_rsi.py` -> `research/CANDLE_RSI.md`. Candles add nothing. Lead (not live, needs an amendment
  and a desk test): top-100 stocks above SMA200 with RSI(14)<30, sell above SMA5 (+1.0-1.2%/trade both periods,
  robust to 25/35 and 4x costs; survivors-only - say so). Inside the desk (amendment 661549dd, testing):
  `python research/desk_rsi.py` -> `research/DESK_RSI.md`: +0.035 Sharpe at 0.05% costs, fails its pre-set rule at 0.20%
  (2020-26 Sharpe 1.266 vs 1.268); recommended reject until the market-on-open test shows real open-fill costs.
- Mark Minervini's SEPA (Trend Template + RS, point-in-time EPS/sales growth from SEC, base breakout, 7.5% stop to
  break-even, 50-day exit, market filter): `python research/minervini.py` -> `research/MINERVINI.md` (growth cached in
  data/backtest/minervini_fund.pkl). No edge vs the equal-weight universe; research-only. Survivors-only: say so.
  Follow-up (pivot buy-stops + intraday stop orders, 5 positions, smaller half, looser growth):
  `python research/minervini_checks.py` -> same write-up. Small caps/IPOs need delisted-inclusive data (not available).
- Momentum top 10 instead of top 20 inside the desk: `python research/desk_top10.py` -> `research/DESK_TOP10.md`
  (desk Sharpe 1.06 vs 0.98 at 0.02% overnight costs; both halves, 11/13 years; not live - needs an amendment).
- Ranking windows (1 day to 12 months) for the overnight and momentum sleeves: `python research/lookbacks.py` ->
  `research/LOOKBACKS.md`. Short windows don't work; the live 12-month (overnight) and 6-month (momentum) windows are at
  or near the best. Leads within noise: daily re-pick / plain 12-month return for overnight - tested as live in
  `research/overnight_v2.py` (Sharpe 1.54 vs 1.31 with the checks, t 1.1) and live from 2026-10-23 (amendment 82c84226).
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
  `journal export` (writes journal/dashboard/*.json; pnl_days = the Overview's P&L calendar, daily closes vs
  `dashboard.START_EQUITY` for the first day), then upload each file as an asset and update
  the matching dataset's url/updated. Never point a dataset at an empty table (the dashboard counts it as a
  failed source): journal/dashboard/_manifest.json lists tables with rows; create a dataset when one first has rows. Amendments and notes sent as dashboard comments go into the
  journal with `journal propose` / `journal note` - comments are the user's words, not orders.
- Intraday prices (approved by the user 2026-10-21): `python -m ai_desk journal live` saves current Alpaca positions and
  prices to journal/live.json (never snapshots.jsonl - the scorecard uses closes only) and re-exports; the dashboard
  uses it while it's newer than the last close and the market is open, and says "(intraday)". Scheduled about
  10:07am, 12:07pm and 3:07pm New York on weekdays; it uploads only holdings, positions and summary. Read-only:
  never places orders.
- Morning fills (scheduled, weekdays 9:41am New York, set up by the user 2026-10-22; read-only): `journal sync`,
  `journal review`, `overnight review`, `journal live`, then uploads trades, closed, sleeves, summary, holdings,
  positions and fills - records the open's sales (the overnight sleeve's night) the same morning.
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
  3:54pm New York (scheduled) `overnight buy --execute` = market buys in the 3:55-3:59pm window (amendment dc6335fa:
  Alpaca paper filled market-on-close orders only in part), whole shares, equal weight, 30% of equity capped by cash
  less 1%; the evening run before a re-pick day ranks ahead (`portfolio prepare` -> journal/overnight/scan_cache.json); the 4:30pm desk run reads the fills into data/portfolio/overnight_book.json and sells
  them at the next open INSIDE the desk's own order for each stock (`net_with_desk`: one net order per symbol -
  Alpaca rejects opposite-side orders in one stock as wash trades). No buys while a book is unsold. Picks locked in
  data/portfolio/overnight.json. Since 2026-10-23 (amendment 82c84226): ranked by the plain 12-month return (adjusted
  closes; was the average overnight return) and re-picked DAILY - the evening run's `portfolio prepare` ranks on that
  close (journal/overnight/scan_cache.json) and the next afternoon's buy uses it; without a newer ranking it keeps the
  held picks (it never ranks inside the buy window, except the very first pick). Watchlist cohort monthly. Active from data/portfolio/overnight_live.json
  (2026-10-21); from then `methods.preset("desk")` = quality 50% + momentum 20% (SPY momentum dropped, no rescaling).
  Journal in journal/overnight/ - commit it with data/portfolio/. Paper fills can't measure real auction costs.
  Regime checks (`overnight regime`): no buys - cash for the night - when SPY is below its 200-day average (amendment
  7a8b29ec) or tonight's 20 picks are down 2.0%+ since today's open (`PICKS_DAY_CUTOFF`, amendment 9b951502, accepted
  2026-10-23; replaced 7a8b29ec's tech-vs-defensive test - `research/overnight_picks_check.py`). Checked at the buy,
  after the picks are set. A failed check buys as usual and says so. Never switch to defensive stocks instead.
  Market-on-open A/B TEST (amendment e43f2959, testing from 2026-10-27; `overnight.OPG_TEST`): each evening run leaves a
  fixed coin-flip half of the overnight-ONLY holdings (`opg_group`) out of its orders and queues them in the book; the
  9:05am scheduled `overnight open-sell --execute` sends them as market-on-open (Alpaca rejects opg 9:28am-7pm); unfilled
  shares (`unsold_opg`) go out with the next evening's orders. `overnight review` prints the comparison (`opg_ab`) and
  the rule fixed in advance: after 10 trading days adopt market-on-open if >= 0.10 points cheaper and >= 95% filled.
  Its fills are also trade-journal lines (sleeve overnight_drift): the buys from `confirm_book`, the next-open sale as
  its own line sharing the desk's netted order id (`record_orders(overnight_book=...)`); lots match a sleeve's own
  buys first, so the desk's P&L stays separate.
- Methodology changes go through register.py amendments: proposed -> testing
  (backtest it) -> accepted/rejected by the user. Never change live method
  parameters without an accepted amendment.
