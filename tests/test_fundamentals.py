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


def test_operating_invested_capital_works_with_negative_equity():
    from ai_desk.fundamentals.metrics import invested_capital

    bal = statements({"Total Assets": [1000] * 4, "Cash Cash Equivalents And Short Term Investments": [100] * 4,
                      "Current Liabilities": [300] * 4, "Current Debt": [50] * 4,
                      "Stockholders Equity": [-200] * 4, "Total Debt": [900] * 4})
    assert (invested_capital(bal) == 1000 - 100 - (300 - 50)).all()


def test_incomplete_downloads_are_never_trusted(tmp_path):
    from ai_desk.fundamentals.yahoo import _complete, load_cached

    empty = {"symbol": "X", "fetched": "2099-01-01T00:00:00+00:00", "info": {"marketCap": None},
             "income": None, "balance": None, "cashflow": None, "q_income": None}
    assert not _complete(empty)
    (tmp_path / "X.json").write_text(json.dumps(empty))
    assert load_cached("X", tmp_path) is None


def _row(symbol, sector, industry, roic_avg=0.2, **kw):
    base = {"sector": sector, "industry": industry, "roic_avg": roic_avg, "roic_min": 0.1,
            "years_of_data": 4, "rev_up_years": 1.0, "fcf_margin": 0.2}
    return pd.Series({**base, **kw}, name=symbol)


def test_business_type_filter_keeps_payment_networks_drops_lenders():
    from ai_desk.fundamentals.filters import business_type_mask

    df = pd.DataFrame([
        _row("V", "Financial Services", "Credit Services"),
        _row("COF", "Financial Services", "Credit Services", roic_avg=np.nan),
        _row("JPM", "Financial Services", "Banks - Diversified"),
        _row("CME", "Financial Services", "Financial Data & Stock Exchanges"),
        _row("O", "Real Estate", "REIT - Retail"),
        _row("MSFT", "Technology", "Software - Infrastructure"),
    ])
    assert list(df.index[business_type_mask(df)]) == ["V", "CME", "MSFT"]


def test_gates_drop_cyclical_and_cash_burning():
    from ai_desk.fundamentals import filters

    df = pd.DataFrame([
        _row("GREAT", "Technology", "Software"),
        _row("CYCLICAL", "Basic Materials", "Gold", roic_min=-0.09),
        _row("LOWRETURN", "Utilities", "Utilities", roic_avg=0.06),
        _row("BURNER", "Technology", "Software", fcf_margin=-0.1),
        _row("SHRINKING", "Technology", "Software", rev_up_years=1 / 3),
    ])
    for m in filters.METRICS:   # give everyone full data coverage
        df[m] = df.get(m, 1.0)
    kept, notes = filters.apply(df, {})
    assert list(kept.index) == ["GREAT"]
    assert len(notes) == 4


def _history(growth, margin, roic):
    n = len(growth)
    return pd.DataFrame({"revenue_$bn": [1.0] * n, "revenue_growth": growth,
                         "operating_margin": margin, "roic_pretax": roic},
                        index=[str(2016 + i) for i in range(n)])


@pytest.mark.parametrize("name, hist, expected", [
    ("steady grower", _history([np.nan] + [0.1] * 9, [0.2] * 10, [0.3] * 10), "pass"),
    ("one bad year is fine", _history([np.nan] + [0.1] * 9, [-0.01] + [0.2] * 9, [-0.01] + [0.3] * 9), "pass"),
    ("commodity cycle: 3 revenue drops", _history([np.nan, .2, -.1, .3, -.2, .1, -.1, .1, .1, .1], [0.3] * 10,
                                                  [0.2] * 10), "fail"),
    ("low returns most years", _history([np.nan] + [0.05] * 9, [0.1] * 10, [0.05] * 7 + [0.3] * 3), "fail"),
    ("loss-making for years", _history([np.nan] + [0.3] * 9, [-0.5] * 4 + [0.4] * 6, [np.nan] * 10), "fail"),
    ("young company", _history([np.nan] + [0.3] * 4, [0.2] * 5, [0.3] * 5), "short history"),
    ("no filings", None, "no SEC data"),
])
def test_long_run_check(name, hist, expected):
    from ai_desk.fundamentals.filters import long_run_check

    status, detail = long_run_check(hist)
    assert status == expected, (name, detail)


def test_apply_long_run_drops_failures_and_unverifiable():
    from ai_desk.fundamentals.filters import apply_long_run

    df = pd.DataFrame(index=["GOOD", "CYCLICAL", "NEW", "FOREIGN"])
    histories = {"GOOD": _history([np.nan] + [0.1] * 9, [0.2] * 10, [0.3] * 10),
                 "CYCLICAL": _history([np.nan, -.1, -.1, -.1, .1, .1, .1, .1, .1, .1], [0.3] * 10, [0.2] * 10),
                 "NEW": _history([np.nan, 0.5], [0.2] * 2, [0.3] * 2)}
    kept, notes = apply_long_run(df, histories)
    assert list(kept.index) == ["GOOD", "NEW"]          # FOREIGN has no SEC data to check
    assert "1 failed" in notes[0] and "FOREIGN" in notes[1]


def test_ticker_header_parsing():
    from ai_desk.fundamentals.edgar import _HEADER

    head = '{"cik":"0001652044","entityType":"operating","name":"Alphabet Inc.","tickers":["GOOGL","GOOG"],"exchanges"'
    m = _HEADER.search(head)
    assert m["name"] == "Alphabet Inc." and '"GOOGL","GOOG"' in m["tickers"]


def test_implausible_forward_pe_is_flagged_not_scored():
    c = make_company(forward_pe=4.7)
    c["info"]["trailingPE"] = 45.8          # forward EPS ~10x trailing: an unadjusted split
    m = compute(c)
    assert np.isnan(m["fwd_earnings_yield"]) and "forward estimate looks wrong" in m["data_flags"]
    ok = make_company(forward_pe=14)
    ok["info"]["trailingPE"] = 27            # 2x: fast growth, plausible
    assert compute(ok)["data_flags"] == ""


def test_no_sec_data_excluded_unless_allowed():
    from ai_desk.fundamentals.filters import apply_long_run

    df = pd.DataFrame(index=["GOOD", "FOREIGN"])
    good = {"GOOD": _history([np.nan] + [0.1] * 9, [0.2] * 10, [0.3] * 10)}
    assert list(apply_long_run(df, good)[0].index) == ["GOOD"]
    assert list(apply_long_run(df, good, allow_unverified=True)[0].index) == ["GOOD", "FOREIGN"]
