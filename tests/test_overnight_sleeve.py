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


def test_desk_swap_drops_spy_momentum_and_rescales_from_the_activation_date():
    from ai_desk.portfolio import methods as m
    sw = {"from": "2026-11-10", "share": 0.3}
    before = dict(m.preset("desk", pd.Timestamp("2026-11-09"), swap=sw))
    after = dict(m.preset("desk", pd.Timestamp("2026-11-10"), swap=sw))
    assert "index_momentum" in before and "index_momentum" not in after
    assert abs(after["quality_screen"] - 0.5 / 0.7) < 1e-12 and abs(after["momentum"] - 0.2 / 0.7) < 1e-12
    assert dict(m.preset("desk", pd.Timestamp("2026-11-10"), swap=None)) == dict(m.PRESETS["desk"])


def test_one_off_resize_unfreezes_locked_holdings_once(tmp_path, monkeypatch):
    import json
    from ai_desk.portfolio import methods as m
    lock = tmp_path / "overnight_live.json"
    monkeypatch.setattr(m, "OVERNIGHT_SWAP", lock)
    lock.write_text(json.dumps({"from": "2020-01-01", "share": 0.3, "rescaled": False}))
    b = m.build(["desk"])
    assert b.unfreeze_once and b.frozen() == set()
    assert "index_momentum" not in [p.name for p, _ in b.parts]
    b.parts = []                                   # don't touch the real sleeves' locks in a test
    b.on_executed()
    assert json.loads(lock.read_text())["rescaled"] is True
    assert not m.build(["desk"]).unfreeze_once


def test_combined_equity_has_no_jump_when_the_overnight_account_joins():
    from ai_desk.scorecard import combine_accounts
    idx = pd.bdate_range("2026-11-02", periods=4)
    desk = pd.Series([100.0, 101.0, 101.0, 102.0], index=idx)
    ovn = pd.Series([np.nan, 43.0, 44.0, 44.0], index=idx)       # joins on day 2
    eq = combine_accounts(desk, ovn)
    assert abs(eq.iloc[1] / eq.iloc[0] - 1.01) < 1e-12           # day 2: only the desk's +1%
    assert abs(eq.iloc[2] / eq.iloc[1] - (1 + 1 / 144)) < 1e-12  # day 3: +1 on 101 + 43
    assert ov.target_equity(100_000) == pytest.approx(42_857.14, abs=0.01)
