import json

import numpy as np
import pandas as pd

from ai_desk import overnight, rsi_dip
from ai_desk.portfolio.methods import RSIDip


def _closes(n=260, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-01", periods=n)
    return pd.DataFrame({s: 100 * np.exp(np.cumsum(rng.normal(0.001, 0.015, n))) for s in ("AA", "BB", "CC")},
                        index=idx)


def test_evaluate_uses_only_data_up_to_the_last_row():
    c = _closes()
    a = rsi_dip.evaluate(c.iloc[:240])
    future = c.copy()
    future.iloc[240:] *= 3
    b = rsi_dip.evaluate(future.iloc[:240])
    pd.testing.assert_frame_equal(a, b)


def test_signal_needs_uptrend_and_low_rsi():
    c = _closes(260, seed=1)
    c["AA"] = np.r_[np.linspace(50, 120, 250), np.linspace(119, 108, 10)]   # uptrend, then 10 down days
    t = rsi_dip.evaluate(c)
    assert t.loc["AA", "above_200"] and t.loc["AA", "rsi_14"] < 30 and t.loc["AA", "signal"]
    c["BB"] = np.linspace(200, 60, 260)                                     # downtrend: never a signal
    assert not rsi_dip.evaluate(c).loc["BB", "signal"]


def test_decide_exits_and_fills_free_slots_lowest_rsi_first():
    t = pd.DataFrame({"close": [10.0, 20, 30, 40, 50], "sma_5": [9.0, 21, 31, 41, 51],
                      "rsi_14": [40.0, 45, 25, 20, 28], "above_5": [True, False, False, False, False],
                      "signal": [False, False, True, True, True]}, index=["H1", "H2", "S1", "S2", "S3"])
    held = {"H1": {"signal_date": "2026-10-01"}, "H2": {"signal_date": "2026-10-01"}}
    d = rsi_dip.decide(t, held, {"H1": 3, "H2": 10}, universe={"S1", "S2", "S3"}, max_positions=2)
    assert set(d["exits"]) == {"H1", "H2"} and "5-day" in d["exits"]["H1"] and "10-day" in d["exits"]["H2"]
    assert d["entries"] == ["S2", "S1"]                     # two free slots, lowest RSI first (20, 25)
    d = rsi_dip.decide(t, held, {"H1": 0, "H2": 2}, universe={"S1", "S2", "S3"}, max_positions=2)
    assert d["keep"] == ["H1", "H2"] and d["entries"] == []  # a buy day's own close never triggers the exit


def test_trading_days_since_counts_closes_after_the_signal():
    idx = pd.bdate_range("2026-10-01", periods=10)
    assert rsi_dip.trading_days_since(idx, "2026-10-01", idx[-1]) == 9


def test_method_uses_todays_scan_and_saves_state_only_when_executed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    c = _closes()
    day = c.index[-1].date().isoformat()
    scan = pd.DataFrame({"close": [1.0, 2, 3], "sma_5": [2.0, 3, 4], "sma_200": [0.5, 1, 1], "rsi_14": [25.0, 22, 50],
                         "above_200": True, "above_5": False, "signal": [True, True, False], "in_top100": True,
                         "asof": day}, index=pd.Index(["AA", "BB", "CC"], name="symbol"))
    (tmp_path / "output").mkdir()
    scan.to_csv(tmp_path / "output" / f"rsi_dip_{pd.Timestamp.today().date().isoformat()}.csv")
    m = RSIDip(max_positions=1)
    w = m.weights(c)
    assert list(w.columns) == ["BB"] and (w["BB"] == 0.10).all()
    assert not (tmp_path / "data/portfolio/rsi_dip.json").exists()        # dry run: nothing saved
    m.on_executed()
    state = json.loads((tmp_path / "data/portfolio/rsi_dip.json").read_text())
    assert list(state["positions"]) == ["BB"] and state["positions"]["BB"]["signal_date"] == day
    # a scan from another close changes nothing: hold BB, buy nothing
    m2 = RSIDip(max_positions=1)
    w2 = m2.weights(c.iloc[:-1])
    assert list(w2.columns) == ["BB"] and m2.frozen() == {"BB"} and "holding" in m2.status()[0]


def test_overnight_budget_grows_after_the_switch():
    assert overnight.share_for("2026-10-27") == overnight.SHARE
    assert overnight.share_for(overnight.SHARE_SWITCH["from"]) == 1.0
    orders = overnight.plan_buys(["AA", "BB"], 100_000, 90_000, {"AA": 100.0, "BB": 50.0}, False, share=1.0)
    spent = sum(o["qty"] * {"AA": 100.0, "BB": 50.0}[o["symbol"]] for o in orders)
    assert 88_000 < spent <= 89_000                         # cash less the 1% buffer, not 30% of equity
