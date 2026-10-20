"""Bottleneck scan: find where money is flowing, then the companies in that
flow whose numbers say "we are the constraint".

Step 1 - MONEY FLOW: rank every industry by how strongly money is moving
  into it: relative strength vs the S&P 500 (6 and 12 months), breadth (share
  of its stocks above their 200-day average), and its companies' revenue
  growth and margin change. Data-driven - new themes surface on their own.

Step 2 - CANDIDATES: companies in the top flow industries, plus every company
  in a curated theme map (themes.py) - e.g. the AI data-centre supply chain.

Step 3 - BOTTLENECK FINGERPRINTS (must pass all):
  * demand: revenue up 10%+ year on year (last two quarters vs a year earlier)
  * pricing power: gross margin not falling (a real bottleneck can raise prices)
  * money still flowing: price above its 200-day average

Step 4 - SCORE (percentiles among candidates, 100 = best):
  * flow (25%): relative strength 6m and 12m, closeness to the 52-week high
  * bottleneck (35%): revenue growth, growth acceleration, gross and operating
    margin expansion, order backlog growth (SEC "remaining performance obligations")
  * asymmetry (25%): price for the growth (forward P/E vs implied earnings
    growth), how stretched the price is above its trend, balance sheet
  * smart money (15%): insiders buying on the open market, and members of
    Congress buying (when that data is supplied) - see smart_money.py

This is a ranked shortlist of TODAY's market, not a backtest: the fundamental
fingerprints can't be tested point-in-time here, and theme maps are written
with hindsight. See research/BOTTLENECK.md for what was tested.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from ai_desk.bottleneck.themes import THEMES, theme_industries, theme_seeds
from ai_desk.fundamentals.metrics import compute as base_metrics
from ai_desk.fundamentals.metrics import line
from ai_desk.fundamentals.yahoo import with_retry

WEIGHTS = {"flow": 0.25, "bottleneck": 0.35, "asymmetry": 0.25, "smart_money": 0.15}
SIGNALS = {
    # metric: (group, higher_is_better)
    "rs_6m": ("flow", True), "rs_12m": ("flow", True), "near_high": ("flow", True),
    "rev_growth": ("bottleneck", True), "rev_acceleration": ("bottleneck", True),
    "gm_change": ("bottleneck", True), "opm_change": ("bottleneck", True), "backlog_growth": ("bottleneck", True),
    "peg": ("asymmetry", False), "extension": ("asymmetry", False), "net_debt_ebitda": ("asymmetry", False),
    "insider_buyers": ("smart_money", True), "insider_net_buy_pct": ("smart_money", True),
    "congress_net_buyers": ("smart_money", True),
}
GATES = {"min_rev_growth": 0.10, "min_gm_change": 0.0, "min_market_cap": 2e9}


# --- prices --------------------------------------------------------------------

def daily_closes(symbols: list[str], period: str = "15mo", batch: int = 100) -> pd.DataFrame:
    """Split/dividend-adjusted daily closes, one column per symbol (gaps kept)."""
    import yfinance as yf

    parts = []
    for i in range(0, len(symbols), batch):
        chunk = symbols[i:i + batch]
        data = with_retry(lambda chunk=chunk: yf.download(chunk, period=period, auto_adjust=True,
                                                          progress=False, threads=True))
        close = data["Close"]
        if isinstance(close, pd.Series):
            close = close.to_frame(chunk[0])
        parts.append(close)
    out = pd.concat(parts, axis=1)
    out.index = pd.to_datetime(out.index).tz_localize(None)
    return out.loc[:, ~out.columns.duplicated()]


def price_signals(close: pd.Series, spy: pd.Series) -> dict:
    s = close.dropna()
    if len(s) < 210:
        return {}
    ret = lambda x, n, skip=0: x.iloc[-1 - skip] / x.iloc[-1 - n] - 1 if len(x) > n else np.nan  # noqa: E731
    sma200 = s.rolling(200).mean().iloc[-1]
    spy = spy.reindex(s.index).ffill()
    return {
        "rs_6m": ret(s, 126) - ret(spy, 126),
        "rs_12m": ret(s, 252, 21) - ret(spy, 252, 21),          # skip the latest month, as in momentum
        "near_high": s.iloc[-1] / s.iloc[-252:].max(),
        "extension": s.iloc[-1] / sma200 - 1,                   # how far above its 200-day average
        "above_200d": bool(s.iloc[-1] > sma200),
        "vol_3m": s.pct_change().iloc[-63:].std() * np.sqrt(252),
    }


# --- fundamentals ---------------------------------------------------------------

def quarterly_signals(company: dict) -> dict:
    """Growth, acceleration and margin change from the last 6 quarters."""
    q = company["q_income"]
    rev, gp, op = line(q, "Total Revenue", "Operating Revenue"), line(q, "Gross Profit"), \
        line(q, "Operating Income", "EBIT")
    out = {"rev_growth": np.nan, "rev_acceleration": np.nan, "gm_change": np.nan, "opm_change": np.nan}
    if len(rev) < 5:
        return out
    n = 2 if len(rev) >= 6 else 1                       # compare the last 2 quarters with the same 2 a year earlier
    recent, year_ago = rev.iloc[-n:].sum(), rev.iloc[-4 - n:-4].sum()
    out["rev_growth"] = recent / year_ago - 1 if year_ago > 0 else np.nan
    if len(rev) >= 6:
        out["rev_acceleration"] = (rev.iloc[-1] / rev.iloc[-5]) - (rev.iloc[-2] / rev.iloc[-6])

    def margin_change(x: pd.Series) -> float:
        """Margin over the recent quarters minus the margin a year earlier."""
        x = x.reindex(rev.index)
        now, then = x.iloc[-n:], x.iloc[-4 - n:-4]
        if now.isna().any() or then.isna().any() or year_ago <= 0:
            return np.nan
        return now.sum() / recent - then.sum() / year_ago

    out["gm_change"] = margin_change(gp)
    out["opm_change"] = margin_change(op)
    return out


def asymmetry_signals(company: dict) -> dict:
    info = company["info"]
    fwd, trail = info.get("forwardPE"), info.get("trailingPE")
    peg = np.nan
    if fwd and trail and fwd > 0 and trail > 0:
        growth = trail / fwd - 1                           # implied next-year earnings growth
        if 0 < growth < 2:                                 # >200% usually means a data error
            peg = fwd / (growth * 100)
    return {"peg": peg, "forward_pe": fwd if fwd and fwd > 0 else np.nan}


# --- the scan -------------------------------------------------------------------

def industry_flow(df: pd.DataFrame, min_members: int = 3) -> pd.DataFrame:
    """Rank industries by money flowing in (median of members' signals)."""
    g = df.groupby("industry")
    flow = pd.DataFrame({
        "members": g.size(),
        "rs_6m": g["rs_6m"].median(),
        "rs_12m": g["rs_12m"].median(),
        "breadth": g["above_200d"].mean(),
        "rev_growth": g["rev_growth"].median(),
        "gm_change": g["gm_change"].median(),
    })
    flow = flow[flow["members"] >= min_members]
    pct = flow[["rs_6m", "rs_12m", "breadth", "rev_growth", "gm_change"]].rank(pct=True) * 100
    flow["flow_score"] = pct.mean(axis=1)
    return flow.sort_values("flow_score", ascending=False)


def score(cands: pd.DataFrame) -> pd.DataFrame:
    out = cands.copy()
    for group in WEIGHTS:
        cols = [m for m, (g, _) in SIGNALS.items() if g == group and m in out and out[m].notna().any()]
        if not cols:
            continue
        pct = pd.DataFrame({m: out[m].rank(pct=True, ascending=SIGNALS[m][1]) * 100 for m in cols})
        out[f"{group}_score"] = pct.mean(axis=1)
    for group in WEIGHTS:          # a group with no data at all (e.g. no congress file) scores neutral
        if f"{group}_score" not in out:
            out[f"{group}_score"] = np.nan
    out["score"] = sum(out[f"{g}_score"].fillna(50) * w for g, w in WEIGHTS.items())
    return out.sort_values("score", ascending=False)


def gates(df: pd.DataFrame) -> pd.Series:
    g = GATES
    return ((df["rev_growth"] >= g["min_rev_growth"]) & (df["gm_change"].fillna(0) >= g["min_gm_change"])
            & df["above_200d"] & (df["market_cap"] >= g["min_market_cap"]))


def run_scan(theme: str | None = "ai_datacenter", top_industries: int = 8, min_cap: float = 10e9,
             with_backlog: bool = True, with_smart_money: bool = True, theme_only: bool = False,
             progress: bool = True) -> dict:
    """theme_only: only companies in the theme map can be picked; the money-flow
    ranking is still reported, so new flows (e.g. energy) stay visible."""
    from ai_desk.fundamentals.universe import large_caps
    from ai_desk.fundamentals.yahoo import fetch_many

    seeds = theme_seeds(theme) if theme else {}
    theme_inds = theme_industries(theme) if theme else {}
    universe = large_caps(min_cap)["symbol"].tolist()
    symbols = list(dict.fromkeys(universe + list(seeds)))
    if progress:
        print(f"  {len(symbols)} companies ({len(universe)} above ${min_cap / 1e9:.0f}B + theme seeds)")
    companies = fetch_many(symbols, workers=2, progress=progress)
    closes = daily_closes(list(companies) + ["SPY"])
    spy = closes["SPY"]

    rows = []
    for sym, c in companies.items():
        if sym not in closes:
            continue
        ps = price_signals(closes[sym], spy)
        if not ps:
            continue
        base = base_metrics(c)
        rows.append({"symbol": sym, "name": base["name"], "industry": base["industry"], "sector": base["sector"],
                     "market_cap": base["market_cap"], "net_debt_ebitda": base["net_debt_ebitda"],
                     **ps, **quarterly_signals(c), **asymmetry_signals(c)})
    df = pd.DataFrame(rows).set_index("symbol")

    flow = industry_flow(df)
    hot = list(flow.index[:top_industries])
    df["segment"] = pd.Series(df.index.map(seeds.get), index=df.index).fillna(df["industry"].map(theme_inds))
    df["source"] = pd.Series(np.where(df["segment"].notna(), "theme", None), index=df.index, dtype=object)
    df.loc[df["industry"].isin(hot) & df["source"].isna(), "source"] = "flow"
    df.loc[df["industry"].isin(hot) & (df["source"] == "theme"), "source"] = "theme+flow"
    cands = df[df["source"].isin(["theme", "theme+flow"] if theme_only else ["theme", "theme+flow", "flow"])].copy()

    if with_backlog:
        cands["backlog_growth"] = _backlogs(list(cands.index))
    else:
        cands["backlog_growth"] = np.nan
    cands["passes"] = gates(cands)
    passing = cands[cands["passes"]].copy()
    if with_smart_money and len(passing):
        from ai_desk.bottleneck.smart_money import smart_money
        if progress:
            print(f"  insider/congress activity for {len(passing)} companies ...")
        passing = passing.join(smart_money(list(passing.index), passing["market_cap"]))
    ranked = score(passing)
    return {"flow": flow, "candidates": cands, "ranked": ranked, "theme": theme,
            "industry_of_hot": hot, "asof": closes.index[-1]}


def _backlogs(symbols: list[str]) -> pd.Series:
    from concurrent.futures import ThreadPoolExecutor

    from ai_desk.fundamentals import edgar

    ciks = edgar.ticker_map()

    def one(sym):
        cik = ciks.get(sym)
        try:
            return edgar.backlog_growth(edgar.fact_table(cik)) if cik else np.nan
        except Exception:  # noqa: BLE001 - backlog is a bonus signal; never fail the scan on it
            return np.nan

    with ThreadPoolExecutor(max_workers=6) as pool:
        return pd.Series(list(pool.map(one, symbols)), index=symbols)


# --- report ---------------------------------------------------------------------

def _pct(v, signed=False):
    return "n/a" if pd.isna(v) else (f"{v:+.0%}" if signed else f"{v:.0%}")


def report(result: dict, top: int = 15, out_dir: str = "output") -> Path:
    flow, cands, ranked, theme = result["flow"], result["candidates"], result["ranked"], result["theme"]
    lines = [f"# Bottleneck scan - {result['asof'].date()}", "",
             "Ranked shortlist of TODAY's market (not a backtest). Scores are percentiles among candidates.", ""]
    lines += ["## Where money is flowing (industries)", "",
              "| # | industry | members | rel. strength 6m | 12m | above 200-day | revenue growth | gross margin chg | flow score |",
              "|---|---|---|---|---|---|---|---|---|"]
    for i, (ind, r) in enumerate(flow.head(15).iterrows(), 1):
        lines.append(f"| {i} | {ind} | {int(r['members'])} | {_pct(r['rs_6m'], True)} | {_pct(r['rs_12m'], True)} | "
                     f"{r['breadth']:.0%} | {_pct(r['rev_growth'], True)} | {_pct(r['gm_change'], True)} | "
                     f"{r['flow_score']:.0f} |")
    if theme:
        t = THEMES[theme]
        lines += ["", f"## Theme: {theme} (map dated {t['as_of']})", "", t["thesis"], "",
                  "| segment | candidates | pass the bottleneck test | best |", "|---|---|---|---|"]
        for seg in t["segments"]:
            c = cands[cands["segment"] == seg]
            p = ranked[ranked["segment"] == seg]
            lines.append(f"| {seg} | {len(c)} | {len(p)} | {', '.join(p.index[:4]) or '-'} |")
    lines += ["", f"## Top {top} bottleneck candidates", "",
              f"{int(cands['passes'].sum())} of {len(cands)} candidates show all three fingerprints "
              "(revenue +10%, margins not falling, price above its 200-day average).", "",
              "| # | symbol | name | segment / industry | score | flow | bottleneck | asymmetry | smart money | "
              "rev growth | gross margin chg | backlog growth | rel. strength 6m | insiders buying (6m) | "
              "Congress net buyers (90d) | fwd P/E | PEG | above 200-day |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, (s, r) in enumerate(ranked.head(top).iterrows(), 1):
        where = r["segment"] if isinstance(r["segment"], str) else r["industry"]
        sm = "n/a" if pd.isna(r.get("smart_money_score")) else f"{r['smart_money_score']:.0f}"
        ins = "n/a" if pd.isna(r.get("insider_buyers")) else (
            f"{int(r['insider_buyers'])} (${r['insider_buy_value'] / 1e6:,.1f}M)" if r["insider_buyers"] else "0")
        cong = "n/a" if pd.isna(r.get("congress_net_buyers")) else f"{int(r['congress_net_buyers']):+d}"
        lines.append(f"| {i} | {s} | {str(r['name'])[:24]} | {where} ({r['source']}) | {r['score']:.0f} | "
                     f"{r['flow_score']:.0f} | {r['bottleneck_score']:.0f} | {r['asymmetry_score']:.0f} | {sm} | "
                     f"{_pct(r['rev_growth'], True)} | {_pct(r['gm_change'], True)} | "
                     f"{_pct(r['backlog_growth'], True)} | {_pct(r['rs_6m'], True)} | {ins} | {cong} | "
                     f"{'n/a' if pd.isna(r['forward_pe']) else f'{r.forward_pe:.0f}'} | "
                     f"{'n/a' if pd.isna(r['peg']) else f'{r.peg:.1f}'} | {_pct(r['extension'], True)} |")
    from ai_desk.bottleneck.smart_money import describe_sources
    lines += ["", f"Data: {describe_sources()}."]
    lines += ["", "_A research shortlist, not buy recommendations. Theme maps are written with hindsight; "
              "check each company's backlog, capacity plans and customer concentration yourself._"]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md = out / f"bottleneck_{date.today().isoformat()}.md"
    md.write_text("\n".join(lines) + "\n")
    ranked.to_csv(out / f"bottleneck_{date.today().isoformat()}.csv")
    return md
