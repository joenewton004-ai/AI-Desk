"""Leopold Aschenbrenner's Situational Awareness LP, quantified from its SEC 13F filings (Q4 2024 - Q2 2026).

    python research/aschenbrenner.py      (needs www.sec.gov - allowed 2026-10-29 - for the first download, cached
                                           in data/sec/13f/; prices from market_data/*.csv via python -m ai_desk fetch)

13F = the quarterly list of a fund's US-listed long stock and options (calls and puts at the UNDERLYING shares' value,
not the option's price) as of the quarter's last day, made public up to 45 days later. It does not show shorts of
stock, non-US holdings, cash, leverage, or anything bought and sold between quarter ends. Fixed before running:
1. The method, from the filings: per quarter the book's size, number of names, the share in stock / calls / puts, net
   exposure (stock + calls - puts, as a share of the long side), concentration (top 5), turnover (share of the long
   book that changed since the last filing), and the themes (a dated, hand-made classification below).
2. Copying it: buy at the open of the first trading day after each filing date, hold until the next filing's entry,
   the last one to END. Versions:
     stocks          the stock lines only, value-weighted
     stocks+calls    calls counted as the stock (delta 1 - overstates how much an option moves)
     full book       stock + calls long, puts SHORT, all at notional, scaled so the long side = 100% of equity
     equal weight    the stock lines, equal weight
   Costs 0.10% each way on the change in weights at each rebalance (small, volatile names). T-bills on any cash.
   Benchmarks over the same days: SPY, QQQ, SMH (semiconductors).
3. What the delay costs: the same books held from each quarter's last day (roughly the fund's own result, if it held
   them all quarter - which it may not have) vs from the filing date (what a copier can do).
Writes research/output/aschenbrenner.md.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "sec" / "13f"
OUT = Path(__file__).resolve().parent / "output"
END = "2026-10-28"
COST = 0.001
CIK = "2045724"
# from data.sec.gov/submissions/CIK0002045724.json (fetched 2026-10-29): accession -> (quarter end, filing date)
FILINGS = {
    "0000935836-25-000120": ("2024-12-31", "2025-02-12"),
    "0002045724-25-000002": ("2025-03-31", "2025-05-14"),
    "0002045724-25-000006": ("2025-06-30", "2025-08-14"),
    "0002045724-25-000008": ("2025-09-30", "2025-11-14"),
    "0002045724-26-000002": ("2025-12-31", "2026-02-11"),
    "0002045724-26-000008": ("2026-03-31", "2026-05-18"),
    "0000935836-26-000418": ("2026-06-30", "2026-08-14"),
}
TICKERS = {  # issuer name in the filings -> ticker (checked against Yahoo, 2026-10-29); Bitfarms renamed Keel in 2026
    "MARVELL TECHNOLOGY": "MRVL", "VISTRA": "VST", "VERTIV": "VRT", "TALEN ENERGY": "TLN", "CONSTELLATION ENERGY": "CEG",
    "MODINE": "MOD", "SANDISK": "SNDK", "MICRON": "MU", "BLOOM ENERGY": "BE", "TAIWAN SEMICONDUCTOR": "TSM",
    "NEBIUS": "NBIS", "COREWEAVE": "CRWV", "CORE SCIENTIFIC": "CORZ", "STMICROELECTRONICS": "STM",
    "APPLIED DIGITAL": "APLD", "RIOT PLATFORMS": "RIOT", "SHARONAI": "SHAZ", "IREN": "IREN", "CLEANSPARK": "CLSK",
    "KEEL INFRASTRUCTURE": "KEEL", "BITFARMS": "KEEL", "SOLARIS ENERGY": "SEI", "WHITEFIBER": "WYFI", "BITDEER": "BTDR",
    "T1 ENERGY": "TE", "HIVE DIGITAL": "HIVE", "BABCOCK": "BW", "PROPETRO": "PUMP", "VISHAY": "VSH", "INFOSYS": "INFY",
    "CEREBRAS": "CBRS", "INTEL": "INTC", "BROADCOM": "AVGO", "ONTO INNOVATION": "ONTO", "EQT": "EQT", "VANECK": "SMH",
    "NVIDIA": "NVDA", "GALAXY DIGITAL": "GLXY", "CIPHER MINING": "CIFR", "LUMENTUM": "LITE", "HUT 8": "HUT",
    "WESTERN DIGITAL": "WDC", "COHERENT": "COHR", "TOWER SEMICONDUCTOR": "TSEM", "SEAGATE": "STX", "KILROY": "KRC",
    "POWER SOLUTIONS": "PSIX", "LIBERTY ENERGY": "LBRT", "ORACLE": "ORCL", "ADVANCED MICRO": "AMD", "ASML": "ASML",
    "CORNING": "GLW",
}
THEMES = {  # a hand-made, dated (2026-10-29) classification of what each holding is for, in the fund's AI-build-out frame
    "power & energy": ["VST", "TLN", "CEG", "BE", "EQT", "SEI", "TE", "BW", "PUMP", "LBRT", "PSIX", "MOD", "VRT"],
    "AI data centres & miners-to-hosts": ["CRWV", "CORZ", "APLD", "IREN", "RIOT", "CLSK", "KEEL", "WYFI", "BTDR", "HIVE",
                                          "CIFR", "HUT", "GLXY", "NBIS", "SHAZ", "KRC"],
    "chips & memory": ["MRVL", "SNDK", "MU", "TSM", "STM", "INTC", "AVGO", "ONTO", "SMH", "NVDA", "WDC", "TSEM", "STX",
                       "AMD", "ASML", "VSH", "CBRS"],
    "optical & networking": ["LITE", "COHR", "GLW"],
    "software & services (puts)": ["ORCL", "INFY"],
}


def download() -> None:
    """Cache each filing's information table from www.sec.gov (the largest XML that isn't primary_doc.xml)."""
    import requests
    ua = next(l.split("=", 1)[1].strip() for l in (ROOT / ".env").read_text().splitlines() if l.startswith("SEC_USER_AGENT"))
    s = requests.Session()
    s.headers["User-Agent"] = ua
    CACHE.mkdir(parents=True, exist_ok=True)
    for acc in FILINGS:
        path = CACHE / f"{acc}.xml"
        if path.exists():
            continue
        base = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{acc.replace('-', '')}/"
        items = s.get(base + "index.json", timeout=30).json()["directory"]["item"]
        x = max((i for i in items if i["name"].endswith(".xml") and i["name"] != "primary_doc.xml"),
                key=lambda i: int(i["size"] or 0))
        path.write_text(s.get(base + x["name"], timeout=30).text)


def ticker(name: str) -> str | None:
    n = name.upper()
    return next((t for k, t in TICKERS.items() if k in n), None)


def holdings() -> pd.DataFrame:
    """Pure (given the cache): one row per filing line - quarter, filing date, ticker, kind (stock/call/put), value."""
    rows = []
    for acc, (q, filed) in FILINGS.items():
        root = ET.parse(CACHE / f"{acc}.xml").getroot()
        for it in root.iter():
            if not it.tag.endswith("infoTable"):
                continue
            g = lambda k: next((e.text for e in it.iter() if e.tag.endswith(k)), None)  # noqa: E731
            pc = (g("putCall") or "").lower()
            rows.append({"quarter": q, "filed": filed, "issuer": g("nameOfIssuer"), "ticker": ticker(g("nameOfIssuer")),
                         "kind": pc or "stock", "value": float(g("value"))})
    df = pd.DataFrame(rows)
    unmapped = df.loc[df["ticker"].isna(), "issuer"].unique()
    if len(unmapped):
        raise ValueError(f"no ticker for {list(unmapped)}")
    return df.groupby(["quarter", "filed", "ticker", "kind"], as_index=False)["value"].sum()


def theme(t: str) -> str:
    return next((k for k, v in THEMES.items() if t in v), "other")


def weights(h: pd.DataFrame, version: str) -> pd.Series:
    """Target weights for one filing (+ long, - short)."""
    if version == "equal weight":
        s = h[h["kind"] == "stock"]["ticker"].unique()
        return pd.Series(1 / len(s), index=s)
    longs = h[h["kind"].isin(["stock"] + (["call"] if version != "stocks" else []))]
    w = longs.groupby("ticker")["value"].sum()
    total = w.sum()
    w = w / total
    if version == "full book":
        puts = h[h["kind"] == "put"].groupby("ticker")["value"].sum() / total
        w = w.sub(puts, fill_value=0.0)
    return w


def prices(tickers) -> dict[str, pd.DataFrame]:
    out = {}
    for t in tickers:
        p = ROOT / "market_data" / f"{t}.csv"
        if p.exists():
            out[t] = pd.read_csv(p, index_col=0, parse_dates=True).loc[:END]
    return out


def run(h: pd.DataFrame, version: str, px: dict, days: pd.DatetimeIndex, start_col: str, rf: pd.Series) -> pd.Series:
    """Daily returns of following the filings: each book from the open after `start_col` (filing date or quarter end)
    until the next book's start; open-to-open returns; costs on weight changes; T-bills on uninvested cash."""
    opens = pd.DataFrame({t: d["open"] for t, d in px.items()}).reindex(days)
    oo = (opens.shift(-1) / opens - 1)
    books = []
    for (q, filed), g in h.groupby(["quarter", "filed"]):
        start = pd.Timestamp(filed if start_col == "filed" else q)
        e = days[days.searchsorted(start, side="right")] if start < days[-1] else None
        if e is not None:
            books.append((e, weights(g, version)))
    books.sort(key=lambda b: b[0])
    r = pd.Series(np.nan, index=days)
    prev = pd.Series(dtype=float)
    for k, (e, w) in enumerate(books):
        x = books[k + 1][0] if k + 1 < len(books) else days[-1]
        seg = days[(days >= e) & (days < x)]
        avail = [t for t in w.index if t in oo.columns]
        w = w[avail]                                   # a name without prices drops out; the rest isn't rescaled
        held = oo.loc[seg, avail].fillna(0.0)
        long_part = (held * w).sum(axis=1)
        cash = 1 - w[w > 0].sum() + (-w[w < 0]).sum() * 0      # cash behind the long side (shorts' collateral too)
        r.loc[seg] = long_part + max(cash, 0.0) * rf.reindex(seg).fillna(0.0) + (-w[w < 0]).sum() * rf.reindex(seg).fillna(0.0)
        turn = w.sub(prev, fill_value=0.0).abs().sum()
        r.loc[e] -= turn * COST
        prev = w
    return r.dropna()


def perf(r: pd.Series, rf: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    ex = r - rf.reindex(r.index).fillna(0.0)
    yrs = len(r) / 252
    return {"total": eq.iloc[-1] - 1, "cagr": eq.iloc[-1] ** (1 / yrs) - 1, "sharpe": ex.mean() / ex.std() * np.sqrt(252),
            "worst": (eq / eq.cummax() - 1).min(), "vol": r.std() * np.sqrt(252)}


def main() -> None:
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    download()
    h = holdings()
    emit("# Leopold Aschenbrenner's Situational Awareness LP, from its 13F filings - generated tables\n")
    emit(f"SEC CIK {CIK}; 7 filings (Q4 2024 - Q2 2026). Options are shown at the underlying shares' value. 13F shows only "
         "US long stock and options at each quarter's end.\n")

    emit("## 1. The method in numbers\n")
    emit("| quarter | filed | book | names | stock / calls / puts | net exposure | top 5 | changed since last | "
         "power | data centres | chips | optical | software puts |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    prev = None
    for (q, filed), g in h.groupby(["quarter", "filed"]):
        tot = g["value"].sum()
        by = g.groupby("kind")["value"].sum() / tot
        longs = g[g["kind"] != "put"].groupby("ticker")["value"].sum()
        net = (longs.sum() - g.loc[g["kind"] == "put", "value"].sum()) / longs.sum()
        lw = longs / longs.sum()
        chg = (lw.sub(prev, fill_value=0.0).abs().sum() / 2) if prev is not None else np.nan
        prev = lw
        th = g.assign(t=g["ticker"].map(theme)).groupby("t")["value"].sum() / tot
        f = lambda k: f"{th.get(k, 0):.0%}"  # noqa: E731
        emit(f"| {q} | {filed} | ${tot / 1e9:.2f}B | {g['ticker'].nunique()} | {by.get('stock', 0):.0%} / "
             f"{by.get('call', 0):.0%} / {by.get('put', 0):.0%} | {net:+.0%} | {lw.nlargest(5).sum():.0%} | "
             f"{'-' if chg != chg else f'{chg:.0%}'} | {f('power & energy')} | {f('AI data centres & miners-to-hosts')} | "
             f"{f('chips & memory')} | {f('optical & networking')} | {f('software & services (puts)')} |")

    px = prices(set(h["ticker"]) | {"SPY", "QQQ", "SMH"})
    missing = sorted(set(h["ticker"]) - set(px))
    days = px["SPY"].loc["2025-02-13":END].index
    irx = pd.read_csv(ROOT / "market_data" / "IRX.csv", index_col=0, parse_dates=True)["close"] / 100 / 252
    rf = irx.reindex(days).ffill().fillna(0.0)
    emit(f"\nPrices missing for: {', '.join(missing) or 'none'}.\n")

    emit("## 2. Copying the filings (bought at the open after each filing date)\n")
    emit(f"{days[0].date()} to {days[-1].date()}. Costs 0.10% each way on weight changes; T-bills on cash.\n")
    emit("| version | total return | per year | Sharpe above T-bills | worst drop | volatility |")
    emit("|---|---|---|---|---|---|")
    results = {}
    for v in ("stocks", "stocks+calls", "full book", "equal weight"):
        r = run(h, v, px, days, "filed", rf)
        results[v] = r
        p = perf(r, rf)
        emit(f"| copy: {v} | {p['total']:+.0%} | {p['cagr']:+.0%} | {p['sharpe']:.2f} | {p['worst']:.0%} | {p['vol']:.0%} |")
    for b in ("SPY", "QQQ", "SMH"):
        r = (px[b]["open"].reindex(days).shift(-1) / px[b]["open"].reindex(days) - 1).dropna()
        results[b] = r
        p = perf(r, rf)
        emit(f"| {b} (hold) | {p['total']:+.0%} | {p['cagr']:+.0%} | {p['sharpe']:.2f} | {p['worst']:.0%} | {p['vol']:.0%} |")

    emit("\n**Each holding period** (copy: stocks+calls vs SPY and SMH, filing date to the next):\n")
    emit("| from | to | copy | SPY | SMH |")
    emit("|---|---|---|---|---|")
    starts = sorted({days[days.searchsorted(pd.Timestamp(f), side="right")] for _, (_, f) in FILINGS.items()
                     if pd.Timestamp(f) < days[-1]})
    for k, s in enumerate(starts):
        x = starts[k + 1] if k + 1 < len(starts) else days[-1]
        seg = lambda r: (1 + r.loc[s:x - pd.Timedelta(days=1)]).prod() - 1  # noqa: E731
        emit(f"| {s.date()} | {x.date()} | {seg(results['stocks+calls']):+.0%} | {seg(results['SPY']):+.0%} | "
             f"{seg(results['SMH']):+.0%} |")

    emit("\n## 3. What the 45-day delay costs (same books, held from the quarter's end instead)\n")
    days_q = px["SPY"].loc["2025-01-02":END].index
    rf_q = irx.reindex(days_q).ffill().fillna(0.0)
    emit("| version | from the quarter end (≈ the fund, if it held all quarter) | from the filing date (a copier) |")
    emit("|---|---|---|")
    for v in ("stocks+calls", "full book"):
        a = run(h, v, px, days_q, "quarter", rf_q).loc[days[0]:]
        b = results[v]
        pa, pb = perf(a, rf), perf(b, rf)
        emit(f"| {v} | {pa['total']:+.0%} ({pa['cagr']:+.0%}/yr, Sharpe {pa['sharpe']:.2f}) | {pb['total']:+.0%} "
             f"({pb['cagr']:+.0%}/yr, Sharpe {pb['sharpe']:.2f}) |")
    emit("\n## 4. Skill or exposure? (daily copy returns regressed on SMH and SPY, above T-bills)\n")
    emit("| version | beta to SMH | beta to SPY | left over (alpha) per year | t |")
    emit("|---|---|---|---|---|")
    for v in ("stocks+calls", "full book", "equal weight"):
        x = pd.DataFrame({"r": results[v], "smh": results["SMH"], "spy": results["SPY"]}).dropna()
        x = x.sub(rf.reindex(x.index), axis=0)
        A = np.c_[np.ones(len(x)), x["smh"], x["spy"]]
        coef, *_ = np.linalg.lstsq(A, x["r"].to_numpy(), rcond=None)
        res = x["r"].to_numpy() - A @ coef
        se = np.sqrt(np.diag(np.linalg.inv(A.T @ A)) * res.var(ddof=3))
        emit(f"| {v} | {coef[1]:.2f} | {coef[2]:+.2f} | {coef[0] * 252:+.0%} | {coef[0] / se[0]:.1f} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "aschenbrenner.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'aschenbrenner.md'}")


if __name__ == "__main__":
    main()
