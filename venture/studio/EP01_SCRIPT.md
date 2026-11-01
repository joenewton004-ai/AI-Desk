# EP01 - I Tested ICT's Silver Bullet on 129,658 Trades

**Sources (check before recording):** `research/ICT.md` (the write-up), `research/output/ict_long.md` (10-year tables,
by-year and by-quarter rows), `research/output/ict.md` (the first 60-day test). Code: `research/ict.py`,
`research/ict_long.py`. Every number in this script appears in those files.

**Length:** ~1,300 spoken words (8-10 minutes at a relaxed pace). Voice: UK, calm, curious, not mocking.

**On-screen disclaimer (first 30 seconds and end card):** *Educational research, not financial advice. I'm not a
financial adviser; past results don't predict future ones.*

---

## FULL SCRIPT

### 0:00 - Hook (first 15 seconds)

[VISUAL: black screen, a counter ticks up fast to 129,658. Then a coin spins.]

One of the most popular day-trading setups on the internet. Ten years of data. A hundred and twenty-nine thousand,
six hundred and fifty-eight trades. And before costs, it did about as well as flipping a coin for direction.

[VISUAL: title card - "ICT Silver Bullet: 10 years, 129,658 trades". Disclaimer strip along the bottom.]

### 0:15 - Who this is for

If you've spent any time on trading YouTube, you've met ICT - the Inner Circle Trader, Michael Huddleston. His ideas
about liquidity, stop hunts and fair value gaps are taught by thousands of creators. Today we're not arguing about
personalities. We're asking one narrow question: if you write the best-known ICT setups down as fixed rules, and run
them on years of real market data, with honest costs - do the setups themselves have an edge?

Quick note before we start: this is educational research. I'm not a financial adviser, and nothing here is a
recommendation to buy or sell anything.

### 0:50 - The idea behind ICT, in plain English

[VISUAL: simple animated candle chart. A horizontal line at yesterday's high, labelled "stops rest here".]

ICT is built on the idea of "liquidity". Obvious highs and lows - like yesterday's high - have lots of stop orders
sitting just beyond them. The theory is that price runs through those stops - that's called a **sweep** - and then
reverses sharply.

[VISUAL: price pokes above the line, snaps back down. Three candles highlighted; the gap between candle 1 and candle 3
shaded and labelled "fair value gap".]

That sharp move often leaves something called a **fair value gap**: three candles where the third doesn't overlap the
first. There's a hole in the price action. The idea is that price tends to come back into that gap - and that's
where you enter.

[VISUAL: a clock graphic, 10:00 to 11:00 New York highlighted - "kill zone".]

Timing matters too. ICT setups are only taken in set windows called "kill zones".

### 1:45 - The two models we tested

[VISUAL: rule card 1 - "SILVER BULLET".]

Model one is the **Silver Bullet**. Between 10 and 11am New York time, after price sweeps the prior day's high or low,
or the opening range, you look for a fair value gap. You place a limit order in the gap, your stop goes beyond the
sweep, your target is twice what you're risking, and you're out by the end of the day.

[VISUAL: rule card 2 - "JUDAS SWING".]

Model two is the **Judas swing**. The first hour fakes out beyond the prior day's high or low, then closes back
inside. You trade against the fake-out at 10:30, again targeting twice your risk.

[VISUAL: on-screen definition - "R = the amount you risk. +1R = you made what you risked. 0R = break-even."]

One bit of jargon: traders measure results in "R" - the amount you risked on the trade. Plus one R means you made
what you risked. Zero R means break-even.

### 2:40 - How we tested it

[VISUAL: checklist animating in, one line at a time.]

Here's the setup, and I want to be upfront about every choice.

- The data: ten years of five-minute bars, January 2016 to October 2026, from Alpaca's consolidated feed.
- The stocks: the 100 largest US companies at each point in time. Over the decade that's 224 different companies; we
  had bars for 222 of them.
- The rules: written into the code before running, based on community descriptions of ICT - not his own course
  material.
- Costs: 0.03% each way. That's cheap - it's what a tight spread on a big, liquid stock looks like.
- And a control. We took the exact same trades - same stock, same time, same stop and target - and flipped a coin for
  the direction. If ICT's direction call has value, it should beat the coin.

We also tried a twist: mixing in company financials. Longs only in the top third of companies by a quality score
built from SEC filings, shorts only in the bottom third. And a trend filter - longs above the 50-day average, shorts
below.

[VISUAL: small caption - "First test (60 days of Yahoo data) came first. This is the 10-year re-run."]

This is actually our second test. The first one only had 60 days of data, which is all Yahoo keeps. So when ten years
of minute-by-minute data became available, we ran it again with the same rules.

### 4:00 - The results

[VISUAL: big number reveal - "129,658 trades".]

Let's start with the Silver Bullet. Over ten years it took 129,658 trades.

[VISUAL: bar chart, "Average result per trade, before costs": Silver Bullet +0.02R, Coin-flip direction -0.00R.
Bars tiny, both near zero. Source tag: research/output/ict_long.md.]

Before costs, the average trade made plus 0.02R. Two hundredths of the amount risked. The coin-flip version made
roughly zero. So there is a direction call in there - and with this many trades, that small number is real. But it's
worth about 0.01% a trade. That's about a sixth of what a round trip costs, even at our cheap 0.03% each way.

[VISUAL: second bar chart, "Per trade, after costs": Silver Bullet -0.051%, Coin flip -0.061%, both red.]

After costs, the Silver Bullet lost 0.051% per trade. The coin flip lost 0.061%. So ICT beat a coin - by a hundredth of
a percent - and both lost money.

[VISUAL: 44-square grid, one square per quarter 2016-2026. Red for a loss, green for a gain. 42 red, 2 green
(2022Q4 and 2025Q1). Data: by-quarter row in research/output/ict_long.md.]

Here's the part that surprised me most. We split the ten years into 44 quarters. The Silver Bullet lost money after
costs in 42 of them. And it lost in every single year, 2016 to 2026 - both halves of the decade came out at exactly
minus 0.051% a trade.

[VISUAL: same chart format, Judas swing: 80,366 trades; before costs -0.00R; after costs -0.053%; coin flip -0.062%.
Then a 44-square grid with 39 red.]

The Judas swing? 80,366 trades. Before costs: minus 0.00R - indistinguishable from a coin. After costs: minus 0.053% a
trade. It lost in 39 of 44 quarters.

[VISUAL: simple table - "As a portfolio (10% per trade, up to 10 trades a day)": Silver Bullet -11.4%/yr, Judas swing
-16.2%/yr.]

Run as a portfolio - 10% of the account per trade, up to ten trades a day - the Silver Bullet lost 11.4% a year and
the Judas swing lost 16.2% a year.

### 5:45 - Did the financials or the trend filter help?

[VISUAL: ladder chart of Silver Bullet versions, after costs: pure -0.051%; + trend bias -0.058%; + financial bias
-0.044%; + financials, long only -0.035%.]

The best version in both tests was going long only in high-quality companies. In the ten-year run that got the Silver
Bullet to plus 0.04R before costs - and still minus 0.035% after. Better, but still a loss. And honestly, that mostly
reflects strong companies drifting up in a rising market, not the setup.

The trend filter - ICT's "higher-timeframe bias" - made things slightly worse, not better.

### 6:30 - Why is day trading this hard?

[VISUAL: a typical intraday move drawn as a bar, with a thin slice cut off and labelled "costs".]

Two reasons come out of this.

First, costs are a big share of every trade. A typical intraday move is half a percent to one percent. When you're
fighting over hundredths of a percent, a round-trip cost of 0.06% swallows a small edge whole.

Second, these are the most efficient stocks in the world. Yesterday's high, the opening range - everyone can see those
levels, including high-frequency trading firms. Obvious levels don't leave a free lunch.

[VISUAL: a perfect-looking ICT chart with arrows, then zoom out to show many messy days around it.]

And why does ICT look so convincing on social media? It's usually taught with charts chosen after the fact, and the
rules are flexible enough that a winning trade can always be explained afterwards. That's not a claim about anyone's
honesty - it's just how hindsight works on a chart.

### 7:20 - What this test can't tell you

[VISUAL: three cards - "Discretion", "Futures & forex", "Small caps".]

To be fair, there are real limits here.

- ICT is discretionary. Someone who practises it would say a skilled trader picks which gap "looks right" and skips
  news days. A fixed-rule test can't measure that skill - it only tests whether the setups themselves have an edge.
- ICT is mostly taught on futures and forex. We tested large US stocks.
- And we didn't test small caps.

What I can say is that a close relative - TJR's model - got the same answer when we ran it on ten years of QQQ and SPY.
That'll be its own video.

### 8:00 - Takeaway

[VISUAL: the coin again, landing. Text: "Before costs: a coin flip. After costs: a loss. 42 of 44 quarters."]

So here's where I land. As fixed rules, on ten years and over two hundred thousand trades across both models, the
Silver Bullet and the Judas swing didn't show an edge. Before costs, they were close to a coin flip. After even cheap
costs, they lost - steadily, almost every quarter.

[VISUAL: two arrows - "minutes" (red) vs "months" (green).]

The ideas that held up in our research - strong company financials, price strength - worked over months, not
minutes, where costs are tiny next to the move.

If you trade ICT and you're profitable, I'd genuinely like to know what you do that a rule can't capture - put it in
the comments. And if you're thinking of starting, test the rules on your own data, with costs, before you put money
behind them.

[VISUAL: end card with disclaimer.]

Educational research, not financial advice. I'm not a financial adviser, and past results don't predict future ones.
Thanks for watching.

---

## CHART LIST (all buildable from the repo)

| Chart | Data |
|---|---|
| Before-costs R: Silver Bullet vs coin flip | `research/output/ict_long.md`, Model 1 table |
| After-costs % per trade, both models + controls | same, Model 1 and Model 2 tables |
| 44-quarter red/green grid (Silver Bullet; Judas swing) | "By quarter" rows in `research/output/ict_long.md` |
| By-year bars, Silver Bullet 2016-2026 | "By year" row in `research/output/ict_long.md` |
| Version ladder (pure / trend / financial / long-only) | Model 1 table |
| Portfolio return per year | Model 1/2 tables, "portfolio return/yr" column |

---

## SHORTS (each <= 45 seconds)

### Short 1 - "The coin flip" (~40s)

[VISUAL: coin spinning, counter to 129,658.]
We tested ICT's Silver Bullet on ten years of data - 129,658 trades on the 100 biggest US stocks.
[VISUAL: two bars, +0.02R vs -0.00R.]
Before costs, it made 0.02 of what it risked per trade. Flipping a coin for the direction made about zero.
[VISUAL: two red bars, -0.051% vs -0.061%.]
After a cheap 0.03% cost each way, both lost money. ICT beat the coin by one hundredth of a percent a trade.
[VISUAL: caption "Fixed-rule version. Discretion not tested."]
These are community rules made precise, not a trader's judgement. Full test on the channel.
*Educational, not financial advice.*

### Short 2 - "42 out of 44" (~35s)

[VISUAL: 44-square grid filling in, square by square.]
Ten years. Forty-four quarters. Here's every quarter of ICT's Silver Bullet, after costs, on large US stocks.
[VISUAL: grid completes - 42 red, 2 green.]
Forty-two losing quarters. Two winning ones. Every single year from 2016 to 2026 was negative.
The Judas swing? Thirty-nine losing quarters out of forty-four.
Liquid stocks' intraday charts are close to random once you count costs. Full breakdown on the channel.
*Educational, not financial advice.*

### Short 3 - "Why setups look perfect" (~40s)

[VISUAL: a flawless ICT chart - sweep, gap, entry, target hit.]
This is what an ICT setup looks like on social media.
[VISUAL: zoom out to dozens of messy days.]
This is what 129,658 of them look like when a computer takes every one by the rules.
Before costs: roughly break-even, like a coin flip. After costs: a loss in 42 of 44 quarters.
Charts picked after the fact always look good - that's hindsight, not a strategy.
Our test can't measure a trader's discretion. It can measure the setups. Full video on the channel.
*Educational, not financial advice.*

---

### Short 4 - "The Judas swing" (~35s)

ICT's other famous setup is the Judas swing. The first hour fakes out past yesterday's high or low, then closes back inside, and you trade against the fake-out.

We tested it on ten years of data. 80,366 trades.

Before costs: zero. Exactly what a coin flip makes. After costs, it lost money in 39 of 44 quarters.

Fixed rules, not a trader's judgement. Full test on the channel. Educational, not financial advice.

### Short 5 - "Can it be rescued?" (~35s)

We tried to rescue ICT's Silver Bullet. First, a trend filter - ICT's higher-timeframe bias.

It made things worse: minus 0.058% a trade after costs, against minus 0.051% without it.

Then we only went long in high-quality companies, judged by their financials. That was the best version we found.

And it still lost 0.035% a trade after costs. Least bad isn't good. Educational, not financial advice.

### Short 6 - "Why costs win" (~30s)

Why is day trading the biggest stocks so hard? Costs.

A typical intraday move is half a percent to one percent. Even at a cheap 0.03% each way, a round trip costs 0.06%.

ICT's direction call was worth about 0.01% a trade. A sixth of the cost.

When you're fighting over hundredths of a percent, costs win. Full test on the channel. Educational, not financial advice.

## YOUTUBE METADATA

**Title:** I Tested ICT's Silver Bullet on 129,658 Trades (10 Years of Data)

**Description:**

Does ICT's Silver Bullet actually have an edge? We turned two of the best-known Inner Circle Trader setups - the
Silver Bullet and the Judas swing - into fixed rules and ran them on ten years of 5-minute bars (January 2016 to
October 2026) for the 100 largest US companies, with costs of 0.03% each way and a coin-flip control.

Results:
- Silver Bullet: 129,658 trades, +0.02R before costs, -0.051% per trade after costs; lost money in 42 of 44 quarters.
- Judas swing: 80,366 trades, -0.00R before costs, -0.053% per trade after costs; lost in 39 of 44 quarters.
- Same trades with a coin-flip direction: -0.061% and -0.062% after costs.
- Long-only in high-quality companies was the least bad version, still -0.035% per trade after costs.

Limits: these are community descriptions of ICT made into fixed rules, not ICT's own course material. A trader's
discretion isn't tested. Tested on large US stocks, not futures, forex or small caps.

Chapters:
0:00 The result
0:15 What we're testing
0:50 ICT in plain English
1:45 Silver Bullet and Judas swing rules
2:40 How we tested it
4:00 Results
5:45 Did financials or trend help?
6:30 Why day trading is so hard
7:20 What this test can't tell you
8:00 Takeaway

Educational research, not financial advice. I'm not a financial adviser; past results don't predict future ones.

**Tags (15):**
ICT, Inner Circle Trader, ICT Silver Bullet, Silver Bullet strategy, Judas swing, fair value gap, liquidity sweep,
backtest, day trading backtest, trading strategy tested, does ICT work, smart money concepts, day trading,
stock market research, trading costs
