"""Congress trades screen: House members' stock trades (STOCK Act Periodic Transaction Reports), kept current.

    python -m ai_desk congress refresh     (new filings since the last run; the evening run's `portfolio prepare` does it)
    python -m ai_desk congress status

Source: disclosures-clerk.house.gov (allowed in the network policy 2026-10-28). Each year's index lists every filing;
electronically filed reports (DocID starting with 2) are text PDFs and are parsed here; paper filings are scanned
images and are skipped. The Senate's site isn't reachable. History (2014-) is built once by research/house_ptr.py into
data/congress/ (not committed); `refresh` adds new filings to it and writes the screen to journal/congress/screen.json
(committed), which `journal export` turns into the dashboard's Congress tab.

What the screen shows is information, not a signal: research/CONGRESS.md found no edge in copying these trades
(bought at the open after the filing: 13.9%/yr vs SPY 13.7%, 2014-2026). Each trade is dated by when it was FILED -
the first day the public could know - and measured from the first close after that.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "congress"
TEXT = DIR / "ptr_text"
TRADES = DIR / "trades.csv"
SCREEN = ROOT / "journal" / "congress" / "screen.json"
RECENT = ROOT / "journal" / "congress" / "recent.csv"     # the last ~13 months of trades, committed: fresh checkouts
SEEN = ROOT / "journal" / "congress" / "seen.json"        # filings already read (incl. ones with no stock trades)
KEEP_DAYS = 400
BASE = "https://disclosures-clerk.house.gov/public_disc"
MIN_GAP = 0.2                                     # at most ~5 requests a second across threads
WINDOW_TRADES, WINDOW_TOP, WINDOW_MEMBERS = 180, 90, 365   # days of filings each table covers
_lock = threading.Lock()
_last = [0.0]

TX = re.compile(r"(?<![A-Za-z])(P|S \(partial\)|S|E)\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+\$([\d,]+)"
                r"(?:\s*-\s*\$?([\d,]+))?")
TICKER = re.compile(r"\(([A-Z]{1,5}(?:[.\-/][A-Z]{1,2})?)\)")
ATYPE = re.compile(r"\[([A-Z]{2})\]")
OWNER = re.compile(r"^\s*(SP|JT|DC)\s{2,}")
AMOUNT_HIGH = re.compile(r"^\s*\$([\d,]+)\s*$")


# --- the House Clerk's filings ------------------------------------------------------------------------------------

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


def rows_for(doc: pd.Series, text: str | None) -> list[dict]:
    return [{**tr, "doc_id": doc["doc_id"], "politician": doc["member"], "state_dst": doc["state_dst"],
             "filed": doc["filed"], "chamber": "house"} for tr in parse(text or "")]


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date", "filed"], dtype={"doc_id": str}, low_memory=False)


def load_trades() -> pd.DataFrame:
    """The full history (data/congress/trades.csv, built by research/house_ptr.py) when this machine has it, else the
    committed last ~13 months (journal/congress/recent.csv) - enough for every table on the screen."""
    if TRADES.exists():
        return _read(TRADES)
    if RECENT.exists():
        return _read(RECENT)
    raise RuntimeError("no Congress trades - run `python research/house_ptr.py` once (~35 min)")


def update(years: list[int] | None = None) -> int:
    """Read filings not seen before (this year, and last year in January); add their trades to the full history (if
    this machine has it) and to the committed recent file."""
    today = pd.Timestamp.now(tz="America/New_York").tz_localize(None)
    years = years or sorted({today.year, (today - pd.Timedelta(days=31)).year})
    have = load_trades()
    seen = set(json.loads(SEEN.read_text())) if SEEN.exists() else set()
    seen |= set(have["doc_id"].dropna())
    idx = pd.concat([index(y) for y in years], ignore_index=True)
    elec = idx[idx["doc_id"].str.startswith("2")].drop_duplicates("doc_id")
    new = elec[~elec["doc_id"].isin(seen)]
    rows = [r for _, doc in new.iterrows() for r in rows_for(doc, text_of(int(doc["year"]), doc["doc_id"]))]
    allt = pd.concat([have, pd.DataFrame(rows)], ignore_index=True) if rows else have
    if rows and TRADES.exists():
        allt.to_csv(TRADES, index=False)
    RECENT.parent.mkdir(parents=True, exist_ok=True)
    allt[allt["filed"] >= today.normalize() - pd.Timedelta(days=KEEP_DAYS)].to_csv(RECENT, index=False)
    SEEN.write_text(json.dumps(sorted(seen | set(elec["doc_id"]))))
    return len(new)


# --- prices -------------------------------------------------------------------------------------------------------

def daily_closes(symbols: list[str], start: str) -> pd.DataFrame:
    """Daily closes from Alpaca (SIP, split-adjusted), many symbols per request; a symbol Alpaca doesn't know is
    dropped (its trades show no move)."""
    from ai_desk.broker.alpaca import AlpacaPaper
    s = AlpacaPaper().session
    want = sorted({x.replace("-", ".") for x in symbols if x})
    rows: dict[str, list] = {}
    while want:
        chunk, want = want[:100], want[100:]
        params = {"symbols": ",".join(chunk), "timeframe": "1Day", "start": f"{start}T00:00:00Z", "limit": 10000,
                  "adjustment": "all", "feed": "sip"}
        while True:
            r = s.get("https://data.alpaca.markets/v2/stocks/bars", params=params, timeout=30)
            if r.status_code == 400 and "invalid symbol" in r.text:
                bad = r.text.split("invalid symbol:")[-1].strip().strip('"}').strip()
                chunk = [c for c in chunk if c != bad]
                if not chunk:
                    break
                params["symbols"] = ",".join(chunk)
                params.pop("page_token", None)
                continue
            r.raise_for_status()
            js = r.json()
            for sym, bs in (js.get("bars") or {}).items():
                rows.setdefault(sym, []).extend(bs)
            if not js.get("next_page_token"):
                break
            params["page_token"] = js["next_page_token"]
    out = {}
    for sym, bs in rows.items():
        ser = pd.Series({pd.Timestamp(b["t"][:10]): float(b["c"]) for b in bs})
        out[sym.replace(".", "-")] = ser
    return pd.DataFrame(out).sort_index()


# --- the screen (pure) --------------------------------------------------------------------------------------------

TITLES = re.compile(r"\b(Mr|Mrs|Ms|Miss|Dr|Hon|Honorable|Jr|Sr)\.?(?=\s|$)", re.I)


def clean_name(name: str) -> str:
    """Pure: 'John J Mr McGuire' -> 'John J McGuire' (the index sometimes keeps titles inside names)."""
    return re.sub(r"\s+", " ", TITLES.sub("", str(name))).strip(" ,.")


def _band(lo, hi) -> str:
    def f(v):
        return f"${v / 1e6:g}M" if v >= 1e6 else f"${v:,.0f}"
    return f"{f(lo)} - {f(hi)}" if hi == hi and hi else f"{f(lo)}+"


def since_filed(closes: pd.DataFrame, ticker: str, filed: pd.Timestamp) -> tuple[float, float] | None:
    """The stock's and SPY's move from the first close after the filing day (when the public could act) to the
    latest close. None if there's no price yet."""
    if ticker not in closes or "SPY" not in closes:
        return None
    after = closes.index[closes.index > filed]
    if len(after) == 0:
        return None
    a, s = closes[ticker], closes["SPY"]
    start = a.loc[after[0]:].first_valid_index()
    end = a.last_valid_index()
    if start is None or end is None or end <= start:
        return None
    return float(a[end] / a[start] - 1), float(s.loc[end] / s.loc[start] - 1)


def screen(trades: pd.DataFrame, closes: pd.DataFrame, today: pd.Timestamp) -> dict[str, list[dict]]:
    """Pure: the dashboard's Congress tables from the trades and daily closes."""
    t = trades[trades["ticker"].notna() & trades["type"].isin(["purchase", "sale"])
               & (trades["asset_type"].isin(["ST", "OP"]) | trades["asset_type"].isna())].copy()
    t["ticker"] = t["ticker"].str.upper().str.replace(".", "-", regex=False)
    t["mid"] = (t["amount_low"] + t["amount_high"].fillna(t["amount_low"])) / 2
    t["delay"] = (t["filed"] - t["date"]).dt.days
    t["politician"] = t["politician"].map(clean_name)
    recent = t[t["filed"] >= today - pd.Timedelta(days=WINDOW_TRADES)]
    keys = ["filed", "date", "politician", "state_dst", "owner", "ticker", "type", "asset_type", "amount_low",
            "amount_high", "doc_id", "delay"]
    recent = (recent.fillna({"asset_type": "", "amount_high": -1, "date": pd.NaT})
              .groupby(keys, dropna=False).size().rename("lots").reset_index()
              .replace({"amount_high": {-1: np.nan}, "asset_type": {"": None}})
              .sort_values(["filed", "politician", "ticker"], ascending=[False, True, True]))
    rows = []
    for k, r in enumerate(recent.itertuples()):
        mv = since_filed(closes, r.ticker, r.filed)
        rows.append({"id": f"{r.doc_id}-{k}", "filed": r.filed.date().isoformat(),
                     "traded": r.date.date().isoformat() if pd.notna(r.date) else None,
                     "days_to_report": int(r.delay) if r.delay == r.delay else None, "member": r.politician,
                     "district": r.state_dst, "owner": {"self": "Member", "SP": "Spouse", "JT": "Joint",
                                                        "DC": "Child"}.get(r.owner, r.owner),
                     "ticker": r.ticker, "side": "Buy" if r.type == "purchase" else "Sell",
                     "asset": "Option" if r.asset_type == "OP" else "Stock", "amount": _band(r.amount_low, r.amount_high), "lots": int(r.lots),
                     "since_filed": round(mv[0], 4) if mv else None, "spy_since": round(mv[1], 4) if mv else None,
                     "vs_spy": round(mv[0] - mv[1], 4) if mv else None})
    trows = pd.DataFrame(rows)

    top_src = t[t["filed"] >= today - pd.Timedelta(days=WINDOW_TOP)]
    top = []
    for tk, g in top_src.groupby("ticker"):
        buys, sells = g[g["type"] == "purchase"], g[g["type"] == "sale"]
        if buys.empty:
            continue
        mv = since_filed(closes, tk, buys["filed"].min())
        top.append({"ticker": tk, "buyers": int(buys["politician"].nunique()), "buys": len(buys), "sells": len(sells),
                    "bought_est": round(float(buys["mid"].sum())), "first_buy_filed": buys["filed"].min().date().isoformat(),
                    "since_first_buy": round(mv[0], 4) if mv else None,
                    "vs_spy": round(mv[0] - mv[1], 4) if mv else None})
    top.sort(key=lambda r: (-r["buyers"], -r["bought_est"]))

    mem_src = t[t["filed"] >= today - pd.Timedelta(days=WINDOW_MEMBERS)]
    members = []
    for m, g in mem_src.groupby("politician"):
        mine = trows[(trows["member"] == m) & (trows["side"] == "Buy")] if len(trows) else trows
        vs = mine["vs_spy"].dropna() if len(mine) else pd.Series(dtype=float)
        members.append({"member": m, "district": g["state_dst"].iloc[-1], "trades": len(g),
                        "buys": int((g["type"] == "purchase").sum()), "sells": int((g["type"] == "sale").sum()),
                        "stocks": int(g["ticker"].nunique()), "est_value": round(float(g["mid"].sum())),
                        "avg_days_to_report": round(float(g["delay"].mean()), 1),
                        "recent_buys_vs_spy": round(float(vs.mean()), 4) if len(vs) else None})
    members.sort(key=lambda r: -r["trades"])

    last30 = t[t["filed"] >= today - pd.Timedelta(days=30)]
    most = top[0]["ticker"] if top else None
    summary = [{"latest_filing": t["filed"].max().date().isoformat() if len(t) else None,
                "trades_30d": len(last30), "buys_30d": int((last30["type"] == "purchase").sum()),
                "sells_30d": int((last30["type"] == "sale").sum()), "members_30d": int(last30["politician"].nunique()),
                "most_bought_90d": most, "most_bought_buyers": top[0]["buyers"] if top else None,
                "median_days_to_report": float(t.loc[t["filed"] >= today - pd.Timedelta(days=365), "delay"].median())
                if len(t) else None}]
    return {"congress_trades": rows, "congress_top": top[:50], "congress_members": members[:50],
            "congress_summary": summary}


def refresh() -> dict:
    """New filings, prices, and the screen saved to journal/congress/screen.json."""
    new = update()
    trades = load_trades()
    today = pd.Timestamp.now(tz="America/New_York").tz_localize(None).normalize()
    tick = trades.loc[trades["filed"] >= today - pd.Timedelta(days=WINDOW_MEMBERS), "ticker"].dropna()
    syms = sorted({x.upper().replace(".", "-") for x in tick} | {"SPY"})
    closes = daily_closes(syms, (today - pd.Timedelta(days=WINDOW_MEMBERS + 10)).date().isoformat())
    now = pd.Timestamp.now(tz="America/New_York")
    if (now.hour, now.minute) < (16, 15):
        closes = closes[closes.index < today]          # today's bar isn't final while the market is open
    out = screen(trades, closes, today)
    out["congress_summary"][0]["refreshed_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out["congress_summary"][0]["new_filings"] = new
    SCREEN.parent.mkdir(parents=True, exist_ok=True)
    SCREEN.write_text(json.dumps(out, indent=1, default=str))
    return {"new_filings": new, **{k: len(v) for k, v in out.items()}}


def tables() -> dict[str, list[dict]]:
    """The saved screen for `journal export` (empty if it was never refreshed)."""
    if not SCREEN.exists():
        return {"congress_trades": [], "congress_top": [], "congress_members": [], "congress_summary": []}
    d = json.loads(SCREEN.read_text())
    return {k: d.get(k, []) for k in ("congress_trades", "congress_top", "congress_members", "congress_summary")}
