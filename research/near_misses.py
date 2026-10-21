"""Picks vs near misses, historically: when the watchlist beats the picks, is the scoring wrong?

    python research/near_misses.py

The live watchlist (ai_desk/watchlist.py) follows the stocks each sleeve almost picked. A few days or
weeks of near misses beating the picks says little; this script asks the same question over 12
years, at every re-pick, so a change to the scoring would rest on hundreds of comparisons instead
of one.

  quality screen  point-in-time SEC snapshots each quarter (data/backtest/snapshots_m*.pkl). Picks =
                  the top 25 gate-passers by score; near misses = the other gate-passers (as live).
                  Return over the next quarter, monthly adjusted prices.
  momentum        the sleeve that takes over the 20% on 2026-11-03: top 20 of the 750 largest by
                  6-month return (skipping the latest week), above the 40-week average; near misses =
                  ranks 21-40. Return over the next 4 weeks, weekly prices.

Then, for the quality screen, which of its five categories (quality, growth, value, strength,
momentum) actually lined up with the next quarter's return among the gate-passers (rank
correlation), and whether re-weighting would have helped in BOTH halves of the history - a weight
that only helps in one half is noise fitted to that half.

Survivors-only prices flatter both groups about equally; the comparison is picks vs near misses,
so that matters less here than usual. Writes research/output/near_misses.md; findings in
research/NEAR_MISSES.md.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import weekly  # noqa: E402
from ai_desk.fundamentals.scoring import CATEGORIES, DEFAULT_WEIGHTS, score  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
MONTH_END = "2026-09-30"
SPLIT = "2020-01-01"


# --- pure pieces (unit-tested) --------------------------------------------------------

def gap_stats(gaps: pd.Series) -> dict:
    """gaps: picks minus near misses, one value per re-pick. t-stat treats re-picks as independent."""
    g = gaps.dropna()
    t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 1 and g.std() > 0 else np.nan
    return {"n": len(g), "mean": g.mean(), "picks_won": (g > 0).mean(), "t": t}


def rank_corr(a: pd.Series, b: pd.Series) -> float:
    d = pd.concat([a, b], axis=1).dropna()
    if len(d) < 5:
        return np.nan
    return float(d.iloc[:, 0].rank().corr(d.iloc[:, 1].rank()))


def forward_return(adj: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, names: list[str]) -> pd.Series:
    """Buy-and-hold return from the close of `start` to the close of `end`; missing data -> dropped."""
    cols = [n for n in names if n in adj.columns]
    a, b = adj.loc[:start, cols].iloc[-1], adj.loc[:end, cols].iloc[-1]
    r = b / a - 1
    return r.where(r.abs() < 3)


# --- the experiment ------------------------------------------------------------------

def quality_screen(emit) -> None:
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update(pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()))
    snaps = dict(sorted(snaps.items()))
    adj = pickle.loads((CACHE / "prices.pkl").read_bytes())["adj"].groupby(level=0).last().loc[:MONTH_END]
    dates = [d for d in snaps if d < pd.Timestamp(MONTH_END)]
    rows, ic, alt = [], [], []
    weight_sets = {
        "Current weights (quality 35, growth 25, value 20, strength 10, momentum 10)": DEFAULT_WEIGHTS,
        "Equal weights": {c: 0.2 for c in CATEGORIES},
        "More momentum (momentum 25, quality 30, growth 20, value 15, strength 10)":
            {"quality": 0.30, "growth": 0.20, "value": 0.15, "strength": 0.10, "momentum": 0.25},
        "More value (value 35, quality 30, growth 15, strength 10, momentum 10)":
            {"quality": 0.30, "growth": 0.15, "value": 0.35, "strength": 0.10, "momentum": 0.10},
        "Quality only": {"quality": 1.0, "growth": 0.0, "value": 0.0, "strength": 0.0, "momentum": 0.0},
    }
    for d, nxt in zip(dates, dates[1:] + [pd.Timestamp(MONTH_END)]):
        snap = snaps[d]
        ok = snap[snap["passes_gates"]].drop(columns="passes_gates")
        if len(ok) < 40:
            continue
        ranked = score(ok)
        fwd = forward_return(adj, d, nxt, list(ranked.index))
        ranked = ranked.assign(fwd=fwd.reindex(ranked.index)).dropna(subset=["fwd"])
        ranked["rank"] = np.arange(1, len(ranked) + 1)
        picks, near = ranked[ranked["rank"] <= 25], ranked[ranked["rank"] > 25]
        rows.append({"date": d, "picks": picks["fwd"].mean(), "near": near["fwd"].mean(),
                     "near_26_50": near[near["rank"] <= 50]["fwd"].mean(), "near_51_up": near[near["rank"] > 50]["fwd"].mean(),
                     "n_near": len(near)})
        ic.append({"date": d, **{c: rank_corr(ranked[f"{c}_score"], ranked["fwd"]) for c in CATEGORIES},
                   "total": rank_corr(ranked["score"], ranked["fwd"])})
        for name, w in weight_sets.items():
            r2 = score(ok, w)
            top = list(r2.index[:25])
            alt.append({"date": d, "set": name, "ret": fwd.reindex(top).mean()})
    q = pd.DataFrame(rows).set_index("date")
    ic = pd.DataFrame(ic).set_index("date")
    alt = pd.DataFrame(alt).pivot(index="date", columns="set", values="ret")

    emit("## 1. Quality screen: top 25 vs the other gate-passers, next quarter\n")
    emit(f"{len(q)} quarterly re-picks, {q.index[0]:%Y-%m} to {q.index[-1]:%Y-%m}; about {q['n_near'].mean():.0f} near misses each time.\n")
    emit("| | avg next-quarter return | picks beat them | gap per quarter (picks - them) | t-stat |\n|---|---|---|---|---|")
    for col, label in (("near", "All near misses"), ("near_26_50", "Near misses ranked 26-50"),
                       ("near_51_up", "Near misses ranked 51+")):
        s = gap_stats(q["picks"] - q[col])
        emit(f"| {label} | {q[col].mean():+.2%} | {s['picks_won']:.0%} of quarters | {s['mean']:+.2%} | {s['t']:.1f} |")
    emit(f"| (Picks: top 25) | {q['picks'].mean():+.2%} | | | |")
    for lo_, hi_, lbl in ((None, SPLIT, "2014-19"), (SPLIT, None, "2020-26")):
        part = q.loc[lo_:hi_]
        s = gap_stats(part["picks"] - part["near"])
        emit(f"\n{lbl}: picks {part['picks'].mean():+.2%} vs near misses {part['near'].mean():+.2%} a quarter; "
             f"picks won {s['picks_won']:.0%} of {s['n']} quarters (t = {s['t']:.1f}).")

    emit("\n## 2. Which parts of the score lined up with the next quarter's return (among gate-passers)\n")
    emit("Rank correlation each quarter, averaged. 0 = no link; +0.05 is a useful signal in stock picking; "
         "|t| above 2 is the usual bar for 'probably not luck'.\n")
    emit("| category | weight now | avg correlation | t-stat | 2014-19 | 2020-26 | positive quarters |\n|---|---|---|---|---|---|---|")
    for c in CATEGORIES + ["total"]:
        s = ic[c].dropna()
        t = s.mean() / (s.std() / np.sqrt(len(s)))
        w = f"{DEFAULT_WEIGHTS[c]:.0%}" if c in DEFAULT_WEIGHTS else "(overall score)"
        emit(f"| {c} | {w} | {s.mean():+.3f} | {t:.1f} | {s.loc[:SPLIT].mean():+.3f} | {s.loc[SPLIT:].mean():+.3f} | "
             f"{(s > 0).mean():.0%} |")

    emit("\n## 3. Would different weights have picked a better top 25?\n")
    emit("Average next-quarter return of the top 25 under each weighting (same gates, same dates).\n")
    emit("| weights | all quarters | 2014-19 | 2020-26 | beat current weights |\n|---|---|---|---|---|")
    cur = alt[list(weight_sets)[0]]
    for name in weight_sets:
        a = alt[name]
        beat = f"{(a > cur).mean():.0%} of quarters" if name != list(weight_sets)[0] else ""
        emit(f"| {name} | {a.mean():+.2%} | {a.loc[:SPLIT].mean():+.2%} | {a.loc[SPLIT:].mean():+.2%} | {beat} |")


def momentum(emit) -> None:
    px, snaps = weekly.load()
    f = weekly.build(px, snaps)
    dates = list(f["dates"])
    rows = []
    for i in range(0, len(dates) - 4, 4):
        d, nxt = dates[i], dates[i + 4]
        mem = [s for s in weekly.members_at(snaps, d) if s in px.columns and pd.notna(px.at[d, s])]
        ok = f["above"].loc[d, mem].fillna(False).astype(bool)
        mom = f["mom"].loc[d, mem][ok].dropna().sort_values(ascending=False)
        if len(mom) < 40:
            continue
        fwd = (px.loc[nxt, mom.index] / px.loc[d, mom.index] - 1).where(lambda r: r.abs() < 3)
        rows.append({"date": d, "picks": fwd.iloc[:20].mean(), "near": fwd.iloc[20:40].mean(),
                     "next": fwd.iloc[40:80].mean(), "ic": rank_corr(mom, fwd)})
    m = pd.DataFrame(rows).set_index("date")
    emit("\n## 4. Momentum sleeve (live from 2026-11-03): top 20 vs ranks 21-40, next 4 weeks\n")
    emit(f"{len(m)} re-picks every 4 weeks, {m.index[0]:%Y-%m} to {m.index[-1]:%Y-%m}.\n")
    emit("| | avg 4-week return | picks beat them | gap (picks - them) | t-stat |\n|---|---|---|---|---|")
    for col, label in (("near", "Near misses (ranks 21-40)"), ("next", "Ranks 41-80")):
        s = gap_stats(m["picks"] - m[col])
        emit(f"| {label} | {m[col].mean():+.2%} | {s['picks_won']:.0%} of re-picks | {s['mean']:+.2%} | {s['t']:.1f} |")
    emit(f"| (Picks: top 20) | {m['picks'].mean():+.2%} | | | |")
    s = m["ic"].dropna()
    emit(f"\nRank correlation of 6-month momentum with the next 4 weeks (above-average stocks only): {s.mean():+.3f} "
         f"(t = {s.mean() / (s.std() / np.sqrt(len(s))):.1f}).")
    for lo_, hi_, lbl in ((None, SPLIT, "2014-19"), (SPLIT, None, "2020-26")):
        part = m.loc[lo_:hi_]
        g = gap_stats(part["picks"] - part["near"])
        emit(f"{lbl}: picks {part['picks'].mean():+.2%} vs near misses {part['near'].mean():+.2%} per 4 weeks; "
             f"picks won {g['picks_won']:.0%} (t = {g['t']:.1f}).")


def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    emit("# Picks vs near misses, 2014-2026 - generated tables\n")
    emit("Survivors-only prices (both groups). Returns are simple averages over the holding period, before costs.\n")
    quality_screen(emit)
    momentum(emit)
    OUT.mkdir(exist_ok=True)
    (OUT / "near_misses.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'near_misses.md'}")


if __name__ == "__main__":
    main()
