"""Watchlist: every company a screen ranked but didn't buy, tracked against the picks.

Each time a sleeve locks new picks (quality screen every quarter, bottleneck every 2
weeks), the rest of that scan is saved as a "cohort" - the near misses with their rank,
score and why they missed the cut. All of them are then measured from the SAME
decision close as the picks, so "did we leave better stocks on the table?" is a fair
question. The scan CSVs in output/ are not committed, so the cohort keeps its own copy.

Files: journal/watchlist.json (cohorts) and journal/watchlist_review.json (latest
returns, for the dashboard). `python -m ai_desk journal watchlist` captures any new
cohorts and refreshes the returns; `portfolio run --execute` captures automatically.

Read it at the END of a cohort (the next re-pick), not daily: a few days of returns are
noise. If over many finished cohorts the near misses keep beating the picks, the
ranking isn't adding anything - that would be a case for an amendment.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ai_desk import tradebook

# columns kept per sleeve (what the dashboard shows next to each name)
KEEP = {
    "quality_screen": ["name", "sector", "industry", "score", "quality_score", "growth_score", "value_score",
                       "strength_score", "momentum_score", "roic_avg", "rev_cagr", "forward_pe", "fcf_yield"],
    "bottleneck": ["name", "sector", "industry", "source", "score", "flow_score", "bottleneck_score",
                   "asymmetry_score", "rs_6m", "rev_growth", "gm_change", "above_ma", "passes", "forward_pe"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cohorts() -> list[dict]:
    p = tradebook.DIR / "watchlist.json"
    return json.loads(p.read_text()) if p.exists() else []


def _save(rows: list[dict]) -> None:
    tradebook.DIR.mkdir(parents=True, exist_ok=True)
    (tradebook.DIR / "watchlist.json").write_text(json.dumps(rows, indent=1, default=str))


def _clean(v):
    if isinstance(v, (np.floating, float)):
        return None if v != v else round(float(v), 5)
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    return v


def bottleneck_reason(row: pd.Series, gates: dict | None = None) -> str:
    """Why a bottleneck candidate failed its gates (empty if it passed)."""
    from ai_desk.bottleneck.scan import GATES

    g = gates or GATES
    out = []
    if not (row.get("rev_growth") == row.get("rev_growth")) or row.get("rev_growth", 0) < g["min_rev_growth"]:
        out.append(f"revenue growth under {g['min_rev_growth']:.0%}")
    if (row.get("gm_change") if row.get("gm_change") == row.get("gm_change") else 0) < g["min_gm_change"]:
        out.append("gross margin falling")
    if not bool(row.get("above_ma")):
        out.append(f"below its {int(row.get('ma_days') or 100)}-day average")
    if (row.get("market_cap") or 0) < g["min_market_cap"]:
        out.append(f"market cap under ${g['min_market_cap'] / 1e9:.0f}B")
    return ", ".join(out)


def build_cohort(sleeve: str, scan: pd.DataFrame, picks: list[str], locked_on: str, ref_date: str,
                 screen_file: str, top: int) -> dict:
    """Pure: turn a scan + the chosen picks into a cohort of picks and near misses."""
    scan = scan.copy()
    if sleeve == "bottleneck" and "passes" in scan:
        passed = scan["passes"].astype(bool)
        scan["rank"] = scan["score"].where(passed).rank(ascending=False, method="first")
    else:
        scan["rank"] = scan["score"].rank(ascending=False, method="first")
    rows = []
    for _, r in scan.sort_values(["rank", "score"], ascending=[True, False], na_position="last").iterrows():
        sym = r["symbol"]
        picked = sym in picks
        if picked:
            status, reason = "picked", f"ranked #{int(r['rank'])} of the top {top}" if r["rank"] == r["rank"] else "picked"
        elif r["rank"] == r["rank"]:
            status, reason = "near miss", f"ranked #{int(r['rank'])} - only the top {top} are bought"
        else:
            status, reason = "failed a gate", bottleneck_reason(r)
        rows.append({"symbol": sym, "rank": _clean(r["rank"]), "status": status, "reason": reason,
                     **{k: _clean(r.get(k)) for k in KEEP.get(sleeve, []) if k in r}})
    return {"id": f"{sleeve}:{locked_on}", "sleeve": sleeve, "locked_on": locked_on, "ref_date": ref_date,
            "screen_file": screen_file, "top": top, "captured_utc": _now(), "rows": rows}


def sync(method, ref_date: str | None = None) -> list[dict]:
    """Capture a cohort for every locked sleeve in `method` that doesn't have one yet."""
    parts = [m for m, _ in getattr(method, "parts", [])] or [method]
    existing = {c["id"] for c in cohorts()}
    new = []
    for m in parts:
        lock_path = getattr(m, "lock_path", "")
        if not lock_path or not Path(lock_path).exists():
            continue
        lock = json.loads(Path(lock_path).read_text())
        cid = f"{m.name}:{lock['locked_on']}"
        csv = Path(m.screen_glob).parent / lock["screen_file"]
        if cid in existing or not csv.exists():
            continue
        ref = ref_date or tradebook._read_plan().get("signal_date") or lock["locked_on"]
        scan = pd.read_csv(csv)
        full = csv.parent / "candidates" / lock["screen_file"]       # bottleneck: gate failures too
        if full.exists():
            cands = pd.read_csv(full)
            cands = cands.rename(columns={cands.columns[0]: "symbol"}) if "symbol" not in cands else cands
            extra = cands[~cands["symbol"].isin(scan["symbol"])].assign(passes=False)
            scan = pd.concat([scan, extra], ignore_index=True)
        new.append(build_cohort(m.name, scan, lock["picks"], lock["locked_on"], str(ref),
                                lock["screen_file"], getattr(m, "top", len(lock["picks"]))))
    if new:
        _save(cohorts() + new)
    return new


# --- review -----------------------------------------------------------------------

def compare(cohort: dict, closes: pd.DataFrame, spy: str = "SPY") -> tuple[list[dict], dict]:
    """Pure: return of every row from the cohort's decision close to the latest close."""
    ref = pd.Timestamp(cohort["ref_date"])
    hist = closes.loc[:ref]
    if hist.empty:
        return [], {}
    start, last = hist.iloc[-1], closes.ffill().iloc[-1]
    rows = []
    for r in cohort["rows"]:
        s = r["symbol"]
        ret = float(last[s] / start[s] - 1) if s in closes and start.get(s) == start.get(s) and start.get(s) else None
        rows.append({"cohort": cohort["id"], "sleeve": cohort["sleeve"], **r,
                     "return": None if ret is None or ret != ret else round(ret, 5)})
    rets = pd.DataFrame(rows)
    picks = rets.loc[rets["status"] == "picked", "return"].dropna()
    near = rets.loc[rets["status"] == "near miss", "return"].dropna()
    failed = rets.loc[rets["status"] == "failed a gate", "return"].dropna()
    watch = rets.loc[rets["status"] != "picked", "return"].dropna()
    pavg = float(picks.mean()) if len(picks) else None
    for r in rows:
        r["vs_picks"] = None if r["return"] is None or pavg is None else round(r["return"] - pavg, 5)
    best = rets[rets["status"] != "picked"].dropna(subset=["return"]).sort_values("return", ascending=False)
    spy_ret = float(last[spy] / start[spy] - 1) if spy in closes and start.get(spy) == start.get(spy) else None
    summary = {
        "cohort": cohort["id"], "sleeve": cohort["sleeve"], "locked_on": cohort["locked_on"],
        "ref_date": cohort["ref_date"], "asof": closes.index[-1].date().isoformat(),
        "days": int(len(closes.loc[ref:]) - 1), "picks": int(len(picks)), "watching": int(len(watch)),
        "picks_avg": pavg, "near_miss_avg": float(near.mean()) if len(near) else None,
        "failed_gate_avg": float(failed.mean()) if len(failed) else None,
        "watch_avg": float(watch.mean()) if len(watch) else None, "spy": spy_ret,
        "watch_beating_picks": int((watch > pavg).sum()) if pavg is not None else None,
        "best_symbol": best["symbol"].iloc[0] if len(best) else None,
        "best_return": float(best["return"].iloc[0]) if len(best) else None,
    }
    return rows, summary


def _closes(symbols: list[str], start: str) -> pd.DataFrame:
    import yfinance as yf

    from ai_desk.fundamentals.yahoo import with_retry

    raw = with_retry(lambda: yf.download(symbols, start=start, auto_adjust=True, progress=False, threads=True))
    c = raw["Close"]
    if isinstance(c, pd.Series):
        c = c.to_frame(symbols[0])
    c.index = pd.to_datetime(c.index).tz_localize(None)
    return c


def review(closes: pd.DataFrame | None = None, write: bool = True) -> dict:
    """Returns for the latest cohort of each sleeve (and every earlier one, for the record)."""
    cs = cohorts()
    if not cs:
        out = {"asof_utc": _now(), "summary": [], "rows": []}
    else:
        if closes is None:
            symbols = sorted({r["symbol"] for c in cs for r in c["rows"]} | {"SPY"})
            start = (pd.Timestamp(min(c["ref_date"] for c in cs)) - pd.Timedelta(days=10)).date().isoformat()
            closes = _closes(symbols, start)
        latest = {}
        for c in cs:
            if c["sleeve"] not in latest or c["locked_on"] > latest[c["sleeve"]]["locked_on"]:
                latest[c["sleeve"]] = c
        rows, summary = [], []
        for c in sorted(cs, key=lambda c: (c["sleeve"], c["locked_on"])):
            r, s = compare(c, closes)
            s["current"] = latest[c["sleeve"]]["id"] == c["id"]
            summary.append(s)
            if s["current"]:
                rows += r
        out = {"asof_utc": _now(), "summary": summary, "rows": rows}
    if write:
        tradebook.DIR.mkdir(parents=True, exist_ok=True)
        (tradebook.DIR / "watchlist_review.json").write_text(json.dumps(out, indent=1, default=str))
    return out
