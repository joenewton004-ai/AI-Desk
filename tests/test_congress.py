import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import congress  # noqa: E402
import house_ptr  # noqa: E402

SAMPLE = """
ID         Owner Asset                                            Transaction Date                 Notification Amount
           JT         Amazon.com, Inc. - Common Stock             P                 11/27/2024 12/03/2024             $15,001 -
                      (AMZN) [ST]                                                                                     $50,000
                      F      S      : New
           SP          Palo Alto Networks, Inc. (PANW)            P                 02/12/2024 02/12/2024            $500,001 -
                       [OP]                                                                                          $1,000,000
                       D           : Purchased 50 call options with a strike price of $200 (XYZ).
                      Regeneron Pharmaceuticals, Inc. -           S (partial)       11/01/2024 12/03/2024             $1,001 - $15,000
                      Common Stock (REGN) [ST]
"""


def test_parse_reads_each_transaction_with_its_own_ticker():
    tr = house_ptr.parse(SAMPLE)
    assert [(x["ticker"], x["asset_type"], x["type"], x["owner"]) for x in tr] == [
        ("AMZN", "ST", "purchase", "JT"), ("PANW", "OP", "purchase", "SP"), ("REGN", "ST", "sale", "self")]
    assert tr[0]["date"] == pd.Timestamp("2024-11-27")
    assert (tr[0]["amount_low"], tr[0]["amount_high"]) == (15001, 50000)
    assert (tr[2]["amount_low"], tr[2]["amount_high"]) == (1001, 15000)


def _trades():
    return pd.DataFrame({
        "politician": ["A", "A", "B", "C"], "ticker": ["X", "X", "X", "Y"], "doc_id": ["1", "1", "2", "3"],
        "type": ["purchase"] * 4, "asset_type": ["ST"] * 4, "owner": ["self"] * 4, "amount_low": [1001, 15001, 1001, 1001],
        "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-10", "2024-01-05"]),
        "filed": pd.to_datetime(["2024-01-20", "2024-01-20", "2024-02-05", "2024-01-25"]),
        "delay": [18, 17, 26, 20]})


def test_one_event_per_report_and_clusters_dated_at_the_second_report():
    ev = congress.events(_trades())
    assert len(ev) == 3
    assert ev.loc[ev["doc_id"] == "1", "amount_low"].item() == 15001
    cl = congress.cluster(ev)
    assert list(cl["politician"]) == ["B"] and cl["filed"].item() == pd.Timestamp("2024-02-05")


def test_events_are_bought_after_the_report_not_the_trade():
    idx = pd.bdate_range("2024-01-01", periods=200)
    opens = pd.DataFrame({"X": np.linspace(100, 200, 200), "Y": 100.0}, index=idx)
    base = {h: np.zeros(len(idx)) for h in congress.HOLDS}
    sc = congress.score(congress.events(_trades()), opens, base)
    for r in sc.itertuples():
        assert r.entry > r.when                        # the first open strictly after the filing day
    filed = congress.score(congress.events(_trades()), opens, base)
    traded = congress.score(congress.events(_trades(), when="date"), opens, base)
    assert (traded["entry"].to_numpy() < filed["entry"].to_numpy()).all()


def test_smart_money_counts_a_trade_only_once_its_report_is_filed():
    from ai_desk.bottleneck.smart_money import congress_signals
    t = _trades()
    assert congress_signals(t, "X", asof="2024-01-15")["congress_net_buyers"] == 0     # traded, not yet filed
    assert congress_signals(t, "X", asof="2024-02-06")["congress_net_buyers"] == 2
