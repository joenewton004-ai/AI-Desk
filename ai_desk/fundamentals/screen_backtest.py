"""Point-in-time backtest of the stock screen.

At each rebalance date the screen is rebuilt using ONLY what was knowable
then:
  * financials from SEC filings FILED on or before that date (no later
    reports, no restatements - see edgar.annual_history(as_of=...))
  * market values from that date's price and the latest reported share count
  * the same gates, 10-year check and scoring as today's screener

Known limitation - survivorship: prices come from Yahoo, which only has
companies that still trade. Firms that went bankrupt or were acquired
before today are missing from every portfolio. That flatters ALL results,
so the fair comparison is the screen vs an equal-weighted portfolio of the
SAME universe (it has the same bias), not just vs SPY.

Other simplifications:
  * monthly data; the portfolio trades at the month-end close of the
    rebalance month (signals use that close and filings filed by then)
  * "forward" P/E isn't available historically, so value uses trailing
    earnings, operating income and free cash flow
  * equal weights, held for a year with weights drifting, 0.10% cost per
    trade on turnover
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ai_desk.fundamentals import edgar
from ai_desk.fundamentals.filters import long_run_check
from ai_desk.fundamentals.scoring import score
from ai_desk.fundamentals.yahoo import with_retry

# SIC codes for businesses the screen's metrics don't fit
EXCLUDED_SIC = [(6000, 6411), (6500, 6799)]   # banks, lenders, brokers, insurers; real estate, REITs, trusts

GATES = {
    "min_roic_avg": 0.15,    # pre-tax; ~12% after tax, the live screener's gate
    "min_roic_worst": 0.0,
    "min_rev_up_years": 0.6,
    "min_fcf_margin": 0.0,
}
LONG_RUN = {"min_years": 5}   # SEC XBRL data starts ~2009, so early dates have <10 years


def excluded_sic(sic: int | None) -> bool:
    return sic is not None and any(lo <= sic <= hi for lo, hi in EXCLUDED_SIC)


# --- data ---------------------------------------------------------------------

@dataclass
class Universe:
    tickers: dict[int, str]                 # cik -> ticker
    tables: dict[int, pd.DataFrame]         # cik -> point-in-time fact table
    sic: dict[int, int | None]


def build_universe(progress: bool = True) -> Universe:
    """Every company with $1B+ revenue in any year since 2012 that still has a
    US listing today (needed for prices) and isn't a financial/real estate firm."""
    ciks = sorted(edgar.revenue_history_ciks())
    if progress:
        print(f"  {len(ciks)} companies reported $1B+ revenue at some point since 2012")
    headers = edgar.company_headers(ciks)
    keep = {}
    for cik, h in headers.items():
        common = [t for t in h["tickers"] if "-" not in t or t.endswith(("-A", "-B"))]  # skip preferreds
        if common and not excluded_sic(h["sic"]):
            keep[cik] = common[0].upper()
    if progress:
        print(f"  {len(keep)} still listed and not financial/real estate; loading SEC filings ...")

    def load(cik):
        try:
            return cik, edgar.fact_table(cik)
        except Exception:  # noqa: BLE001
            return cik, None

    with ThreadPoolExecutor(max_workers=6) as pool:
        tables = {c: t for c, t in pool.map(load, keep) if t is not None and not t.empty}
    return Universe({c: keep[c] for c in tables}, tables, {c: headers[c]["sic"] for c in tables})


def load_prices(tickers: list[str], start: str = "2012-01-01", batch: int = 100) -> dict[str, pd.DataFrame]:
    """Monthly Close (split-adjusted), Adj Close (total return) and stock splits."""
    import yfinance as yf

    frames = {"close": [], "adj": [], "splits": []}
    for i in range(0, len(tickers), batch):
        chunk = tickers[i:i + batch]
        data = with_retry(lambda chunk=chunk: yf.download(chunk, start=start, interval="1mo", auto_adjust=False,
                                                          actions=True, progress=False, threads=True))
        frames["close"].append(data["Close"])
        frames["adj"].append(data["Adj Close"])
        frames["splits"].append(data["Stock Splits"])
    out = {k: pd.concat(v, axis=1) for k, v in frames.items()}
    # Yahoo labels a month by its first day; use month-end so dates line up with filings
    for k in out:
        out[k].index = out[k].index.to_period("M").to_timestamp("M")
        out[k] = out[k].loc[:, ~out[k].columns.duplicated()]
    return out


# --- the screen at one date ---------------------------------------------------

def snapshot(u: Universe, prices: dict[str, pd.DataFrame], date: pd.Timestamp,
             universe_size: int = 750) -> pd.DataFrame:
    """Metrics for every company as they looked on `date`."""
    close, adj, splits = prices["close"], prices["adj"], prices["splits"].fillna(0).replace(0, 1)
    rows = []
    if date not in close.index:
        raise ValueError(f"no prices for {date.date()}")
    for cik, ticker in u.tickers.items():
        if ticker not in close.columns or pd.isna(close.at[date, ticker]):
            continue
        hist = edgar.annual_history(cik, table=u.tables[cik], as_of=date)
        if hist.empty or len(hist) < 3:
            continue
        last_fy = pd.Period(hist.index[-1], "Y").end_time
        if (date - last_fy).days > 550:       # stopped filing annual reports
            continue
        when, shares = edgar.shares_outstanding(u.tables[cik], as_of=date)
        if shares and not np.isnan(shares):
            # Yahoo prices are split-adjusted to today; the share count is as
            # reported. Re-apply every split since that share count's date.
            later_splits = splits[ticker].loc[splits.index > when].prod()
            mcap = close.at[date, ticker] * shares * later_splits
        else:
            # no usable share count (e.g. only per-class counts, like Visa): scale the
            # latest public float by the price move since its date. Splits cancel out
            # because both prices are split-adjusted. Understates closely held firms.
            fdate, fval = edgar.public_float(u.tables[cik], as_of=date)
            px = close[ticker].loc[:fdate].dropna() if fdate is not None else pd.Series(dtype=float)
            if px.empty or (date - fdate).days > 550:
                continue
            mcap = fval * close.at[date, ticker] / px.iloc[-1]
        rows.append(metrics_from_history(cik, ticker, hist, mcap, momentum(adj[ticker], date), u.sic[cik]))
    df = pd.DataFrame(rows).set_index("symbol")
    df = df[df["revenue_$bn"] >= 0.5].nlargest(universe_size, "market_cap")
    # market-share proxy: growth vs the median of the same 2-digit SIC industry
    group = df["sic2"].where(df.groupby("sic2")["rev_cagr"].transform("count") >= 3, -1)
    df["rev_vs_peers"] = df["rev_cagr"] - df.groupby(group)["rev_cagr"].transform("median")
    return df


def momentum(adj: pd.Series, date: pd.Timestamp) -> float:
    """12-1 month total return ending at `date`."""
    s = adj.loc[:date].dropna()
    if len(s) < 13:
        return np.nan
    return s.iloc[-2] / s.iloc[-13] - 1


def metrics_from_history(cik, ticker, hist: pd.DataFrame, mcap: float, mom: float, sic: int | None) -> dict:
    h4 = hist.tail(4)
    rev = hist["revenue_$bn"]
    years = len(rev.tail(4)) - 1
    cagr = (rev.iloc[-1] / rev.tail(4).iloc[0]) ** (1 / years) - 1 if years and rev.tail(4).iloc[0] > 0 \
        and rev.iloc[-1] > 0 else np.nan
    last = hist.iloc[-1]
    ebit, ni, fcf = last["operating_income_$bn"] * 1e9, last["net_income_$bn"] * 1e9, last["fcf_$bn"] * 1e9
    ev = mcap + (last["debt_$bn"] - last["cash_$bn"]) * 1e9
    ni4 = h4["net_income_$bn"].sum()
    gm = h4["gross_margin"].dropna()
    return {
        "symbol": ticker, "cik": cik, "market_cap": mcap, "revenue_$bn": last["revenue_$bn"],
        "sic2": (sic or 0) // 100,
        "years_of_data": len(hist),
        "roic_avg": h4["roic_pretax"].mean(), "roic_min": h4["roic_pretax"].min(),
        "gross_margin": gm.iloc[-1] if len(gm) else np.nan, "op_margin": last["operating_margin"],
        "fcf_margin": last["fcf_margin"],
        "fcf_conversion": h4["fcf_$bn"].sum() / ni4 if ni4 > 0 else np.nan,
        "rev_cagr": cagr, "rev_growth_recent": last["revenue_growth"],
        "rev_up_years": (h4["revenue_growth"].dropna() > 0).mean() if h4["revenue_growth"].notna().any() else np.nan,
        "gm_trend": gm.iloc[-1] - gm.iloc[0] if len(gm) >= 2 else np.nan,
        "net_debt_ebitda": (last["debt_$bn"] - last["cash_$bn"]) * 1e9 / ebit if ebit > 0 else np.nan,
        # historical forward estimates don't exist: trailing earnings stand in
        "fwd_earnings_yield": ni / mcap if ni > 0 else np.nan,
        "ebit_yield": ebit / ev if ev > 0 else np.nan,
        "fcf_yield": fcf / mcap if pd.notna(fcf) else np.nan,
        "momentum_12_1": mom,
        "long_run": long_run_check(hist, LONG_RUN)[0],
    }


def passes_gates(df: pd.DataFrame) -> pd.Series:
    g = GATES
    # a missing FCF figure (capex filed under a company-specific tag, e.g. NVIDIA
    # 2013-21) is "unknown", not a fail; ROIC and growth must be present
    fcf_ok = (df["fcf_margin"] > g["min_fcf_margin"]) | df["fcf_margin"].isna()
    return ((df["roic_avg"] >= g["min_roic_avg"]) & (df["roic_min"] > g["min_roic_worst"])
            & (df["rev_up_years"] >= g["min_rev_up_years"]) & fcf_ok
            & (df["long_run"] != "fail"))


# --- simulation ---------------------------------------------------------------

@dataclass
class BacktestRun:
    returns: pd.DataFrame                       # monthly returns per portfolio
    holdings: dict[pd.Timestamp, list[str]] = field(default_factory=dict)
    counts: pd.DataFrame | None = None


def run(u: Universe, prices: dict[str, pd.DataFrame], start: str = "2014-03-31", top_n: int = 25,
        rebalance_month: int = 3, cost: float = 0.001, progress: bool = True) -> BacktestRun:
    adj = prices["adj"]
    monthly = adj.pct_change(fill_method=None)
    dates = [d for d in adj.index if d >= pd.Timestamp(start) and d.month == rebalance_month]
    end = adj.index[-1]
    books = {"screen_top": {}, "gates_only": {}, "universe_ew": {}}
    holdings, counts = {}, []
    for d in dates:
        snap = snapshot(u, prices, d)
        ok = snap[passes_gates(snap)]
        ranked = score(ok) if len(ok) else ok
        top = list(ranked.index[:top_n])
        holdings[d] = top
        books["screen_top"][d] = top
        books["gates_only"][d] = list(ok.index)
        books["universe_ew"][d] = list(snap.index)
        counts.append({"date": d.date(), "universe": len(snap), "pass_gates": len(ok)})
        if progress:
            print(f"  {d.date()}: universe {len(snap)}, pass gates {len(ok)}, top {top_n}: {', '.join(top[:8])} ...")

    rets = {name: _simulate(book, monthly, end, cost) for name, book in books.items()}
    return BacktestRun(pd.DataFrame(rets), holdings, pd.DataFrame(counts))


def _simulate(book: dict[pd.Timestamp, list[str]], monthly: pd.DataFrame, end: pd.Timestamp,
              cost: float) -> pd.Series:
    """Equal-weight each list at its date, let weights drift for the year,
    charge `cost` per unit of turnover at each rebalance. A missing return
    (e.g. a ticker gap) is treated as cash for that month."""
    dates = sorted(book)
    out, weights = {}, pd.Series(dtype=float)
    for i, d in enumerate(dates):
        names = [n for n in book[d] if n in monthly.columns]
        target = pd.Series(1 / len(names), index=names) if names else pd.Series(dtype=float)
        turnover = target.sub(weights, fill_value=0).abs().sum() if len(weights) else 1.0
        weights = target
        nxt = dates[i + 1] if i + 1 < len(dates) else end
        months = monthly.loc[(monthly.index > d) & (monthly.index <= nxt)]
        first = True
        for m, row in months.iterrows():
            r = row.reindex(weights.index).fillna(0.0)
            port = float((weights * r).sum())
            if first:
                port -= turnover * cost
                first = False
            out[m] = port
            grown = weights * (1 + r)
            weights = grown / grown.sum() if grown.sum() > 0 else grown
    return pd.Series(out).sort_index()
