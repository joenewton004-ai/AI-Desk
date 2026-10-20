import math

import numpy as np
import pandas as pd

from ai_desk import scorecard, tradebook


def test_sharpe_band_narrows_with_time():
    lo1, hi1 = scorecard.sharpe_band(0.9, 1)
    lo5, hi5 = scorecard.sharpe_band(0.9, 5)
    assert lo1 < -0.2 and hi1 > 2.0           # one year tells you very little
    assert hi5 - lo5 < hi1 - lo1


def test_perf_and_capture():
    idx = pd.bdate_range("2026-01-01", periods=300)
    rb = np.random.default_rng(1).normal(0.0004, 0.012, 300)
    bench = pd.Series(100 * np.cumprod(1 + rb), index=idx)
    desk = pd.Series(100 * np.cumprod(1 + np.where(rb > 0, 0.9 * rb, 0.5 * rb)), index=idx)   # catches less downside
    m = scorecard.perf(desk)
    assert m["days"] == 299 and m["total_return"] > 0 and m["max_drawdown"] <= 0
    c = scorecard.capture(desk, bench)
    assert c["downside_capture"] < c["upside_capture"]


def test_sleeve_returns_fill_quality_and_exits():
    idx = pd.bdate_range("2026-10-19", periods=30)
    closes = pd.DataFrame({"AA": np.linspace(100, 129, 30), "BB": 50.0}, index=idx)
    opens = closes * 0.99
    snaps = [{"date": str(d.date()), "holdings": {"AA": {"qty": 10, "sleeve": "bottleneck"},
                                                  "BB": {"qty": 2, "sleeve": "quality_screen"}}} for d in idx[:3]]
    sr = scorecard.sleeve_returns(snaps, closes)
    assert len(sr) == 2 and abs(sr["bottleneck"].iloc[0] - 1 / 100) < 1e-12 and sr["quality_screen"].iloc[0] == 0
    trades = [{"id": "b1", "symbol": "AA", "side": "buy", "est_price": 100.0, "fill_price": 99.5,
               "filled_qty": 10, "filled_utc": "2026-10-20T13:30:00Z", "created_utc": "2026-10-19T22:00:00Z",
               "sleeve": "bottleneck"},
              {"id": "s1", "symbol": "AA", "side": "sell", "est_price": 101.0, "fill_price": 101.0,
               "filled_qty": 10, "filled_utc": "2026-10-21T13:30:00Z", "created_utc": "2026-10-20T22:00:00Z",
               "sleeve": "bottleneck", "exit_reason": "below 100-day average"}]
    f = {r["id"]: r for r in scorecard.fill_quality(trades, opens)}
    assert f["b1"]["vs_close_bps"] == -50.0                       # bought below the signal close: a gain
    assert f["b1"]["vs_open_bps"] == round((99.5 / opens.at[idx[1], "AA"] - 1) * 1e4, 1)
    ex = scorecard.exit_followup(trades, closes, horizon=20)
    assert len(ex) == 1 and ex[0]["complete"] and ex[0]["return_after"] > 0.1   # it kept rising: exit cost us


def test_cone_contains_expected_path():
    c = scorecard.cone(pd.bdate_range("2026-10-20", periods=253), 0.16, 0.165)
    assert c.iloc[0].abs().max() < 1e-12
    assert c["low"].iloc[-1] < c["expected"].iloc[-1] < c["high"].iloc[-1]
    assert abs(c["expected"].iloc[-1] - 0.16) < 0.01


class FakeBroker:
    def __init__(self, idx):
        self.idx = idx

    def account(self):
        return {"equity": "101000", "cash": "1000"}

    def positions(self):
        return {"SPY": 40.0}

    def latest_prices(self):
        return {"SPY": 700.0}

    def portfolio_history(self):
        eq = 100_000 * np.cumprod(np.r_[1, 1 + np.full(len(self.idx) - 1, 0.001)])
        ts = [int(t.timestamp()) for t in self.idx.tz_localize("America/New_York") + pd.Timedelta(hours=16)]
        return {"timestamp": ts, "equity": list(eq)}


def test_build_writes_scorecard_and_is_early():
    idx = pd.bdate_range("2026-10-20", periods=10)
    closes = pd.DataFrame({"SPY": np.linspace(700, 707, 10), "RSP": 190.0}, index=idx)
    tradebook._append("trades.jsonl", {"id": "x", "created_utc": "2026-10-19T22:00:00Z", "signal_date": "2026-10-19", "symbol": "SPY",
                                       "side": "buy", "qty": 40, "est_price": 700.0, "sleeve": "index_momentum",
                                       "order_id": "o1", "status": "filled", "fill_price": 700.2,
                                       "filled_qty": 40, "filled_utc": "2026-10-20T13:30:00Z"})
    b = FakeBroker(idx)
    row = scorecard.snapshot(b, date="2026-10-20")
    assert row["holdings"]["SPY"]["sleeve"] == "index_momentum"
    scorecard.snapshot(b, date="2026-10-20")                       # same day replaces, not duplicates
    assert len(scorecard.snapshots()) == 1
    out = scorecard.build(b, prices={"close": closes, "open": closes}, cash_rate=pd.Series(0.04, index=idx))
    status = {r["metric"]: r["status"] for r in out["scorecard"]}
    assert status["Sharpe (above T-bills)"] == "too early"
    assert status["Orders rejected, canceled or expired"] == "ok"
    assert out["desk"]["days"] == 9 and len(out["curve"]) == 10
    assert (tradebook.DIR / "scorecard.json").exists()
    from ai_desk import dashboard
    t = dashboard.tables()
    assert t["score_headline"][0]["days"] == 9 and len(t["scorecard"]) == len(out["scorecard"])
    assert not math.isnan(out["curve"][-1]["desk"])
