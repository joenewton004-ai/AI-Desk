# George Soros: what he did, and the part of it a rule can copy

_October 2026. Code: `research/soros.py`. Tables: [`output/soros.md`](output/soros.md). Research, not advice._

## What he did

| | |
|---|---|
| **Fund** | Soros Fund Management / the Quantum Fund, from 1969-73. Stanley Druckenmiller ran it day to day 1988-2000 |
| **Style** | Global macro: large, often leveraged, discretionary bets on currencies, interest rates, bonds and stock markets, long or short |
| **Idea** | "Reflexivity": markets' beliefs change the fundamentals they're about, so booms and busts feed on themselves until they break. In practice: find a trend driven by a misconception, ride it, size up when sure, get out fast when wrong |
| **Famous trades** | 1985: long yen and mark against the dollar, +122% that year. 1992: short the pound before it left the European exchange-rate mechanism, about $1 billion profit. 1987: lost about $350m when he sold futures just before the crash's rebound |
| **Record (reported)** | +3,365% from 1969 to 1980 vs +47% for the S&P 500; about 30% a year on average for 1970-2000; the first losing year was 1981 |

The figures come from company histories and profiles, not audited fund records. His trades were discretionary, and
the fund's macro bets (currencies, futures) never appear in its public 13F filings, which list only US stock holdings.
Sources: [Encyclopedia.com: Soros Fund Management](https://www.encyclopedia.com/books/politics-and-business-magazines/soros-fund-management-llc),
[company-histories.com](https://company-histories.com/Soros-Fund-Management-LLC-Company-History.html),
[referenceforbusiness.com](https://www.referenceforbusiness.com/history2/85/Soros-Fund-Management-LLC.html),
[freenance.io fund profile](https://freenance.io/funds/soros-fund-management),
[SourceWatch: Quantum Fund](https://sourcewatch.org/index.php/Quantum_Fund),
[Auburn University archive (2000)](https://webhome.auburn.edu/~pughwi1/soros.html),
[Traders Union](https://tradersunion.com/news/editors-picks/show/3204600-from-buffett-to-soros/),
[Benzinga (2024)](https://benzinga.com/startups/24/02/37185069/george-soross-former-co-founder-sounds-economic-alarm-saying-the-next-problem-has-to-be-the-worst-in)
(read 2026-10-26).

## The testable core: follow each market's trend, across asset classes

On 9 ETFs: US stocks (SPY, QQQ, IWM, DIA), international stocks (EFA, EEM), Treasuries (TLT, IEF) and gold (GLD).
Monthly, 2006-2026; 0.05% per unit traded; T-bills on cash.

| | Return/yr | Volatility | Sharpe | Worst drop | 2006-15 | 2016-26 | 2008 | 2022 |
|---|---|---|---|---|---|---|---|---|
| **A. Trend, long only:** hold each market whose 12-month return beat T-bills | 7.3% | 7% | **0.79** | **−9%** | 0.85 | 0.71 | −1% | −7% |
| B. Trend, long and short (as a macro fund would) | 5.1% | 9% | 0.40 | −28% | 0.57 | 0.22 | **+25%** | +3% |
| C. B, each market sized to 10% volatility | 4.8% | 5% | 0.60 | −9% | 0.84 | 0.40 | +10% | +3% |
| D. Concentrated: the 3 strongest markets | 10.1% | 13% | 0.69 | −26% | 0.77 | 0.59 | +10% | −16% |
| E. A, with a 3-month trend | 7.2% | 7% | 0.81 | −9% | 0.91 | 0.67 | −1% | −6% |
| SPY | 11.1% | 15% | 0.67 | −51% | 0.47 | 0.84 | −37% | −18% |
| 60/40 SPY/IEF | 8.2% | 9% | 0.72 | −29% | 0.69 | 0.72 | −18% | −17% |

- **Following trends across markets is the best risk control we've tested.** Long-only trend (A) had a slightly
  better Sharpe than SPY and 60/40, and a worst drop of **−9%** against −51% for SPY. That includes 2008 (−1%) and
  2022 (−7%, when stocks and bonds fell together). It held in both halves, and with a 3-month or 12-month trend.
- **It earns less.** 7.3% a year against SPY's 11.1%, because it's often partly in cash and in bonds.
- **Shorting falling markets, as Soros did, made money in crashes** (+25% in 2008) but cost in between. Recent years
  had sharp V-shaped recoveries that caught the shorts (2016-26 Sharpe 0.22).
- **As a 30% slice next to SPY,** it trims the worst drop from −51% to −40% for 1% a year less return.
- **This is not his skill.** The rules copy only the trend-following skeleton of macro trading: no currencies, no
  leverage, no judgement about which booms are built on a misconception.

## Verdict

**No way to copy Soros himself; his discretionary bets aren't public or testable.** The rule-based core, trend-
following across asset classes, is genuinely useful **for risk control** (worst drop −9% vs −51%) with a similar Sharpe
to SPY, though not for higher returns. The desk's old SPY-momentum sleeve was a one-market version of this idea. A
multi-market trend sleeve is a reasonable candidate if you ever want the desk to fall less in a crash; it would need
its own amendment and a desk-level test. Recorded as research-only (`soros_macro_trend`).
