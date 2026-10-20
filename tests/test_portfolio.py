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
