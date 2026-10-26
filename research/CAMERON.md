# Ross Cameron (Warrior Trading): gap-and-go day trading

_October 2026. Code: `research/cameron.py`. Tables: [`output/cameron.md`](output/cameron.md). Research, not advice._

## What he does and trades

| | |
|---|---|
| **Who** | Founder of Warrior Trading (2012), a day-trading education business |
| **What** | Small-cap US stocks making big moves: momentum scalping, in and out within minutes to hours |
| **When** | Pre-market and the first hours after the open |
| **Stock selection ("5 pillars")** | Up 10%+ on the day; relative volume 5x+ (against a 30-day average); a news catalyst (earnings, FDA, contracts); his material also cites a low share price (about $2-20) and a small float (shares available to trade; often quoted as under 20 million). The last two aren't confirmed in the sources found |
| **Entries** | Breakouts and the first pullbacks on 1-5-minute charts ("micro pullbacks", flags) |
| **Risk** | Tight stops below the pullback; take profits quickly |

**The FTC case (2022).** The FTC sued Warrior Trading and Cameron over advertising that "showcased the trading
results of Cameron" as profitable and scalable for customers, while the FTC alleged most customers lost money. They
settled for **$3 million in refunds**, without admitting or denying the allegations. The FTC said it didn't allege that
Cameron's own results were false. Sources: [FTC business blog (April 2022)](https://www.ftc.gov/business-guidance/blog/2022/04/ftc-bids-good-night-deceptive-day-trading-earnings-claims),
[FTC complaint](https://business.ftc.gov/system/files/ftc_gov/pdf/2023198WarriorTradingComplaint_0.pdf),
[FTC order](https://www.ftc.gov/system/files/ftc_gov/pdf/2023198WarriorTradingStipulatedPermInjunction_0.pdf),
[FTC press release](https://www.ftc.gov/node/78914), [FTC case page](https://www.ftc.gov/node/78866),
[Berkshire Edge](https://theberkshireedge.com/great-barrington-stock-trading-company-agrees-to-3-million-settlement-with-feds/),
[WWLP](https://www.wwlp.com/news/local-news/berkshire-county/warrior-trading-ordered-to-refund-investors-after-false-gains-claims/amp),
[daytradingtoolkit.com review](https://daytradingtoolkit.com/reviews/warrior-trading-review). The 5-pillar thresholds
come from TradingView indicator descriptions: [1](https://ru.tradingview.com/scripts/search/scalp/page-34),
[2](https://kr.tradingview.com/scripts/search/screener/page-12) (read 2026-10-26).

## What we could test, and what we couldn't

**We have no historical small-cap data.** There's no point-in-time list of past low-float gappers, and Yahoo's
prices cover survivors only, which would flatter small caps most. So this tests his core pattern, that big gaps up keep
running during the day, on the 750 largest US companies, 2014-2026. Buy at the open, sell at the close, 0.10% each way:

| Rule | Trades | Win rate | Per trade after costs | t |
|---|---|---|---|---|
| Gap up 4%+ at the open | 20,676 | 47% | −0.13% | −4.1 |
| Gap up 10%+ | 2,322 | 47% | −0.35% | −2.9 |
| Gap up 20%+ | 271 | 44% | −1.18% | −2.5 |
| Gap up 4%+, $10-20 stocks | 2,870 | 46% | −0.01% | −0.1 |
| Gap up 4%+, the less-traded half | 9,433 | 46% | −0.07% | −1.4 |
| *Gap up 4%+ AND 5x volume that day (**hindsight**)* | 1,509 | 64% | *+1.54%* | 9.8 |
| Every stock, open to close (the costs alone) | 2.4m | 44% | −0.19% | |

And on 5-minute bars (120 large stocks, the last ~60 days): buying the first pullback on 3%+ gap-ups (break of the first
red candle's high, stop at its low, 2R target, out by 11:00) lost −0.44% a trade over 144 trades (t −4.0).

- **Gaps on large stocks don't keep running.** Bought at the open, they earn about nothing before costs (+0.07% for 4%+
  gaps) and lose after them. The bigger the gap, the worse.
- **The volume filter is where any edge would be, and we can't test it fairly.** Gappers that ended the day on 5x normal
  volume made +1.5% from the open. But the full day's volume is only known at the close. Cameron judges it early, from
  pre-market and first-minutes volume, and that needs minute-by-minute volume history we don't have (Yahoo keeps 60
  days; data.alpaca.markets is blocked here).
- **Small caps behave differently.** Low-float stocks can run 50-100% in a morning, which large caps don't. They're
  also where spreads, halts and fills are worst. A paper account fills at prices a real one often wouldn't get.

## Verdict

**Not testable on his own turf with our data; on large stocks, gap-and-go loses money.** The one real clue (heavy
volume) can only be checked with intraday volume history. The FTC case is a reminder that a trader's own results say
little about what students or copiers get. It doesn't fit the desk (stocks bought once a day, large caps, paper
fills). Recorded as research-only (`cameron_gap_and_go`).
