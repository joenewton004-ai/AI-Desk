import json
import pandas as pd
import pytest

from ai_desk import register, tradebook
from ai_desk.portfolio import executor
from ai_desk.portfolio.methods import build


class Broker:
    """Fake Alpaca: fills every order at a fixed price per symbol."""

    def __init__(self, prices):
        self.prices, self.pos, self.orders = prices, {}, {}

    def account(self):
        return {"equity": "100000"}

    def positions(self):
        return dict(self.pos)

    def open_orders(self, symbol=None):
        return []

    def asset(self, symbol):
        return {"shortable": True, "fractionable": True}

    def submit_market_order(self, symbol, qty, side):
        oid = f"o{len(self.orders)}"
        self.orders[oid] = {"symbol": symbol, "qty": qty, "side": side}
        self.pos[symbol] = self.pos.get(symbol, 0) + (qty if side == "buy" else -qty)
        return {"id": oid}

    def submit_limit_order(self, symbol, qty, side, limit_price):
        self.limits = getattr(self, "limits", {}) | {symbol: limit_price}
        return self.submit_market_order(symbol, qty, side)

    def get_order(self, oid):
        o = self.orders[oid]
        return {"status": "filled", "filled_avg_price": str(self.prices[o["symbol"]]),
                "filled_qty": str(o["qty"]), "filled_at": "2026-10-20T13:30:00Z"}


class Fixed:
    """A tiny method with fixed targets, so the test doesn't depend on signals."""

    def __init__(self, name, targets):
        self.name, self.t = name, pd.Series(targets)

    def latest(self, closes):
        return self.t

    def rationale(self, symbol):
        return {"why": f"{self.name} wants {symbol}"} if symbol in self.t else {}

    def exit_reason(self, symbol):
        return None if symbol in self.t else f"{self.name} dropped it"


def test_execute_records_trades_with_sleeve_and_reason(tmp_path, monkeypatch):
    from ai_desk.portfolio.methods import Blend, Method

    class Wrap(Method):
        def __init__(self, inner):
            self.inner, self.name = inner, inner.name

        def symbols(self):
            return list(self.inner.t.index)

        def weights(self, closes):
            return pd.DataFrame([self.inner.t.to_numpy()] * len(closes), index=closes.index, columns=self.inner.t.index)

        def rationale(self, symbol):
            return self.inner.rationale(symbol)

        def exit_reason(self, symbol):
            return self.inner.exit_reason(symbol)

    monkeypatch.setattr(executor, "JOURNAL", tmp_path / "plan.csv")
    m = Blend(parts=[(Wrap(Fixed("stocks", {"AA": 0.5})), 0.6), (Wrap(Fixed("index", {"BB": 1.0})), 0.4)])
    broker = Broker({"AA": 100.0, "BB": 50.0, "CC": 10.0})
    broker.pos["CC"] = 10                                  # held, but no sleeve wants it any more
    executor.run(m, execute=True, source="synthetic", max_data_age_days=None, broker=broker)
    rows = {r["symbol"]: r for r in tradebook.trades()}
    assert rows["AA"]["sleeve"] == "stocks" and rows["BB"]["sleeve"] == "index"
    assert rows["AA"]["rationale"] == {"stocks": {"why": "stocks wants AA"}}
    assert rows["CC"]["side"] == "sell" and "dropped it" in rows["CC"]["exit_reason"]
    assert tradebook.sync_fills(broker) == 3 and all(r["fill_price"] for r in tradebook.trades())

    # the plan snapshot and dashboard tables
    from ai_desk import dashboard
    plan = {r["symbol"]: r for r in tradebook._read_plan()["rows"]}
    assert plan["AA"]["sleeve"] == "stocks" and plan["CC"]["side"] == "sell"
    tradebook.add_note(rows["AA"]["id"], "bought on the screen")
    t = dashboard.tables()
    assert {r["symbol"] for r in t["trades"]} == {"AA", "BB", "CC"}
    assert next(r for r in t["trades"] if r["symbol"] == "AA")["notes"] == "bought on the screen"
    assert t["summary"][0]["trades_filled"] == 3
    assert {r["sleeve"] for r in t["sleeves"]} >= {"stocks", "index"}
    assert dashboard.export()["trades"] == 3 and (tradebook.DIR / "dashboard" / "methods.json").exists()


def _fill(sym, side, qty, price, when, sleeve="bottleneck", reason="x"):
    tradebook._append("trades.jsonl", {
        "id": f"{sym}{side}{when}", "created_utc": when, "symbol": sym, "side": side, "qty": qty,
        "sleeve": sleeve, "status": "filled", "filled_qty": qty, "fill_price": price, "filled_utc": when,
        "exit_reason": reason if side == "sell" else None, "rationale": {"score": 70}})


def test_fifo_lots_and_review():
    _fill("AAA", "buy", 10, 100.0, "2026-01-01")
    _fill("AAA", "buy", 10, 120.0, "2026-02-01")
    _fill("AAA", "sell", 15, 130.0, "2026-03-01", reason="exit rule: closed below its 100-day average")
    op, cl = tradebook.lots()
    assert list(cl["qty"]) == [10, 5] and cl["pnl"].sum() == pytest.approx(10 * 30 + 5 * 10)
    assert op["qty"].sum() == 5 and op["entry_price"].iloc[0] == 120.0
    r = tradebook.review({"AAA": 110.0})
    s = r["by_sleeve"]["bottleneck"]
    assert s["realized_pnl"] == pytest.approx(350) and s["unrealized_pnl"] == pytest.approx(5 * -10)
    assert s["win_rate"] == 1.0 and r["exit_reasons"][0]["exit_reason"] == "exit rule"


def test_notes_and_amendment_lifecycle():
    tradebook.add_note("bottleneck", "energy picks dominated after the oil spike", author="claude")
    assert tradebook.notes()[0]["author"] == "claude"
    a = register.propose("momentum", "cap any one industry at 5 of 20 picks", "too concentrated in chips")
    assert register.decide(a["id"], "testing")["status"] == "testing"
    done = register.decide(a["id"], "accepted", "backtest: Sharpe 0.60 -> 0.64")
    assert done["decided_utc"] and done["evidence"].startswith("backtest")
    with pytest.raises(ValueError):
        register.decide(a["id"], "maybe")
    reg = register.register()
    mo = next(m for m in reg["methods"] if m["name"] == "momentum")
    assert mo["in_live_mix"] and mo["allocation"] == 0.2 and mo["amendments"][0]["status"] == "accepted"
    assert mo["parameters"]["rebalance_days"] == 28
    bn = next(m for m in reg["methods"] if m["name"] == "bottleneck")
    assert not bn["in_live_mix"]                               # replaced by momentum from 2026-10-21


def test_watchlist_cohort_and_compare():
    from ai_desk import watchlist

    scan = pd.DataFrame({"symbol": ["AA", "BB", "CC", "DD"], "score": [90, 80, 70, 95], "name": list("abcd"),
                         "passes": [True, True, True, False], "rev_growth": [0.3, 0.2, 0.15, 0.05],
                         "gm_change": [0.01, 0.0, 0.02, 0.01], "above_ma": [True, True, True, True],
                         "market_cap": [5e10] * 4, "ma_days": [100] * 4})
    c = watchlist.build_cohort("bottleneck", scan, ["AA"], "2026-10-20", "2026-10-19", "x.csv", top=1)
    by = {r["symbol"]: r for r in c["rows"]}
    assert by["AA"]["status"] == "picked" and by["BB"]["status"] == "near miss" and by["BB"]["rank"] == 2
    assert by["DD"]["status"] == "failed a gate" and "revenue growth" in by["DD"]["reason"]
    idx = pd.bdate_range("2026-10-15", periods=8)
    closes = pd.DataFrame({"AA": 100.0, "BB": 100.0, "CC": 100.0, "DD": 100.0, "SPY": 100.0}, index=idx)
    closes.loc[idx[-1]] = [110, 130, 90, 100, 105]
    rows, s = watchlist.compare(c, closes)
    assert s["picks_avg"] == pytest.approx(0.10) and s["watch_beating_picks"] == 1 and s["best_symbol"] == "BB"
    assert s["spy"] == pytest.approx(0.05) and s["days"] == len(closes.loc["2026-10-19":]) - 1
    assert {r["symbol"]: r["vs_picks"] for r in rows}["BB"] == pytest.approx(0.20)
    watchlist._save([c])
    out = watchlist.review(closes, live={"bottleneck"})
    assert out["summary"][0]["current"] and len(out["rows"]) == 4
    out = watchlist.review(closes, live={"momentum"})          # a retired sleeve's cohort stays on record only
    assert not out["summary"][0]["current"] and out["rows"] == []


def test_overnight_cohort_measured_close_to_open_only():
    from ai_desk import overnight, watchlist

    idx = pd.bdate_range("2026-10-15", periods=60)
    syms = [f"S{i}" for i in range(6)]
    closes = pd.DataFrame(100.0, index=idx, columns=syms)
    volume = pd.DataFrame(1e6, index=idx, columns=syms)
    volume["S5"] = 10.0                                        # illiquid: fails the gate
    score = pd.Series([0.006, 0.005, 0.004, 0.003, 0.002, 0.009], index=syms)
    el = overnight.eligible(closes, volume).iloc[-1]
    near = overnight.near_misses(score, el, closes, volume, n=2, more=2)
    assert [r["symbol"] for r in near] == ["S2", "S3", "S5"]
    assert not near[-1]["passes"] and "trades under" in near[-1]["gate_reason"]
    lock = {"picked_on": "2026-10-20", "ref_date": "2026-10-19", "picks": ["S0", "S1"],
            "rows": [{"symbol": "S0", "score": 0.006}, {"symbol": "S1", "score": 0.005}]}
    c = watchlist.capture_overnight(lock, near)
    by = {r["symbol"]: r for r in c["rows"]}
    assert by["S0"]["status"] == "picked" and by["S2"]["status"] == "near miss" and by["S2"]["rank"] == 3
    assert by["S5"]["status"] == "failed a gate" and "trades under" in by["S5"]["reason"]
    assert watchlist.capture_overnight(lock, near) is None       # once per re-pick
    # S0 gains 2% overnight then gives it back in the day; S2 only moves in the day
    d = pd.bdate_range("2026-10-15", periods=8)
    cl = pd.DataFrame(100.0, index=d, columns=["S0", "S1", "S2", "S3", "S5", "SPY"])
    op = cl.copy()
    op.loc[d[-1], "S0"] = 102.0
    cl.loc[d[-1], "S2"] = 120.0
    rows, s = watchlist.compare(c, cl, opens=op)
    r = {x["symbol"]: x["return"] for x in rows}
    assert r["S0"] == pytest.approx(0.02) and r["S2"] == pytest.approx(0.0) and s["measure"] == "overnight"


def test_limit_cap_sends_capped_limit_orders(tmp_path, monkeypatch):
    from ai_desk.portfolio.methods import Method

    class One(Method):
        name = "one"

        def symbols(self):
            return ["AA"]

        def weights(self, closes):
            return pd.DataFrame({"AA": 0.5}, index=closes.index)

    monkeypatch.setattr(executor, "JOURNAL", tmp_path / "plan.csv")
    broker = Broker({"AA": 100.0})
    executor.run(One(), executor.Limits(limit_cap=0.02), execute=True, source="synthetic", max_data_age_days=None,
                 broker=broker)
    t = tradebook.trades()[0]
    assert t["order_type"] == "limit" and broker.limits["AA"] == t["limit_price"]
    assert t["limit_price"] <= t["est_price"] * 1.02 + 1e-9


def test_export_never_writes_nan_and_lists_empty_tables():
    import json
    import math

    from ai_desk import dashboard
    (tradebook.DIR).mkdir(parents=True, exist_ok=True)
    (tradebook.DIR / "scorecard.json").write_text(json.dumps({"desk": {"sharpe": math.nan, "days": 0}}))
    dashboard.export()
    text = (tradebook.DIR / "dashboard" / "score_headline.json").read_text()
    assert "NaN" not in text and json.loads(text)[0]["sharpe"] is None
    m = json.loads((tradebook.DIR / "dashboard" / "_manifest.json").read_text())
    assert "closed" in m["empty"] and "methods" in m["with_rows"]


def test_buy_only_cap_leaves_sells_as_market_orders(tmp_path, monkeypatch):
    from ai_desk.portfolio.methods import Method

    class Flat(Method):
        name = "flat"

        def symbols(self):
            return ["AA"]

        def weights(self, closes):
            return pd.DataFrame({"AA": 0.5}, index=closes.index)

    monkeypatch.setattr(executor, "JOURNAL", tmp_path / "plan.csv")
    broker = Broker({"AA": 100.0, "BB": 50.0})
    broker.pos["BB"] = 10                                       # not wanted: will be sold
    executor.run(Flat(), executor.Limits(limit_cap=0.02, limit_cap_side="buy"), execute=True, source="synthetic",
                 max_data_age_days=None, broker=broker)
    by = {t["symbol"]: t for t in tradebook.trades()}
    assert by["AA"]["order_type"] == "limit" and by["BB"]["order_type"] == "market"


def test_watchlist_diagnose_says_too_early_before_the_repick_and_explains_the_gap():
    from ai_desk import watchlist
    rows = ([{"symbol": f"P{i}", "status": "picked", "sector": "Energy", "score": 90 - i, "return": -0.01} for i in range(5)]
            + [{"symbol": f"N{i}", "status": "near miss", "sector": "Tech", "score": 70 - i, "return": 0.02} for i in range(10)])
    s = {"cohort": "quality_screen:x", "sleeve": "quality_screen", "asof": "2026-10-21", "days": 3,
         "picks_avg": -0.01, "near_miss_avg": 0.02}
    c = watchlist.diagnose(s, rows)
    assert c["verdict"] == "too early"
    assert abs(c["gap"] + 0.03) < 1e-9
    assert c["chance"] == 1.0                                  # every random group of 5 did at least as well
    assert c["sectors"][0]["sector"] in ("Energy", "Tech") and c["sectors"][0]["effect"] < 0
    assert c["factors"]["score"] < 0                           # higher score, lower return in this cohort
    late = watchlist.diagnose({**s, "days": 63}, rows)
    assert late["verdict"] == "worth a test"                   # a full cohort, beyond chance
    won = watchlist.diagnose({**s, "days": 63}, [{**r, "return": -r["return"]} for r in rows])
    assert won["verdict"] == "ranking held up"


def test_watchlist_daily_log_keeps_one_row_per_cohort_per_day(tmp_path, monkeypatch):
    from ai_desk import tradebook, watchlist
    monkeypatch.setattr(tradebook, "DIR", tmp_path)
    c = {"cohort": "momentum:x", "asof": "2026-11-04", "verdict": "too early", "gap": 0.01, "sectors": []}
    watchlist.log_checks([c])
    watchlist.log_checks([c, {**c, "asof": "2026-11-05"}])
    h = watchlist.daily_history()
    assert [r["asof"] for r in h] == ["2026-11-04", "2026-11-05"] and "sectors" not in h[0]


def test_open_position_kept_by_the_successor_sleeve_moves_to_it(tmp_path, monkeypatch):
    lock = tmp_path / "momentum.json"
    lock.write_text(json.dumps({"picks": ["AMD"], "locked_on": "2026-10-21"}))
    monkeypatch.setattr(tradebook, "HANDOVERS", {"bottleneck": ("momentum", lock)})
    assert tradebook.handed_over("bottleneck", "AMD") == "momentum"
    assert tradebook.handed_over("bottleneck", "COP") == "bottleneck"     # sold on the switch: stays on record
    assert tradebook.handed_over("quality_screen", "AMD") == "quality_screen"


class _M:
    def describe(self):
        return "desk"

    def exit_reason(self, s):
        return None

    def rationale(self, s):
        return {}


def test_netted_overnight_sale_is_split_by_sleeve_and_fills_shared():
    from ai_desk.portfolio.executor import Order, Plan
    tradebook._append("trades.jsonl", {"id": "q1", "created_utc": "2026-10-20T14:00:00+00:00", "symbol": "LRCX",
                                       "side": "buy", "qty": 7.0, "sleeve": "quality_screen", "fill_price": 250.0,
                                       "filled_qty": 7.0, "filled_utc": "2026-10-20T14:00:00+00:00"})
    tradebook.record_overnight_buys([{"order_id": "b1", "date": "2026-10-21", "symbol": "LRCX", "qty": 6, "ref_price": 262.0,
                                      "filled_qty": 4.0, "fill_price": 261.0, "filled_utc": "2026-10-21T19:59:57Z"}])
    tradebook.record_overnight_buys([{"order_id": "b1", "symbol": "LRCX", "filled_qty": 4.0, "fill_price": 261.0}])  # once
    sleeves = {"quality_screen": pd.Series({"LRCX": 0.012, "KO": 0.02})}
    plan = Plan(orders=[Order("LRCX", "sell", 5.0, 260.0, "resize")])  # overnight's 4 + 1 the quality sleeve trims
    rows = tradebook.record_orders(plan, _M(), sleeves, "2026-10-21", {"LRCX": {"id": "s1"}},
                                   overnight_book={"LRCX": 4.0, "KO": 2.0}, prices={"KO": 60.0})
    by = [(r["symbol"], r["side"], r["qty"], r["sleeve"], r["order_id"]) for r in rows]
    assert ("LRCX", "sell", 4.0, "overnight_drift", "s1") in by and ("LRCX", "sell", 1.0, "quality_screen", "s1") in by
    # KO: the desk kept exactly the overnight shares - no order, they change hands at the last close
    assert ("KO", "sell", 2.0, "overnight_drift", None) in by and ("KO", "buy", 2.0, None, None) in by

    class B:
        def get_order(self, oid):
            return {"status": "filled", "filled_qty": "5", "filled_avg_price": "264", "filled_at": "2026-10-22T13:30:01Z"}
    tradebook.sync_fills(B())
    sold = {(t["sleeve"], t["side"]): t for t in tradebook.trades() if t["symbol"] == "LRCX"}
    assert sold[("overnight_drift", "sell")]["filled_qty"] == pytest.approx(4.0)
    assert sold[("quality_screen", "sell")]["filled_qty"] == pytest.approx(1.0)
    op, cl = tradebook.lots()
    on = cl[cl["sleeve"] == "overnight_drift"]
    assert len(on) == 1 and on.iloc[0]["entry_price"] == 261.0 and on.iloc[0]["exit_price"] == 264.0
    left = op[op["symbol"] == "LRCX"]
    assert left["sleeve"].tolist() == ["quality_screen"] and left["qty"].iloc[0] == pytest.approx(6.0)   # 7 - 1


def test_overnight_shares_count_as_held_until_the_next_open(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    from ai_desk import overnight as ov
    monkeypatch.setattr(ov, "BOOK", tmp_path / "book.json")
    ov.BOOK.write_text(json.dumps({"date": "2026-10-21", "holdings": {"BE": 1.0}, "sell_sent": True}))
    assert ov.held_overnight(datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)) == {"BE": 1.0}   # 4am New York
    assert ov.held_overnight(datetime(2026, 10, 22, 14, 0, tzinfo=timezone.utc)) == {}          # 10am: sold
