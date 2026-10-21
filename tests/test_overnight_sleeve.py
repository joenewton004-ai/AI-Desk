from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from ai_desk import overnight as ov


def _bars(n=260, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-01", periods=n)
    c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (n, 3)), axis=0)), index=idx, columns=list("ABC"))
    o = c.shift(1) * (1 + np.array([0.002, 0.0, -0.002]))       # A gaps up overnight, C gaps down
    return o.fillna(c), c


def test_score_uses_only_data_up_to_each_close():
    o, c = _bars()
    full = ov.overnight_score(o, c)
    cut = ov.overnight_score(o.iloc[:230], c.iloc[:230])
    pd.testing.assert_frame_equal(full.iloc[:230], cut)
    last = full.iloc[-1]
    assert last["A"] > last["B"] > last["C"]


def test_pick_respects_eligibility_and_size():
    score = pd.Series({"A": 0.003, "B": 0.002, "C": 0.001})
    elig = pd.Series({"A": False, "B": True, "C": True})
    assert ov.pick(score, elig, 1) == ["B"]


def test_repick_after_a_month_end_only():
    lock = {"ref_date": "2026-09-30"}
    assert ov.repick_due(None, pd.Timestamp("2026-10-20"))
    assert not ov.repick_due(lock, pd.Timestamp("2026-09-30"))
    assert ov.repick_due(lock, pd.Timestamp("2026-10-30"))


def test_plan_buys_whole_shares_with_a_buffer_and_never_on_top_of_holdings():
    orders = ov.plan_buys(["A", "B"], 10_000, {"A": 33.0, "B": 7000.0}, {})
    assert orders == [{"symbol": "A", "qty": 148, "side": "buy", "ref_price": 33.0, "notional": 148 * 33.0}]  # B: < 1 share
    assert ov.plan_buys(["A"], 10_000, {"A": 33.0}, {"Z": 5}) == []
    assert ov.plan_sells({"A": 148.0, "B": 0.4}) == [{"symbol": "A", "qty": 148, "side": "sell"}]


def test_windows_and_account_guard():
    assert ov.in_window(datetime(2026, 10, 21, 19, 40, tzinfo=timezone.utc), ov.BUY_WINDOW)      # 3:40pm New York
    assert not ov.in_window(datetime(2026, 10, 21, 19, 55, tzinfo=timezone.utc), ov.BUY_WINDOW)  # 3:55pm: too late
    assert ov.in_window(datetime(2026, 10, 22, 13, 15, tzinfo=timezone.utc), ov.SELL_WINDOW)     # 9:15am
    assert not ov.in_window(datetime(2026, 10, 24, 13, 15, tzinfo=timezone.utc), ov.SELL_WINDOW)  # Saturday
    with pytest.raises(RuntimeError):
        ov.same_account_guard("PA123", "PA123")
    ov.same_account_guard("PA999", "PA123")
    assert abs(ov.fill_cost("buy", 100.05, 100.0) - 0.0005) < 1e-12
    assert abs(ov.fill_cost("sell", 99.95, 100.0) - 0.0005) < 1e-12


def test_auction_orders_need_whole_shares():
    from ai_desk.broker.alpaca import AlpacaPaper
    b = AlpacaPaper(key_id="PKTEST", secret="x")
    with pytest.raises(ValueError):
        b.submit_market_order("A", 1.5, "buy", time_in_force="cls")
    with pytest.raises(RuntimeError):
        AlpacaPaper(key_env=("NO_SUCH_KEY_1", "NO_SUCH_KEY_2"), require_keys=True)
