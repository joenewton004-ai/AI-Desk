"""Which stocks to screen: large US-listed companies from Yahoo's screener."""

from __future__ import annotations

import pandas as pd

from ai_desk.fundamentals.yahoo import with_retry


def large_caps(min_market_cap: float = 10e9, limit: int = 1000) -> pd.DataFrame:
    """US-listed equities above `min_market_cap`, largest first.

    Dropped:
      * companies reporting in another currency (mostly foreign ADRs) - their
        statements and US share price don't mix cleanly in ratios
      * duplicate share classes (GOOG/GOOGL, BRK-A/BRK-B) - keeps the most traded
    """
    import yfinance as yf
    from yfinance import EquityQuery as Q

    query = Q("and", [Q("eq", ["region", "us"]),
                      Q("is-in", ["exchange", "NMS", "NYQ", "NGM", "NCM", "ASE"]),
                      Q("gt", ["intradaymarketcap", min_market_cap])])
    rows, offset = [], 0
    while offset < limit:
        page = with_retry(lambda: yf.screen(query, sortField="intradaymarketcap", sortAsc=False,
                                            size=250, offset=offset))
        quotes = page.get("quotes", [])
        rows += quotes
        offset += 250
        if len(quotes) < 250 or offset >= page.get("total", 0):
            break
    df = pd.DataFrame([{
        "symbol": q["symbol"], "name": q.get("longName") or q.get("shortName"),
        "market_cap": q.get("marketCap"), "quote_type": q.get("quoteType"),
        "financial_currency": q.get("financialCurrency"),
        "avg_volume": q.get("averageDailyVolume3Month") or 0,
    } for q in rows])
    return clean_universe(df)


def clean_universe(df: pd.DataFrame) -> pd.DataFrame:
    df = df[(df["quote_type"] == "EQUITY") & (df["financial_currency"].fillna("USD") == "USD")]
    df = (df.sort_values("avg_volume", ascending=False)
            .drop_duplicates(subset="name", keep="first")
            .sort_values("market_cap", ascending=False))
    return df.reset_index(drop=True)
