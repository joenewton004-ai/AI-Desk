"""Can the overnight picks be made safer? Earnings nights, volatile stocks, sector crowding, more names.

    python research/overnight_safety.py      (first run reads ~800 companies' SEC filing lists, ~5 minutes)

The live sleeve (12-month ranking, daily re-pick ranked the evening before, SPY 200-day and picks-day checks) holds 20
stocks a night. A stock's worst nights are mostly earnings releases: companies report after the close or before the
open, exactly inside the sleeve's holding period. Variants, fixed before running:
  E   skip a stock on a night it reports: an SEC 8-K with item 2.02 ("results of operations") accepted after 4pm New
      York (that night) or before 9:30am (the night before that open); the next-ranked stock takes its place
  V   skip the most volatile fifth of the eligible stocks (60-day daily volatility, known at the ranking close)
  S   at most 4 stocks from one industry group (2-digit SIC code)
  N30 30 stocks instead of 20
  ESV E + S + V together
Live, E would need an earnings calendar (dates are announced weeks ahead); the backtest uses the actual release time,
so a rare surprise release counts as known - a small flattery. Costs 0.02% each way (and 0.05%); survivors-only prices.
Writes research/output/overnight_safety.md.
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
import swing  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402

OUT, CACHE = orr.OUT, orr.CACHE
EARNINGS = CACHE / "earnings_8k.pkl"


# --- earnings releases from SEC filing lists ---------------------------------------------

def _releases(cik: int) -> list[tuple[int, str]]:
    from ai_desk.fundamentals import edgar
    base = "https://data.sec.gov/submissions/"
    r = edgar._get(f"{base}CIK{cik:010d}.json")
    if r.status_code != 200:
        return []
    j = r.json()
    blocks = [j["filings"]["recent"]]
    for f in j["filings"].get("files", []):
        if f.get("filingTo", "") >= "2013-06-01":
            rr = edgar._get(base + f["name"])
            if rr.status_code == 200:
                blocks.append(rr.json())
    out = []
    for b in blocks:
        for form, items, acc in zip(b.get("form", []), b.get("items", []), b.get("acceptanceDateTime", [])):
            if form in ("8-K", "8-K/A") and "2.02" in (items or "") and acc:
                out.append((cik, acc))
    return out


def earnings_releases(ciks: list[int]) -> pd.DataFrame:
    """Every 8-K item 2.02 acceptance time (New York) per CIK; cached."""
    have = pd.read_pickle(EARNINGS) if EARNINGS.exists() else pd.DataFrame(columns=["cik", "accepted"])
    todo = sorted(set(ciks) - set(have["cik"].astype(int)) - set(have.attrs.get("empty", [])))
    if todo:
        with ThreadPoolExecutor(4) as pool:
            rows = [x for part in pool.map(_releases, todo) for x in part]
        new = pd.DataFrame(rows, columns=["cik", "accepted"])
        new["accepted"] = pd.to_datetime(new["accepted"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
        empty = sorted(set(todo) - set(new["cik"]))
        have = pd.concat([have, new], ignore_index=True)
        have.attrs["empty"] = sorted(set(have.attrs.get("empty", [])) | set(empty))
        have.to_pickle(EARNINGS)
    return have


def earnings_nights(accepted: pd.Series, dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Pure: the trading day whose OPEN ends the night containing each release - after 4pm -> the next trading day;
    before 9:30am -> that day (or the next trading day on a weekend/holiday); during the session -> none."""
    out = []
    for ts in pd.to_datetime(accepted):
        mins = ts.hour * 60 + ts.minute
        day = ts.normalize()
        if mins >= 16 * 60:
            k = dates.searchsorted(day, side="right")
        elif mins < 9 * 60 + 30:
            k = dates.searchsorted(day, side="left")
        else:
            if day in dates:
                continue                                         # released while the market was open
            k = dates.searchsorted(day, side="left")             # e.g. a weekend filing: before the next open
        if k < len(dates):
            out.append(dates[k])
    return pd.DatetimeIndex(out)


def daily_capped(score: pd.DataFrame, eligible: pd.DataFrame, group: pd.Series, n: int, cap: int) -> pd.DataFrame:
    """Pure: like lookbacks.daily_top (the n best eligible each row) but at most `cap` from one group."""
    s = score.where(eligible).to_numpy(dtype=float)
    g = group.reindex(score.columns).to_numpy()
    out = np.zeros_like(s, dtype=bool)
    for i, row in enumerate(s):
        ok = np.flatnonzero(np.isfinite(row))
        if len(ok) < n:
            continue
        count: dict = {}
        taken = 0
        for j in ok[np.argsort(-row[ok], kind="stable")]:
            if count.get(g[j], 0) < cap:
                out[i, j] = True
                count[g[j]] = count.get(g[j], 0) + 1
                taken += 1
                if taken == n:
                    break
    return pd.DataFrame(out, index=score.index, columns=score.columns)


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    d = swing.fetch_daily([])
    o, c, v = (d[k].astype(float).loc[:ov.END] for k in ("open", "close", "volume"))
    full = ict.snapshots()
    snaps = {k: list(s.index) for k, s in full.items()}
    dates, symbols = c.index, list(c.columns)
    member = pd.DataFrame(swing.membership(dict(sorted(snaps.items())), dates, symbols), index=dates, columns=symbols)
    eligible = member & (c > 10) & ((c * v).rolling(50, min_periods=40).mean() > 20e6)
    on, day = ov.split_returns(o, c)
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).fillna(0)
    mkt = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(dates).ffill()
    spy_flag = (mkt < mkt.rolling(200).mean()).shift(1).fillna(False).astype(bool)
    ret12 = c / c.shift(252) - 1

    # point-in-time symbol -> CIK and industry (latest snapshot that lists it)
    cik, sic = {}, {}
    for k in sorted(full):
        s = full[k]
        for sym, row in s.iterrows():
            if pd.notna(row.get("cik")):
                cik[sym] = int(row["cik"])
            if pd.notna(row.get("sic2")):
                sic[sym] = int(row["sic2"])
    used = [s for s in symbols if eligible[s].any() and s in cik]
    print(f"earnings releases for {len(used)} companies...", flush=True)
    rel = earnings_releases(sorted({cik[s] for s in used}))
    by_cik = {k: g["accepted"] for k, g in rel.groupby("cik")}
    report = pd.DataFrame(False, index=dates, columns=symbols)       # True = this night (ending at the open) has a release
    for s in used:
        acc = by_cik.get(cik[s])
        if acc is not None and len(acc):
            nights = earnings_nights(acc, dates)
            report.loc[report.index.isin(nights), s] = True
    covered = sum(1 for s in used if cik[s] in by_cik)

    vol60 = c.pct_change().rolling(60, min_periods=40).std()
    calm = vol60.le(vol60.where(eligible).quantile(0.80, axis=1), axis=0)     # not in the most volatile fifth
    group = pd.Series(sic).reindex(symbols).fillna(-1)

    def held(n: int = 20, elig: pd.DataFrame = eligible, cap: int | None = None) -> pd.DataFrame:
        if cap:
            return daily_capped(ret12, elig, group, n, cap).shift(2, fill_value=False)
        return lb.daily_top(ret12, elig, n).shift(2, fill_value=False)

    def skip_earnings(n: int, elig: pd.DataFrame, cap: int | None) -> pd.DataFrame:
        # the ranking is made two closes before the night; a stock reporting that night is replaced by the next one
        elig_night = elig & ~report.shift(-2, fill_value=False)      # night ending at t+2 = bought at t+1's close
        return held(n, elig_night, cap)

    variants = {
        "Live (top 20)": held(),
        "E: skip earnings nights": skip_earnings(20, eligible, None),
        "V: skip the most volatile fifth": held(20, eligible & calm),
        "S: at most 4 per industry": held(20, eligible, 4),
        "N30: 30 stocks": held(30),
        "ESV: E + S + V": skip_earnings(20, eligible & calm, 4),
    }
    emit("# Safer overnight picks? - generated tables\n")
    emit(f"Daily, {ov.START} to {ov.END}, **survivors-only prices**, the live rules and checks. Earnings releases: SEC 8-K "
         f"item 2.02 acceptance times for {covered} of {len(used)} companies ({len(rel):,} releases). Sharpe above T-bills.\n")
    emit("| version | costs | return/yr | volatility | Sharpe | worst drop | worst night | 1-in-100 night | worst month | "
         "2014-19 | 2020-26 | picks with earnings that night |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|---|")
    keep = {}
    for name, h in variants.items():
        h = h.loc[ov.START:ov.END]
        idx = h.index
        pday = day.shift(1).where(h).mean(axis=1).reindex(idx)
        flag = (spy_flag.reindex(idx).fillna(False) | opc.bad_day(pday, 0.10)).astype(bool)
        earn_share = (h & report.reindex(idx).fillna(False)).sum(axis=1).sum() / max(1, h.sum(axis=1).sum())
        for cost in (0.0002, 0.0005):
            base = orr.nightly(on.reindex(idx), h, cost)
            r = orr.switch(base, rf.reindex(idx).fillna(0), flag)
            s, a, b = orr.stats(r, rf), orr.stats(r.loc[:ov.MID], rf), orr.stats(r.loc[ov.MID:], rf)
            m = (1 + r).resample("ME").prod() - 1
            inv = r[~flag & h.any(axis=1)]
            emit(f"| {name} | {cost:.2%} | {s['CAGR']:.1%} | {s['vol']:.1%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | "
                 f"{r.min():+.1%} | {np.percentile(inv, 1):+.2%} | {m.min():+.1%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} | "
                 f"{earn_share:.1%} |")
            if cost == 0.0002:
                keep[name] = (r, h)

    r0, h0 = keep["Live (top 20)"]
    worst = r0.nsmallest(20).index
    with_rel = [t for t in worst if (h0.loc[t] & report.loc[t]).any()]
    emit(f"\nThe live version's 20 worst nights: {len(with_rel)} had a pick reporting earnings that night. The worst five: "
         + "; ".join(f"{t.date()} {r0[t]:+.1%} (earnings: {', '.join(report.columns[(h0.loc[t] & report.loc[t]).to_numpy()]) or 'none'})"
                     for t in r0.nsmallest(5).index) + ".")
    pick_nights = on.reindex(h0.index).where(h0)
    er = pick_nights.where(report.reindex(h0.index).fillna(False))
    ne = pick_nights.where(~report.reindex(h0.index).fillna(False))
    emit(f"A pick's night with earnings: average {er.stack().mean():+.3%}, volatility {er.stack().std():.2%}, worst "
         f"{er.stack().min():+.1%}; without: {ne.stack().mean():+.3%}, {ne.stack().std():.2%}, {ne.stack().min():+.1%}.")

    OUT.mkdir(exist_ok=True)
    (OUT / "overnight_safety.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'overnight_safety.md'}")


if __name__ == "__main__":
    main()
