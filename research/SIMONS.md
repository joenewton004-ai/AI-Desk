# Jim Simons and the Medallion fund: how it traded, and what we can learn

_October 2026. Desk research, no backtest (the fund's trades are not public). Sources at the end,
accessed 2026-10-21; verify figures there. Research, not advice._

## First, a correction: Simons was quantitative, not qualitative

Jim Simons (1938-2024) was a mathematician, a codebreaker and a geometry prize-winner. His firm,
Renaissance Technologies, hired mathematicians, physicists and speech-recognition researchers, not
stock analysts. He was the purest example of **quantitative** investing: computer models found
patterns in data and traded them, and people did not override them. Qualitative investing, judging
a company's management, products and story, is what Lynch did. Simons did the opposite.

## Can we see his trades?

**No.** Medallion has been closed to outside money since 1993; only employees and their families
invest. It doesn't publish holdings. Renaissance's public 13F filings show the firm's *other*
funds (RIEF, RIDA), which are slower, much bigger and much less successful. Copying a 13F would
copy those funds, not Medallion. Everything known comes from Gregory Zuckerman's book
*The Man Who Solved the Market* (2019), interviews and academic estimates.

## What is known

| Feature | What's reported |
|---|---|
| Returns | About 66% a year before fees, 39% after (1988-2018; Cornell 2019, from Zuckerman's figures). A later paper argues that naive compounding overstates this and estimates under 35% a year before fees. |
| Consistency | In the decade from 2000 (dot-com crash, 2007 "quant quake", 2008, the 2010 flash crash) it lost money in only 3 months (Bloomberg). |
| Win rate | About **50.75%** of trades: barely better than a coin flip, but repeated over millions of trades. |
| Holding period | Very short: thousands of positions opened and closed constantly, long and short, typically days. |
| What it bets on | Mostly **relationships between securities** ("statistical arbitrage", built by ex-IBM researchers Robert Mercer and Peter Brown), not whether one stock or the market goes up; earlier, trends and patterns in futures. |
| Hedging | Close to market-neutral: longs and shorts offset, so a market crash isn't a big loss. |
| Leverage | Reported as high, often quoted at 12-20x, but from secondary sources (unverified). It works because the hedged book's swings are small. |
| Size | Kept small (around $10 billion), with profits paid out each year: the edges disappear if traded too big. |
| Fees | 5% of assets plus 44% of profits, and investors still earned about 39% a year. |
| Machinery | Over 10 million lines of code; obsessive data cleaning; modelling its own trading costs and market impact. |

## The patterns in how it traded

1. **Many tiny edges, not one big idea.** No single signal was strong. Thousands of weak ones,
   each slightly better than chance, were combined. A 50.75% hit rate only pays if you make a vast
   number of independent bets, so the law of large numbers does the work.
2. **Short horizons.** Mispricings over hours to days are where the patterns live (people
   over-reacting, forced sellers, temporary supply and demand). They're also the patterns that
   vanish when too much money chases them, hence the size cap.
3. **Hedge out what you can't predict.** By pairing longs against shorts in related stocks, the
   fund bet only on the relationship, not on the market, which is why its worst years (2008) were
   its best.
4. **Costs are part of the signal.** A pattern only counts if it survives the cost of trading it.
   Medallion modelled its own price impact in detail.
5. **No human overrides.** Simons insisted the models be followed even in drawdowns; people
   overruling the model was treated as the biggest risk.
6. **Data first.** They gathered and cleaned decades of prices (some typed in by hand from old
   records) before anyone else valued it.

## What it means for this desk

- **We can't copy it, and shouldn't try.** Medallion's edge comes from scale, decades of data,
  hundreds of PhDs, near-zero trading costs, intraday execution and high leverage on a hedged book.
  Our own tests show what happens at retail scale: short-term reversal (research/WEEKLY.md), VCP
  swing trading (SWING.md) and ICT day trading (ICT.md) all died on costs. The tiny edges that pay
  Medallion are smaller than our costs.
- **The principles it shares with the desk are already the desk's rules:** rules not discretion
  ("no LLM in the decision path", no overrides), costs in every backtest, honest out-of-sample
  testing, and many small independent bets rather than one story.
- **What we could borrow:**
  - Its focus on **market-neutral relationships** (we tested pairs trading in research/METHODS.md:
    weak at daily frequency after costs).
  - **Combining several weak signals** instead of hunting for one strong one. That is a reasonable
    next research direction for the quality screen's scoring, tested the same way as
    research/NEAR_MISSES.md.
- **The honest lesson:** Medallion is the exception that proves how hard the rest is. Even
  Renaissance's own public funds, run by the same firm with the same people, earned roughly
  market-like returns. The edge did not scale to a slower, bigger strategy.

## Sources (accessed 2026-10-21)

- Cornell, B. (2019), "Medallion Fund: The Ultimate Counterexample?", summarised by CXO Advisory:
  https://www.cxoadvisory.com/investing-expertise/proof-of-superior-investment-expertise/ and Institutional Investor:
  https://www.institutionalinvestor.com/article/2bswymr8cih3jeaslxc00/portfolio/famed-medallion-fund-stretches-explanation-to-the-limit-professor-claims
- Re-estimate of Medallion's returns (arXiv 2405.10917): https://arxiv.org/pdf/2405.10917v2
- Bloomberg Businessweek, "The unsolved mystery of the Medallion fund's success":
  https://www.bloombergquint.com/amp/businessweek/the-unsolved-mystery-of-the-medallion-fund-s-success
- Institutional Investor, Medallion vs Renaissance's other funds:
  https://www.institutionalinvestor.com/article/b1l98yt4p0bvr4/The-Famed-Medallion-Fund-Is-Crushing-It-Other-RenTech-Funds-Not-So-Much
- Validea summary of press coverage: https://blog.validea.com/amid-tumult-renaissance-medallion-fund-gains-24-to-date/
- Leverage and trade-count figures (secondary, unverified): https://www.quantvps.com/blog/jim-simons-trading-strategy
- Zuckerman, G. (2019), *The Man Who Solved the Market* (the primary public account).
