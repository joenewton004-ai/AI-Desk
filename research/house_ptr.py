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
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.congress import BASE, DIR, TEXT, index, parse, text_of  # noqa: E402,F401 - shared with the live screen


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
