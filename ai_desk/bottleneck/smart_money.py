"""Smart-money signals: insiders and members of Congress buying a stock.

INSIDERS (SEC Form 4, via Yahoo). Only OPEN-MARKET PURCHASES count - an
officer or director spending their own money. Stock grants and option
exercises are compensation, not conviction, so they're ignored (Yahoo's own
"insider purchases" total mixes them in). Research: insider purchases,
especially several insiders buying together ("cluster buys"), have predicted
above-market returns (Lakonishok & Lee 2001; Cohen, Malloy & Pomorski 2012).
Insider SALES are mostly diversification and taxes, so they carry little signal.

CONGRESS (STOCK Act disclosures). Weaker evidence: members can report up to
45 days after trading, and studies since 2012 mostly find no outperformance.
Trades are read from data/congress/trades.csv if present, with columns:
    date, ticker, politician, chamber, type (purchase | sale), amount_low, amount_high [, filed]
`python research/house_ptr.py` builds it from the House Clerk's reports (House only, electronic filings;
research/CONGRESS.md tests it). Any other provider can be converted to that file.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ai_desk.fundamentals.yahoo import with_retry

INSIDER_CACHE = Path("data/insiders")
CONGRESS_FILE = Path("data/congress/trades.csv")


def insider_transactions(symbol: str, max_age_days: float = 3) -> pd.DataFrame:
    """Recent Form 4 transactions for one company (cached a few days)."""
    path = INSIDER_CACHE / f"{symbol}.json"
    if path.exists() and time.time() - path.stat().st_mtime < max_age_days * 86400:
        return pd.read_json(path.read_text(), orient="records")
    import yfinance as yf

    df = with_retry(lambda: yf.Ticker(symbol).insider_transactions, tries=4)
    df = pd.DataFrame() if df is None else df
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(df.to_json(orient="records", date_format="iso"))
    return df


def insider_signals(tx: pd.DataFrame, market_cap: float, asof=None, days: int = 180) -> dict:
    """Open-market buying by insiders over the last `days`."""
    out = {"insider_buyers": 0, "insider_buy_value": 0.0, "insider_net_buy_pct": 0.0}
    if tx is None or tx.empty or "Text" not in tx:
        return {k: np.nan for k in out}
    asof = pd.Timestamp(asof or pd.Timestamp.today()).tz_localize(None)
    t = tx.copy()
    t["date"] = pd.to_datetime(t["Start Date"], errors="coerce").dt.tz_localize(None)
    t = t[t["date"] >= asof - pd.Timedelta(days=days)]
    text = t["Text"].fillna("").str.lower()
    buys = t[text.str.startswith("purchase")]                    # "Purchase at price 41.20 per share."
    sells = t[text.str.startswith("sale")]
    buy_value = float(pd.to_numeric(buys["Value"], errors="coerce").fillna(0).sum())
    sell_value = float(pd.to_numeric(sells["Value"], errors="coerce").fillna(0).sum())
    out["insider_buyers"] = int(buys["Insider"].nunique())
    out["insider_buy_value"] = buy_value
    out["insider_net_buy_pct"] = (buy_value - sell_value) / market_cap if market_cap else np.nan
    return out


def congress_trades(path: Path | None = None) -> pd.DataFrame | None:
    p = Path(path or CONGRESS_FILE)
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=["date"], low_memory=False)
    if "filed" in df:
        df["filed"] = pd.to_datetime(df["filed"])
    df["ticker"] = df["ticker"].str.upper().str.strip()
    df["type"] = df["type"].str.lower().str.strip()
    return df


def congress_signals(trades: pd.DataFrame | None, symbol: str, asof=None, days: int = 90) -> dict:
    """Distinct members of Congress buying minus selling over the last `days`, by the day each report was FILED
    when the file has it (research/house_ptr.py writes `filed`) - a trade isn't public until then, up to 45 days
    after the trade date; files without it fall back to the trade date."""
    if trades is None:
        return {"congress_net_buyers": np.nan}
    asof = pd.Timestamp(asof or pd.Timestamp.today())
    when = trades["filed"] if "filed" in trades else trades["date"]
    t = trades[(trades["ticker"] == symbol) & (when >= asof - pd.Timedelta(days=days)) & (when <= asof)]
    buyers = t.loc[t["type"].str.startswith("purchase"), "politician"].nunique()
    sellers = t.loc[t["type"].str.startswith("sale"), "politician"].nunique()
    return {"congress_net_buyers": buyers - sellers}


def smart_money(symbols: list[str], market_caps: pd.Series, workers: int = 2) -> pd.DataFrame:
    """Insider and congressional signals for a list of companies."""
    from concurrent.futures import ThreadPoolExecutor

    congress = congress_trades()

    def one(sym):
        try:
            ins = insider_signals(insider_transactions(sym), market_caps.get(sym))
        except Exception:  # noqa: BLE001 - a bonus signal; never fail the scan on it
            ins = {"insider_buyers": np.nan, "insider_buy_value": np.nan, "insider_net_buy_pct": np.nan}
        return {"symbol": sym, **ins, **congress_signals(congress, sym)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(one, symbols))
    return pd.DataFrame(rows).set_index("symbol")


def describe_sources() -> str:
    c = congress_trades()
    congress = (f"congressional trades: {len(c)} rows from {CONGRESS_FILE}" if c is not None
                else f"congressional trades: none loaded (no {CONGRESS_FILE})")
    return "insider trades: SEC Form 4 via Yahoo (open-market purchases only); " + congress
