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
    assert [o["qty"] for o in orders] == [95, 1357]                 # leftover $1 buys nothing more
    # whole shares: a $900 stock on a $1,500 slice gets one share, then the leftover tops up the most underweight
    o2 = ov.plan_buys(["X", "Y"], 10_000, 10_000, {"X": 900.0, "Y": 100.0}, book_open=False, share=0.3)
    spent = sum(o["notional"] for o in o2)
    assert spent <= 0.3 * 10_000 and 0.3 * 10_000 - spent < 100   # within one cheap share of the budget
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
    assert ov.in_window(datetime(2026, 10, 21, 19, 56, tzinfo=timezone.utc), ov.BUY_WINDOW)      # 3:56pm New York
    assert not ov.in_window(datetime(2026, 10, 21, 19, 32, tzinfo=timezone.utc), ov.BUY_WINDOW)  # 3:32pm: too early
    assert ov.in_window(datetime(2026, 10, 21, 19, 59, tzinfo=timezone.utc), ov.BUY_WINDOW)      # 3:59pm: last minute
    assert not ov.in_window(datetime(2026, 10, 21, 20, 0, tzinfo=timezone.utc), ov.BUY_WINDOW)   # 4pm: closed
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
    ov._append("orders.jsonl", {"kind": "buy_mkt", "date": "2026-10-24", "symbol": "LRCX", "qty": 6, "order_id": "x2"})
    assert ov.confirm_book(B(), "2026-10-24") == {"LRCX": 30.0}   # market buys near the close count too


def test_auction_orders_need_whole_shares():
    from ai_desk.broker.alpaca import AlpacaPaper
    b = AlpacaPaper(key_id="PKTEST", secret="x")
    with pytest.raises(ValueError):
        b.submit_market_order("A", 1.5, "buy", time_in_force="cls")


def test_desk_swap_drops_spy_momentum_from_the_activation_date_without_rescaling():
    from ai_desk.portfolio import methods as m
    sw = {"from": "2026-10-23", "share": 0.3}            # both dates before the desk was rearranged (c52ce018)
    before = dict(m.preset("desk", pd.Timestamp("2026-10-22"), swap=sw))
    after = dict(m.preset("desk", pd.Timestamp("2026-10-23"), swap=sw))
    assert "index_momentum" in before and after == {"quality_screen": 0.5, "momentum": 0.2}


def test_a_ranking_saved_the_evening_before_is_used_only_for_its_own_close():
    ov.DIR.mkdir(parents=True, exist_ok=True)
    (ov.DIR / "scan_cache.json").write_text('{"ref_date": "2026-10-30", "picks": ["A"], "rows": [], "latest_price": {}}')
    assert ov._cached_scan(pd.Timestamp("2026-10-30"))["picks"] == ["A"]
    assert ov._cached_scan(pd.Timestamp("2026-11-02")) is None


def test_regime_flags_spy_trend_and_a_bad_day_for_the_picks():
    up = pd.Series(np.linspace(100, 200, 250))
    assert ov.regime_flags(up, 0.0) == []
    down = pd.concat([up, pd.Series([140.0])], ignore_index=True)     # today well below the 200-day average
    assert "200-day" in ov.regime_flags(down, 0.0)[0]
    flags = ov.regime_flags(up, -0.025)                               # picks down 2.5% since the open, cut-off 1.9%
    assert len(flags) == 1 and "picks are down" in flags[0]
    assert ov.regime_flags(up, -0.010) == []
    assert ov.regime_flags(up.iloc[:50], None) == []                  # not enough history, no prices: no flags


def test_picks_day_return_is_open_to_now_and_drops_bad_data():
    opens = pd.Series({"A": 100.0, "B": 50.0, "C": 10.0})
    now = pd.Series({"A": 97.0, "B": 49.0, "C": 30.0})                # C +200%: bad data
    assert abs(ov.picks_day_return(opens, now) - (-0.03 - 0.02) / 2) < 1e-12
    assert ov.picks_day_return(pd.Series(dtype=float), pd.Series(dtype=float)) is None


def test_buy_stays_in_cash_when_a_check_fires(monkeypatch):
    monkeypatch.setattr(ov, "swap_active", lambda t=None: True)
    monkeypatch.setattr(ov, "check_regime", lambda *a, **k: {"cash": True, "reasons": ["SPY below its 200-day average"]})
    monkeypatch.setattr(ov, "latest_prices", lambda syms: {s: 100.0 for s in syms})
    ov.LOCK.write_text('{"picked_on": "2026-10-21", "ref_date": "2026-10-20", "picks": ["MU", "LRCX"], "rows": []}')

    class B:
        def account(self):
            return {"equity": "100000", "cash": "30000", "account_number": "PA1"}

        def clock(self):
            return {"is_open": True}

        def submit_market_order(self, *a, **k):
            raise AssertionError("no orders on a cash night")
    out = ov.buy(execute=True, now=datetime(2026, 10, 23, 19, 56, tzinfo=timezone.utc), broker=B())
    assert out["sent"] == 0 and "in cash tonight" in out["blocked"]


def test_v2_ranks_on_the_12_month_return_and_repicks_daily():
    idx = pd.bdate_range("2025-01-01", periods=260)
    adj = pd.DataFrame({"A": np.linspace(100, 200, 260), "B": np.linspace(100, 110, 260)}, index=idx)
    r = ov.twelve_month_return(adj)
    assert np.isnan(r.iloc[251]["A"]) and abs(r.iloc[-1]["A"] - (200 / adj["A"].iloc[-253] - 1)) < 1e-12
    cut = ov.twelve_month_return(adj.iloc[:255])                       # no lookahead: same values on the shorter history
    assert np.allclose(cut.iloc[-1], r.iloc[254])
    lock = {"ref_date": "2026-10-22", "picks": ["A"]}
    assert ov.repick_due(lock, pd.Timestamp("2026-10-23")) and not ov.repick_due(lock, pd.Timestamp("2026-10-22"))
    assert ov.new_month(lock, "2026-11-02") and not ov.new_month(lock, "2026-10-23")


def test_buy_uses_the_evening_ranking_only_if_newer_than_the_picks():
    ov.DIR.mkdir(parents=True, exist_ok=True)
    (ov.DIR / "scan_cache.json").write_text('{"ref_date": "2026-10-23", "picks": ["B"], "rows": [], "latest_price": {}}')
    assert ov._newer_ranking({"ref_date": "2026-10-22"}, "2026-10-26")["picks"] == ["B"]   # Monday, after a Friday rank
    assert ov._newer_ranking({"ref_date": "2026-10-23"}, "2026-10-26") is None              # already held
    assert ov._newer_ranking({"ref_date": "2026-10-22"}, "2026-10-23") is None              # ranked on today: not yet


def test_opg_group_takes_half_of_the_overnight_only_holdings():
    book = {f"S{i}": 10.0 for i in range(40)} | {"MIX": 5.0, "FRAC": 2.5}
    pos = {s: q for s, q in book.items()} | {"MIX": 12.0}            # MIX: the desk holds more than the sleeve's 5
    targets = pd.Series({"KEEP": 0.02})
    g = ov.opg_group(book, pos, targets, "2026-10-27")
    assert "MIX" not in g and "FRAC" not in g and 10 <= len(g) <= 30  # a coin-flip half of the 40
    assert g == ov.opg_group(book, pos, targets, "2026-10-27")        # fixed for the day
    assert g != ov.opg_group(book, pos, targets, "2026-10-28")        # and different the next


def test_market_on_open_sales_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(ov, "BOOK", tmp_path / "book.json")
    monkeypatch.setattr(ov, "OPG_TEST", True)                         # the flow as it ran during the test
    ov.BOOK.write_text('{"date": "2026-10-26", "holdings": {"A": 3.0, "B": 2.0}, "costs": {"A": 10.0}, "sell_sent": true}')
    ov.queue_opg({"A": 3.0}, "2026-10-26")
    sent = []

    class B:
        def submit_market_order(self, sym, qty, side, time_in_force="day"):
            sent.append((sym, qty, side, time_in_force))
            return {"id": "o1"}

        def get_order(self, oid):
            return {"status": "canceled", "filled_qty": "1"}
    late = ov.open_sell(execute=True, now=datetime(2026, 10, 27, 13, 40, tzinfo=timezone.utc), broker=B())  # 9:40am
    assert late["sent"] == 0 and "9:28" in late["blocked"] and not sent
    out = ov.open_sell(execute=True, now=datetime(2026, 10, 27, 13, 5, tzinfo=timezone.utc), broker=B())    # 9:05am
    assert out["sent"] == 1 and sent == [("A", 3, "sell", "opg")]
    assert ov.open_sell(execute=True, now=datetime(2026, 10, 27, 13, 6, tzinfo=timezone.utc), broker=B())["sent"] == 0
    assert ov.unsold_opg(B()) == {"A": 2.0}                           # the auction sold 1 of 3: 2 go out tonight
    assert ov.unsold_opg(B()) == {}                                   # counted once


def test_market_on_open_test_is_off_after_amendment_e43f2959_was_rejected(tmp_path, monkeypatch):
    assert ov.OPG_TEST is False
    monkeypatch.setattr(ov, "BOOK", tmp_path / "book.json")
    ov.BOOK.write_text('{"date": "2026-10-29", "holdings": {"A": 3.0}, "opg_pending": {"A": 3.0}}')
    sent = []

    class B:
        def submit_market_order(self, *a, **k):
            sent.append(a)
            return {"id": "x"}
    out = ov.open_sell(execute=True, now=datetime(2026, 10, 30, 13, 5, tzinfo=timezone.utc), broker=B())
    assert out["sent"] == 0 and "ended" in out["blocked"] and not sent


def test_opg_ab_compares_like_with_like():
    fills = [{"kind": "sell_opg", "fill_date": "2026-10-27", "qty": 10, "filled_qty": 10, "cost": 0.0005},
             {"kind": "sell_opg", "fill_date": "2026-10-27", "qty": 10, "filled_qty": 5, "cost": 0.0015},
             {"kind": "sell_open", "fill_date": "2026-10-27", "qty": 4, "filled_qty": 4, "cost": 0.005},
             {"kind": "sell_open", "fill_date": "2026-10-27", "qty": 4, "filled_qty": 9, "cost": 0.02},   # shared order
             {"kind": "sell_open", "fill_date": "2026-10-26", "qty": 4, "filled_qty": 4, "cost": 0.01}]   # before the test
    ab = ov.opg_ab(fills)
    assert abs(ab["opg_cost"] - 0.001) < 1e-12 and abs(ab["market_cost"] - 0.005) < 1e-12
    assert ab["market_sales"] == 1 and abs(ab["opg_fill_rate"] - 0.75) < 1e-12


def test_official_line_pairs_each_buy_with_its_next_sale():
    from ai_desk.overnight import official_line
    fills = [
        {"side": "buy", "symbol": "AA", "fill_date": "2026-10-21", "fill": 100.2, "filled_qty": 10, "official": 100.0},
        {"side": "sell", "symbol": "AA", "fill_date": "2026-10-22", "fill": 100.5, "filled_qty": 10, "official": 101.0},
        {"side": "buy", "symbol": "BB", "fill_date": "2026-10-21", "fill": 50.0, "filled_qty": 4, "official": 50.0},
        {"side": "sell", "symbol": "BB", "fill_date": "2026-10-22", "fill": None, "filled_qty": 0, "official": 49.0},
        {"side": "buy", "symbol": "AA", "fill_date": "2026-10-22", "fill": 101.0, "filled_qty": 5, "official": 101.0},
    ]
    r = official_line(fills)
    assert r["totals"]["nights"] == 1 and r["nights"][0]["stocks"] == 1      # BB unsold (no fill); AA 10-22 still held
    n = r["nights"][0]
    assert n["paper"] == round(10 * (100.5 - 100.2), 2) and n["official"] == 10.0
    assert r["totals"]["difference"] == round(10.0 - 3.0, 2)
