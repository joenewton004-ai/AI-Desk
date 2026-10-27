"""ICT day trading re-run on ten years of Alpaca 5-minute bars (the first test had 60 days of Yahoo bars).

    python research/ict_long.py      (needs: python research/alpaca_bars.py --5min <the universe> - see below)

The SAME rules as research/ict.py, unchanged (Silver Bullet on 5-minute bars; Judas swing on hourly bars, here built
from the 5-minute bars as 9:30, 10:30 ... 15:30 candles like Yahoo's), the same universe rule (the 100 largest US
companies at the latest quarter-end known at the time, filings public 45 days later), the same financial and trend
biases, costs (0.03% each way, stress 0.10%), portfolio (10% per trade, at most 10 a day) and coin-flip control.
New: 2016-2026 instead of the last 60 days / 3 years, and results by year and by half (2016-20 vs 2021-26).
Bars: Alpaca SIP, split-adjusted, regular session. A company Alpaca has no bars for (e.g. renamed or delisted under
another ticker) is skipped and counted. Writes research/output/ict_long.md; findings in research/ICT.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import alpaca_bars  # noqa: E402
import ict  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
START, END = "2016-01-04", alpaca_bars.END
SPLIT = pd.Timestamp("2021-01-01")


def universe(snaps, start: str = "2015-09-30", end: str = "2026-09-30") -> list[str]:
    names = set()
    for k, s in snaps.items():
        if pd.Timestamp(start) <= k <= pd.Timestamp(end):
            names |= set(s["market_cap"].nlargest(ict.N_UNIVERSE).index)
    return sorted(names)


def hourly(b5: pd.DataFrame) -> pd.DataFrame:
    """Pure: 5-minute bars -> hourly candles starting 9:30, 10:30, ..., 15:30 (the last one is half an hour)."""
    mins = b5.index.hour * 60 + b5.index.minute - (9 * 60 + 30)
    key = b5.index.normalize() + pd.to_timedelta(9 * 60 + 30 + (mins // 60) * 60, unit="min")
    g = b5.groupby(key)
    return pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                         "close": g["close"].last()})


def members_by_day(snaps, days: pd.DatetimeIndex) -> dict[pd.Timestamp, set]:
    keys = sorted(snaps)
    out = {}
    for d in days:
        known = [k for k in keys if k + pd.Timedelta(days=45) <= d]
        if known:
            q = known[-1]
            out[d] = (q, set(snaps[q]["market_cap"].nlargest(ict.N_UNIVERSE).index))
    return out


def symbol_trades(sym: str, b5: pd.DataFrame, member: dict, thirds, above) -> tuple[list, list]:
    """Silver Bullet and Judas trades for one symbol on the days it was in the top 100."""
    alp = sym.replace("-", ".")
    b5 = b5.loc[START:f"{END} 23:59"]
    if b5.empty:
        return [], []
    hb = hourly(b5)
    day5 = b5.index.normalize()
    dayh = hb.index.normalize()
    dh = b5["high"].groupby(day5).max()
    dl = b5["low"].groupby(day5).min()
    days = dh.index
    g5 = {d: x for d, x in b5.groupby(day5)}
    gh = {d: x for d, x in hb.groupby(dayh)}
    sb, jd = [], []
    for i in range(1, len(days)):
        d, p = days[i], days[i - 1]
        m = member.get(d)
        if not m or sym not in m[1]:
            continue
        pdh, pdl = float(dh.iat[i - 1]), float(dl.iat[i - 1])
        if not (np.isfinite(pdh) and np.isfinite(pdl)):
            continue
        ap = above.index[above.index < d]
        trend = bool(above.at[ap[-1], sym]) if sym in above.columns and len(ap) else None
        extra = {"date": d, "symbol": alp, "fin": int(thirds[m[0]].get(sym, 0)), "trend_up": trend}
        tr = ict.silver_bullet(g5[d][["open", "high", "low", "close"]], pdh, pdl)
        if tr:
            sb.append({**tr, **extra})
        tr = ict.judas(gh[d], pdh, pdl)
        if tr:
            jd.append({**tr, **extra})
    return sb, jd


def by_period(name: str, t: pd.DataFrame, emit) -> None:
    if t.empty:
        return
    net = t["ret"] - 2 * ict.COST
    yr = net.groupby(pd.to_datetime(t["date"]).dt.year).agg(["count", "mean"])
    a, b = net[pd.to_datetime(t["date"]) < SPLIT], net[pd.to_datetime(t["date"]) >= SPLIT]
    emit(f"\n{name} - per trade after costs: 2016-20 {a.mean():+.3%} ({len(a):,} trades), 2021-26 {b.mean():+.3%} "
         f"({len(b):,}). By year: " + ", ".join(f"{y} {r['mean']:+.3%}" for y, r in yr.iterrows()) + ".")


def main() -> None:
    lines: list[str] = []

    def emit(x=""):
        print(x, flush=True)
        lines.append(x)

    import pickle
    snaps = ict.snapshots()
    daily = pickle.loads((ict.CACHE / "daily_ohlcv.pkl").read_bytes())
    daily = {k: v.astype(float) for k, v in daily.items()}
    thirds, above = ict.bias_tables(snaps, daily["close"])
    from ai_desk.data import load_cash_rate
    rf = float(load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).loc[START:].mean()) / 252

    spy = alpaca_bars.bars("SPY", timeframe="5Min", extended=True)
    days = pd.DatetimeIndex(sorted(set(alpaca_bars.regular_session(spy).index.normalize())))
    days = days[(days >= pd.Timestamp(START)) & (days <= pd.Timestamp(END))]
    member = members_by_day(snaps, days)
    sb, jd, missing, used = [], [], [], 0
    syms = universe(snaps)
    for k, sym in enumerate(syms):
        path = ict.CACHE / f"alpaca_5m_{sym.replace('-', '.')}.pkl"
        if not path.exists():
            missing.append(sym)
            continue
        b5 = pd.read_pickle(path)
        if b5.empty:
            missing.append(sym)
            continue
        used += 1
        a, b = symbol_trades(sym, b5, member, thirds, above)
        sb += a
        jd += b
        if (k + 1) % 25 == 0:
            print(f"  {k + 1}/{len(syms)} symbols", flush=True)
    member_days = sum(len(m[1]) for m in member.values())
    have = {s for s in syms if s not in missing}
    covered = sum(len(m[1] & have) for m in member.values())

    emit("# ICT day trading on ten years of Alpaca bars - generated tables\n")
    emit(f"Same rules as research/ict.py. {days[0].date()} to {days[-1].date()}, {len(days):,} trading days. Universe: "
         f"the 100 largest US companies at the latest known quarter-end; {used} of {len(syms)} companies have Alpaca "
         f"bars, covering {covered / member_days:.0%} of member-days. Missing: {', '.join(missing) or 'none'}. "
         "Costs 0.03% each way (stress 0.10%). Portfolio: 10% per trade, at most 10 trades a day, T-bills otherwise.\n")
    t5, t1 = pd.DataFrame(sb), pd.DataFrame(jd)
    ict.report("Model 1: Silver Bullet, 5-minute bars", t5, days, emit, rf)
    by_period("Silver Bullet (pure)", t5, emit)
    ict.report("Model 2: Judas swing, hourly bars", t1, days, emit, rf)
    by_period("Judas swing (pure)", t1, emit)

    OUT.mkdir(exist_ok=True)
    (OUT / "ict_long.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'ict_long.md'}")


if __name__ == "__main__":
    main()
