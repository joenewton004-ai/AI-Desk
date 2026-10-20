import numpy as np
import pandas as pd
import pytest

from ai_desk.data import load_many
from ai_desk.portfolio import executor
from ai_desk.portfolio.backtest import run_portfolio_backtest
from ai_desk.portfolio.executor import Limits, plan_orders
from ai_desk.portfolio.methods import METHODS, PairsMethod, build

PRICES = pd.Series({"AAA": 100.0, "BBB": 50.0, "CCC": 20.0})


def by_symbol(plan):
    return {(o.symbol, o.side): o for o in plan.orders}


def test_plan_opens_resizes_and_closes():
    plan = plan_orders(pd.Series({"AAA": 0.10, "BBB": 0.05}), {"BBB": 300, "CCC": 50}, PRICES, 100_000)
    o = by_symbol(plan)
    assert o[("AAA", "buy")].qty == 100                  # 10% of 100k / $100
    assert o[("BBB", "sell")].qty == 200                 # 300 -> 100 shares (5%)
    assert o[("CCC", "sell")].qty == 50                  # not a target any more: close it
    assert [x.side for x in plan.orders] == ["sell", "sell", "buy"]   # sells first


def test_tiny_resizes_skipped_but_closes_always_trade():
    plan = plan_orders(pd.Series({"AAA": 0.10}), {"AAA": 98, "CCC": 1}, PRICES, 100_000)
    assert [(o.symbol, o.qty) for o in plan.orders] == [("CCC", 1)]


def test_limits_cap_positions_and_drop_shorts_when_disabled():
    plan = plan_orders(pd.Series({"AAA": 0.40, "BBB": -0.05}), {}, PRICES, 100_000, Limits(max_position=0.10))
    assert by_symbol(plan)[("AAA", "buy")].qty == 100
    assert ("BBB", "sell") not in by_symbol(plan)
    assert any("shorting disabled" in n for n in plan.notes) and any("capped" in n for n in plan.notes)


def test_gross_exposure_scaled_down():
    t = pd.Series({"AAA": 0.10, "BBB": 0.10, "CCC": 0.10})
    plan = plan_orders(t, {}, PRICES, 100_000, Limits(max_gross=0.15))
    assert sum(o.notional for o in plan.orders) <= 15_000 + 1


def test_long_to_short_flip_is_two_orders_and_needs_shortable():
    lim = Limits(allow_short=True)
    plan = plan_orders(pd.Series({"AAA": -0.05}), {"AAA": 20}, PRICES, 100_000, lim, shortable={"AAA": False})
    assert [(o.side, o.qty, bool(o.blocked)) for o in plan.orders] == [("sell", 20, False), ("sell", 50, True)]


def test_oversized_order_blocked():
    plan = plan_orders(pd.Series({"AAA": 0.10}), {}, PRICES, 100_000, Limits(max_order=0.05))
    assert plan.orders[0].blocked and not plan.sendable


def test_missing_price_leaves_position_alone():
    plan = plan_orders(pd.Series({"ZZZ": 0.10}), {"ZZZ": 5}, PRICES, 100_000)
    assert not plan.orders and any("no price" in n for n in plan.notes)


@pytest.fixture
def prices():
    return load_many(["AA", "BB", "CC", "DD"], source="synthetic")


@pytest.mark.parametrize("spec, params", [
    ("index_momentum", {"symbol": "AA"}),
    ("index_rotation", {"symbols": "AA,BB,CC,DD", "top": 2}),
    ("index_rotation", {"symbols": "AA,BB,CC,DD", "drop_worst": 1, "weighting": "rank", "lookbacks": "63,126,252"}),
    ("sma_crossover", {"symbols": "AA,BB"}),
    ("pairs", {"pairs": "AA/BB,CC/DD"}),
    ("pairs", {"pairs": "AA/BB", "mode": "long_only"}),
])
def test_methods_have_no_lookahead(prices, spec, params):
    m = build([spec], params)
    closes = prices["close"][m.symbols()]
    cut = 1000
    future = closes.copy()
    future.iloc[cut:] *= np.linspace(0.5, 2.0, len(closes) - cut)[:, None]
    pd.testing.assert_frame_equal(m.weights(closes).iloc[:cut], m.weights(future).iloc[:cut])


def test_pairs_are_dollar_neutral_and_long_only_never_shorts(prices):
    ls = PairsMethod(pairs="AA/BB,CC/DD").weights(prices["close"])
    assert ls.sum(axis=1).abs().max() < 1e-12 and ls.abs().sum(axis=1).max() > 0
    lo = PairsMethod(pairs="AA/BB,CC/DD", mode="long_only").weights(prices["close"])
    assert (lo >= 0).all().all() and lo.sum(axis=1).max() <= 1 + 1e-12


def test_blend_and_switcher():
    b = build(["sma_crossover:0.3", "index_momentum:0.7"], {"symbols": "AA", "index_momentum.symbol": "BB"})
    assert b.symbols() == ["AA", "BB"]
    assert "30%" in b.describe() and "70%" in b.describe()
    with pytest.raises(ValueError):
        build(["sma_crossover:0.8", "index_momentum:0.8"])
    with pytest.raises(ValueError):
        build(["nope"])
    with pytest.raises(ValueError):
        build(["pairs"], {"pairs.bogus": 1})
    assert set(METHODS) >= {"index_momentum", "sma_crossover", "pairs", "quality_screen"}


def test_backtest_runs_with_shorts_and_charges_borrow(prices):
    m = PairsMethod(pairs="AA/BB")
    cheap = run_portfolio_backtest(m, prices, borrow_fee=0.0)
    dear = run_portfolio_backtest(m, prices, borrow_fee=0.05)
    assert dear.equity.iloc[-1] < cheap.equity.iloc[-1]


class FakeBroker:
    def __init__(self, positions=None, pending=False):
        self._pos, self.pending, self.sent = positions or {}, pending, []

    def account(self):
        return {"equity": "100000"}

    def positions(self):
        return self._pos

    def open_orders(self, symbol=None):
        return [{"id": "x"}] if self.pending else []

    def asset(self, symbol):
        return {"shortable": True}

    def submit_market_order(self, symbol, qty, side):
        self.sent.append((symbol, qty, side))
        return {"id": f"o{len(self.sent)}"}


def test_executor_run_dry_then_execute(tmp_path, monkeypatch):
    monkeypatch.setattr(executor, "JOURNAL", tmp_path / "journal.csv")
    m = build(["sma_crossover"], {"symbols": "AA,BB"})
    broker = FakeBroker()
    plan = executor.run(m, source="synthetic", max_data_age_days=None, broker=broker)
    assert not broker.sent and (tmp_path / "journal.csv").exists()
    executor.run(m, execute=True, source="synthetic", max_data_age_days=None, broker=broker)
    assert len(broker.sent) == len(plan.sendable)


def test_executor_refuses_to_stack_on_pending_orders(tmp_path, monkeypatch):
    monkeypatch.setattr(executor, "JOURNAL", tmp_path / "journal.csv")
    broker = FakeBroker(pending=True)
    plan = executor.run(build(["sma_crossover"], {"symbols": "AA"}), execute=True, source="synthetic",
                        max_data_age_days=None, broker=broker)
    assert not broker.sent and all(o.blocked for o in plan.orders)


def test_index_funds_get_their_own_cap():
    prices = pd.Series({"SPY": 500.0, "AAA": 100.0})
    plan = plan_orders(pd.Series({"SPY": 0.50, "AAA": 0.50}), {}, prices, 100_000)
    o = by_symbol(plan)
    assert o[("SPY", "buy")].qty == 100 and not o[("SPY", "buy")].blocked      # 50% allowed for SPY
    assert o[("AAA", "buy")].qty == 100                                         # stock capped at 10%


def test_fractional_longs_whole_shorts_and_non_fractionable():
    prices = pd.Series({"LLY": 1240.0, "AAA": 100.0, "BBB": 50.0})
    plan = plan_orders(pd.Series({"LLY": 0.02, "AAA": -0.05, "BBB": 0.0333}), {}, prices, 100_000,
                       Limits(allow_short=True), shortable={"AAA": True}, fractionable={"LLY": True, "BBB": False})
    o = by_symbol(plan)
    assert o[("LLY", "buy")].qty == pytest.approx(1.6129)           # $2,000 / $1,240, 4 dp, rounded down
    assert o[("AAA", "sell")].qty == 50                             # short: whole shares
    assert o[("BBB", "buy")].qty == 66                              # not fractionable: whole shares
    whole = plan_orders(pd.Series({"LLY": 0.02}), {}, prices, 100_000, Limits(fractional=False))
    assert whole.orders[0].qty == 1


def test_fractional_position_closes_exactly():
    plan = plan_orders(pd.Series(dtype=float), {"LLY": 1.6129}, pd.Series({"LLY": 1240.0}), 100_000)
    assert plan.orders[0].side == "sell" and plan.orders[0].qty == pytest.approx(1.6129)


def test_qty_formatting_for_the_api():
    from ai_desk.broker.alpaca import format_qty

    assert format_qty(12) == "12" and format_qty(1.6129) == "1.6129" and format_qty(0.0001) == "0.0001"


def test_live_keys_refused(monkeypatch):
    from ai_desk.broker.alpaca import AlpacaPaper

    with pytest.raises(RuntimeError, match="LIVE"):
        AlpacaPaper(key_id="AKXXXX", secret="s")
    assert AlpacaPaper(key_id="PKXXXX", secret="s").key_id == "PKXXXX"
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    monkeypatch.setattr("ai_desk.broker.alpaca.load_dotenv", lambda *a, **k: None)
    injected = AlpacaPaper()                      # cloud: keys added by the network secret
    assert injected.injected and "APCA-API-KEY-ID" not in injected.session.headers


def test_cash_buffer_scales_full_investment_to_99_percent():
    prices = pd.Series({"SPY": 500.0, "AAA": 100.0})
    plan = plan_orders(pd.Series({"SPY": 0.50, "AAA": 0.50}), {}, prices, 100_000,
                       Limits(max_position=0.5))
    assert sum(o.notional for o in plan.orders) == pytest.approx(99_000, abs=1)
    assert any("cash buffer" in n for n in plan.notes)
    small = plan_orders(pd.Series({"AAA": 0.50}), {}, prices, 100_000, Limits(max_position=0.5))
    assert small.orders[0].notional == pytest.approx(50_000)          # under 99%: untouched


# --- quarterly lock for the stock screen -------------------------------------------------

def _screen(tmp_path, picks, date=None):
    date = date or pd.Timestamp.today().date()
    pd.DataFrame({"score": range(len(picks), 0, -1)}, index=pd.Index(picks, name="symbol")) \
        .to_csv(tmp_path / f"screen_{date}.csv")


def _qs(tmp_path, **kw):
    from ai_desk.portfolio.methods import QualityScreen

    return QualityScreen(top=3, screen_glob=str(tmp_path / "screen_*.csv"),
                         lock_path=str(tmp_path / "lock.json"), **kw)


def _write_lock(tmp_path, picks, days_ago):
    import json

    (tmp_path / "lock.json").write_text(json.dumps({
        "picks": picks, "screen_file": "screen_old.csv",
        "locked_on": str((pd.Timestamp.today() - pd.Timedelta(days=days_ago)).date())}))


def test_first_pick_locks_only_after_execution(tmp_path):
    _screen(tmp_path, ["AAA", "BBB", "CCC", "DDD"])
    m = _qs(tmp_path)
    assert m.symbols() == ["AAA", "BBB", "CCC"] and m.frozen() == set()
    assert not (tmp_path / "lock.json").exists()          # a dry run commits to nothing
    m.on_executed()
    assert (tmp_path / "lock.json").exists()


def test_between_repicks_holds_locked_stocks_even_without_a_fresh_screen(tmp_path):
    _write_lock(tmp_path, ["AAA", "BBB", "CCC"], days_ago=30)
    m = _qs(tmp_path)                                      # no screen file at all
    assert m.symbols() == ["AAA", "BBB", "CCC"] and m.frozen() == {"AAA", "BBB", "CCC"}
    assert "next re-pick due" in m.status()[0]


def test_quarterly_repick_reports_changes_and_needs_a_fresh_screen(tmp_path):
    _write_lock(tmp_path, ["AAA", "BBB", "CCC"], days_ago=100)
    with pytest.raises(RuntimeError, match="re-pick is due"):
        _qs(tmp_path).symbols()
    _screen(tmp_path, ["AAA", "DDD", "EEE"])
    m = _qs(tmp_path)
    assert m.symbols() == ["AAA", "DDD", "EEE"] and m.frozen() == set()
    assert "selling BBB, CCC; buying DDD, EEE" in m.status()[0]


def test_forced_rebalance(tmp_path):
    _write_lock(tmp_path, ["AAA", "BBB", "CCC"], days_ago=10)
    _screen(tmp_path, ["XXX", "YYY", "ZZZ"])
    assert _qs(tmp_path, rebalance=True).symbols() == ["XXX", "YYY", "ZZZ"]


def test_frozen_positions_drift_but_dropped_ones_still_close():
    prices = pd.Series({"AAA": 100.0, "BBB": 100.0})
    plan = plan_orders(pd.Series({"AAA": 0.10}), {"AAA": 150, "BBB": 10}, prices, 100_000, frozen={"AAA"})
    assert [(o.symbol, o.side) for o in plan.orders] == [("BBB", "sell")]   # AAA (15%) left to drift


# --- weekly bottleneck sleeve ----------------------------------------------------------------

def _bn(tmp_path, **kw):
    from ai_desk.portfolio.methods import Bottleneck

    return Bottleneck(top=3, screen_glob=str(tmp_path / "bottleneck_*.csv"),
                      lock_path=str(tmp_path / "bn.json"), **kw)


def _bn_scan(tmp_path, picks):
    pd.DataFrame({"score": range(len(picks), 0, -1)}, index=pd.Index(picks, name="symbol")) \
        .to_csv(tmp_path / f"bottleneck_{pd.Timestamp.today().date()}.csv")


def _trend_closes(down=("CCC",)):
    idx = pd.bdate_range(end=pd.Timestamp.today(), periods=300)
    up = np.linspace(100, 200, 300)
    data = {s: (up[::-1] if s in down else up) * (1 + 0.01 * np.sin(np.arange(300) * (i + 1)))
            for i, s in enumerate(["AAA", "BBB", "CCC"])}
    return pd.DataFrame(data, index=idx)


def test_bottleneck_inverse_vol_weights_capped(tmp_path):
    _bn_scan(tmp_path, ["AAA", "BBB", "CCC"])
    closes = _trend_closes(down=())
    w = _bn(tmp_path).latest(closes)
    assert w.sum() == pytest.approx(1.0) and w.max() <= 2 / 3 + 1e-9
    assert w["AAA"] > w["CCC"]               # AAA wiggles least, so it gets the biggest share


def test_bottleneck_exit_below_moving_average(tmp_path):
    _bn_scan(tmp_path, ["AAA", "BBB", "CCC"])
    m = _bn(tmp_path)
    w = m.latest(_trend_closes(down=("CCC",)))
    assert w["CCC"] == 0 and w["AAA"] > 0                # CCC is falling: below its 200-day average
    assert any("below its moving average" in n for n in m.status())


def test_bottleneck_repicks_weekly_and_exits_stay_out(tmp_path):
    import json

    (tmp_path / "bn.json").write_text(json.dumps({
        "picks": ["AAA", "BBB", "CCC"], "screen_file": "x", "weights": {"AAA": .4, "BBB": .3, "CCC": .3},
        "locked_on": str((pd.Timestamp.today() - pd.Timedelta(days=3)).date())}))
    m = _bn(tmp_path)
    closes = _trend_closes(down=("CCC",))
    assert m.latest(closes)["CCC"] == 0 and m.frozen() == {"AAA", "BBB"}
    m.on_executed()                                       # the sale went through: remember it
    again = _bn(tmp_path)
    assert again.latest(_trend_closes(down=()))["CCC"] == 0      # bounced, but stays out until re-pick
    (tmp_path / "bn.json").write_text(json.dumps({
        "picks": ["AAA"], "screen_file": "x", "locked_on": str((pd.Timestamp.today() - pd.Timedelta(days=8)).date())}))
    _bn_scan(tmp_path, ["BBB", "CCC", "AAA"])
    assert "re-pick due" in _bn(tmp_path).status()[0]    # a week later: fresh picks


def test_desk_preset():
    m = build(["desk"])
    assert [(p.name, w) for p, w in m.parts] == [("quality_screen", 0.5), ("bottleneck", 0.2), ("index_momentum", 0.3)]


def test_bottleneck_exit_uses_the_scans_moving_average(tmp_path):
    pd.DataFrame({"score": [3, 2, 1], "ma_days": 100}, index=pd.Index(["AAA", "BBB", "CCC"], name="symbol")) \
        .to_csv(tmp_path / f"bottleneck_{pd.Timestamp.today().date()}.csv")
    m = _bn(tmp_path)
    m.symbols()
    assert m._ma_days() == 100
    assert _bn(tmp_path, exit_ma=50)._ma_days() == 50          # explicit override wins


def test_index_rotation_holds_the_strongest_with_positive_momentum():
    idx = pd.bdate_range("2020-01-01", periods=600)
    up = pd.Series(np.linspace(100, 200, 600), index=idx)
    closes = pd.DataFrame({"UP": up, "FLAT": up * 0 + 100 + np.arange(600) * 0.01, "DOWN": up[::-1].to_numpy()},
                          index=idx)
    m = build(["index_rotation"], {"symbols": "UP,FLAT,DOWN", "top": 2})
    w = m.weights(closes).iloc[-1]
    assert w["UP"] == 0.5 and w["FLAT"] == 0.5 and w["DOWN"] == 0
    assert m.rationale("UP")["rank"] == 1 and "switch off" in m.exit_reason("DOWN")
    # avoid the worst: hold all but the weakest, the leader gets the biggest slice
    r = build(["index_rotation"], {"symbols": "UP,FLAT,DOWN", "drop_worst": 1, "weighting": "rank"})
    w = r.weights(closes).iloc[-1]
    assert abs(w["UP"] - 2 / 3) < 1e-12 and abs(w["FLAT"] - 1 / 3) < 1e-12 and w["DOWN"] == 0
    assert "weakest" in r.exit_reason("DOWN") or "switch off" in r.exit_reason("DOWN")
    one = build(["index_rotation"], {"symbols": "UP", "top": 1}).weights(closes)["UP"]
    spy = build(["index_momentum"], {"symbol": "UP"}).weights(closes)["UP"]
    pd.testing.assert_series_equal(one, spy, check_names=False)


def test_limit_price_is_capped_and_rounded_to_cents():
    from ai_desk.broker.alpaca import format_limit
    from ai_desk.portfolio.executor import limit_price
    assert limit_price(100.0, "buy", 0.02) == 102.0
    assert limit_price(33.337, "buy", 0.02) == 34.0                  # 34.00374 -> rounded DOWN, never past the cap
    assert limit_price(33.337, "sell", 0.02) == 32.68                # 32.67026 -> rounded UP for a sell
    assert limit_price(0.5, "buy", 0.02) == 0.51 and format_limit(0.51) == "0.5100"
    assert format_limit(102.0) == "102.00"


def test_repick_status_and_buy_only_cap(tmp_path, monkeypatch):
    import json
    from ai_desk.portfolio.methods import Bottleneck
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"picks": ["AA"], "screen_file": "bottleneck_2026-10-20.csv", "locked_on": "2026-10-20"}))
    (tmp_path / "bottleneck_2026-10-20.csv").write_text("symbol,score\nAA,1\n")
    m = Bottleneck(lock_path=str(lock), screen_glob=str(tmp_path / "bottleneck_*.csv"))
    early = m.repick_status(pd.Timestamp("2026-10-27"))
    assert not early["due"] and not early["needs_scan"] and early["next_repick"] == "2026-11-03"
    due = m.repick_status(pd.Timestamp("2026-11-03"))
    assert due["due"] and due["needs_scan"] and due["scan_command"].startswith("python -m ai_desk bottleneck scan")
    (tmp_path / "bottleneck_2026-11-03.csv").write_text("symbol,score\nBB,1\n")
    assert not m.repick_status(pd.Timestamp("2026-11-03"))["needs_scan"]       # today's scan is already there
