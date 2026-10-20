# The bottleneck sleeve

_October 2026. Code: `ai_desk/bottleneck/`. Tables:
[`output/bottleneck_backtest.md`](output/bottleneck_backtest.md) (from
`python research/bottleneck_backtest.py`) and the latest
`output/bottleneck_<date>.md` scan. Educational research, not financial
advice._

## The idea

When a wave of money floods into one build-out (AI data centres today),
the best opportunities often aren't the obvious names. They're the
suppliers of whatever is **scarce and slow to expand**: power, grid
equipment, cooling, specialist construction, memory. Those companies show
the same four fingerprints:

| fingerprint | measured by |
|---|---|
| **Money flowing in** | Relative strength vs the S&P 500 over 6 and 12 months, and how close the stock is to its 52-week high. The same is measured for its whole industry. |
| **Demand outrunning supply** | Revenue growth, whether that growth is speeding up, and order backlog growth from SEC filings ("remaining performance obligations") |
| **Pricing power** | Gross and operating margins *rising*. The clearest sign a company is the constraint. |
| **Asymmetry** | Forward P/E relative to expected earnings growth, how far the price is stretched above its trend, and the balance sheet |
| **Smart money** | Insiders buying on the open market (SEC Form 4), and members of Congress buying, when that data is supplied |

## The rules

1. **Find the flows.** Rank every industry by money flow. This is data-driven, so
   new themes surface on their own.
2. **Build candidates.** Take companies in the top flow industries, plus every
   company in the theme map (`bottleneck/themes.py`): a dated, human-curated
   supply-chain map for the AI data-centre build-out.
3. **Must pass all three:** revenue up 10% or more year on year, gross margin
   not falling, and price above its 200-day average.
4. **Score:** flow 25%, bottleneck 35%, asymmetry 25%, smart money 15%.
5. **Hold** the top 8, sized by inverse volatility and capped at 2× an equal
   share.
6. **Re-pick weekly.** **Sell** any holding that closes below its 200-day
   average, checked on every run. A sold stock stays out until the next
   re-pick, so it doesn't bounce in and out.

`--theme-only` restricts buying to the theme map. Money-flow industries are
still shown in the report.

## What the backtest says

Only the *money-flow rotation* can be tested fairly: industry and stock
relative strength, the trend rule, volatility sizing and weekly re-picks.
That was tested point-in-time on weekly prices from 2014 to 2026.

| | Return/yr | Volatility | Sharpe | Worst drop |
|---|---|---|---|---|
| Flow rotation, re-picked weekly | 11.8% | 32% | 0.45 | −61% |
| …at 3× trading costs | 3.4% | 32% | 0.21 | −67% |
| …re-picked every 4 weeks (exit checked weekly) | 13.3% | 32% | 0.49 | −68% |
| …re-picked every 13 weeks (exit checked weekly) | 21.2% | 34% | 0.68 | −42% |
| Equal-weight universe | 14.2% | 20% | 0.66 | −41% |
| SPY | 13.7% | 16% | 0.75 | −32% |

- **No reliable edge from price flows alone.** Weekly re-picks did worse
  than simply owning SPY, with double the volatility. It's very sensitive to
  costs, because weekly re-picking trades a lot.
- **Results swing with the settings.** Re-picking every 13 weeks did much
  better, but every 4 weeks did worse. Results that jump around like this as
  one setting changes are a sign of noise, not a robust edge.
- **It depends on the era.** It lost badly in 2014-2019 (5.3%/yr vs SPY
  12.1%) and did well in 2020-2026 (17.9% vs 15.0%), the AI and energy era.
- **Survivorship flatters it.** Momentum stocks that collapsed and delisted
  are missing from the data.

### Parameter experiment: moving average × re-pick frequency

The moving average is used both to buy (price must be above it) and to sell
(a close below it). The exit is checked weekly throughout.

| MA | re-pick | return/yr | Sharpe | worst drop | 2014-19 | 2020-26 | at 3× costs |
|---|---|---|---|---|---|---|---|
| 50-day | weekly | 8.9% | 0.37 | −45% | −2.8% | 20.4% | −1.9% |
| 50-day | 2 weeks | 12.3% | 0.48 | −45% | 1.1% | 23.2% | 4.1% |
| 50-day | 4 weeks | 13.5% | 0.50 | −50% | 2.6% | 24.0% | 7.2% |
| 100-day | weekly | 9.8% | 0.40 | −47% | 2.1% | 17.1% | 0.2% |
| **100-day** | **2 weeks** | **17.0%** | **0.60** | −46% | 9.7% | 23.8% | 10.2% |
| 100-day | 4 weeks | 13.0% | 0.49 | −44% | 6.3% | 19.3% | 8.4% |
| 200-day | weekly | 11.8% | 0.45 | −61% | 5.3% | 17.9% | 3.4% |
| 200-day | 2 weeks | 14.1% | 0.51 | −63% | 10.2% | 17.7% | 8.8% |
| 200-day | 4 weeks | 13.3% | 0.49 | −68% | 6.5% | 19.6% | 9.6% |

SPY: 13.7%/yr (Sharpe 0.75); 12.1% in 2014-19 and 15.0% in 2020-26.

What's robust and what isn't:
- **Weekly re-picks are the worst choice with every moving average.** Every
  2 or 4 weeks beats weekly in all three rows, because weekly churn and its
  costs eat the edge. That's the most dependable finding here.
- **Shorter averages cut the worst drawdown** (50-day and 100-day: −44% to −50%;
  200-day: −61% to −68%). They exit sooner.
- **The 50-day is too twitchy in sideways markets.** It made roughly nothing
  in 2014-2019, and it did best only in the strongly trending 2020-2026.
- **100-day every 2 weeks is the best cell**, and it's the only setting that
  did reasonably in *both* halves. But its neighbours (100-day weekly 9.8%,
  100-day every 4 weeks 13.0%) are well below it. A lone peak like that is
  partly luck, so expect less in practice.
- **No setting beats SPY's Sharpe (0.75)** on the rotation alone. The
  sleeve's case rests on diversifying the quality screen.

**In the desk** with 100-day / 2 weeks: 16.3%/yr, Sharpe 0.88, worst drop
−22.8%. That compares with 15.5%, 0.85 and −24.0% for 200-day weekly, and
15.8%, 0.89 and −27.6% for 70/30 with no bottleneck sleeve.

Settings: `python -m ai_desk bottleneck scan --ma 100`. The sleeve's sell rule
automatically uses the same average. Set the re-pick frequency with
`--param bottleneck.rebalance_days=14`.

**In the desk (monthly, 2014-2026):**

| | Return/yr | Sharpe | Worst drop |
|---|---|---|---|
| 50% screen + 20% rotation + 30% SPY momentum | 15.5% | 0.85 | −24% |
| 70% screen + 30% SPY momentum (previous) | 15.8% | 0.89 | −28% |

The rotation's correlation with the quality screen is only 0.48, so it
diversifies. That cut the worst drop, but it slightly lowered the return per
unit of risk.

## What is NOT tested

- **The fundamental fingerprints:** margin expansion, backlog and growth
  acceleration. Quarterly data isn't available point-in-time here. This is
  where the "bottleneck" idea differs from plain momentum, so it may be
  better *or* worse than the rotation test.
- **Insider and congressional buying:** insider purchases have the stronger
  research record; congressional trades the weaker.
- **The theme map:** it is written with hindsight. We know AI power worked.
  That is the biggest bias in the whole idea.

## Data notes

- **Insiders:** SEC Form 4 via Yahoo, counting *open-market purchases* only.
  Yahoo's own "insider purchases" total includes stock grants, which aren't
  conviction. Yahoo throttles this endpoint; results are cached 3 days, and a
  missing value counts as neutral.
- **Congress:** no free source is reachable from this environment. The free
  datasets are offline, and the official House and Senate sites and the
  commercial APIs are blocked. Drop a file at `data/congress/trades.csv` with
  columns `date, ticker, politician, chamber, type (purchase|sale),
  amount_low, amount_high` and the scan uses it automatically. Members can
  report up to 45 days late, and studies since 2012 mostly find no
  outperformance.

## Verdict

Run it as a **20% experiment**, not a proven edge. Watch three things in
paper trading:
1. Does it beat the equal-weight universe *after* costs?
2. How often does the 200-day exit fire, and do exited stocks keep falling?
3. Does `--theme-only` (the AI build-out) do better than following
   whatever is hot (today: energy)?
