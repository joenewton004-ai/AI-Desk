"""Long-run financial history from SEC EDGAR's XBRL "company facts" API.

Every number a US-listed company has reported in a 10-K / 20-F since ~2009,
tagged with the date it was FILED - which is what a point-in-time backtest
needs (you can only act on a number after it's public).

Only data.sec.gov is used. The SEC asks callers to identify themselves:
set SEC_USER_AGENT in .env to something like "Your Name you@example.com".
"""

from __future__ import annotations

import gzip
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

CACHE = Path("data/sec")
BASE = "https://data.sec.gov"

# first listed = preferred; companies switch tags over time (e.g. revenue in 2018)
FLOW = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax", "Revenue",
                "RevenueFromContractsWithCustomers",
                # pre-2018 filers often split revenue into goods/services lines (e.g. Coca-Cola)
                "SalesRevenueGoodsNet", "SalesRevenueServicesNet"],
    "gross_profit": ["GrossProfit"],
    # filers without an operating line (Eli Lilly, KLA, AngloGold): fall back to pre-tax income
    "operating_income": ["OperatingIncomeLoss", "ProfitLossFromOperatingActivities",
                         "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                         "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
                         "ProfitLossBeforeTax"],
    "net_income": ["NetIncomeLoss", "ProfitLossAttributableToOwnersOfParent", "ProfitLoss",
                   "NetIncomeLossAvailableToCommonStockholdersBasic"],   # e.g. Booking after 2010
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities",
                            "CashFlowsFromUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
              "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"],
}
INSTANT = {
    "assets": ["Assets"],
    "current_liabilities": ["LiabilitiesCurrent", "CurrentLiabilities"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashAndCashEquivalents"],
    "current_debt": ["DebtCurrent", "LongTermDebtCurrent", "CurrentBorrowings",
                     "CurrentPortionOfLongtermBorrowings"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt", "NoncurrentPortionOfNoncurrentBorrowings"],
}
ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F")


def _user_agent() -> str:
    from ai_desk.broker.alpaca import load_dotenv

    load_dotenv()
    return os.environ.get("SEC_USER_AGENT", "AI-Desk research tool")


_rate_lock = threading.Lock()
_last_request = [0.0]
MIN_INTERVAL = 0.125   # at most 8 requests/second across all threads (SEC limit: 10)


def _wait_turn() -> None:
    with _rate_lock:
        wait = _last_request[0] + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request[0] = time.monotonic()


def _get(url: str, stream: bool = False) -> requests.Response:
    """GET with the SEC's required User-Agent, a shared rate limit (safe to
    call from several threads) and backoff on throttling."""
    for attempt in range(5):
        _wait_turn()
        r = requests.get(url, headers={"User-Agent": _user_agent()}, timeout=30, stream=stream)
        if r.status_code in (429, 503):
            time.sleep(2 ** attempt)
            continue
        return r
    return r


def company_facts(cik: int, cache_dir: Path = CACHE, max_age_days: float = 7) -> dict:
    """All XBRL facts for one company. Cached gzipped (~10x smaller than raw)."""
    path = cache_dir / f"CIK{cik:010d}.json.gz"
    if path.exists() and time.time() - path.stat().st_mtime < max_age_days * 86400:
        return json.loads(gzip.decompress(path.read_bytes()))
    r = _get(f"{BASE}/api/xbrl/companyfacts/CIK{cik:010d}.json")
    if r.status_code == 404:
        return {"facts": {}}   # company has no XBRL financial data
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(r.content))
    return r.json()


# --- ticker -> CIK -----------------------------------------------------------
# www.sec.gov (and its ticker list) isn't reachable here, only data.sec.gov.
# So: list every company that reported revenue recently (XBRL "frames"), then
# read the ticker symbols from the top of each company's filing index.

# IFRS filers don't appear in the frames API; these are verified by hand
# against data.sec.gov/submissions (newest registration first).
KNOWN_CIKS = {"AU": [1973832, 1067428], "BHP": [811809]}
_HEADER = re.compile(r'"name":"(?P<name>[^"]*)","tickers":\[(?P<tickers>[^\]]*)\]')


def candidate_ciks(min_revenue: float = 1e8, min_assets: float = 5e8) -> set[int]:
    """Companies big enough to matter. Annual revenue frames miss many
    non-December fiscal years (TJX, Copart), so also include everyone with a
    sizeable balance sheet at recent quarter-ends - every filer reports one."""
    ciks = set()
    for tag in ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"):
        for y in (2023, 2024, 2025):
            r = _get(f"{BASE}/api/xbrl/frames/us-gaap/{tag}/USD/CY{y}.json")
            if r.status_code == 200:
                ciks |= {e["cik"] for e in r.json()["data"] if e["val"] >= min_revenue}
    for period in ("CY2025Q1I", "CY2025Q2I", "CY2025Q3I", "CY2025Q4I"):
        r = _get(f"{BASE}/api/xbrl/frames/us-gaap/Assets/USD/{period}.json")
        if r.status_code == 200:
            ciks |= {e["cik"] for e in r.json()["data"] if e["val"] >= min_assets}
    return ciks


_SIC = re.compile(r'"sic":"(?P<sic>\d*)"')


def company_header(cik: int) -> dict:
    """Name, tickers and SIC industry code, reading only the start of the
    filing index (the full file is ~150KB; the header is in the first few
    hundred bytes)."""
    r = _get(f"{BASE}/submissions/CIK{cik:010d}.json", stream=True)
    try:
        text = ""
        for chunk in r.iter_content(2048):
            text += chunk.decode("utf-8", "ignore")
            m = _HEADER.search(text)
            if m:
                sic = _SIC.search(text)
                return {"name": m["name"], "tickers": re.findall(r'"([^"]+)"', m["tickers"]),
                        "sic": int(sic["sic"]) if sic and sic["sic"] else None}
            if len(text) > 20_000:
                break
    finally:
        r.close()
    return {"name": "", "tickers": [], "sic": None}


def tickers_for(cik: int) -> tuple[str, list[str]]:
    h = company_header(cik)
    return h["name"], h["tickers"]


def company_headers(ciks: list[int], cache_dir: Path = CACHE) -> dict[int, dict]:
    """Name, tickers and SIC code per CIK (cached; these rarely change)."""
    path = cache_dir / "headers.json"
    cache = {int(k): v for k, v in json.loads(path.read_text()).items()} if path.exists() else {}
    todo = [c for c in ciks if c not in cache]
    if todo:
        with ThreadPoolExecutor(max_workers=6) as pool:
            for i, (cik, h) in enumerate(zip(todo, pool.map(company_header, todo)), 1):
                cache[cik] = h
                if i % 250 == 0:
                    print(f"  SEC company headers: {i}/{len(todo)}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache))
    return {c: cache[c] for c in ciks}


def revenue_history_ciks(min_revenue: float = 1e9, years=range(2012, 2026)) -> set[int]:
    """Every company that reported $1B+ annual revenue in any year since 2012 -
    including ones that later shrank (the backtest universe must not be
    chosen with hindsight)."""
    ciks = set()
    for tag in ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"):
        for y in years:
            r = _get(f"{BASE}/api/xbrl/frames/us-gaap/{tag}/USD/CY{y}.json")
            if r.status_code == 200:
                ciks |= {e["cik"] for e in r.json()["data"] if e["val"] >= min_revenue}
    return ciks


def ticker_map(cache_dir: Path = CACHE, max_age_days: float = 30, progress: bool = True) -> dict[str, list[int]]:
    """{ticker: [cik, ...]} for sizeable US filers. The first build takes a few
    minutes (thousands of small requests); later rebuilds only look up
    companies not seen before. Refreshed monthly."""
    path = cache_dir / "ticker_map_v2.json"
    cache = json.loads(path.read_text()) if path.exists() else {"tickers": {}, "checked": []}
    if path.exists() and time.time() - path.stat().st_mtime < max_age_days * 86400:
        return {**cache["tickers"], **KNOWN_CIKS}
    checked = set(cache["checked"])
    todo = sorted(candidate_ciks() - checked)
    out = cache["tickers"]
    with ThreadPoolExecutor(max_workers=6) as pool:   # the rate limiter keeps it under the SEC cap
        for i, (cik, (_, tickers)) in enumerate(zip(todo, pool.map(tickers_for, todo)), 1):
            for t in tickers:
                out.setdefault(t.upper(), [cik])
            checked.add(cik)
            if progress and i % 250 == 0:
                print(f"  SEC ticker map: {i}/{len(todo)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tickers": out, "checked": sorted(checked)}))
    return {**out, **KNOWN_CIKS}


def _entries(facts: dict, tag: str) -> list[dict]:
    for taxonomy in ("us-gaap", "ifrs-full", "dei"):
        node = facts.get("facts", {}).get(taxonomy, {}).get(tag)
        if node:
            units = node["units"]
            unit = "USD" if "USD" in units else ("shares" if "shares" in units else None)
            return units.get(unit, []) if unit else []
    return []


def fact_table(ciks: int | list[int]) -> pd.DataFrame:
    """Every annual-report value we use, one row per reported number, with the
    date it was FILED - so later we can ask "what was known on date X?".
    Also the cover-page share count from every filing (10-K and 10-Q)."""
    rows = []
    for cik in [ciks] if isinstance(ciks, int) else ciks:
        facts = company_facts(cik)
        for item, tags in (FLOW | INSTANT).items():
            flow = item in FLOW
            for prio, tag in enumerate(tags):
                for e in _entries(facts, tag):
                    if e.get("form") not in ANNUAL_FORMS:
                        continue
                    if flow:
                        if "start" not in e:
                            continue
                        days = (pd.Timestamp(e["end"]) - pd.Timestamp(e["start"])).days
                        if not 350 <= days <= 380:   # full years only, not quarters
                            continue
                    rows.append((item, prio, e["end"], e["filed"], e.get("accn", ""), e["val"]))
        # share counts, best first: cover page (any filing), balance sheet, then
        # diluted weighted average (always one total, even with several share classes)
        for prio, tag in enumerate(("EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding",
                                    "WeightedAverageNumberOfDilutedSharesOutstanding")):
            for e in _entries(facts, tag):
                if prio == 2 and ("start" not in e or not 80 <= (pd.Timestamp(e["end"]) -
                                                                   pd.Timestamp(e["start"])).days <= 380):
                    continue
                rows.append(("shares", prio, e["end"], e["filed"], e.get("accn", ""), e["val"]))
        # market value of shares held by outside investors (cover page of each 10-K): a
        # fallback for companies whose share counts are only reported per class (Visa)
        for e in _entries(facts, "EntityPublicFloat"):
            rows.append(("public_float", 0, e["end"], e["filed"], e.get("accn", ""), e["val"]))
    t = pd.DataFrame(rows, columns=["item", "prio", "end", "filed", "accn", "val"])
    t["end"] = pd.to_datetime(t["end"])
    t["filed"] = pd.to_datetime(t["filed"])
    return t


def _annual(table: pd.DataFrame, item: str) -> pd.Series:
    """One value per fiscal year end. Restatements: the latest filing (in the
    table given) wins. Tag switches: preferred tags first, others fill gaps."""
    rows = table[table["item"] == item]
    merged = pd.Series(dtype=float)
    for _, grp in rows.sort_values("filed").groupby("prio", sort=True):
        s = grp.groupby("end")["val"].last()
        merged = s if merged.empty else merged.combine_first(s)
    return merged.sort_index()


def shares_outstanding(table: pd.DataFrame, as_of=None) -> tuple[pd.Timestamp | None, float]:
    """(date, shares) from the latest cover page filed by `as_of`. Companies
    with several share classes report one line per class - summed here."""
    sh = table[table["item"] == "shares"]
    if as_of is not None:
        sh = sh[sh["filed"] <= pd.Timestamp(as_of)]
    for _, grp in sh.groupby("prio", sort=True):
        # ignore sources that have gone stale (e.g. a tag the company stopped using)
        recent = grp[grp["filed"] >= sh["filed"].max() - pd.Timedelta(days=200)]
        if recent.empty:
            continue
        last = recent[recent["accn"] == recent.sort_values("filed")["accn"].iloc[-1]]
        last = last[last["end"] == last["end"].max()]
        when = last["end"].max()
        ref = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.today()
        if (ref - when).days > 400:      # over a year old: treat as unknown
            return None, np.nan
        return when, float(last["val"].sum())
    return None, np.nan


def public_float(table: pd.DataFrame, as_of=None) -> tuple[pd.Timestamp | None, float]:
    """(date, $ value) of the latest public float filed by `as_of`."""
    pf = table[table["item"] == "public_float"]
    if as_of is not None:
        pf = pf[pf["filed"] <= pd.Timestamp(as_of)]
    if pf.empty:
        return None, np.nan
    last = pf.sort_values(["filed", "end"]).iloc[-1]
    return last["end"], float(last["val"])


def annual_history(ciks: int | list[int], years: int = 12, as_of=None,
                   table: pd.DataFrame | None = None) -> pd.DataFrame:
    """Annual table: revenue, margins, cash flow and return on capital.

    as_of: only use numbers FILED on or before this date (point-in-time view,
           for backtests - no peeking at later reports or restatements).
    Pass several CIKs, newest first, for a company that re-registered (e.g.
    AngloGold Ashanti moved from South Africa to the UK in 2023).
    """
    t = fact_table(ciks) if table is None else table
    if as_of is not None:
        t = t[t["filed"] <= pd.Timestamp(as_of)]
    raw = pd.DataFrame({item: _annual(t, item) for item in FLOW | INSTANT})
    if raw.empty or "revenue" not in raw:
        return pd.DataFrame()
    # fiscal years can end a few days apart in different tags (52/53-week years)
    raw.index = pd.to_datetime(raw.index)
    raw = raw[raw["revenue"].notna()]
    raw = raw.groupby(raw.index.to_period("Y")).last()
    raw = raw.iloc[-years:]
    if raw.empty:
        return pd.DataFrame()

    out = pd.DataFrame(index=raw.index.astype(str))
    out.index.name = "fiscal_year"
    rev = raw["revenue"].to_numpy()
    out["revenue_$bn"] = rev / 1e9
    consecutive = pd.Series(raw.index.year).diff().eq(1).to_numpy()
    out["revenue_growth"] = np.where(consecutive, pd.Series(rev).pct_change().to_numpy(), np.nan)
    out["gross_margin"] = (raw["gross_profit"] / raw["revenue"]).to_numpy()
    out["operating_margin"] = (raw["operating_income"] / raw["revenue"]).to_numpy()
    fcf = raw["operating_cash_flow"] - raw["capex"]   # blank if capex isn't tagged, never overstated
    out["fcf_margin"] = (fcf / raw["revenue"]).to_numpy()
    # pre-tax operating return on capital, same capital definition as the screener
    capital = raw["assets"] - raw["cash"].fillna(0) - (raw["current_liabilities"] - raw["current_debt"].fillna(0))
    out["roic_pretax"] = (raw["operating_income"] / capital.where(capital > 0)).to_numpy()
    # absolute values, for valuation in backtests
    out["operating_income_$bn"] = raw["operating_income"].to_numpy() / 1e9
    out["net_income_$bn"] = raw["net_income"].to_numpy() / 1e9
    out["fcf_$bn"] = fcf.to_numpy() / 1e9
    out["debt_$bn"] = (raw["long_term_debt"].fillna(0) + raw["current_debt"].fillna(0)).to_numpy() / 1e9
    out["cash_$bn"] = raw["cash"].fillna(0).to_numpy() / 1e9
    return out.replace([np.inf, -np.inf], np.nan)
