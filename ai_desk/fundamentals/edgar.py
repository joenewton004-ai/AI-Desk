"""Long-run financial history from SEC EDGAR's XBRL "company facts" API.

Every number a US-listed company has reported in a 10-K / 20-F since ~2009,
tagged with the date it was FILED - which is what a point-in-time backtest
needs (you can only act on a number after it's public).

Only data.sec.gov is used. The SEC asks callers to identify themselves:
set SEC_USER_AGENT in .env to something like "Your Name you@example.com".
"""

from __future__ import annotations

import json
import os
import time
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
                "RevenueFromContractsWithCustomers"],
    "gross_profit": ["GrossProfit"],
    # last resort for filers with no operating line (e.g. AngloGold): pre-tax profit
    "operating_income": ["OperatingIncomeLoss", "ProfitLossFromOperatingActivities", "ProfitLossBeforeTax"],
    "net_income": ["NetIncomeLoss", "ProfitLossAttributableToOwnersOfParent", "ProfitLoss"],
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
}
ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F")


def _user_agent() -> str:
    from ai_desk.broker.alpaca import load_dotenv

    load_dotenv()
    return os.environ.get("SEC_USER_AGENT", "AI-Desk research tool")


def company_facts(cik: int, cache_dir: Path = CACHE, max_age_days: float = 7) -> dict:
    path = cache_dir / f"CIK{cik:010d}.json"
    if path.exists():
        age = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
        if age < max_age_days * 86400:
            return json.loads(path.read_text())
    for attempt in range(4):
        r = requests.get(f"{BASE}/api/xbrl/companyfacts/CIK{cik:010d}.json",
                         headers={"User-Agent": _user_agent()}, timeout=30)
        if r.status_code == 200:
            break
        time.sleep(2 ** attempt)   # SEC allows ~10 requests/second; back off on 429/503
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text)
    return r.json()


def _entries(facts: dict, tag: str) -> list[dict]:
    for taxonomy in ("us-gaap", "ifrs-full"):
        node = facts.get("facts", {}).get(taxonomy, {}).get(tag)
        if node:
            units = node["units"]
            unit = "USD" if "USD" in units else ("shares" if "shares" in units else None)
            return units.get(unit, []) if unit else []
    return []


def _annual(facts: dict, tags: list[str], flow: bool) -> pd.Series:
    """One value per fiscal year end, from annual reports only. For flow items
    (revenue, cash flow) only ~12-month periods count; restated figures take
    the most recently filed version."""
    merged = pd.Series(dtype=float)
    for tag in tags:
        rows = []
        for e in _entries(facts, tag):
            if e.get("form") not in ANNUAL_FORMS:
                continue
            end = pd.Timestamp(e["end"])
            if flow:
                if "start" not in e:
                    continue
                days = (end - pd.Timestamp(e["start"])).days
                if not 350 <= days <= 380:
                    continue
            rows.append((end, e["filed"], e["val"]))
        if not rows:
            continue
        df = pd.DataFrame(rows, columns=["end", "filed", "val"]).sort_values("filed")
        s = df.groupby("end")["val"].last()
        merged = s if merged.empty else merged.combine_first(s)
    return merged.sort_index()


def annual_history(ciks: int | list[int], years: int = 12) -> pd.DataFrame:
    """Annual table: revenue, margins, cash flow and return on capital.

    Pass several CIKs, newest first, for a company that re-registered (e.g.
    AngloGold Ashanti moved from South Africa to the UK in 2023).
    Share counts are left out: EDGAR keeps them as originally reported, so
    stock splits would look like 10x dilution.
    """
    raw = pd.DataFrame()
    for cik in [ciks] if isinstance(ciks, int) else ciks:
        facts = company_facts(cik)
        cols = {k: _annual(facts, v, flow=True) for k, v in FLOW.items()}
        cols |= {k: _annual(facts, v, flow=False) for k, v in INSTANT.items()}
        raw = pd.DataFrame(cols) if raw.empty else raw.combine_first(pd.DataFrame(cols))
    # fiscal years can end a few days apart in different tags (52/53-week years)
    raw.index = pd.to_datetime(raw.index)
    raw = raw[raw["revenue"].notna()]
    raw = raw.groupby(raw.index.to_period("Y")).last()
    raw = raw.iloc[-years:]

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
    return out.replace([np.inf, -np.inf], np.nan)
