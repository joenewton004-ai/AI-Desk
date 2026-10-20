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
    a = register.propose("bottleneck", "cap any one industry at 3 of 8 picks", "too concentrated in oil")
    assert register.decide(a["id"], "testing")["status"] == "testing"
    done = register.decide(a["id"], "accepted", "backtest: Sharpe 0.60 -> 0.64")
    assert done["decided_utc"] and done["evidence"].startswith("backtest")
    with pytest.raises(ValueError):
        register.decide(a["id"], "maybe")
    reg = register.register()
    bn = next(m for m in reg["methods"] if m["name"] == "bottleneck")
    assert bn["in_live_mix"] and bn["allocation"] == 0.2 and bn["amendments"][0]["status"] == "accepted"
    assert bn["parameters"]["rebalance_days"] == 14
