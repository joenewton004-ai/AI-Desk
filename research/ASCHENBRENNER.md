# Leopold Aschenbrenner's methodology, quantified

_October 2026. Code: `research/aschenbrenner.py`. Tables: [`output/aschenbrenner.md`](output/aschenbrenner.md). Source:
the 7 SEC 13F filings of Situational Awareness LP (CIK 2045724), Q4 2024 - Q2 2026, from www.sec.gov (allowed by the
owner 2026-10-29). Research, not advice._

## Who and what

- **Who:** Leopold Aschenbrenner, a former OpenAI researcher, wrote "Situational Awareness" (June 2024), arguing that
  AI scaling will need trillion-dollar compute clusters and huge new power supply. He then launched a hedge fund on
  that view.
- **What reporting says it does:** long the build-out behind AI rather than AI companies (chips, memory, data
  centres, power, bitcoin miners turning into AI hosts); puts on chipmakers; bets against software that AI could
  disrupt.
  ([longtermwiki](https://www.longtermwiki.com/knowledge-base/organizations/finance/situational-awareness-lp),
  [KuCoin Q1 2026 13F summary](https://www.kucoin.com/blog/th-leopold-aschenbrenner-full-q1-2026-13f-breakdown),
  read 2026-10-29)
- **Performance claims:** reported returns vary wildly (from "+47% after fees in H1 2025" to "over 1,000%"). Late-July
  2026 reports describe steep losses and a forced unwind
  ([IBTimes](https://www.ibtimes.com/ai-star-leopold-aschenbrenner-built-45-billion-hedge-fund-weeks-later-it-has-been-forced-unwind-3805913),
  [indiainfoline](https://www.indiainfoline.com/news/international/who-is-leopold-aschenbrenner-how-the-former-openai-researchers-45-billion-ai-hedge-fund-ran-into-trouble)).
  **Verify against primary sources:** none of these is a fund statement.

## 1. The method in numbers (from the filings)

| quarter end | public | 13F book | names | stock / calls / puts | net exposure | top 5 | power | data centres | chips |
|---|---|---|---|---|---|---|---|---|---|
| 2024-12 | 2025-02-12 | $0.25B | 6 | 100 / 0 / 0% | +100% | 97% | 66% | 0% | 34% |
| 2025-03 | 2025-05-14 | $1.0B | 12 | 54 / 46 / 0% | +100% | 76% | 23% | 12% | 64% |
| 2025-06 | 2025-08-14 | $2.1B | 9 | 52 / 21 / 27% | +63% | 83% | 22% | 14% | 64% |
| 2025-09 | 2025-11-14 | $4.1B | 25 | 54 / 24 / 21% | +73% | 77% | 10% | 53% | 35% |
| 2025-12 | 2026-02-11 | $5.5B | 25 | 71 / 29 / 0% | +100% | 68% | 22% | 48% | 20% |
| 2026-03 | 2026-05-18 | $13.7B | 29 | 28 / 10 / **62%** | **-62%** | 68% | 8% | 16% | 68% |
| 2026-06 | 2026-08-14 | $20.2B | 24 | 100 / 0 / 0% | +100% | 78% | 11% | 24% | 65% |

(Themes are a hand-made classification dated 2026-10-29; options are at the underlying shares' value.)

What the numbers say about the method:
- **A concentrated theme book, not a diversified fund.** The top 5 names are 68-97% of the long side.
- **The theme moved through the AI supply chain.** First power (Vistra, Talen, Constellation: 66% of the first book);
  then chips (Intel calls, Broadcom); then data centres and miners-to-hosts (CoreWeave, Core Scientific, IREN, Applied
  Digital: about half the book by late 2025); then memory (SanDisk and Micron, 55% of the latest book).
- **Options are central.** Calls were up to 46% of the book.
- **Puts flipped him to net short in Q1 2026.** Puts on SMH, NVIDIA, Oracle, Broadcom, AMD and TSMC were 62% of the
  book, so he was net short (-62%) at the end of March 2026.
- **By the end of June 2026 the book was all stock again,** with no options: consistent with the reported unwind.
- **High turnover:** 33-84% of the long book changed each quarter.

## 2. Copying it (bought the day after each filing became public)

| version, 2025-02-13 to 2026-10-28 | total | per year | Sharpe | worst drop | volatility |
|---|---|---|---|---|---|
| copy: stocks only | +99% | +50% | 0.87 | -49% | 69% |
| copy: stocks + calls (as stock) | +129% | +63% | 1.00 | -49% | 67% |
| copy: full book (puts as shorts) | +91% | +46% | 0.88 | -49% | 57% |
| copy: equal weight | +159% | +75% | 1.15 | -52% | 63% |
| SPY | +30% | +17% | 0.76 | -20% | 17% |
| QQQ | +38% | +21% | 0.78 | -24% | 22% |
| **SMH (semiconductor ETF)** | **+128%** | **+63%** | **1.33** | **-33%** | 40% |

- **Copying made a lot of money: +91% to +159% in 20 months**, far ahead of SPY and QQQ.
- **But simply holding the semiconductor ETF did the same or better.** It made +128% with a higher Sharpe (1.33 vs
  0.87-1.15) and a smaller worst drop (-33% vs about -50%).
- **Period by period, the copy beat SMH in 5 of 7 holding periods.** It lost 17% in each of the first period
  (Feb-May 2025) and the last (Aug-Oct 2026, around the reported unwind).

## 3. Skill or exposure?

| version | moves like SMH x | plus SPY x | left over per year (alpha) | t |
|---|---|---|---|---|
| stocks + calls | 1.47 | -0.07 | -9% | -0.4 |
| full book | 0.80 | +0.75 | -1% | 0.0 |
| equal weight | 1.22 | +0.26 | +4% | 0.1 |

**This is the core finding.**
- What a copier gets is a leveraged semiconductor bet: about 1.5x SMH's daily moves. Once that's removed, nothing is
  left (t between -0.4 and 0.1).
- The thesis was right about the direction: AI infrastructure boomed in 2025-26. But on these filings the copy book
  didn't pick better than holding the whole chip index, and it carried more risk.

## 4. What the 45-day delay costs

| version | held from each quarter's end (≈ the fund, if it held all quarter) | held from the filing date (a copier) |
|---|---|---|
| stocks + calls | +105% (Sharpe 0.91) | +129% (Sharpe 1.00) |
| full book | +1% (Sharpe 0.25) | +91% (Sharpe 0.88) |

- **The delay helped a copier here, which is luck, not a feature.** Over the 45 days before the March 2026 book was
  published, its large put positions lost money, as chips kept rising into May. A copier only took them on after.
- **The fund's real result can't be read from this.** The fund trades between quarter ends, its true positions are
  unknown, and option values here are notional. Reported fund returns are press claims to verify.

## Verdict

**The method is a concentrated, options-heavy bet on the AI build-out, rotated through its bottlenecks (power →
chips → data centres → memory), with big hedges at times.**
- Quantified from his filings, copying it worked in 2025-26 because the theme boomed.
- It behaved like about 1.5x a semiconductor ETF, with no measurable skill beyond that, and a worse risk-adjusted
  result than holding SMH.
- Its swing to net short in early 2026 and the reported unwind show the risk of following a concentrated macro bet
  with a 45-day lag.

**For the desk:**
- The idea is close to the retired **bottleneck sleeve** (`BOTTLENECK.md`), which also picked AI-supply-chain themes
  by hand.
- Twenty months, one theme, and survivors (every holding still trades) are far too little to justify a sleeve.
- Not proposed. Recorded as research-only (`aschenbrenner_13f`).

## Limits

- **13F shows only US long stock and options at quarter ends.** Short stock, non-US holdings, cash, leverage and
  intra-quarter trades are invisible.
- **Calls counted as stock overstate them.** An option's delta is below 1, while its leverage and time decay are
  ignored.
- **The theme labels are my classification, dated 2026-10-29,** not the fund's.
