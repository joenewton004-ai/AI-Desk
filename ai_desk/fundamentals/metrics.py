"""Turn a company's financial statements into the numbers that describe a
great business. Each function documents its formula. All "per year" values
use annual reports; growth "now" uses the latest quarter.

Yahoo statement tables have one row per line item (e.g. "Total Revenue") and
one column per period, newest first.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_TAX = 0.21


def line(df: pd.DataFrame, *names: str) -> pd.Series:
    """One line item as a series ordered OLDEST -> NEWEST, gaps dropped.
    Several names = fallbacks, since companies label things differently."""
    for name in names:
        if df is not None and not df.empty and name in df.index:
            s = pd.to_numeric(df.loc[name], errors="coerce")
            s.index = pd.to_datetime(s.index)
            s = s.sort_index().dropna()
            if not s.empty:
                return s
    return pd.Series(dtype=float)


def _last(s: pd.Series) -> float:
    return float(s.iloc[-1]) if len(s) else np.nan


def _div(a: float, b: float) -> float:
    return a / b if b and np.isfinite(a) and np.isfinite(b) and b != 0 else np.nan


def cagr(s: pd.Series) -> float:
    """Compound annual growth from the first to the last value."""
    if len(s) < 2 or s.iloc[0] <= 0 or s.iloc[-1] <= 0:
        return np.nan
    years = (s.index[-1] - s.index[0]).days / 365.25
    return (s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1 if years > 0.5 else np.nan


def invested_capital(balance: pd.DataFrame) -> pd.Series:
    """Operating invested capital: the money tied up in running the business.

        total assets - cash & short-term investments
                     - (current liabilities - short-term debt)

    i.e. operating assets net of what suppliers/customers fund for free
    (payables, deferred revenue). Unlike "debt + equity" it still works when
    buybacks have pushed shareholders' equity negative (McDonald's, AutoZone).
    Falls back to debt + equity if those lines are missing.
    """
    assets = line(balance, "Total Assets")
    cash = line(balance, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents")
    cur_liab = line(balance, "Current Liabilities")
    cur_debt = line(balance, "Current Debt And Capital Lease Obligation", "Current Debt")
    if len(assets) and len(cur_liab):
        return (assets - cash.reindex(assets.index).fillna(0)
                - (cur_liab - cur_debt.reindex(cur_liab.index).fillna(0))).dropna()
    ic = line(balance, "Invested Capital")
    if ic.empty:
        ic = line(balance, "Total Debt").add(line(balance, "Stockholders Equity"), fill_value=0)
    return ic


def roic_by_year(income: pd.DataFrame, balance: pd.DataFrame) -> pd.Series:
    """Return on invested capital = NOPAT / invested capital.

    NOPAT (profit from operations after tax) = EBIT x (1 - tax rate).
    Invested capital: see `invested_capital`, averaged over the year.
    Years where it is <= 0 at either end are left blank - the ratio means
    nothing there.
    """
    ebit = line(income, "EBIT", "Operating Income")
    tax = line(income, "Tax Rate For Calcs").clip(0, 0.35).reindex(ebit.index).fillna(DEFAULT_TAX)
    ic = invested_capital(balance)
    prior = ic.shift(1)
    ic_avg = ((ic + prior) / 2).fillna(ic)
    # an average across a sign flip (e.g. +300 -> -40) would look positive and mislead
    valid = (ic > 0) & ((prior > 0) | prior.isna())
    nopat = ebit * (1 - tax)
    roic = nopat / ic_avg.where(valid).reindex(nopat.index)
    return roic.dropna()


def compute(company: dict) -> dict:
    inc, bal, cf, q = company["income"], company["balance"], company["cashflow"], company["q_income"]
    info = company["info"]

    revenue = line(inc, "Total Revenue", "Operating Revenue")
    gross = line(inc, "Gross Profit")
    op_inc = line(inc, "Operating Income", "EBIT")
    ebit = line(inc, "EBIT", "Operating Income")
    ebitda = line(inc, "EBITDA", "Normalized EBITDA")
    net_inc = line(inc, "Net Income", "Net Income Common Stockholders")
    shares = line(inc, "Diluted Average Shares", "Basic Average Shares")
    fcf = line(cf, "Free Cash Flow")
    sbc = line(cf, "Stock Based Compensation")
    debt = line(bal, "Total Debt")
    cash = line(bal, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents")
    q_rev = line(q, "Total Revenue", "Operating Revenue")

    roic = roic_by_year(inc, bal)
    gm = (gross / revenue).dropna()
    rev_yoy = revenue.pct_change().dropna()

    market_cap = info.get("marketCap") or np.nan
    ev = info.get("enterpriseValue") or (market_cap + _last(debt) - _last(cash))
    fwd_pe = info.get("forwardPE")
    common_ni = np.nansum(net_inc.values) if len(net_inc) else np.nan

    return {
        "symbol": company["symbol"],
        "name": info.get("longName") or company["symbol"],
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": market_cap,
        "years_of_data": int(len(revenue)),
        # --- quality: is it a great business?
        "roic": _last(roic),                                   # latest year
        "roic_avg": float(roic.mean()) if len(roic) else np.nan,
        "roic_min": float(roic.min()) if len(roic) else np.nan,  # worst year: persistence
        "gross_margin": _last(gm),
        "op_margin": _div(_last(op_inc), _last(revenue)),
        "fcf_margin": _div(_last(fcf), _last(revenue)),
        # profits backed by cash? (sum over all years; ~1 or higher is healthy)
        "fcf_conversion": _div(np.nansum(fcf.values), common_ni) if common_ni and common_ni > 0 else np.nan,
        # --- growth
        "rev_cagr": cagr(revenue),
        # latest quarter vs the same quarter a year earlier (seasonality-safe)
        "rev_growth_recent": _div(q_rev.iloc[-1], q_rev.iloc[-5]) - 1 if len(q_rev) >= 5 else np.nan,
        "rev_up_years": float((rev_yoy > 0).mean()) if len(rev_yoy) else np.nan,
        "gm_trend": float(gm.iloc[-1] - gm.iloc[0]) if len(gm) >= 2 else np.nan,
        # --- financial strength
        "net_debt_ebitda": _div(_last(debt) - _last(cash), _last(ebitda)) if _last(ebitda) > 0 else np.nan,
        "share_change": cagr(shares),                         # negative = buybacks
        "sbc_pct_revenue": _div(_last(sbc), _last(revenue)),
        # --- valuation
        "forward_pe": fwd_pe if fwd_pe and fwd_pe > 0 else np.nan,
        "fwd_earnings_yield": 1 / fwd_pe if fwd_pe and fwd_pe > 0 else np.nan,
        "ev_ebit": _div(ev, _last(ebit)) if _last(ebit) > 0 else np.nan,
        "ebit_yield": _div(_last(ebit), ev),
        "fcf_yield": _div(_last(fcf), market_cap),
        "peg": info.get("trailingPegRatio"),
    }


def compute_all(companies: dict[str, dict]) -> pd.DataFrame:
    df = pd.DataFrame([compute(c) for c in companies.values()]).set_index("symbol")
    # market-share proxy: growing faster than the industry's typical company?
    peer_group = df["industry"].where(df.groupby("industry")["rev_cagr"].transform("count") >= 3, df["sector"])
    df["rev_vs_peers"] = df["rev_cagr"] - df.groupby(peer_group)["rev_cagr"].transform("median")
    return df
