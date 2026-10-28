"""House of Representatives stock trades (STOCK Act Periodic Transaction Reports) from the House Clerk.

    python research/house_ptr.py [--years 2014-2026] [--workers 4]

Source: disclosures-clerk.house.gov (allowed in the network policy 2026-10-28). Each year's index
(public_disc/financial-pdfs/<year>FD.zip) lists every filing; FilingType P = a PTR, with its FilingDate - the day it
was filed. Electronically filed PTRs (DocID starting with 2) are text PDFs and are parsed here; paper filings
(DocID 8.../9..., about a third of 2014-2019 and ~15% since) are scanned images and are SKIPPED - say so when quoting.
Text of each PDF is cached in data/congress/ptr_text/<DocID>.txt; the trades go to data/congress/trades.csv in the
smart_money format (date = TRADE date) plus `filed` = the day the report was filed (the first day the public could
know - signals must use it, not the trade date), member, owner, asset type and doc id. House only: the Senate's
site (efdsearch.senate.gov) is not in the network policy.
"""

from __future__ import annotations

import argparse
import io
import re
import subprocess
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "congress"
TEXT = DIR / "ptr_text"
BASE = "https://disclosures-clerk.house.gov/public_disc"
MIN_GAP = 0.2                                     # at most ~5 requests a second across threads
_lock = threading.Lock()
_last = [0.0]

TX = re.compile(r"(?<![A-Za-z])(P|S \(partial\)|S|E)\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+\$([\d,]+)"
                r"(?:\s*-\s*\$?([\d,]+))?")
TICKER = re.compile(r"\(([A-Z]{1,5}(?:[.\-/][A-Z]{1,2})?)\)")
ATYPE = re.compile(r"\[([A-Z]{2})\]")
OWNER = re.compile(r"^\s*(SP|JT|DC)\s{2,}")
AMOUNT_HIGH = re.compile(r"^\s*\$([\d,]+)\s*$")


def _get(url: str, tries: int = 4) -> requests.Response:
    for k in range(tries):
        with _lock:
            wait = _last[0] + MIN_GAP - time.time()
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.time()
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent": "AI-Desk research"})
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(str(r.status_code))
            return r
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
            if k == tries - 1:
                raise
            time.sleep(2 ** (k + 1))
    raise RuntimeError("unreachable")


def index(year: int) -> pd.DataFrame:
    """Every PTR filed in one year's index: member, state/district, filing date, doc id."""
    z = zipfile.ZipFile(io.BytesIO(_get(f"{BASE}/financial-pdfs/{year}FD.zip").content))
    x = z.read(f"{year}FD.xml").decode("utf-8-sig")
    rows = []
    for m in re.findall(r"<Member>(.*?)</Member>", x, re.S):
        f = dict(re.findall(r"<(\w+)>([^<]*)</\1>", m))
        if f.get("FilingType") == "P" and f.get("DocID"):
            rows.append({"year": year, "doc_id": f["DocID"], "member": f"{f.get('First', '')} {f.get('Last', '')}".strip(),
                         "state_dst": f.get("StateDst", ""), "filed": pd.to_datetime(f.get("FilingDate"))})
    return pd.DataFrame(rows)


def text_of(year: int, doc_id: str) -> str | None:
    """The PDF's text (pdftotext -layout), cached. None if it couldn't be fetched."""
    p = TEXT / f"{doc_id}.txt"
    if p.exists():
        return p.read_text()
    r = _get(f"{BASE}/ptr-pdfs/{year}/{doc_id}.pdf")
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        return None
    out = subprocess.run(["pdftotext", "-layout", "-", "-"], input=r.content, capture_output=True).stdout
    t = out.decode("utf-8", "replace")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t)
    return t


def parse(text: str) -> list[dict]:
    """Pure: the transactions in one electronic PTR's text. Each transaction line carries the type (P purchase,
    S sale, S (partial), E exchange), trade date, notification date and amount band; the asset's name, ticker and
    [type] sit on that line or wrap onto the lines just after it."""
    lines = text.splitlines()
    hits = [(i, m) for i, ln in enumerate(lines) for m in [TX.search(ln)] if m]
    out = []
    for k, (i, m) in enumerate(hits):
        hi = hits[k + 1][0] if k + 1 < len(hits) else len(lines)
        after = []
        for ln in lines[i + 1:min(hi, i + 4)]:
            if re.search(r"^\s*(F|D|C|S|L)\s{2,}\S|Filing Status|Description|Comments|Subholding", ln):
                break                                  # the next fields belong to this trade but aren't its asset
            after.append(ln)
        here = lines[i][:m.start()]
        window = " ".join([here] + after)             # never the lines above: they end the previous trade
        tick = TICKER.findall(window)
        atype = ATYPE.findall(window)
        own = OWNER.match(lines[i])
        high = m.group(5)
        if not high:
            for ln in after:
                h = AMOUNT_HIGH.search(ln.strip()) or re.search(r"\$([\d,]+)\s*$", ln)
                if h:
                    high = h.group(1)
                    break
        typ = {"P": "purchase", "S": "sale", "S (partial)": "sale", "E": "exchange"}[m.group(1)]
        out.append({"ticker": tick[0] if tick else None, "asset_type": atype[0] if atype else None,
                    "owner": own.group(1) if own else "self", "type": typ,
                    "date": pd.to_datetime(m.group(2), format="%m/%d/%Y", errors="coerce"),
                    "amount_low": int(m.group(4).replace(",", "")),
                    "amount_high": int(high.replace(",", "")) if high else None})
    return out


def build(years: range, workers: int = 4) -> pd.DataFrame:
    idx = pd.concat([index(y) for y in years], ignore_index=True)
    elec = idx[idx["doc_id"].str.startswith("2")].drop_duplicates("doc_id")
    print(f"{len(idx):,} PTRs listed, {len(elec):,} electronic (paper scans skipped)", flush=True)
    done = [0]

    def one(row):
        t = text_of(int(row.year), row.doc_id)
        done[0] += 1
        if done[0] % 250 == 0:
            print(f"  {done[0]:,}/{len(elec):,}", flush=True)
        return [{**tr, "doc_id": row.doc_id, "politician": row.member, "state_dst": row.state_dst,
                 "filed": row.filed, "chamber": "house"} for tr in parse(t or "")]

    with ThreadPoolExecutor(workers) as ex:
        trades = [tr for rs in ex.map(one, elec.itertuples()) for tr in rs]
    df = pd.DataFrame(trades)
    DIR.mkdir(parents=True, exist_ok=True)
    idx.to_csv(DIR / "ptr_index.csv", index=False)
    df.to_csv(DIR / "trades.csv", index=False)
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2014-2026")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    y0, y1 = (int(x) for x in a.years.split("-"))
    df = build(range(y0, y1 + 1), a.workers)
    print(f"{len(df):,} transactions; with a ticker: {df['ticker'].notna().mean():.0%}; "
          f"stocks [ST]: {(df['asset_type'] == 'ST').mean():.0%}")
    print(df["type"].value_counts().to_string())
    print(f"wrote {DIR / 'trades.csv'}")


if __name__ == "__main__":
    main()
