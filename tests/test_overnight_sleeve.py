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


def test_plan_buys_uses_the_sleeve_share_capped_by_cash():
    # 30% of $100k = $30k over 2 picks, but only $20k cash (less a 1% buffer) is free: $19k / 2 each
    orders = ov.plan_buys(["A", "B"], 100_000, 20_000, {"A": 100.0, "B": 7.0}, book_open=False)
    assert [o["qty"] for o in orders] == [95, 1357]
    assert ov.plan_buys(["A"], 100_000, 50_000, {"A": 100.0}, book_open=False)[0]["qty"] == 300
    assert ov.plan_buys(["A"], 100_000, 50_000, {"A": 100.0}, book_open=True) == []    # last night's shares unsold


def test_net_with_desk_sells_the_overnight_shares_inside_the_desks_own_order():
    prices = pd.Series({"MU": 100.0, "LITE": 50.0, "KO": 60.0})
    targets = pd.Series({"MU": 0.02, "KO": 0.02})              # desk: 2% MU (momentum, locked), 2% KO
    positions = {"MU": 50.0, "LITE": 30.0, "KO": 33.0}          # MU: 20 desk + 30 overnight; LITE overnight only
    book = {"MU": 30.0, "LITE": 30.0}
    t, fz = ov.net_with_desk(targets, positions, book, prices, 100_000, frozen={"MU", "KO"})
    assert t["LITE"] == 0.0                                    # sold entirely
    assert abs(t["MU"] - 20 * 100 / 100_000) < 1e-12           # keep the desk's 20 shares, sell the overnight 30
    assert "MU" not in fz and "KO" in fz                       # MU unfrozen only so its overnight part can go


def test_windows_and_fill_cost():
    assert ov.in_window(datetime(2026, 10, 21, 19, 40, tzinfo=timezone.utc), ov.BUY_WINDOW)      # 3:40pm New York
    assert not ov.in_window(datetime(2026, 10, 21, 19, 55, tzinfo=timezone.utc), ov.BUY_WINDOW)  # 3:55pm: too late
    assert abs(ov.fill_cost("buy", 100.05, 100.0) - 0.0005) < 1e-12
    assert abs(ov.fill_cost("sell", 99.95, 100.0) - 0.0005) < 1e-12


def test_book_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(ov, "BOOK", tmp_path / "book.json")
    monkeypatch.setattr(ov, "DIR", tmp_path / "journal")
    ov._append("orders.jsonl", {"kind": "buy_moc", "date": "2026-10-22", "symbol": "MU", "qty": 30, "order_id": "x1"})

    class B:
        def get_order(self, oid):
            return {"filled_qty": "30", "status": "filled"}
    assert ov.confirm_book(B(), "2026-10-22") == {"MU": 30.0}
    assert not ov.book_open("2026-10-22")                     # same day: the evening run will sell it
    assert ov.book_open("2026-10-23")                         # next day, never sold: block new buys
    ov.mark_sold({"MU": 30.0}, {"MU": "s1"}, "2026-10-22")
    assert not ov.book_open("2026-10-23")
    assert ov.confirm_book(B(), "2026-10-23") == {}           # nothing bought that day


def test_auction_orders_need_whole_shares():
    from ai_desk.broker.alpaca import AlpacaPaper
    b = AlpacaPaper(key_id="PKTEST", secret="x")
    with pytest.raises(ValueError):
        b.submit_market_order("A", 1.5, "buy", time_in_force="cls")


def test_desk_swap_drops_spy_momentum_from_the_activation_date_without_rescaling():
    from ai_desk.portfolio import methods as m
    sw = {"from": "2026-11-10", "share": 0.3}
    before = dict(m.preset("desk", pd.Timestamp("2026-11-09"), swap=sw))
    after = dict(m.preset("desk", pd.Timestamp("2026-11-10"), swap=sw))
    assert "index_momentum" in before and after == {"quality_screen": 0.5, "momentum": 0.2}
