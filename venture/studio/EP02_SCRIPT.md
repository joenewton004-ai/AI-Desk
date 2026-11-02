# EP02 - I Tested TJR's Strategy on 10 Years of Data

**Sources (check before recording):** `research/TJR.md` (write-up), `research/output/tjr_long.md` (10-year tables),
`research/output/tjr.md` (the first 49-day futures test). Code: `research/tjr.py`, `research/tjr_long.py`.
Every number in this script appears in those files.

**Length:** ~1,300 spoken words (~8 minutes in the cloned voice). Pronunciation list checked
(`voice/PRONUNCIATION.md`): no "minute data".

**On-screen disclaimer (first 30 seconds and end card):** *Educational research, not financial advice. I'm not a
financial adviser; past results don't predict future ones.*

**Fairness rules for this one:** describe TJR's public method, not the person. His income claims are unverified -
don't repeat them. His own rulebook isn't public: say so. No "scam", no "fraud".

---

## FULL SCRIPT

### 0:00 - Hook

[VISUAL: counter ticks up to 3,401. Then two bars side by side: "TJR's model -0.088R" and "Random direction -0.087R".]

At the end of the last video I promised you TJR. So here it is. Ten years of data. Three thousand four hundred and
one trades. And after costs, it lost almost exactly what you'd lose by picking a random direction.

[VISUAL: title card - "TJR's model: 10 years, 3,401 trades". Disclaimer strip.]

### 0:15 - Who this is for

TJR is one of the most-watched day traders on social media. He trades the New York open, on Nasdaq and S&P 500
futures, with a style that grew out of ICT - the same family of ideas we tested last time. Today's question is the
same narrow one: if you write his best-known setup down as fixed rules and run it on years of real data, with
honest costs, does the setup itself have an edge?

Quick note before we start: this is educational research. I'm not a financial adviser, and nothing here is a
recommendation to buy or sell anything.

### 0:45 - The model in plain English

[VISUAL: chart with yesterday's high, yesterday's low and the overnight high/low drawn as lines, labelled "liquidity".]

The model starts with liquidity: obvious levels where lots of orders sit. Yesterday's high and low. The overnight
high and low. In the futures, the Asia and London session highs and lows too.

[VISUAL: price spikes through the overnight high and snaps back. Label: "sweep".]

Between half past nine and eleven, New York time, you wait for price to sweep one of those levels - trade through
it, then close back inside.

[VISUAL: after the sweep, price breaks the last small swing the other way. Label: "break of structure".]

Then you want proof the move has turned: a break of structure, where price breaks the last small swing the other way.
Some versions use an inverse fair value gap instead - price closing straight through the gap the sweep left behind.

[VISUAL: entry arrow, stop beyond the sweep, target 2R.]

You enter on the next bar, put your stop just beyond the sweep, and aim for two times what you risked, or for the
liquidity on the other side.

### 1:50 - Where the rules came from

[VISUAL: card - "His own rulebook isn't public."]

One honest caveat up front. TJR's own rulebook isn't public. What I've tested is the version the community agrees
on - write-ups and published indicator scripts that describe the same steps. If his real rules differ, this test is
of the community's version, not his.

### 2:15 - How we tested it

[VISUAL: checklist builds line by line.]

Here's every choice, upfront.

- The data: ten years of five-minute bars, January 2016 to October 2026, including pre-market and after-hours.
- The markets: QQQ and SPY. QQQ tracks the Nasdaq-100 and SPY tracks the S&P 500, so they stand in for the
  futures he trades.
- The levels: yesterday's high and low, and the overnight high and low. US stocks don't trade during the Asia and
  London sessions, so those levels are dropped.
- The costs: one hundredth of a percent each way. That's cheap.
- The control: the same trades at the same times, but with the direction picked at random.

[VISUAL: card - "Test 1: 49 days of futures. Test 2: ten years."]

This is actually our second test. The first one used real futures, but only 49 trading days of five-minute bars -
all the free data goes back. About 76 trades. That's far too few to tell anything, so we went looking for ten years.

### 3:20 - The results

[VISUAL: big number - 3,401 trades.]

Over ten years, the main version - sweep, break of structure, two R target - took 3,401 trades.

[VISUAL: before-costs bar: +0.007R, on a -1R to +1R scale so it looks as small as it is.]

Before costs, the average trade made plus 0.007R. Seven thousandths of what was risked. That's zero, to any
practical purpose.

[VISUAL: after-costs bars: TJR's model -0.088R vs random direction -0.087R.]

After costs, it lost 0.088R a trade. And the random-direction version? It lost 0.087R. The setup and a coin toss
landed in the same place.

[VISUAL: win-rate card - 37% wins, 57% stopped out.]

It won 37% of the time. At a two R target you need to win a third of the time just to break even before costs, so on paper that
sounds fine - until you notice the stops are tight, about a third of a percent of the price. Our cheap cost of a
hundredth of a percent each way works out at about a tenth of an R on every trade. That's the whole loss.

### 4:40 - Every version

[VISUAL: version ladder - all after-costs R per trade.]

We tried every variation the community describes.

[VISUAL: highlight each row as it's read.]

A three R target: minus 0.110. Aiming for the liquidity on the other side: minus 0.116. Adding a one-hour trend
filter: minus 0.085. The inverse fair value gap instead of a break of structure: minus 0.062 - the least bad, but
in the second half of the decade it fell to minus 0.112.

Every single version lost money after costs, and none of them beat the random-direction trades by more than luck.

### 5:30 - Year by year

[VISUAL: bars per year, 2016-2026, red and green.]

Year by year, the main version made money in three years out of eleven: 2020, 2024 and 2025, each by a few
hundredths of an R. The other eight lost.

### 5:50 - Did any level work?

[VISUAL: table of eight cells - QQQ/SPY x the four levels, after-costs R.]

What about the individual levels? Seven of the eight lost money. One looked good: sweeps of SPY's previous-day high,
plus 0.097R over 401 trades. But when you slice results eight ways, one of them will look good by chance. Nothing
about it repeated anywhere else, so I wouldn't read anything into it.

### 6:25 - Why

[VISUAL: card - "Before costs: zero. After costs: below zero."]

So why doesn't it work as rules? The same reason as ICT. Before costs, the setup doesn't predict direction - it's
plus 0.007R, basically zero. Then any cost at all pushes zero below zero.

[VISUAL: card - "Futures are cheaper - but zero minus a smaller cost is still below zero."]

To be fair to TJR, futures are cheaper to trade than QQQ and SPY. On futures the cost might be two to four hundredths
of an R instead of a tenth. That shrinks the loss. It doesn't create an edge.

### 6:55 - What this test can't tell you

[VISUAL: three boxes: "QQQ/SPY, not futures", "No Asia or London levels", "Discretion not tested".]

There are real limits here.

- QQQ and SPY aren't the futures. The futures trade overnight, so the Asia and London levels he watches only exist
  there.
- His rulebook isn't public. This is the community's version, made precise.
- And the big one: discretion. Which sweep counts, whether a break of structure looks clean, which days to skip
  for news. That judgement may well be his real skill. A fixed-rule test can't measure it.

### 7:35 - Takeaway

[VISUAL: two cards side by side - "ICT: coin flip" and "TJR: coin flip".]

So here's where I land. As fixed rules, on ten years of data, TJR's New York-open model did what ICT's setups did
last time: before costs, about as well as a coin flip. After costs, a loss.

[VISUAL: end card - "What should we test next?"]

If you trade this model and you're profitable, I'd genuinely like to know what you do that a rule can't capture - put
it in the comments. And tell me what we should test next.

Educational research, not financial advice. I'm not a financial adviser, and past results don't predict future
ones. Thanks for watching.

---

## CHART LIST (all from the repo)

| Chart | Data |
|---|---|
| Counter 3,401 + hook bars -0.088R vs -0.087R | `research/output/tjr_long.md`, main table + control row |
| Before costs +0.007R on a -1R..+1R scale | same, "avg R before costs" |
| Win rate 37%, stopped out 57% | same |
| Version ladder (BOS 2R/3R/opposite, 1-hour bias, iFVG 2R) | same, main table |
| iFVG halves: -0.006 (2016-20) vs -0.112 (2021-26) | same |
| Year bars 2016-2026 | "By year" line |
| Eight level cells | "By instrument and level swept" table |
| Risk 0.34% of price, cost ~0.095R | last line of `tjr_long.md` |

---

## SHORTS (next week, one a day; [mood] tags drive Candle)

### Short 1 - "TJR vs random" (~30s)

[neutral] We tested TJR's New York-open model on ten years of data. 3,401 trades.

[shocked] After costs it lost 0.088R a trade. Random direction, same times, lost 0.087R.

[sceptical] The setup and a coin toss landed in the same place. Fixed rules, not his judgement. Full test on the channel. Educational, not financial advice.

### Short 2 - "37% wins and still losing" (~30s)

[neutral] TJR's model won 37% of its trades. At a 2R target, that sounds like enough.

[thinking] But the stops are tight - about a third of a percent of the price. So even a cheap cost eats about a tenth of an R every trade.

[sceptical] Before costs it made almost nothing. After costs, a loss. Educational, not financial advice.

### Short 3 - "3 good years out of 11" (~25s)

[neutral] Ten years of TJR's model, one year at a time.

[shocked] Three years made money: 2020, 2024 and 2025 - each by a few hundredths of an R. The other eight lost.

[thinking] Full breakdown on the channel. Educational, not financial advice.

### Short 4 - "The one level that worked" (~30s)

[pleased] One part of TJR's model looked great: sweeps of SPY's previous-day high made 0.097R a trade.

[sceptical] But it was one of eight slices, and the other seven lost. Slice anything eight ways and one will look good by chance.

[thinking] That's how backtests fool people. Educational, not financial advice.

### Short 5 - "Every version lost" (~30s)

[thinking] We tried every version of TJR's model the community describes.

[sceptical] A 3R target, the opposite liquidity, a trend filter, an inverse fair value gap. Every one lost money after costs.

[neutral] Full test on the channel. Educational, not financial advice.

### Short 6 - "ICT and TJR, same answer" (~30s)

[neutral] Last week we tested ICT. This week, TJR.

[shocked] Different teachers, same family of ideas - and the same result: before costs, a coin flip. After costs, a loss.

[thinking] As fixed rules, at least. Discretion is the part we can't test. Educational, not financial advice.

---

## YOUTUBE METADATA

**Title:** I Tested TJR's Strategy on 10 Years of Data (3,401 Trades)

**Description:**

Does TJR's New York-open model have an edge? We turned the community's description of TJR's setup - a liquidity
sweep, a break of structure (or inverse fair value gap), stop beyond the sweep, 2R target - into fixed rules and ran
it on ten years of 5-minute bars (January 2016 to October 2026) for QQQ and SPY, standing in for the Nasdaq and S&P
500 futures he trades. Costs: 0.01% each way. Control: the same trades in a random direction.

Results:
- Main version: 3,401 trades, 37% wins, +0.007R before costs, -0.088R per trade after costs.
- Random direction at the same times: -0.087R.
- Every variation lost after costs (3R target -0.110R, opposite liquidity -0.116R, 1-hour bias -0.085R, inverse FVG -0.062R).
- Profitable in 3 of 11 years (2020, 2024, 2025).

Limits: TJR's own rulebook isn't public; this is the community's version made precise. QQQ/SPY aren't the futures, so
the Asia and London levels are left out. A trader's discretion isn't tested.

Chapters: (set from the finished video's timings)

Narrated with an AI clone of my own voice.
Educational research, not financial advice. I'm not a financial adviser; past results don't predict future ones.

**Tags:** TJR, TJR Trades, TJR strategy, TJR model, liquidity sweep, break of structure, inverse fair value gap, ICT,
smart money concepts, day trading backtest, trading strategy tested, NQ futures, ES futures, New York open, trading costs
