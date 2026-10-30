"""Earnings-night skip and sector caps for the overnight sleeve, re-tested through the 2026-10-30 open.

    python research/overnight_safety2.py      (extends prices to 2026-10-30's open in data/backtest/daily_ohlcv_ext.pkl
                                               and re-reads each company's latest SEC filing list; ~10 minutes)

Asked after the 2026-10-29 -> 10-30 night (-$9.8k: an SMH -5% gap plus Intel/Twilio/Illumina/SanDisk earnings).
research/overnight_safety.py (data to 2026-10-20) found no filter worth its price; this re-run adds the latest nights,
the earnings releases since, tighter caps and a cash version of the skip. Variants, fixed before running:
  Live                       the live rule (12-month return, top 20, daily re-pick, SPY 200-day + picks-day checks)
  E swap                     skip a stock on a night it reports (SEC 8-K item 2.02 after 4pm / before 9:30am); the
                             next-ranked stock takes its place (overnight_safety.py's E)
  E cash                     the same, but the skipped slot stays in T-bills
  S4 / S3 / S2               at most 4 / 3 / 2 stocks from one industry (2-digit SIC)
  H6                         at most 6 of the 20 from computer hardware + electronics (SIC 35 and 36: chips, memory,
                             storage, servers - Intel, AMD, Dell, Marvell, Micron, Tower...), others at most 4
  E cash + S3                both
  60% / 50% share            the live picks with 60% / 50% of the money, the rest in T-bills
ADOPT a variant only if (fixed before running): its Sharpe beats Live's in BOTH 2014-2019 and 2020-2026, AND its
worst drop or worst month is smaller, at both 0.02% and 0.05% costs each way. The 50/60% versions are judged the
same way (they are the 'less money overnight' alternative, an amendment either way).
Earnings dates use the actual release time (live would need an earnings calendar - a small flattery). Survivors-only
prices. Writes research/output/overnight_safety2.md.
"""

from __future__ import annotations

import pickle
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import ict  # noqa: E402
import lookbacks as lb  # noqa: E402
import overnight as ov  # noqa: E402
import overnight_picks_check as opc  # noqa: E402
import overnight_regime as orr  # noqa: E402
import overnight_safety as osf  # noqa: E402
import swing  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals.yahoo import with_retry  # noqa: E402

CACHE, OUT = orr.CACHE, orr.OUT
EXT = CACHE / "daily_ohlcv_ext.pkl"
END = "2026-10-30"                  # the night ending at this open is the last one (only the open of this day is used)
HARDWARE = {35, 36}


def extended_prices() -> dict[str, pd.DataFrame]:
    """daily_ohlcv.pkl + Yahoo days after it, each symbol rescaled to the old series on the overlapping days (adjusted
    prices shift when a dividend is paid). The last day keeps only its open (its close isn't final)."""
    if EXT.exists():
        return pickle.loads(EXT.read_bytes())
    import yfinance as yf
    old = swing.fetch_daily([])
    syms = list(old["close"].columns)
    parts = {k: [] for k in old}
    for i in range(0, len(syms), 100):
        chunk = syms[i:i + 100]
        d = with_retry(lambda chunk=chunk: yf.download(chunk, start="2026-10-08", end="2026-10-31", interval="1d",
                                                       auto_adjust=True, progress=False, threads=4))
        for k in parts:
            parts[k].append(d[k.capitalize()])
        print(f"  new days {min(i + 100, len(syms))}/{len(syms)}", flush=True)
    new = {}
    for k, v in parts.items():
        df = pd.concat(v, axis=1, sort=True)
        df = df.loc[:, ~df.columns.duplicated()]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        new[k] = df.reindex(columns=syms)
    last = old["close"].index[-1]
    overlap = new["close"].index[(new["close"].index <= last)]
    scale = (old["close"].loc[overlap] / new["close"].loc[overlap]).median()
    out = {}
    for k in old:
        add = new[k].loc[new[k].index > last]
        if k != "volume":
            add = add * scale
        if k != "open":
            add.loc[add.index >= pd.Timestamp(END)] = np.nan     # today's bar: only the open is final
        out[k] = pd.concat([old[k], add.astype("float32")]).loc[:END]
    EXT.write_bytes(pickle.dumps(out))
    return out


def refresh_releases(ciks: list[int]) -> pd.DataFrame:
    """The cached 8-K item 2.02 times plus anything newer in each company's latest filing list."""
    have = osf.earnings_releases(ciks)

    def recent(cik: int):
        try:
            r = osf._get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
            b = r.json()["filings"]["recent"] if r.status_code == 200 else {}
        except Exception:  # noqa: BLE001
            return []
        return [(cik, acc) for form, items, acc in zip(b.get("form", []), b.get("items", []), b.get("acceptanceDateTime", []))
                if form in ("8-K", "8-K/A") and "2.02" in (items or "") and acc and acc[:10] >= "2026-10-01"]

    with ThreadPoolExecutor(4) as pool:
        rows = [x for part in pool.map(recent, sorted(set(ciks))) for x in part]
    new = pd.DataFrame(rows, columns=["cik", "accepted"])
    new["accepted"] = pd.to_datetime(new["accepted"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return pd.concat([have, new], ignore_index=True).drop_duplicates()


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    d = extended_prices()
    o, c, v = (d[k].astype(float) for k in ("open", "close", "volume"))
    c_ff = c.ffill(limit=1)                                    # so the last night has its previous close
    full = ict.snapshots()
    snaps = {k: list(s.index) for k, s in full.items()}
    dates, symbols = c.index, list(c.columns)
    member = pd.DataFrame(swing.membership(dict(sorted(snaps.items())), dates, symbols), index=dates, columns=symbols)
    eligible = member & (c_ff > 10) & ((c_ff * v).rolling(50, min_periods=40).mean() > 20e6)
    on, day = ov.split_returns(o, c_ff)
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).fillna(0)
    mkt = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(dates).ffill()
    spy_flag = (mkt < mkt.rolling(200).mean()).shift(1).fillna(False).astype(bool)
    ret12 = c_ff / c_ff.shift(252) - 1

    cik, sic = {}, {}
    for k in sorted(full):
        for sym, row in full[k].iterrows():
            if pd.notna(row.get("cik")):
                cik[sym] = int(row["cik"])
            if pd.notna(row.get("sic2")):
                sic[sym] = int(row["sic2"])
    used = [s for s in symbols if eligible[s].any() and s in cik]
    print(f"earnings releases for {len(used)} companies (cached + the latest filing lists)...", flush=True)
    rel = refresh_releases(sorted({cik[s] for s in used}))
    by_cik = {k: g["accepted"] for k, g in rel.groupby("cik")}
    report = pd.DataFrame(False, index=dates, columns=symbols)
    for s in used:
        acc = by_cik.get(cik[s])
        if acc is not None and len(acc):
            report.loc[report.index.isin(osf.earnings_nights(acc, dates)), s] = True

    group = pd.Series(sic).reindex(symbols).fillna(-1)
    hw_group = group.where(~group.isin(HARDWARE), 3536)        # SIC 35 and 36 counted as one group

    def held(elig=eligible, cap=None, grp=group) -> pd.DataFrame:
        if cap:
            return osf.daily_capped(ret12, elig, grp, 20, cap).shift(2, fill_value=False)
        return lb.daily_top(ret12, elig, 20).shift(2, fill_value=False)

    def hw_capped() -> pd.DataFrame:
        """At most 6 from SIC 35+36 and at most 4 from any other industry."""
        s = ret12.where(eligible).to_numpy(dtype=float)
        g, hw = group.to_numpy(), hw_group.to_numpy()
        out = np.zeros_like(s, dtype=bool)
        for i, row in enumerate(s):
            ok = np.flatnonzero(np.isfinite(row))
            if len(ok) < 20:
                continue
            cnt, hwn, taken = {}, 0, 0
            for j in ok[np.argsort(-row[ok], kind="stable")]:
                if hw[j] == 3536 and hwn >= 6:
                    continue
                if cnt.get(g[j], 0) >= 4:
                    continue
                out[i, j] = True
                cnt[g[j]] = cnt.get(g[j], 0) + 1
                hwn += hw[j] == 3536
                taken += 1
                if taken == 20:
                    break
        return pd.DataFrame(out, index=ret12.index, columns=ret12.columns).shift(2, fill_value=False)

    rep_night = report                                          # True on the day whose open ends a release night
    live = held()
    variants = {
        "Live": (live, None, 1.0),
        "E swap": (held(eligible & ~report.shift(-2, fill_value=False)), None, 1.0),
        "E cash": (live, rep_night, 1.0),
        "S4": (held(cap=4), None, 1.0),
        "S3": (held(cap=3), None, 1.0),
        "S2": (held(cap=2), None, 1.0),
        "H6": (hw_capped(), None, 1.0),
        "E cash + S3": (held(cap=3), rep_night, 1.0),
        "60% share": (live, None, 0.6),
        "50% share": (live, None, 0.5),
    }
    emit("# Earnings-night skip and sector caps, re-tested through 2026-10-30 - generated tables\n")
    emit(f"Daily, {ov.START} to the {END} open, **survivors-only prices**, the live rules and checks; Sharpe above T-bills. "
         f"Earnings releases: {len(rel):,} (SEC 8-K item 2.02), refreshed 2026-10-30.\n")
    emit("| version | costs | return/yr | volatility | Sharpe | worst drop | worst night | worst month | 2014-19 | 2020-26 | "
         "Oct 29 night | Oct 30 night |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|---|")
    res = {}
    for name, (h, skip, share) in variants.items():
        h = h.loc[ov.START:END]
        idx = h.index
        pday = day.shift(1).where(h).mean(axis=1).reindex(idx)
        flag = (spy_flag.reindex(idx).fillna(False) | opc.bad_day(pday, 0.10)).astype(bool)
        for cost in (0.0002, 0.0005):
            if skip is None:
                base = orr.nightly(on.reindex(idx), h, cost)
            else:                                               # skipped slots earn T-bills, the rest as usual
                keep = h & ~skip.reindex(idx).fillna(False)
                n = h.sum(axis=1).replace(0, np.nan)
                ret = (on.reindex(idx).where(keep).sum(axis=1) - keep.sum(axis=1) * 2 * cost) / n
                base = ret.fillna(0.0) + (h.sum(axis=1) - keep.sum(axis=1)) / n.fillna(1) * rf.reindex(idx).fillna(0)
            r = orr.switch(base, rf.reindex(idx).fillna(0), flag)
            r = share * r + (1 - share) * rf.reindex(idx).fillna(0)
            s, a, b = orr.stats(r, rf), orr.stats(r.loc[:ov.MID], rf), orr.stats(r.loc[ov.MID:], rf)
            m = (1 + r).resample("ME").prod() - 1
            res[(name, cost)] = (s, a, b, m.min())
            emit(f"| {name} | {cost:.2%} | {s['CAGR']:.1%} | {s['vol']:.1%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | "
                 f"{r.min():+.1%} | {m.min():+.1%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} | "
                 f"{r.get(pd.Timestamp('2026-10-29'), np.nan):+.1%} | {r.get(pd.Timestamp('2026-10-30'), np.nan):+.1%} |")

    emit("\n## Verdicts (adopt only if Sharpe beats Live in both halves AND worst drop or worst month is smaller, at both costs)\n")
    for name in variants:
        if name == "Live":
            continue
        ok = True
        for cost in (0.0002, 0.0005):
            s, a, b, wm = res[(name, cost)]
            s0, a0, b0, wm0 = res[("Live", cost)]
            ok &= a["Sharpe"] > a0["Sharpe"] and b["Sharpe"] > b0["Sharpe"] and (s["maxdd"] > s0["maxdd"] or wm > wm0)
        emit(f"- {name}: {'**adopt (passes)**' if ok else 'no'}")
    h0 = live.loc["2026-10-30"]
    picks = list(h0.index[h0.to_numpy()])
    emit(f"\nThe model's picks for the Oct 30 night: {', '.join(picks)}; reporting that night: "
         f"{', '.join(s for s in picks if report.loc['2026-10-30', s]) or 'none'}.")
    OUT.mkdir(exist_ok=True)
    (OUT / "overnight_safety2.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'overnight_safety2.md'}")


if __name__ == "__main__":
    main()
