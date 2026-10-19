from unittest.mock import patch

import pytest

from ai_desk.fundamentals import edgar


def fact(start, end, val, filed, form="10-K"):
    e = {"end": end, "val": val, "filed": filed, "form": form}
    if start:
        e["start"] = start
    return e


FACTS = {"facts": {"us-gaap": {
    "Revenues": {"units": {"USD": [
        fact("2022-01-01", "2022-12-31", 100, "2023-02-01"),
        fact("2022-10-01", "2022-12-31", 30, "2023-02-01"),              # a quarter inside the 10-K: ignored
        fact("2023-01-01", "2023-12-31", 120, "2024-02-01"),
        fact("2023-01-01", "2023-12-31", 118, "2025-02-01"),              # restated later: latest filing wins
        fact("2024-01-01", "2024-12-31", 150, "2024-08-01", form="10-Q"),  # not an annual report: ignored
    ]}},
    "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
        fact("2024-01-01", "2024-12-31", 150, "2025-02-01"),             # tag switch fills the gap
    ]}},
    "OperatingIncomeLoss": {"units": {"USD": [
        fact("2022-01-01", "2022-12-31", 20, "2023-02-01"),
        fact("2023-01-01", "2023-12-31", 24, "2024-02-01"),
        fact("2024-01-01", "2024-12-31", 30, "2025-02-01"),
    ]}},
    "Assets": {"units": {"USD": [fact(None, d, 200, "2025-02-01") for d in ("2022-12-31", "2023-12-31", "2024-12-31")]}},
    "LiabilitiesCurrent": {"units": {"USD": [fact(None, d, 50, "2025-02-01") for d in ("2022-12-31", "2023-12-31", "2024-12-31")]}},
    "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [fact(None, d, 30, "2025-02-01") for d in ("2022-12-31", "2023-12-31", "2024-12-31")]}},
}}}


def test_annual_history_parses_restatements_tag_switches_and_skips_quarters():
    with patch.object(edgar, "company_facts", return_value=FACTS):
        h = edgar.annual_history(1)
    assert list(h.index) == ["2022", "2023", "2024"]
    assert list(h["revenue_$bn"] * 1e9) == pytest.approx([100, 118, 150])
    assert h.loc["2023", "revenue_growth"] == pytest.approx(0.18)
    assert h.loc["2024", "operating_margin"] == pytest.approx(0.2)
    assert h.loc["2024", "roic_pretax"] == pytest.approx(30 / (200 - 30 - 50))
    assert h["fcf_margin"].isna().all()          # no capex tagged -> blank, never overstated
