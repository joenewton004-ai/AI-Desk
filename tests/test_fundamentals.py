import json

import numpy as np
import pandas as pd
import pytest

from ai_desk.fundamentals.metrics import compute, compute_all, roic_by_year
from ai_desk.fundamentals.scoring import score
from ai_desk.fundamentals.universe import clean_universe
from ai_desk.fundamentals.yahoo import _decode

YEARS = pd.to_datetime(["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31"])   # newest first, like Yahoo
QUARTERS = pd.to_datetime(["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"])


def statements(rows: dict, cols=YEARS) -> pd.DataFrame:
    return pd.DataFrame(rows, index=cols).T


def make_company(symbol="TEST", revenue=(146.41, 133.1, 121, 110), invested=(400, 400, 400, 400),
                 ebit=(40, 36, 32, 30), market_cap=1000.0, forward_pe=20.0):
    return {
        "symbol": symbol,
        "info": {"longName": f"{symbol} Inc", "sector": "Technology", "industry": "Software",
                 "marketCap": market_cap, "enterpriseValue": market_cap + 50, "forwardPE": forward_pe},
        "income": statements({
            "Total Revenue": revenue, "Gross Profit": [r * 0.6 for r in revenue],
            "EBIT": ebit, "Operating Income": ebit, "EBITDA": [e + 10 for e in ebit],
            "Net Income": [e * 0.75 for e in ebit], "Tax Rate For Calcs": [0.25] * 4,
            "Diluted Average Shares": [97, 98, 99, 100],
        }),
        "balance": statements({"Invested Capital": invested, "Total Debt": [150] * 4,
                               "Cash Cash Equivalents And Short Term Investments": [100] * 4}),
        "cashflow": statements({"Free Cash Flow": [30] * 4, "Stock Based Compensation": [2] * 4}),
        "q_income": statements({"Total Revenue": [44, 40, 39, 37, 40]}, QUARTERS),
    }


def test_core_metrics():
    m = compute(make_company())
    assert m["rev_cagr"] == pytest.approx(0.10, abs=0.002)               # 110 -> 146.41 over 3 years
    assert m["gross_margin"] == pytest.approx(0.60)
    assert m["roic"] == pytest.approx(40 * 0.75 / 400)                    # NOPAT / invested capital
    assert m["net_debt_ebitda"] == pytest.approx((150 - 100) / 50)
    assert m["rev_growth_recent"] == pytest.approx(44 / 40 - 1)           # same quarter last year
    assert m["fcf_yield"] == pytest.approx(30 / 1000)
    assert m["fwd_earnings_yield"] == pytest.approx(1 / 20)
    assert m["share_change"] < 0                                          # buybacks
    assert m["fcf_conversion"] == pytest.approx(120 / (0.75 * (40 + 36 + 32 + 30)))


def test_roic_skips_negative_invested_capital():
    c = make_company(invested=(-50, -40, 300, 300))
    roic = roic_by_year(c["income"], c["balance"])
    assert len(roic) == 2 and (roic > 0).all()


def test_negative_forward_pe_is_missing_not_cheap():
    m = compute(make_company(forward_pe=-12))
    assert np.isnan(m["forward_pe"]) and np.isnan(m["fwd_earnings_yield"])


def test_cache_round_trip():
    c = make_company()
    raw = {"symbol": "TEST", "fetched": "2026-01-01T00:00:00+00:00", "info": c["info"]}
    for k in ("income", "balance", "cashflow", "q_income"):
        raw[k] = c[k].to_json(orient="split", date_format="iso")
    back = _decode(json.loads(json.dumps(raw)))
    assert compute(back)["roic"] == pytest.approx(compute(c)["roic"])


def test_scoring_prefers_better_business():
    great = make_company("GREAT", ebit=(80, 70, 60, 50), forward_pe=20)
    poor = make_company("POOR", ebit=(5, 6, 7, 8), revenue=(100, 105, 108, 110), forward_pe=40)
    mid = make_company("MID")
    ranked = score(compute_all({c["symbol"]: c for c in (great, mid, poor)}))
    assert list(ranked.index) == ["GREAT", "MID", "POOR"]
    assert "ROIC" in ranked.loc["GREAT", "strengths"]


def test_clean_universe_drops_duplicates_and_foreign_reporters():
    df = pd.DataFrame([
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "market_cap": 4e12, "quote_type": "EQUITY",
         "financial_currency": "USD", "avg_volume": 30e6},
        {"symbol": "GOOG", "name": "Alphabet Inc.", "market_cap": 4e12, "quote_type": "EQUITY",
         "financial_currency": "USD", "avg_volume": 20e6},
        {"symbol": "TSM", "name": "Taiwan Semi", "market_cap": 2e12, "quote_type": "EQUITY",
         "financial_currency": "TWD", "avg_volume": 10e6},
    ])
    assert clean_universe(df)["symbol"].tolist() == ["GOOGL"]
