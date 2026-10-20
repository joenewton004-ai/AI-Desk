"""Backtest the testable part of the bottleneck sleeve: weekly money-flow rotation.

    python research/bottleneck_backtest.py

What IS tested (point-in-time, weekly, 2014-2026):
  each week, rank industries by money flow (relative strength 26 and 52
  weeks, breadth above the 40-week average ~ 200-day), take the 8 strongest
  stocks above their 40-week average in the top industries, size by inverse
  volatility (capped at 2x equal), re-pick weekly, 0.10% cost per trade.
  A stock that drops below its average is gone at the next weekly re-pick
  (live, the exit is checked on every run).

What is NOT tested: the fundamental fingerprints (quarterly margins and
backlog aren't available point-in-time here), insider/congress signals, and
the theme map (it's written with hindsight - the biggest bias of all).

Bias warning: prices are survivors only (companies trading today). That
flatters momentum strategies especially: stocks that soared then collapsed
and delisted are missing. Compare with the equal-weight universe (same bias).
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals.yahoo import with_retry  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
END = "2026-10-16"
lines: list[str] = []


def emit(t=""):
    print(t)
    lines.append(t)


def weekly_prices(tickers: list[str]) -> pd.DataFrame:
    path = CACHE / "weekly_adj.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    import yfinance as yf

    parts = []
    for i in range(0, len(tickers), 100):
        chunk = tickers[i:i + 100]
        d = with_retry(lambda chunk=chunk: yf.download(chunk, start="2012-01-01", interval="1wk",
                                                       auto_adjust=True, progress=False, threads=True))
        parts.append(d["Close"])
        print(f"  weekly prices {min(i + 100, len(tickers))}/{len(tickers)}")
    px = pd.concat(parts, axis=1, sort=True)
    px = px.loc[:, ~px.columns.duplicated()]
    px.index = pd.to_datetime(px.index).tz_localize(None)
    path.write_bytes(pickle.dumps(px))
    return px


def clean_returns(px: pd.DataFrame) -> pd.DataFrame:
    """Weekly returns with data glitches removed (a price of 0 gives an infinite return)."""
    r = px.where(px > 0).pct_change(fill_method=None)
    return r.where(r.abs() < 3)          # a >300% week is almost always bad data in a liquid stock


def flow_rotation(px: pd.DataFrame, industry: pd.Series, spy: pd.Series, top_industries=8, n=8,
                  cost=0.001, start="2014-01-01", repick_weeks=1) -> tuple[pd.Series, pd.DataFrame]:
    """repick_weeks > 1: re-pick every N weeks, but still drop any holding that
    closes below its 40-week average in between (the live exit rule)."""
    ret = clean_returns(px)
    rs26 = px / px.shift(26) - 1 - (spy / spy.shift(26) - 1).values[:, None]
    rs52 = px.shift(4) / px.shift(52) - 1 - (spy.shift(4) / spy.shift(52) - 1).values[:, None]
    ma40 = px.rolling(40, min_periods=40).mean()
    above = px > ma40
    vol = ret.rolling(13, min_periods=10).std()
    dates = px.loc[start:END].index
    weights, out = pd.Series(dtype=float), {}
    picks_log = []
    held = pd.Series(dtype=float)
    for i in range(len(dates) - 1):
        d, nxt = dates[i], dates[i + 1]
        if i % repick_weeks and len(held):
            # between re-picks: keep holdings, but sell anything below its average
            target = weights[[s for s in weights.index if above.at[d, s]]] if len(weights) else weights
            target = target / target.sum() if target.sum() > 0 else target
            turnover = target.sub(weights, fill_value=0).abs().sum()
            r = ret.loc[nxt].reindex(target.index).fillna(0.0)
            out[nxt] = float((target * r).sum()) - turnover * cost
            grown = target * (1 + r)
            weights = grown / grown.sum() if grown.sum() > 0 else grown
            continue
        live = px.loc[d].notna() & rs26.loc[d].notna() & rs52.loc[d].notna()
        snap = pd.DataFrame({"rs26": rs26.loc[d], "rs52": rs52.loc[d], "above": above.loc[d],
                             "ind": industry}).loc[live[live].index]
        g = snap.groupby("ind")
        flow = pd.DataFrame({"rs26": g["rs26"].median(), "rs52": g["rs52"].median(),
                             "breadth": g["above"].mean(), "n": g.size()})
        flow = flow[flow["n"] >= 4]
        flow["score"] = flow[["rs26", "rs52", "breadth"]].rank(pct=True).mean(axis=1)
        hot = flow.nlargest(top_industries, "score").index
        cands = snap[snap["ind"].isin(hot) & snap["above"]]
        cands = cands.assign(s=cands[["rs26", "rs52"]].rank(pct=True).mean(axis=1)).nlargest(n, "s")
        target = pd.Series(dtype=float)
        if len(cands):
            inv = 1 / vol.loc[d, cands.index].replace(0, np.nan)
            target = (inv / inv.sum()).fillna(1 / len(cands)).clip(upper=2 / len(cands))
            target /= target.sum()
        turnover = target.sub(weights, fill_value=0).abs().sum()
        r = ret.loc[nxt].reindex(target.index).fillna(0.0)
        out[nxt] = float((target * r).sum()) - turnover * cost
        grown = target * (1 + r)
        weights = grown / grown.sum() if grown.sum() > 0 else grown
        held = weights
        picks_log.append({"date": d.date(), "industries": ", ".join(map(str, hot[:4])), "picks": ", ".join(cands.index)})
    return pd.Series(out), pd.DataFrame(picks_log)


def stats(r: pd.Series, rf_weekly: pd.Series, per_year: int) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    ex = r - rf_weekly.reindex(r.index).fillna(0)
    return {"CAGR": eq.iloc[-1] ** (per_year / len(r)) - 1, "volatility": r.std() * np.sqrt(per_year),
            "Sharpe": ex.mean() / ex.std() * np.sqrt(per_year), "max drawdown": (eq / eq.cummax() - 1).min()}


def table(rows):
    cols = list(next(iter(rows.values())))
    out = ["| | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for k, v in rows.items():
        out.append(f"| {k} | " + " | ".join(f"{v[c]:.2f}" if c == "Sharpe" else f"{v[c]:.1%}" for c in cols) + " |")
    return "\n".join(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    u = pickle.loads((CACHE / "universe.pkl").read_bytes())
    tickers = sorted(set(u.tickers.values()))
    # Yahoo labels weeks differently by batch/exchange; align everything to Friday closes
    px = weekly_prices(tickers + ["SPY"]).resample("W-FRI").last().loc[:END]
    spy = px["SPY"]
    stocks = px.drop(columns="SPY")
    sic3 = pd.Series({t: (u.sic[c] or 0) // 10 for c, t in u.tickers.items()})
    industry = sic3.reindex(stocks.columns)
    rf_annual = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    rf_w = (rf_annual.resample("W-MON").last().reindex(px.index, method="ffill") / 52).shift(1)

    emit("## 1. Weekly money-flow rotation (8 stocks, re-picked weekly), 2014-2026\n")
    rot, picks = flow_rotation(stocks, industry, spy)
    universe = clean_returns(stocks).loc[rot.index].mean(axis=1)
    spy_r = spy.pct_change().loc[rot.index]
    rows = {"Flow rotation (weekly)": stats(rot, rf_w, 52), "Universe, equal-weight": stats(universe, rf_w, 52),
            "SPY": stats(spy_r, rf_w, 52)}
    emit(table(rows))

    emit("\n### Robustness\n")
    rows = {}
    for label, kw in (("top 4 industries", {"top_industries": 4}), ("top 12 industries", {"top_industries": 12}),
                      ("16 stocks", {"n": 16}), ("costs x3 (0.3%/trade)", {"cost": 0.003}),
                      ("re-pick every 4 weeks (exit rule weekly)", {"repick_weeks": 4}),
                      ("re-pick every 13 weeks (exit rule weekly)", {"repick_weeks": 13})):
        r, _ = flow_rotation(stocks, industry, spy, **kw)
        rows[label] = stats(r, rf_w, 52)
    emit(table(rows))
    for a, b in (("2014", "2019"), ("2020", END)):
        emit(f"\n{a}-{b[:4]}: rotation {stats(rot.loc[a:b], rf_w, 52)['CAGR']:.1%}/yr vs universe "
             f"{stats(universe.loc[a:b], rf_w, 52)['CAGR']:.1%} vs SPY {stats(spy_r.loc[a:b], rf_w, 52)['CAGR']:.1%}")
    yearly = pd.DataFrame({"rotation": rot, "SPY": spy_r}).groupby(rot.index.year).apply(lambda x: (1 + x).prod() - 1)
    emit(f"\nBeat SPY in {int((yearly['rotation'] > yearly['SPY']).sum())} of {len(yearly)} calendar years. "
         f"Worst year: {yearly['rotation'].min():+.1%} ({yearly['rotation'].idxmin()}). "
         f"Average weekly turnover: about {picks['picks'].str.split(', ').map(len).mean():.0f} names held.")

    emit("\n## 2. The full desk, monthly: 50% quality screen (quarterly) + 20% flow rotation + 30% SPY momentum\n")
    scr = pd.read_csv(OUT / "screen_backtest_returns.csv", index_col=0, parse_dates=True)
    rot_m = (1 + rot).resample("ME").prod() - 1
    q = pickle.loads((CACHE / "snapshots_m3.pkl").read_bytes())
    from ai_desk.fundamentals import screen_backtest as sb
    prices = pickle.loads((CACHE / "prices.pkl").read_bytes())
    for k in prices:
        prices[k] = prices[k].groupby(level=0).last() if k != "splits" else prices[k].groupby(level=0).max()
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update(pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()))
    quarterly = sb.simulate({"t": sb.books(dict(sorted(snaps.items())), 25)["screen_top"]}, prices, "2026-09-30")["t"]
    rf_m = (rf_annual.resample("ME").last() / 12).shift(1)
    spy_m = prices["adj"]["SPY"].loc[:"2026-09-30"]
    on = (spy_m / spy_m.shift(12) - 1 > 0).shift(1)
    idx = quarterly.index.intersection(rot_m.index)
    spy_mom = spy_m.pct_change().reindex(idx).where(on.reindex(idx).fillna(True).astype(bool), rf_m.reindex(idx))
    blends = {
        "Desk 50/20/30": 0.5 * quarterly.reindex(idx) + 0.2 * rot_m.reindex(idx) + 0.3 * spy_mom,
        "Previous 70/30 (screen + SPY momentum)": 0.7 * quarterly.reindex(idx) + 0.3 * spy_mom,
        "Quality screen alone (quarterly)": quarterly.reindex(idx),
        "Flow rotation alone": rot_m.reindex(idx),
        "SPY": scr["SPY"].reindex(idx),
    }
    emit(table({k: stats(v, rf_m, 12) for k, v in blends.items()}))
    corr = pd.DataFrame({"screen": quarterly.reindex(idx), "rotation": rot_m.reindex(idx)}).corr().iloc[0, 1]
    emit(f"\nMonthly correlation between the quality screen and the flow rotation: {corr:.2f}")

    emit("\n## 3. Recent picks (last 6 weeks)\n")
    emit("| week | top industries (SIC codes) | picks |\n|---|---|---|")
    for _, row in picks.tail(6).iterrows():
        emit(f"| {row['date']} | {row['industries']} | {row['picks']} |")

    (OUT / "bottleneck_backtest.md").write_text("# Bottleneck sleeve backtest - generated tables\n\n" + "\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'bottleneck_backtest.md'}")


if __name__ == "__main__":
    main()
