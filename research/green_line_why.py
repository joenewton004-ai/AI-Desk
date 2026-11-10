"""Why did the 200-day line help NVIDIA and Apple but not Tesla, Amazon or Microsoft? (follow-up to GREEN_LINE_TECH.md)

    python research/green_line_why.py

Three parts, all for the seven stocks of research/green_line_tech.py:
  A. Price behaviour - what the line avoided (the stock's return on days the line said 'out'), how often it was a
     false alarm (back in at a higher price than it left), how deep and how SLOW each big fall was (a line needs a
     fall that lasts months, not a crash that recovers in weeks), trend persistence (variance ratio of monthly
     returns: above 1 = moves tend to continue).
  B. Financials from SEC filings (XBRL, so fiscal years ~2009 on): revenue growth and how much it swings, years of
     falling revenue, margins.
  C. The line's biggest saves and its worst whipsaws per stock, with dates - to match against the business story.
Prices: Yahoo with dividends to the 2026-11-09 close (same as green_line_tech.py). Hindsight: these are today's
winners. Seven stocks is a small sample - patterns here are explanations, not rules. Writes
research/output/green_line_why.md; write-up in research/GREEN_LINE_WHY.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from ai_desk.data import load_yahoo  # noqa: E402
from ai_desk.fundamentals import edgar  # noqa: E402
from ai_desk.fundamentals.yahoo import with_retry  # noqa: E402
import green_line as gl  # noqa: E402
import green_line_tech as glt  # noqa: E402

# verified via data.sec.gov/submissions 2026-11-10 (Alphabet: newest registration first, then Google Inc.)
CIKS = {"AAPL": [320193], "MSFT": [789019], "NVDA": [1045810], "AMZN": [1018724], "GOOGL": [1652044, 1288776],
        "META": [1326801], "TSLA": [1318605]}


# --- pure pieces (unit-tested) --------------------------------------------------------

def spells(sig: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Each run of 'out' (False) after the first 'in': (the close the line said out, the close it said back in).
    A spell still open at the end runs to the last date."""
    s = sig.astype(bool)
    out, start, seen_in = [], None, False
    for t, v in s.items():
        if v:
            if start is not None:
                out.append((start, t))
                start = None
            seen_in = True
        elif seen_in and start is None:
            start = t
    if start is not None:
        out.append((start, s.index[-1]))
    return out


def drawdowns(close: pd.Series, depth: float = 0.30) -> list[dict]:
    """Falls of at least `depth` from a high: peak date, trough date, depth, days down, days back to the old high."""
    peak_val, peak_t, trough_val, trough_t, res = close.iloc[0], close.index[0], close.iloc[0], close.index[0], []
    for t, v in close.items():
        if v >= peak_val:
            if trough_val / peak_val - 1 <= -depth:
                res.append({"peak": peak_t, "trough": trough_t, "depth": trough_val / peak_val - 1,
                            "days_down": close.index.get_loc(trough_t) - close.index.get_loc(peak_t),
                            "days_back": close.index.get_loc(t) - close.index.get_loc(trough_t)})
            peak_val, peak_t, trough_val, trough_t = v, t, v, t
        elif v < trough_val:
            trough_val, trough_t = v, t
    if trough_val / peak_val - 1 <= -depth:
        res.append({"peak": peak_t, "trough": trough_t, "depth": trough_val / peak_val - 1,
                    "days_down": close.index.get_loc(trough_t) - close.index.get_loc(peak_t), "days_back": None})
    return res


def variance_ratio(close: pd.Series, k: int = 12) -> float:
    """Var of k-month log returns / (k x var of 1-month): about 1 for a random walk, above 1 when moves persist."""
    m = np.log(close.resample("ME").last()).diff().dropna()
    mk = np.log(close.resample("ME").last()).diff(k).dropna()
    return float(mk.var() / (k * m.var()))


# --- the study --------------------------------------------------------------------------

def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    emit("# Why the 200-day line helped NVIDIA and Apple - generated tables\n")
    emit("Prices with dividends to the 2026-11-09 close; the line = close above its 200-day simple average, switch at "
         "the next open, 0.05% a switch. Financials from SEC XBRL filings. **Hindsight: these are today's winners.**\n")
    rows, saves, fin = [], {}, {}
    for sym in glt.MAG7:
        d = with_retry(lambda sym=sym: load_yahoo(sym, "1995-01-01", glt.END))
        c = d["close"].astype(float)
        sig = gl.above(c, c.rolling(200).mean())
        first = c.index[260]
        c, sig = c.loc[first:], sig.loc[first:]
        daily = c.pct_change()
        pos = sig.astype(bool).shift(1, fill_value=False).astype(bool)                     # held on day t if the line said 'in' at t-1's close
        # compounded, annualized: what a dollar did on the days the line held / sat out (big falls compound)
        out_ret = (1 + daily[~pos].dropna()).prod() ** (252 / max(1, (~pos).sum())) - 1
        in_ret = (1 + daily[pos].dropna()).prod() ** (252 / max(1, pos.sum())) - 1
        sp = spells(sig)
        moves = [(a, b, c.loc[b] / c.loc[a] - 1) for a, b in sp]
        false_alarm = np.mean([m > 0 for _, _, m in moves]) if moves else np.nan
        dds = drawdowns(c)
        caught = []
        for dd in dds:                                         # share of each big fall the line sat out
            seg = daily.loc[dd["peak"]:dd["trough"]].iloc[1:]
            held = pos.reindex(seg.index)
            fall_all = (1 + seg).prod() - 1
            fall_line = (1 + seg.where(held, 0)).prod() - 1
            caught.append(1 - fall_line / fall_all if fall_all < 0 else np.nan)
        rows.append({"sym": sym, "from": first.year, "vol": daily.std() * np.sqrt(252), "in": in_ret, "out": out_ret,
                     "spells_yr": len(sp) / (len(c) / 252), "false": false_alarm,
                     "big_falls": len(dds), "days_down": np.mean([x["days_down"] for x in dds]) if dds else np.nan,
                     "avoided": np.nanmean(caught) if caught else np.nan, "vr": variance_ratio(c)})
        saves[sym] = (sorted(moves, key=lambda x: x[2])[:3], sorted(moves, key=lambda x: -x[2])[:3], dds)
        try:
            fin[sym] = edgar.annual_history(CIKS[sym], years=20)
        except Exception as e:  # noqa: BLE001
            print(f"  {sym}: SEC data failed ({e})")
            fin[sym] = pd.DataFrame()

    emit("## A. How each stock moves, and what the line did\n")
    emit("| stock | from | volatility | return/yr while in | return/yr on 'out' days | out-spells a year | "
         "false alarms (back in higher) | falls of 30%+ | avg days peak->trough | share of those falls avoided | "
         "trend persistence (VR12) |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        emit(f"| {r['sym']} | {r['from']} | {r['vol']:.0%} | {r['in']:+.0%} | {r['out']:+.0%} | {r['spells_yr']:.1f} | "
             f"{r['false']:.0%} | {r['big_falls']} | {r['days_down']:.0f} | {r['avoided']:.0%} | {r['vr']:.2f} |")

    emit("\n## B. The business (SEC filings, fiscal years ~2009 on)\n")
    emit("| stock | years | revenue first -> last ($bn) | revenue growth/yr | growth swings (sd) | years revenue fell | "
         "gross margin avg (min-max) | operating margin avg (min-max) | FCF margin avg |")
    emit("|---|---|---|---|---|---|---|---|---|")
    for sym in glt.MAG7:
        f = fin[sym]
        if f.empty:
            emit(f"| {sym} | no data | | | | | | | |")
            continue
        g = f["revenue_growth"].dropna()
        n = len(f) - 1
        cagr = (f["revenue_$bn"].iloc[-1] / f["revenue_$bn"].iloc[0]) ** (1 / n) - 1 if n > 0 else np.nan
        gm, om = f["gross_margin"].dropna(), f["operating_margin"].dropna()
        emit(f"| {sym} | {f.index[0]}-{f.index[-1]} | {f['revenue_$bn'].iloc[0]:.1f} -> {f['revenue_$bn'].iloc[-1]:.1f} | "
             f"{cagr:.0%} | {g.std():.0%} | {int((g < 0).sum())} ({', '.join(i for i in g.index[g < 0]) or '-'}) | "
             + (f"{gm.mean():.0%} ({gm.min():.0%}-{gm.max():.0%})" if len(gm) else "-") + " | "
             + (f"{om.mean():.0%} ({om.min():.0%}-{om.max():.0%})" if len(om) else "-") + " | "
             + (f"{f['fcf_margin'].mean():.0%}" if f['fcf_margin'].notna().any() else "-") + " |")

    emit("\n## C. The line's best saves and worst whipsaws (price change while out)\n")
    for sym in glt.MAG7:
        best, worst, dds = saves[sym]
        emit(f"**{sym}** - saves: " + "; ".join(f"{a.date()} -> {b.date()} {m:+.0%}" for a, b, m in best)
             + ". Whipsaws: " + "; ".join(f"{a.date()} -> {b.date()} {m:+.0%}" for a, b, m in worst)
             + ". Falls of 30%+: " + "; ".join(f"{x['peak'].date()} -> {x['trough'].date()} {x['depth']:.0%} "
                                              f"({x['days_down']} days down)" for x in dds) + ".\n")
    gl.OUT.mkdir(exist_ok=True)
    (gl.OUT / "green_line_why.md").write_text("\n".join(lines) + "\n")
    for sym in glt.MAG7:                                       # full yearly financials for the write-up
        if not fin[sym].empty:
            fin[sym].round(3).to_csv(gl.OUT / f"green_line_why_{sym}.csv")
    print(f"\nwrote {gl.OUT / 'green_line_why.md'}")


if __name__ == "__main__":
    main()
