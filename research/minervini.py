"""Mark Minervini's SEPA method as fixed rules, built up one layer at a time.

    python research/minervini.py

Minervini ("Trade Like a Stock Market Wizard", 2013; "Think & Trade Like a Champion", 2017) buys leaders in
strong uptrends with fast-growing earnings, on a breakout from a tight base, and cuts losses fast. The layers:

  template    his 8-point Trend Template: above the 50/150/200-day averages, stacked 50 > 150 > 200, the 200-day
              rising for a month, 30%+ above the 52-week low, within 25% of the high, RS rating 70+
  + growth    latest quarter's EPS up 25%+ and sales up 20%+ on a year earlier, from SEC 10-Q/10-K filings as
              first reported, used only from the day after the filing (point-in-time)
  + accel     EPS growth faster than the quarter before (his "acceleration")
  + market    new buys only while SPY is above its 200-day average
  entry       either hold the qualifiers (rotation: up to 10, kept while they still qualify) or buy a breakout
              from a tight base (the VCP rule of research/swing.py) on 1.5x volume
  exits       his risk rules: 7.5% stop, stop raised to break-even once a trade is up 15% (2x the risk), then sold
              on a close below the 50-day average; no profit target, no time limit

Universe = the 750 largest US companies at each quarter-end (point-in-time), survivors-only Yahoo prices (they
flatter every long-only rule here). Decide at the close, fill at the next open; idle cash earns T-bills; 0.10%
per trade each way. Writes research/output/minervini.md; findings in research/MINERVINI.md.
"""

from __future__ import annotations

import gzip
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import swing  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals import edgar  # noqa: E402

CACHE = ROOT / "data" / "backtest"
SEC = ROOT / "data" / "sec"
OUT = Path(__file__).resolve().parent / "output"
START, END, MID = swing.START, swing.END, swing.MID
COST = 0.001
STALE_DAYS = 200          # a quarter's figures count until ~2 quarters after it ended (a late filing is not news)
QUARTERLY_FORMS, ANNUAL_FORMS = ("10-Q", "10-Q/A"), ("10-K", "10-K/A")


# --- pure pieces (unit-tested) --------------------------------------------------------

def quarters_from_filings(entries: list[dict]) -> pd.DataFrame:
    """Three-month values as FIRST reported, indexed by quarter end, with the filing date. Fourth quarters come
    from the 10-K: the year's value less the three quarters reported earlier that year."""
    q, y = {}, []
    for e in entries:
        if "start" not in e or e.get("val") is None:
            continue
        days = (pd.Timestamp(e["end"]) - pd.Timestamp(e["start"])).days
        rec = (pd.Timestamp(e["start"]), pd.Timestamp(e["end"]), pd.Timestamp(e["filed"]), float(e["val"]))
        if e.get("form") in QUARTERLY_FORMS + ANNUAL_FORMS and 80 <= days <= 100:
            if rec[1] not in q or rec[2] < q[rec[1]][1]:
                q[rec[1]] = (rec[3], rec[2])
        elif e.get("form") in ANNUAL_FORMS and 350 <= days <= 380:
            y.append(rec)
    first_y = {}
    for s, e_, f, v in y:
        if e_ not in first_y or f < first_y[e_][2]:
            first_y[e_] = (s, e_, f, v)
    for s, e_, f, v in first_y.values():
        if e_ in q:
            continue
        inside = [k for k in q if s < k < e_ and q[k][1] <= f]
        if len(inside) == 3:
            q[e_] = (v - sum(q[k][0] for k in inside), f)
    if not q:
        return pd.DataFrame(columns=["val", "filed"])
    df = pd.DataFrame([(k, v, f) for k, (v, f) in q.items()], columns=["end", "val", "filed"]).set_index("end")
    return df.sort_index()


def yoy_growth(q: pd.DataFrame) -> pd.Series:
    """Growth on the same quarter a year earlier; only against a positive base (a loss to a profit has no rate)."""
    out = {}
    ends = list(q.index)
    for k, end in enumerate(ends):
        prior = [p for p in ends[:k] if 350 <= (end - p).days <= 380]
        if prior:
            base = q.at[prior[-1], "val"]
            out[end] = q.at[end, "val"] / base - 1 if base > 0 else np.nan
    return pd.Series(out, dtype=float)


def rs_rating(c: pd.DataFrame, member: np.ndarray) -> np.ndarray:
    """IBD-style relative strength, 1-99: 40% the last 3 months' return + 20% each of the 6, 9 and 12-month
    returns, ranked against the universe that day. Uses closes up to that day only."""
    r = lambda n: c / c.shift(n) - 1  # noqa: E731
    score = (0.4 * r(63) + 0.2 * r(126) + 0.2 * r(189) + 0.2 * r(252)).to_numpy(dtype=float)
    score = np.where(member, score, np.nan)
    rank = pd.DataFrame(score).rank(axis=1, pct=True).to_numpy()
    return np.nan_to_num(rank * 98 + 1, nan=0.0)


def trend_template(c: pd.DataFrame, h: pd.DataFrame, lo: pd.DataFrame) -> pd.DataFrame:
    """The 8 points less RS (added separately), each decided at the close from data up to it."""
    ma50, ma150, ma200 = (c.rolling(n, min_periods=n).mean() for n in (50, 150, 200))
    hi52 = h.rolling(252, min_periods=200).max()
    lo52 = lo.rolling(252, min_periods=200).min()
    return ((c > ma150) & (c > ma200) & (ma150 > ma200) & (ma200 > ma200.shift(21)) & (ma50 > ma150)
            & (c > ma50) & (c >= 1.30 * lo52) & (c >= 0.75 * hi52))


def growth_on_days(fund: dict[str, pd.DataFrame], dates: pd.DatetimeIndex, symbols: list[str],
                   min_eps: float = 0.25, min_sales: float = 0.20, accel: bool = False) -> np.ndarray:
    """ok[i, j]: the latest quarter public by dates[i] (filed the day before or earlier, ended within STALE_DAYS)
    had EPS growth >= min_eps and sales growth >= min_sales (and, with accel, EPS growth above the quarter before)."""
    ok = np.zeros((len(dates), len(symbols)), dtype=bool)
    for j, s in enumerate(symbols):
        f = fund.get(s)
        if f is None or f.empty:
            continue
        f = f.sort_values("filed")
        good = (f["eps_g"] >= min_eps) & (f["rev_g"] >= min_sales)
        if accel:
            good &= f["eps_g"] > f["eps_g_prev"]
        known = dates.searchsorted(f["filed"] + pd.Timedelta(days=1))      # usable from the next day
        for k, (a, end, g) in enumerate(zip(known, f.index, good)):
            b = known[k + 1] if k + 1 < len(f) else len(dates)
            stale = dates.searchsorted(end + pd.Timedelta(days=STALE_DAYS))
            if g:
                ok[a:min(b, stale), j] = True
    return ok


def simulate(o: np.ndarray, c: np.ndarray, buy: np.ndarray, keep: np.ndarray | None, rank: np.ndarray,
             ma50: np.ndarray, rf: np.ndarray, dates, symbols, allow_new: np.ndarray | None = None, slots: int = 10,
             stop: float | None = 0.075, breakeven_at: float | None = 0.15, ma_exit: bool = True,
             cost: float = COST, start: int = 0) -> tuple[pd.Series, pd.DataFrame]:
    """Daily book. At close t: exits (stop, a qualifier that stopped qualifying, close below the 50-day after the
    stop went to break-even) and the best-ranked new buys; both fill at the open t+1. Each buy gets 1/slots of
    equity, the rest earns T-bills."""
    cash, pos = 1.0, {}
    exits_due, entries_due = {}, []
    eq_out, trades = [], []
    for i in range(start, len(dates)):
        for j, why in list(exits_due.items()):
            px = o[i, j] if np.isfinite(o[i, j]) else c[i - 1, j]
            p = pos.pop(j)
            cash += p["shares"] * px * (1 - cost)
            trades.append({"symbol": symbols[j], "entry_date": p["entry_date"], "exit_date": dates[i],
                           "return": px / p["entry"] * (1 - cost) ** 2 - 1, "days": i - p["entry_i"], "why": why})
        exits_due = {}
        if entries_due:
            equity = cash + sum(p["shares"] * c[i - 1, j] for j, p in pos.items() if np.isfinite(c[i - 1, j]))
            for j in entries_due:
                if len(pos) >= slots or not np.isfinite(o[i, j]) or o[i, j] <= 0:
                    continue
                spend = min(equity / slots, cash)
                if spend <= equity / slots * 0.2:
                    break
                pos[j] = {"shares": spend * (1 - cost) / o[i, j], "entry": o[i, j], "entry_i": i,
                          "entry_date": dates[i], "floor": o[i, j] * (1 - stop) if stop else -np.inf, "even": False}
                cash -= spend
        entries_due = []
        cash *= 1 + rf[i]
        eq_out.append(cash + sum(p["shares"] * (c[i, j] if np.isfinite(c[i, j]) else p["entry"]) for j, p in pos.items()))
        for j, p in pos.items():
            px = c[i, j]
            if not np.isfinite(px):
                continue
            if breakeven_at is not None and not p["even"] and px >= p["entry"] * (1 + breakeven_at):
                p["even"], p["floor"] = True, max(p["floor"], p["entry"])
            if px <= p["floor"]:
                exits_due[j] = "break-even stop" if p["even"] else "stop"
            elif keep is not None and not keep[i, j]:
                exits_due[j] = "no longer qualifies"
            elif ma_exit and p["even"] and np.isfinite(ma50[i, j]) and px < ma50[i, j]:
                exits_due[j] = "below 50-day"
        free = slots - len(pos) + len(exits_due)
        if free > 0 and (allow_new is None or allow_new[i]):
            cand = [j for j in np.flatnonzero(buy[i]) if j not in pos]
            cand.sort(key=lambda j: -rank[i, j])
            entries_due = cand[:free]
    return pd.Series(eq_out, index=dates[start:]), pd.DataFrame(trades)


# --- data -------------------------------------------------------------------------------

def fundamentals(u) -> dict[str, pd.DataFrame]:
    """Per ticker: quarterly EPS and sales growth with filing dates, from the cached SEC company facts."""
    path = CACHE / "minervini_fund.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    out = {}
    for n, (cik, ticker) in enumerate(u.tickers.items()):
        f = SEC / f"CIK{cik:010d}.json.gz"
        if not f.exists():
            continue
        facts = json.loads(gzip.decompress(f.read_bytes()))
        eps = None
        for tag in ("EarningsPerShareDiluted", "EarningsPerShareBasic"):
            node = facts.get("facts", {}).get("us-gaap", {}).get(tag)
            if node and "USD/shares" in node["units"]:
                eps = quarters_from_filings(node["units"]["USD/shares"])
                if len(eps):
                    break
        rev = pd.DataFrame(columns=["val", "filed"])
        for tag in edgar.FLOW["revenue"]:
            r = quarters_from_filings(edgar._entries(facts, tag))
            if len(r) > len(rev):
                rev = r
        if eps is None or eps.empty or rev.empty:
            continue
        g = pd.DataFrame({"eps_g": yoy_growth(eps), "rev_g": yoy_growth(rev)}).dropna(subset=["eps_g"])
        g["eps_g_prev"] = g["eps_g"].shift(1)
        g["filed"] = eps["filed"].reindex(g.index)
        g = g.dropna(subset=["filed"])
        if len(g):
            out[ticker] = g
        if (n + 1) % 300 == 0:
            print(f"  fundamentals: {n + 1}/{len(u.tickers)} companies", flush=True)
    path.write_bytes(pickle.dumps(out))
    return out


# --- the experiment ---------------------------------------------------------------------

def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    u = pickle.loads((CACHE / "universe.pkl").read_bytes())
    d = swing.fetch_daily(swing.universe_tickers())
    o, h, lo, c, v = (d[k].astype(float).loc[:END] for k in ("open", "high", "low", "close", "volume"))
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update({k: list(s.index) for k, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    dates, symbols = c.index, list(c.columns)
    member = swing.membership(dict(sorted(snaps.items())), dates, symbols)
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).shift(1).fillna(0)
    start = int(dates.searchsorted(pd.Timestamp(START)))
    O, C = o.to_numpy(dtype=float), c.to_numpy(dtype=float)

    print("signals...", flush=True)
    liquid = ((c > 10) & ((c * v).rolling(50, min_periods=40).mean() > 20e6)).to_numpy()
    rs = rs_rating(c, member)
    tmpl = trend_template(c, h, lo).to_numpy() & liquid & member
    tmpl_rs = tmpl & (rs >= 70)
    fund = fundamentals(u)
    covered = np.array([s in fund for s in symbols])
    grow = growth_on_days(fund, dates, symbols)
    accel = growth_on_days(fund, dates, symbols, accel=True)
    vcp = swing.signals(o, h, lo, c, v)
    base = vcp["setup"].to_numpy() & member
    ma50 = vcp["ma50"].to_numpy(dtype=float)
    spy = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(dates).ffill()
    mkt = (spy > spy.rolling(200).mean()).to_numpy()
    R = rf.to_numpy()

    def run(buy, keep=None, **kw):
        return simulate(O, C, buy, keep, rs, ma50, R, dates, symbols, start=start, **kw)

    rot = dict(stop=None, breakeven_at=None, ma_exit=False)      # rotation: hold while it qualifies
    sepa = tmpl_rs & grow
    books = {
        "A. Trend Template + RS 70, held while it qualifies": run(tmpl_rs, tmpl_rs, **rot),
        "B. + EPS 25% / sales 20% growth": run(sepa, sepa, **rot),
        "C. + EPS accelerating": run(tmpl_rs & accel, tmpl_rs & accel, **rot),
        "D. B + his stops (7.5%, break-even at +15%, then 50-day)": run(sepa, sepa),
        "E. Full SEPA: B's stocks on a base breakout, his stops": run(sepa & base),
        "F. E + market filter (SPY above its 200-day)": run(sepa & base, allow_new=mkt),
        "G. E without the growth rules (chart only)": run(tmpl_rs & base),
    }
    uni_r = pd.Series(np.nanmean(np.where(member[start + 1:], C[start + 1:] / C[start:-1] - 1, np.nan), axis=1),
                      index=dates[start + 1:]).clip(-0.5, 0.5)
    uni = pd.concat([pd.Series([1.0], index=[dates[start]]), (1 + uni_r).cumprod()])
    cov_r = pd.Series(np.nanmean(np.where(member[start + 1:] & covered, C[start + 1:] / C[start:-1] - 1, np.nan),
                                 axis=1), index=dates[start + 1:]).clip(-0.5, 0.5)
    cov = pd.concat([pd.Series([1.0], index=[dates[start]]), (1 + cov_r).cumprod()])
    spy_eq = spy.iloc[start:] / spy.iloc[start]

    emit("# Minervini SEPA as fixed rules - generated tables\n")
    emit(f"Daily, {dates[start].date()} to {dates[-1].date()}; universe = the 750 largest US companies at each "
         "quarter-end (point-in-time); **survivors-only Yahoo prices**. Growth figures from SEC filings as first "
         f"reported, usable the day after filing ({len(fund)} of {len(symbols)} companies covered). Decide at the "
         "close, fill at the next open; up to 10 positions of 10%; idle cash earns T-bills; 0.10% per trade each "
         "way. Sharpe above T-bills.\n")
    emit("## 1. Layer by layer\n")
    emit("| | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | trades | invested |")
    emit("|---|---|---|---|---|---|---|---|---|")

    def row(name, eq, t=None):
        s, a, b = swing.stats(eq, rf), swing.stats(eq.loc[:MID], rf), swing.stats(eq.loc[MID:], rf)
        inv = f"{t['days'].sum() / (10 * (len(dates) - start)):.0%}" if t is not None and len(t) else ("100%" if t is None else "0%")
        emit(f"| {name} | {s['CAGR']:.1%} | {s['volatility']:.0%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | "
             f"{a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {'' if t is None else len(t)} | {inv} |")

    for k, (eq, t) in books.items():
        row(k, eq, t)
    row("Equal-weight universe", uni)
    row("Equal-weight, companies with SEC growth data", cov)
    row("SPY", spy_eq)

    emit("\n## 2. The trades\n")
    emit("| | trades | win rate | avg win | avg loss | per trade | profit factor | avg days |\n|---|---|---|---|---|---|---|---|")
    for k, (eq, t) in books.items():
        s = swing.trade_stats(t)
        if s["trades"]:
            emit(f"| {k[:2]} | {s['trades']} | {s['win rate']:.0%} | {s['avg win']:+.1%} | {s['avg loss']:+.1%} | "
                 f"{s['expectancy']:+.2%} | {s['profit factor']:.2f} | {s['avg days']:.0f} |")
    t_e = books["E. Full SEPA: B's stocks on a base breakout, his stops"][1]
    if len(t_e):
        emit("\nHow the full-SEPA (E) trades ended:\n")
        emit("| exit | trades | avg return |\n|---|---|---|")
        for why, g in t_e.groupby("why"):
            emit(f"| {why} | {len(g)} | {g['return'].mean():+.1%} |")

    emit("\n## 3. Does the growth filter pick better stocks? (no trading rules)\n")
    emit("Average next-month return of qualifying stocks vs all universe members, month-ends, close to close.\n")
    me = [i for i in range(start, len(dates) - 21) if dates[i].month != dates[i + 1].month]
    fwd = C[[i + 21 for i in me]] / C[me] - 1
    emit("| group | months | avg stocks | next month | vs universe | beat universe |\n|---|---|---|---|---|---|")
    base_m = np.array([np.nanmean(np.where(member[i], f, np.nan)) for i, f in zip(me, fwd)])
    for name, mask in (("Trend Template + RS 70", tmpl_rs), ("+ growth (SEPA screen)", sepa),
                       ("+ accelerating EPS", tmpl_rs & accel), ("growth alone (no chart rules)", grow & member),
                       ("RS 90+ with the template", tmpl & (rs >= 90))):
        g = np.array([np.nanmean(np.where(mask[i], f, np.nan)) if mask[i].any() else np.nan for i, f in zip(me, fwd)])
        n = np.array([mask[i].sum() for i in me])
        ok = np.isfinite(g)
        diff = g[ok] - base_m[ok]
        tstat = diff.mean() / diff.std(ddof=1) * np.sqrt(len(diff)) if len(diff) > 2 else np.nan
        emit(f"| {name} | {ok.sum()} | {n[ok].mean():.0f} | {np.nanmean(g):+.2%} | {diff.mean():+.2%} (t {tstat:.1f}) | "
             f"{(diff > 0).mean():.0%} |")

    emit("\n## 4. Stress tests on the best rule-based version\n")
    best = max(books, key=lambda k: swing.stats(books[k][0], rf)["Sharpe"])
    emit(f"Best Sharpe above: **{best}**. Changes one at a time:\n")
    emit("| change | return/yr | Sharpe | worst drop | trades |\n|---|---|---|---|---|")
    args = {"A": (tmpl_rs, tmpl_rs, rot), "B": (sepa, sepa, rot), "C": (tmpl_rs & accel, tmpl_rs & accel, rot),
            "D": (sepa, sepa, {}), "E": (sepa & base, None, {}), "F": (sepa & base, None, {"allow_new": mkt}),
            "G": (tmpl_rs & base, None, {})}[best[0]]
    for name, kw in {"as above": {}, "costs 0.20% each way": dict(cost=0.002), "costs 0.30% each way": dict(cost=0.003),
                     "5 positions of 20%": dict(slots=5), "20 positions of 5%": dict(slots=20),
                     "market filter on": dict(allow_new=mkt)}.items():
        eq, t = run(args[0], args[1], **{**args[2], **kw})
        s = swing.stats(eq, rf)
        emit(f"| {name} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | {len(t)} |")

    emit("\n## 5. Year by year\n")
    names = list(books)
    emit("| year | " + " | ".join(n[:2].strip(". ") for n in names) + " | equal-weight | SPY |")
    emit("|---" * (len(names) + 3) + "|")
    yr = lambda eq: eq.resample("YE").last().pct_change().fillna(eq.resample("YE").last().iloc[0] / eq.iloc[0] - 1)  # noqa: E731
    ys = [yr(books[n][0]) for n in names] + [yr(uni), yr(spy_eq)]
    for y in ys[0].index:
        emit(f"| {y.year} | " + " | ".join(f"{s.get(y, np.nan):+.0%}" for s in ys) + " |")

    OUT.mkdir(exist_ok=True)
    (OUT / "minervini.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'minervini.md'}")


if __name__ == "__main__":
    main()
