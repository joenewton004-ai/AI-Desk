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

The daily check (`diagnose`) says how unusual today's gap is (a permutation test: how often
a random group of the same size, drawn from the same cohort, did as well as the picks),
which scores and sectors explain it, and a verdict under fixed rules decided in advance:
too early before the re-pick; after it, "worth a test" only if the gap is beyond chance.
Each day's check is appended to journal/watchlist_daily.jsonl. The 12-year baseline is in
research/NEAR_MISSES.md (`python research/near_misses.py`).
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
    "momentum": ["name", "sector", "industry", "score", "mom_6m", "above_200", "passes", "market_cap"],
}


# trading days until each sleeve re-picks: the point at which a cohort can be judged
HORIZON = {"quality_screen": 63, "bottleneck": 10, "momentum": 20}
# research/NEAR_MISSES.md, 2014-2026 (survivors-only): how often the picks beat the near misses at past re-picks
BASELINE = {"quality_screen": "picks beat the other gate-passers in 64% of 50 quarters (+1.6%/quarter, t = 2.5)",
            "momentum": "picks beat ranks 21-40 in 66% of 163 re-picks (+1.3% per 4 weeks, t = 4.0)",
            "bottleneck": "not measured (the sleeve is replaced by momentum on 2026-11-03)"}
SCORE_COLS = {"quality_screen": ["score", "quality_score", "growth_score", "value_score", "strength_score",
                                 "momentum_score"],
              "bottleneck": ["score", "flow_score", "bottleneck_score", "asymmetry_score", "rs_6m"],
              "momentum": ["score", "mom_6m"]}


def diagnose(summary: dict, rows: list[dict], draws: int = 2000, seed: int = 0) -> dict:
    """Pure: why are the near misses ahead of (or behind) the picks, and does it matter yet?"""
    df = pd.DataFrame(rows)
    out = {"cohort": summary.get("cohort"), "sleeve": summary.get("sleeve"), "asof": summary.get("asof"),
           "days": summary.get("days"), "horizon": HORIZON.get(summary.get("sleeve"), 20),
           "picks_avg": summary.get("picks_avg"), "near_miss_avg": summary.get("near_miss_avg")}
    if df.empty or "return" not in df:
        return {**out, "verdict": "no data", "explanation": "no returns yet"}
    df = df[df["status"].isin(["picked", "near miss"])].dropna(subset=["return"])
    picks, near = df[df["status"] == "picked"], df[df["status"] == "near miss"]
    if picks.empty or near.empty:
        return {**out, "verdict": "no data", "explanation": "picks or near misses missing"}
    gap = float(picks["return"].mean() - near["return"].mean())
    rets = df["return"].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    sims = np.array([rng.choice(rets, size=len(picks), replace=False).mean() for _ in range(draws)])
    chance = float((sims >= picks["return"].mean()).mean())     # share of random groups doing as well as the picks
    # which scores lined up with the return since the decision close (rank correlation, all rows)
    factors = {}
    for col in SCORE_COLS.get(out["sleeve"], ["score"]):
        if col in df and df[col].notna().sum() >= 10:
            x = pd.to_numeric(df[col], errors="coerce")
            factors[col] = round(float(x.rank().corr(df["return"].rank())), 3)
    # sectors: where the picks are over/underweight vs the near misses, and how those sectors did
    sec = []
    if "sector" in df:
        allr = df.groupby("sector")["return"].mean()
        pw = picks["sector"].value_counts(normalize=True)
        nw = near["sector"].value_counts(normalize=True)
        for name in allr.index:
            tilt = float(pw.get(name, 0) - nw.get(name, 0))
            rel = float(allr[name] - df["return"].mean())
            sec.append({"sector": name, "tilt": round(tilt, 3), "return": round(float(allr[name]), 5),
                        "vs_cohort": round(rel, 5), "effect": round(tilt * rel, 5)})
        sec.sort(key=lambda r: abs(r["effect"]), reverse=True)
    days, horizon = out["days"] or 0, out["horizon"]
    ahead = "ahead of" if gap >= 0 else "behind"
    if days < horizon:
        verdict = "too early"
        why = (f"day {days} of {horizon}: judge this cohort at its re-pick. A random group of the same size did at "
               f"least as well as the picks {chance:.0%} of the time, so today's gap is ordinary noise"
               if 0.05 < chance < 0.95 else
               f"day {days} of {horizon}: an unusually large gap for now ({chance:.0%} of random groups did as well "
               "as the picks), but early gaps often reverse - judge at the re-pick")
    elif gap < 0 and chance > 0.95:
        verdict = "worth a test"
        why = ("the near misses beat the picks by more than chance over a full cohort. Check whether it repeats "
               "across cohorts and in research/NEAR_MISSES.md before proposing an amendment")
    else:
        verdict = "within noise" if gap < 0 else "ranking held up"
        why = (f"picks {ahead} the near misses by {abs(gap):.1%} over the full cohort; {chance:.0%} of random "
               "groups did as well as the picks")
    best_f = max(factors.items(), key=lambda kv: abs(kv[1])) if factors else None
    expl = [f"picks {ahead} near misses by {abs(gap):.2%}"]
    if sec and abs(sec[0]["effect"]) > 0.0005:
        s0 = sec[0]
        expl.append(f"biggest sector effect: {s0['sector']} ({s0['tilt']:+.0%} more of the picks than of the near misses; "
                    f"the sector is {s0['vs_cohort']:+.2%} vs the cohort average), worth {s0['effect']:+.2%} of the gap")
    if best_f:
        expl.append(f"score most linked to returns so far: {best_f[0]} (rank corr {best_f[1]:+.2f})")
    return {**out, "gap": round(gap, 5), "chance": round(chance, 3), "factors": factors, "sectors": sec[:5],
            "verdict": verdict, "reason": why, "explanation": "; ".join(expl),
            "baseline": BASELINE.get(out["sleeve"], "")}


def log_checks(checks: list[dict]) -> None:
    """Append today's checks to journal/watchlist_daily.jsonl (one row per cohort per day)."""
    p = tradebook.DIR / "watchlist_daily.jsonl"
    seen = set()
    if p.exists():
        seen = {(r.get("cohort"), r.get("asof")) for r in map(json.loads, p.read_text().splitlines()) if r}
    with p.open("a") as f:
        for c in checks:
            if (c.get("cohort"), c.get("asof")) not in seen and c.get("verdict") != "no data":
                f.write(json.dumps({k: v for k, v in c.items() if k not in ("sectors",)}, default=str) + "\n")


def daily_history() -> list[dict]:
    p = tradebook.DIR / "watchlist_daily.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


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
    if "passes" in scan and sleeve in ("bottleneck", "momentum"):
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
            status, reason = "failed a gate", ("below its 200-day average" if sleeve == "momentum"
                                               else bottleneck_reason(r))
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
        out = {"asof_utc": _now(), "summary": [], "rows": [], "checks": []}
    else:
        if closes is None:
            symbols = sorted({r["symbol"] for c in cs for r in c["rows"]} | {"SPY"})
            start = (pd.Timestamp(min(c["ref_date"] for c in cs)) - pd.Timedelta(days=10)).date().isoformat()
            closes = _closes(symbols, start)
        latest = {}
        for c in cs:
            if c["sleeve"] not in latest or c["locked_on"] > latest[c["sleeve"]]["locked_on"]:
                latest[c["sleeve"]] = c
        rows, summary, checks = [], [], []
        for c in sorted(cs, key=lambda c: (c["sleeve"], c["locked_on"])):
            r, s = compare(c, closes)
            s["current"] = latest[c["sleeve"]]["id"] == c["id"]
            summary.append(s)
            if s["current"]:
                rows += r
                checks.append(diagnose(s, r))
        out = {"asof_utc": _now(), "summary": summary, "rows": rows, "checks": checks}
        if write:
            tradebook.DIR.mkdir(parents=True, exist_ok=True)
            log_checks(checks)
    if write:
        tradebook.DIR.mkdir(parents=True, exist_ok=True)
        (tradebook.DIR / "watchlist_review.json").write_text(json.dumps(out, indent=1, default=str))
    return out
