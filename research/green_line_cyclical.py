"""Does the 200-day line repeatably help CYCLICAL stocks and ETFs more than steady ones? (follow-up to GREEN_LINE_WHY.md)

    python research/green_line_cyclical.py

GREEN_LINE_WHY.md explained after the fact why the line helped NVIDIA and Apple: cyclical businesses whose bad patches
last. This tests that story on NEW names (the Mag 7 are left out), grouped by sector BEFORE looking at results:
  cyclical ETFs   SMH XLE XLB XLI XLY XLF XHB IYT XME KRE
  defensive ETFs  XLP XLU XLV
  cyclical stocks chips/hardware (INTC AMD MU AMAT LRCX KLAC TXN ADI CSCO HPQ WDC STX), machinery/industrial (CAT DE
                  CMI PCAR GE BA), autos (F), metals (FCX NUE), energy (XOM CVX SLB HAL COP), homebuilders (LEN DHI PHM)
  steady stocks   PG KO PEP JNJ WMT MCD CL KMB MO GIS HSY SO DUK ED AEP CLX COST ABT SYY ADP PAYX
Same rule and costs as research/green_line.py: close above the 200-day simple average -> hold, else T-bills; switch at
the next open; 0.05% a switch; Sharpe above T-bills; prices with dividends from 1995 (or listing) to the 2026-11-09
close; each name split into two halves at its own midpoint. Second check: for the stocks, revenue swings from SEC
filings (sd of yearly revenue growth, fiscal ~2009 on) vs how much the line changed the Sharpe.
REPEATABLE (fixed before running) only if ALL of:
  1. cyclical stocks: the line raises the Sharpe for a majority, and the median Sharpe change > 0, in BOTH halves
  2. cyclical ETFs: median Sharpe change > 0 in both halves
  3. cyclical stocks' median change beats steady stocks' in both halves
  4. revenue swings vs Sharpe change: rank correlation > 0 with p < 0.05
Survivors only (all still trade today; failed cyclicals like Lehman or Bethlehem Steel are missing - that flatters
buy and hold, and the line, unevenly). Writes research/output/green_line_cyclical.md; findings in
research/GREEN_LINE_CYCLICAL.md.
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
from ai_desk.fundamentals.yahoo import with_retry  # noqa: E402
import green_line as gl  # noqa: E402

END = "2026-11-10"                           # exclusive: last bar 2026-11-09
GROUPS = {
    "cyclical ETFs": ["SMH", "XLE", "XLB", "XLI", "XLY", "XLF", "XHB", "IYT", "XME", "KRE"],
    "defensive ETFs": ["XLP", "XLU", "XLV"],
    "cyclical stocks": ["INTC", "AMD", "MU", "AMAT", "LRCX", "KLAC", "TXN", "ADI", "CSCO", "HPQ", "WDC", "STX",
                        "CAT", "DE", "CMI", "PCAR", "GE", "BA", "F", "FCX", "NUE", "XOM", "CVX", "SLB", "HAL", "COP",
                        "LEN", "DHI", "PHM"],
    "steady stocks": ["PG", "KO", "PEP", "JNJ", "WMT", "MCD", "CL", "KMB", "MO", "GIS", "HSY", "SO", "DUK", "ED",
                      "AEP", "CLX", "COST", "ABT", "SYY", "ADP", "PAYX"],
}


def one(o: pd.Series, c: pd.Series, rf: pd.Series) -> dict:
    """Pure: buy and hold vs the 200-day SMA line on one price series - whole period and each half."""
    first = c.index[260]
    sig = gl.above(c, c.rolling(200).mean())
    hold = c.pct_change().loc[first:].dropna()
    line = gl.book(o, c, rf, sig).loc[first:].dropna()
    mid = hold.index[len(hold) // 2]
    out = {"from": first.year}
    for tag, sl in (("all", slice(None)), ("h1", slice(None, mid)), ("h2", slice(mid, None))):
        h, ln = gl.stats(hold.loc[sl], rf), gl.stats(line.loc[sl], rf)
        out[f"d_sharpe_{tag}"] = ln["Sharpe"] - h["Sharpe"]
        if tag == "all":
            out.update({"hold_cagr": h["CAGR"], "line_cagr": ln["CAGR"], "hold_sharpe": h["Sharpe"],
                        "line_sharpe": ln["Sharpe"], "hold_dd": h["maxdd"], "line_dd": ln["maxdd"]})
    return out


def revenue_swing(sym: str, table: dict) -> float:
    """sd of yearly revenue growth from SEC filings (fiscal ~2009 on); NaN if the CIK can't be verified."""
    from ai_desk.fundamentals import edgar
    cik = table.get(sym.replace(".", "-"))
    if not cik or sym not in [t.upper() for t in edgar.company_header(cik)["tickers"]]:   # verified on data.sec.gov
        return np.nan
    f = edgar.annual_history([cik], years=20)
    g = f["revenue_growth"].dropna() if not f.empty else pd.Series(dtype=float)
    return float(g.std()) if len(g) >= 8 else np.nan


def main() -> None:
    from scipy.stats import spearmanr

    from ai_desk.fundamentals import edgar

    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    irx = with_retry(lambda: load_yahoo("^IRX", "1990-01-01", END))["close"] / 100
    r = edgar._get("https://www.sec.gov/files/company_tickers.json")
    table = {v["ticker"].upper(): int(v["cik_str"]) for v in r.json().values()} if r.ok else {}
    rows = []
    for group, syms in GROUPS.items():
        for sym in syms:
            try:
                d = with_retry(lambda sym=sym: load_yahoo(sym, "1995-01-01", END))
            except Exception as e:  # noqa: BLE001
                print(f"  {sym}: no prices ({e})")
                continue
            o, c = d["open"].astype(float), d["close"].astype(float)
            rf = irx.reindex(c.index).ffill().bfill() / 252
            res = one(o, c, rf)
            res.update({"group": group, "sym": sym,
                        "rev_sd": revenue_swing(sym, table) if group.endswith("stocks") else np.nan})
            rows.append(res)
            print(f"  {sym}: {res['d_sharpe_all']:+.2f}", flush=True)
    df = pd.DataFrame(rows)

    emit("# The 200-day line on cyclical vs steady names - generated tables\n")
    emit("200-day SMA line vs buy and hold, prices with dividends to the 2026-11-09 close, 0.05% a switch, T-bills on "
         "cash, Sharpe above T-bills. Each name split into halves at its own midpoint. **Survivors only.**\n")
    emit("## By group\n")
    emit("| group | names | line raises Sharpe (all / 1st half / 2nd half) | median Sharpe change (all / 1st / 2nd) | "
         "median return/yr hold -> line | median worst drop hold -> line |")
    emit("|---|---|---|---|---|---|")
    med = {}
    for g, x in df.groupby("group", sort=False):
        share = [(x[f"d_sharpe_{t}"] > 0).mean() for t in ("all", "h1", "h2")]
        m = [x[f"d_sharpe_{t}"].median() for t in ("all", "h1", "h2")]
        med[g] = (share, m)
        emit(f"| {g} | {len(x)} | {share[0]:.0%} / {share[1]:.0%} / {share[2]:.0%} | "
             f"{m[0]:+.2f} / {m[1]:+.2f} / {m[2]:+.2f} | {x['hold_cagr'].median():.1%} -> {x['line_cagr'].median():.1%} | "
             f"{x['hold_dd'].median():.0%} -> {x['line_dd'].median():.0%} |")

    emit("\n## Every name\n")
    emit("| group | name | from | hold return/yr | line return/yr | hold Sharpe | line Sharpe | change (1st / 2nd half) | "
         "worst drop hold -> line | revenue growth swings (sd) |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    for _, x in df.sort_values(["group", "d_sharpe_all"], ascending=[True, False]).iterrows():
        emit(f"| {x['group']} | {x['sym']} | {x['from']} | {x['hold_cagr']:.1%} | {x['line_cagr']:.1%} | "
             f"{x['hold_sharpe']:.2f} | {x['line_sharpe']:.2f} | {x['d_sharpe_all']:+.2f} ({x['d_sharpe_h1']:+.2f} / "
             f"{x['d_sharpe_h2']:+.2f}) | {x['hold_dd']:.0%} -> {x['line_dd']:.0%} | "
             + ("-" if pd.isna(x["rev_sd"]) else f"{x['rev_sd']:.0%}") + " |")

    st = df[df["group"].str.endswith("stocks")].dropna(subset=["rev_sd"])
    rho, p = spearmanr(st["rev_sd"], st["d_sharpe_all"]) if len(st) > 5 else (np.nan, np.nan)
    emit(f"\n## Revenue swings vs the line's effect (stocks with SEC data: {len(st)})\n")
    emit(f"Rank correlation between revenue-growth swings and the Sharpe change: {rho:+.2f} (p = {p:.3f}).")
    for g in ("cyclical stocks", "steady stocks"):
        x = st[st["group"] == g]
        emit(f"- {g}: median revenue swing {x['rev_sd'].median():.0%}")

    cs, ce, ss = med["cyclical stocks"], med["cyclical ETFs"], med["steady stocks"]
    tests = {
        "1. cyclical stocks: majority raised AND median > 0, both halves":
            all(cs[0][i] > 0.5 and cs[1][i] > 0 for i in (1, 2)),
        "2. cyclical ETFs: median > 0, both halves": all(ce[1][i] > 0 for i in (1, 2)),
        "3. cyclical stocks beat steady stocks, both halves": all(cs[1][i] > ss[1][i] for i in (1, 2)),
        "4. revenue swings vs Sharpe change: rho > 0, p < 0.05": bool(rho > 0 and p < 0.05),
    }
    emit("\n## Verdict (all four must pass)\n")
    for k, v in tests.items():
        emit(f"- {k}: {'**pass**' if v else 'fail'}")
    emit(f"\n**Repeatable: {'yes' if all(tests.values()) else 'no'}**")
    gl.OUT.mkdir(exist_ok=True)
    (gl.OUT / "green_line_cyclical.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {gl.OUT / 'green_line_cyclical.md'}")


if __name__ == "__main__":
    main()
