# AI-Desk

A small, honest, **rules-based** trading desk for the S&P 500 (SPY), built to
be extended to options as you learn.

```
data  ->  strategy (signal)  ->  risk (sizing + kill switches)  ->  backtest  or  broker (paper)
```

Claude Code is the *engineer* here: it helps you write, test and review
strategies. The strategies themselves are plain, deterministic rules you
can backtest and explain. No LLM makes trade decisions.

**Trading journal dashboard:** https://claude.ai/artifact/PFSUn2FY2CarKh4Cxuni4y
(positions, trades with notes, methods and amendments; refreshed with `python -m ai_desk journal export`)

> Educational software, not financial advice. Most strategies that look good
> in a backtest fail live. Paper trade for months before risking money.

---

## 1. Setup (one time)

You need Python 3.10+. In a terminal, from this folder:

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -e ".[dev,plot]"
python -m pytest            # should say all tests passed
```

## 2. Your first backtest

```bash
python -m ai_desk backtest --strategy all --start 2000-01-01 --out output --plot
```

This downloads SPY daily prices since 2000 (cached in `data/`), runs every
strategy, and prints a comparison against buy & hold. `output/equity.png`
shows the equity curves and drawdowns.

To save prices as CSV files (for repeatable research, or for working
offline):

```bash
python -m ai_desk fetch SPY QQQ IWM GLD TLT IEF ^VIX ^IRX
python -m ai_desk backtest --strategy all --source market_data/SPY.csv
```

`market_data/` is git-ignored. Yahoo's data is for personal use, so don't
publish it.

No internet? Add `--source synthetic` to use fake data. That's good for
learning the tools, but meaningless for judging a strategy.

### Reading the results

| metric | what it tells you |
|---|---|
| `cagr` | average yearly growth |
| `sharpe` | return per unit of risk. Buy & hold SPY is roughly 0.5. Above 1.0 long term is rare, so be suspicious |
| `max_drawdown` | worst peak-to-trough loss. Ask yourself: could you live through it without switching the bot off? |
| `time_in_market` | how often you're exposed. Less time in the market means less risk, and spare cash for other strategies |
| `costs_pct_of_start` | what trading friction cost you |

## 3. The strategies included

| name | idea | parameters |
|---|---|---|
| `buy_hold` | the benchmark everything must beat | none |
| `trend` | hold SPY above its 200-day average, cash below. Aims to sit out big crashes | `lookback`, `band` |
| `rsi_reversion` | buy sharp 2-day dips inside an uptrend, sell the bounce | `rsi_window`, `entry_rsi`, `exit_sma`, `trend_sma` |
| `momentum` | hold while the 12-month return is positive, checked monthly | `lookback`, `skip`, `monthly` |
| `vix_filter` | step aside when the VIX spikes, re-enter when it calms down | `exit_above`, `enter_below` |
| `turn_of_month` | hold only the last day and first 3 days of each month | `days_before`, `days_after` |

**Which ones hold up on real data?** See
[`research/FINDINGS.md`](research/FINDINGS.md). In short, `momentum` and
`trend` cut the worst crash losses roughly in half while keeping most of the
market's return. The others failed the robustness tests.

Change parameters with `--param`:

```bash
python -m ai_desk backtest --strategy trend --param lookback=150 --param band=0.02
```

Add risk rules with flags. They work with any strategy:

```bash
--target-vol 0.12     # size positions to ~12% annual volatility
--max-dd-halt 0.25    # circuit breaker: go to cash and stop after a 25% drawdown
--commission-bps 1 --slippage-bps 2   # trading costs (defaults shown)
--cash-rate auto      # cash earns the T-bill rate (default); or none, or e.g. 0.03
```

By default, uninvested cash earns the T-bill rate (Yahoo's `^IRX`), and
Sharpe/Sortino measure returns *above* that rate. Earning interest on cash
isn't skill, so it shouldn't make a strategy look better.

## 4. Don't fool yourself: validation

Try 50 parameter combinations and one will look brilliant **by luck**.
These two commands check whether an edge is real.

**Out-of-sample split.** Tune on data before 2015, then see how the strategy does after:

```bash
python -m ai_desk validate --strategy trend --split 2015-01-01 --grid lookback=100,150,200,250 --grid band=0,0.01,0.02
```

The sensitivity table should show a broad *plateau* of decent results. If
only one exact setting works, it's noise.

**Walk-forward.** This is the most honest test. It optimises on 5 years,
trades the next year blind, then slides forward a year and repeats:

```bash
python -m ai_desk walkforward --strategy trend --grid lookback=100,150,200,250 --train-years 5
```

Rules of thumb before trusting a strategy:
- It holds up out-of-sample and in walk-forward, not just in-sample.
- It survives doubled costs (`--slippage-bps 5`).
- You can explain *why* the edge exists and who is on the other side of the trade.
- It has at least ~100 trades. Fewer than that is mostly luck.

### Full edge research

```bash
python -m ai_desk fetch SPY QQQ IWM GLD TLT IEF ^VIX ^IRX
python research/edges.py
```

This runs every strategy through the same tests: full period, three
sub-periods, a cost stress test, other markets, a parameter plateau check
and walk-forward. It also studies overnight vs intraday returns and
multi-asset rotation. The output goes to `research/output/`, and the
write-up is in `research/FINDINGS.md`.

## 5. Paper trading (Alpaca)

### Connect the broker (one time)

1. Create a free account at [alpaca.markets](https://alpaca.markets) and
   switch to **Paper Trading**. You get a simulated account with $100k.
2. On the paper dashboard, generate API keys. Paper key IDs start with
   **PK**. The desk refuses live keys, which start with AK.
3. Give the keys to the desk:
   - **On your computer:** copy `.env.example` to `.env` and fill in
     `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`. `.env` is git-ignored.
   - **In a Claude Code cloud session:** add a **network secret** for host
     `paper-api.alpaca.markets` with two custom headers and no prefix:
     `APCA-API-KEY-ID` = your key ID and `APCA-API-SECRET-KEY` = your
     secret (note the hyphens). The keys are then added on the way out and
     never enter the session. Start a new session afterwards. Never paste
     keys into a chat.
4. Check the connection:

```bash
python -m ai_desk broker status    # account, equity, buying power, market clock, positions
```

If it fails, the message says why: missing keys, live keys, rejected keys
or network blocked.

### Single-symbol strategies

After the US market close, run:

```bash
python -m ai_desk paper --strategy trend              # dry run: shows the order it WOULD place
python -m ai_desk paper --strategy trend --execute    # sends it to your paper account
```

Orders sent after the close fill at the next open, the same timing the
backtest assumes. Every run is logged to `logs/journal.csv`.

Built-in safety checks:
- The broker URL is hard-coded to **paper**. Real money needs a deliberate code change.
- It refuses to trade if the price data is stale or too short.
- It blocks any order larger than 105% of account equity (`--max-order-pct`).
- It halts if the account is 20% below its journal peak (`--account-dd-halt`).
- It won't stack a new order on top of one that's still pending.

To automate the run, schedule the command for ~4:30pm New York time on
weekdays. On Windows use Task Scheduler. On macOS or Linux use cron.
(Power Automate Desktop can also run it.) Check the journal weekly and
compare it to the backtest.

## 5b. Multi-stock portfolios and the methodology switcher

A **method** turns market data into target weights for many symbols. The
**executor** compares those targets with your Alpaca paper account and
works out the orders.

| method | what it does |
|---|---|
| `index_momentum` | SPY while its 12-month return is positive, otherwise cash |
| `sma_crossover` | each symbol held while its 50-day average is above its 200-day (`--param symbols=SPY,QQQ`) |
| `pairs` | duopoly pairs trading: when two rivals' price gap is stretched, short the leader and buy the laggard (`--param mode=long_only` to avoid shorting) |
| `quality_screen` | the stock screen's top 25, equal weight, **re-picked every quarter**. Picks are locked when bought: in between, only other methods trade and the stocks drift. When a re-pick is due, run `python -m ai_desk screen` first; `--rebalance` re-picks early |
| `thesis` | preset: 50% `quality_screen` + 50% `index_momentum` (see research/THESIS.md) |
| `aggressive` | preset: 70% `quality_screen` + 30% `index_momentum` - more return, bigger drawdowns |
| `bottleneck` | top 8 of the bottleneck scan (`python -m ai_desk bottleneck scan`), sized by volatility, re-picked every 2 weeks, sold if below its 100-day average |
| `desk` | preset: 50% `quality_screen` + 20% `bottleneck` + 30% `index_momentum` |

Blend methods with `name:share`, and set parameters with `--param`. Prefix a
parameter with the method name to target one method in a blend.

```bash
python -m ai_desk portfolio backtest --method pairs --param pairs.entry_z=2.5 --split 2019-01-01
python -m ai_desk portfolio backtest --method sma_crossover:0.5 --method index_momentum:0.5
python -m ai_desk portfolio plan --method thesis              # dry run: shows the orders it would place
python -m ai_desk portfolio run  --method thesis --execute    # sends them to Alpaca PAPER
```

Executor safety rules:
- At most 10% of equity in any single stock (`--max-position`) and 60% in a broad index fund like SPY (`--max-fund-position`). No leverage
  (`--max-gross 1.0`), and no single order above 25% of equity.
- Resizes under 0.5% of equity are skipped. Closing a position always trades.
- Shorts are only allowed if the method needs them, and only for shares the
  broker says are shortable. Flipping from long to short is sent as two
  orders.
- It refuses to trade on stale prices, while orders are still pending, or
  when the account is 20% below its peak.
- Every planned order is logged to `logs/portfolio_journal.csv`.
- **Fractional shares** are used for long positions where Alpaca allows
  them, so a 2% slot in a $1,240 stock buys 1.61 shares, not 1. Shorts, and
  stocks Alpaca marks as not fractionable, use whole shares.
  `--whole-shares` turns this off.

How the new methods did on real data: [`research/METHODS.md`](research/METHODS.md).

## 5c. Bottleneck scan: where money is flowing, and who is the constraint

```bash
python -m ai_desk bottleneck scan               # theme map (AI data centres) + top money-flow industries
python -m ai_desk bottleneck scan --theme-only  # only buy from the theme map
python -m ai_desk portfolio plan --method desk  # 50% quality + 20% bottleneck + 30% SPY momentum
```

The scan ranks industries by money flow. It then looks for companies with a
bottleneck's fingerprints: rising revenue, *expanding* margins, a growing
backlog, insiders buying, and a price that's still trending up. Method,
evidence and limits: [`research/BOTTLENECK.md`](research/BOTTLENECK.md).
The price-flow part has been backtested; it is not a proven edge, so run it
as an experiment.

## 6. Stock screener: great businesses at reasonable prices

```bash
python -m ai_desk screen                       # every US-listed company above $10B
python -m ai_desk screen --top 50 --min-cap 50e9
python -m ai_desk screen --tickers MSFT AAPL COST V
python -m ai_desk screen --min-roic 0.15 --max-forward-pe 35 --weight value=0.35
python -m ai_desk screen --no-gates            # rank everything, not just great businesses
python -m ai_desk screen --no-history          # skip the 10-year SEC check (faster)
```

The first run downloads about 4 years of statements per company from Yahoo,
which takes a while. After that, results are cached for a week. Each run
writes `output/screen_<date>.md`, a ranked shortlist explaining *why* each
company scored as it did, plus a CSV with every metric for every company.

Before ranking, companies have to pass the **great-business gates**, which
are on by default:
- an average ROIC of at least 12%
- no year with negative ROIC
- revenue rising in most years
- positive free cash flow
- at least 75% of the metrics available

These keep out businesses at a cyclical peak (miners in a commodity boom,
for example) and turnarounds, which would otherwise rank high on one hot
year.

Then comes the **10-year check**. Yahoo's 4 years can sit entirely inside a
boom, so the screen also reads each company's last 10 years of SEC filings.
A company fails, and is excluded, if:
- it made an operating loss in more than 2 of the 10 years
- its revenue fell in more than 2 years
- its pre-tax ROIC was under 10% in more than 3 of the years where it can be measured

Companies with under 7 years of filings ("short history") are kept but
flagged. Companies with no SEC data to check, mostly foreign filers using
international accounting standards, are excluded and listed in the report.
`--allow-unverified` keeps them. When a company's filings have no
operating-income line (Eli Lilly, for example), pre-tax income is used
instead.

A **data sanity check** also flags forward P/Es that imply earnings more
than tripling next year. That's usually a Yahoo error, such as an estimate
not adjusted for a stock split. These are left out of the value score. The first
run builds a ticker-to-SEC-ID map and downloads the filings, which takes
several minutes. After that, everything is cached. `--no-history` skips the
check.

Each company is then compared with the rest of the universe. Every metric becomes
a percentile (100 = best), the metrics average into categories, and the
categories average into the overall score:

| category (weight) | metrics |
|---|---|
| **quality** (35%) | average and worst-year ROIC, gross margin, operating margin, FCF ÷ net income |
| **growth** (25%) | revenue CAGR, latest-quarter growth vs a year ago, growth vs industry peers (the market-share proxy), gross-margin trend |
| **value** (20%) | forward P/E, EV/EBIT, FCF yield |
| **strength** (10%) | net debt ÷ EBITDA, share-count change (buybacks vs dilution), stock comp ÷ revenue |
| **momentum** (10%) | 12-month price change, skipping the latest month |

Notes on the method:
- ROIC = EBIT × (1 − tax rate) ÷ average operating invested capital. Operating
  invested capital is total assets, minus cash, minus non-debt current
  liabilities. This version still works when buybacks have pushed
  shareholders' equity negative, as at McDonald's or AutoZone.
- Banks, lenders, insurers, asset managers and REITs are excluded, because
  these metrics don't apply to them. Payment networks, exchanges, data
  providers and insurance brokers stay in, as long as they report normal
  operating statements.
- When Yahoo throttles, it sometimes returns empty data. The downloader
  retries, and never caches an incomplete company.
- **This is a screener, not a backtest.** Yahoo has about 4 years of history
  and no delisted companies, so it can't show how the screen would have
  performed in the past. That needs point-in-time data from SEC EDGAR, which
  is the next step.

### Has the screen worked historically?

```bash
python research/screen_backtest.py       # first run ~30-40 minutes; cached afterwards
```

This rebuilds the screen at each past rebalance date, using only SEC filings
that had been filed by then, and compares the result with SPY and with an
equal-weighted portfolio of the same universe. Results are in
`research/output/screen_backtest.md`. The overall strategy write-up, with
what's proven and what isn't, is [`research/THESIS.md`](research/THESIS.md).

### Research notes on the shortlist

`ai_desk/fundamentals/edgar.py` pulls 10+ years of reported financials from
SEC EDGAR. Set `SEC_USER_AGENT` in `.env` first: the SEC asks for a name and
email. Notes on the screen's top companies live in `research/notes/<date>/`.
Each one gives the 10-year record, the market's worry, the risks and the
sources. `python research/build_notes.py research/notes/<date>` refreshes
the numbers in them from the data.

## 7. Options: learning toolkit

Before trading options, learn what each structure risks and earns:

```bash
python -m ai_desk options price --spot 580 --strike 590 --days 30 --vol 0.18
python -m ai_desk options covered_call --spot 580 --width 10
python -m ai_desk options cash_secured_put --spot 580 --width 20
python -m ai_desk options bull_put_spread --spot 580 --width 10
python -m ai_desk options iron_condor --spot 580 --width 15 --days 45
```

Each command prints the premiums (from Black-Scholes), max profit, max
loss, breakevens, and a P&L table at expiry.

**Suggested path:**
1. **Greeks.** Use `options price` to see how delta, theta and vega change
   as you vary `--days`, `--vol` and `--strike`.
2. **Defined-risk income.** Start with covered calls and cash-secured puts,
   then move to vertical spreads. Avoid naked short options: the loss can be
   far larger than the premium you collect.
3. **Combine with your index signals.** For example, only sell put spreads
   when the `trend` strategy is long. This is where your stock edges and
   options meet.
4. **Real backtests.** Options can't be backtested honestly from stock
   prices alone. You need historical option-chain data from a provider such
   as ORATS, Polygon/Massive, CBOE DataShop or ThetaData. That's the
   natural next module to build.
5. **Paper-trade options.** Alpaca and Interactive Brokers both support
   paper options trading.

## 8. Adding your own strategy

1. Copy `ai_desk/strategies/trend.py` to a new file and change the rules in
   `target_exposure`. It must return, for each day, the exposure you want
   based only on data up to that day's close.
2. Register it in `ai_desk/strategies/__init__.py`.
3. Run `python -m pytest`. The `test_no_lookahead` test checks every
   registered strategy for accidental use of future data.

A good prompt for Claude Code: *"Add a strategy that ... Write a test for
it, run the backtest and walk-forward against buy & hold, and tell me
honestly whether it adds anything."*

## Project layout

```
ai_desk/
  data.py            price loading (Yahoo, CSV, synthetic) + caching
  indicators.py      SMA, RSI, realised volatility
  strategies/        one file per edge; registry in __init__.py
research/
  edges.py           robustness tests for every strategy
  FINDINGS.md        what held up on real data, and what didn't
  risk.py            vol targeting, leverage cap, drawdown halt, rebalance threshold
  backtest.py        next-open execution with costs
  metrics.py         CAGR, Sharpe, Sortino, drawdown...
  validation.py      out-of-sample split, parameter sensitivity, walk-forward
  live.py            daily paper-trading run + journal
  broker/alpaca.py   Alpaca paper REST client
  options/           Black-Scholes, Greeks, implied vol, strategy payoffs
  fundamentals/      stock screener: universe, Yahoo statements, metrics, scoring, SEC data
  portfolio/         multi-stock methods (switcher), multi-asset backtest, order executor
  cli.py             the `python -m ai_desk ...` commands
tests/               pytest suite
```

## Roadmap ideas

- Multiple symbols and portfolio-level risk (e.g. SPY + QQQ + TLT + GLD)
- Historical option-chain data loader and options backtester
- Comparing the live journal against the backtest (slippage tracking)
- Email or Teams alerts from the daily run
