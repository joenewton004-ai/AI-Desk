"""Industry of each stock for the overnight sleeve's sector cap (amendment in `overnight.SECTOR_CAP`).

Industry = the 2-digit SEC SIC code of the company's filing record (the same grouping research/overnight_safety2.py
tested). Ticker -> CIK from www.sec.gov/files/company_tickers.json (reachable since 2026-10-29), SIC from
data.sec.gov/submissions. Saved in data/portfolio/sectors.json (COMMITTED, so a fresh checkout doesn't re-download);
a symbol not found stays unknown and is never capped (it counts as its own group).
"""

from __future__ import annotations

import json
from pathlib import Path

FILE = Path("data/portfolio/sectors.json")
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def load() -> dict[str, dict]:
    return json.loads(FILE.read_text()) if FILE.exists() else {}


def _sec_symbol(sym: str) -> str:
    return sym.upper().replace(".", "-")             # Alpaca BRK.B -> SEC BRK-B


def lookup(symbols: list[str]) -> dict[str, int | None]:
    """{symbol: 2-digit SIC or None}; fetches only symbols not saved yet (one ticker list + one header each)."""
    have = load()
    todo = [s for s in symbols if s not in have]
    if todo:
        from ai_desk.fundamentals import edgar
        try:
            r = edgar._get(TICKERS_URL)
            table = {_sec_symbol(v["ticker"]): int(v["cik_str"]) for v in r.json().values()} if r.ok else {}
        except Exception:  # noqa: BLE001 - unknown industries are simply not capped
            table = {}
        for s in todo:
            cik = table.get(_sec_symbol(s))
            sic = None
            if cik:
                try:
                    sic = edgar.company_header(cik).get("sic")
                except Exception:  # noqa: BLE001
                    sic = None
            if cik or table:                           # don't save misses when the ticker list itself failed
                have[s] = {"cik": cik, "sic": sic}
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(json.dumps(dict(sorted(have.items())), indent=0))
    return {s: (have.get(s, {}).get("sic") or 0) // 100 or None for s in symbols}
