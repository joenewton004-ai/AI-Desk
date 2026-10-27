# Which trading platform could do better for the desk?

_October 2026. Desk research (no code). Research, not advice. Sources read 2026-10-27; broker fee pages are undated,
so check them before acting._

## Why the question matters

The desk now puts about 95% of its money in the overnight sleeve (amendment c52ce018). That sleeve breaks even at
about 0.045% per trade each way, and the desk-level case needs about 0.02%. So **the cost of buying near the close
and selling at the open decides whether this desk works.**

The live paper sales at the open have filled 0.45-0.68% below the official open, 10× too expensive. The question is
whether that's the market, Alpaca, or Alpaca's paper simulator.

## What we found

**1. The paper simulator is the most likely culprit, not the market.**
- Alpaca staff say paper fills use live quotes: buys fill at the ask and sells at the bid, with no price improvement
  ([forum](https://forum.alpaca.markets/t/slippage-paper-trading-vs-real-trading/2801)). Users describe this as
  "pessimistic" fills.
- At 9:30am the quoted spread is at its widest of the day, so selling at the bid then is the worst possible fill.
- Staff also say that market-on-open and market-on-close orders ("OPG"/"CLS") are areas where paper "doesn't mimic
  live trading very well" ([forum](https://forum.alpaca.markets/t/accurate-opg-and-cls-prices-for-paper-trading/3762)).
- Paper fills also ignore liquidity, and partial fills are random
  ([TradersPost](https://blog.traderspost.io/article/alpaca-paper-trading)).

**2. In a live account, auction orders fill at the official price.**
- A real market-on-open order joins the exchange's opening auction and fills at the official opening price. A
  market-on-close order does the same at the official close.
- That is exactly the price the overnight research assumed. So with live auction orders the cost is close to just
  commissions and exchange fees: no spread, no slippage.
- One user did report a live opening-auction fill above the official open
  ([forum](https://forum.alpaca.markets/t/time-in-force-opg-filled-price-open-price/1884)), so it should be checked
  rather than assumed.

**3. No paper account can measure this.**
- Interactive Brokers' paper accounts don't support auction orders at all
  ([IBKR API limitations](https://www.interactivebrokers.com/docs/tws-api/doc/notes-limitations/limitations/paper-trading)).
- Its simulator also ignores slippage and price improvement
  ([IBKR Campus](https://www.interactivebrokers.com/campus/ibkr-quant-news/from-back-test-to-paper-trading/)).
- Switching paper platforms therefore wouldn't tell us the real cost.

## The platforms

| | Alpaca (live) | Interactive Brokers Pro | Interactive Brokers Lite | Charles Schwab |
|---|---|---|---|---|
| Auction orders by API | Yes: OPG (open) and CLS (close) ([docs](https://alpaca.markets/sdks/python/api_reference/trading/enums.html), [changelog](https://docs.alpaca.markets/us/changelog/2026-05-05-tif-38d668f)) | Yes (MOO/MOC; a market order sent before the open is treated as market-on-open) | Yes | Close yes; open reportedly not by API ([user report](https://wealth-lab.com/Discussion/What-exit-types-are-supported-by-Schwab-12148)) |
| Commission | $0 | Tiered $0.0005-0.0035/share + exchange fees; Fixed $0.005/share, $1 minimum ([IBKR](https://www.interactivebrokers.com/plans)) | $0 | $0 |
| Catch | Paid by wholesalers for order flow: about 0.7-0.95¢ per 100 shares on market orders ([Alpaca 606 reports](https://files.alpaca.markets/disclosures/library/SEC+606a1+-+2026Q2.pdf)). Auction orders go to the exchange auction | Orders a program sends straight to one exchange pay the Fixed rate, not Tiered ([IBKR](https://brokerage.ibkr.com/en/accounts/fees/alternate-exchange-commissions.php?nhf=T)). Accounts doing more than 10% of their volume in opening/closing auctions may be charged extra ([IBKR](https://www.interactivebrokers.com/plans)); this desk would be close to 100% | Same 10% auction rule, and it's built for manual trading | No paper trading by API; third-party wrappers only |
| Approx. cost per trade at our size (~$4,750 an order, ~30 shares) | ~0% commission | Tiered: ~$0.35-0.50 an order, ~0.01% each way. Fixed: $1 minimum, ~0.02% each way, half the sleeve's edge | Possibly ~0.005 $/share once over the 10% auction threshold | Unknown for the open |
| Fit for the desk | Already wired up; same code | Strong execution and real auction access, but a new API (TWS/Client Portal) and fees that eat the edge at our order size | Poor | Poor (no open auction by API) |

Not researched in depth: Tradier, TradeStation, Webull, Robinhood. None offers something the first two don't for
this use.

## What this means

- **On a live account, Alpaca is likely the cheapest platform for this desk, not the problem.** It charges no
  commission and supports real opening and closing auction orders. Interactive Brokers gives top-class execution, but
  at ~$4,750 an order its per-order minimums and auction rules cost 0.01-0.02% each way. That's a big slice of an
  edge worth ~0.045%.
- **The 0.45-0.68% losses at the open are very likely a paper artefact:** sells filled at the 9:30am bid, with no
  price improvement. The market-on-open test (amendment e43f2959) still has value, because it shows whether Alpaca's
  paper auction fills sit closer to the official open. But **no paper test can prove the real cost.**
- **The only way to measure real costs is real trades.** This desk stays on Alpaca PAPER, and moving to live money
  is the owner's decision alone. One option, for the owner to decide, would be a very small live account running
  the same overnight orders, to measure actual auction fills against the official prices. Nothing here changes the
  paper setup.
- **A useful step that's free:** score the paper overnight sleeve against the official open and close prices as
  well as its fills. Those are the prices a live auction order would get, and `overnight review` already reports
  fills against the official open. That gives a "what a live account would have made" line next to the paper
  result.
