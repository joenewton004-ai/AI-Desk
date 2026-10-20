"""Minimal Alpaca PAPER trading client (REST API, no SDK needed).

The base URL is hard-wired to the paper endpoint on purpose. Moving to real
money should be a deliberate code change after months of paper results,
never a config typo.
"""

from __future__ import annotations

import os
from pathlib import Path

import requests

PAPER_URL = "https://paper-api.alpaca.markets/v2"


def load_dotenv(path: str | Path = ".env") -> None:
    """Read KEY=VALUE lines from .env into the environment (without overriding)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def format_qty(qty: float) -> str:
    """'12', '1.6129' - never scientific notation, which the API rejects."""
    return f"{qty:.6f}".rstrip("0").rstrip(".")


class AlpacaPaper:
    def __init__(self, key_id: str | None = None, secret: str | None = None, timeout: float = 15):
        load_dotenv()
        self.key_id = key_id or os.environ.get("APCA_API_KEY_ID")
        self.secret = secret or os.environ.get("APCA_API_SECRET_KEY")
        # Without keys here, assume a cloud session's network secret adds the
        # APCA-API-KEY-ID / APCA-API-SECRET-KEY headers on the way out (the keys
        # never enter the session). If nothing adds them, Alpaca answers 401/403
        # and `broker status` explains what to set up.
        self.injected = not (self.key_id and self.secret)
        if self.key_id and self.key_id.startswith("AK"):
            # Alpaca live-trading key IDs start with AK, paper ones with PK
            raise RuntimeError("These look like LIVE trading keys (they start with 'AK'). This desk only "
                               "trades paper - generate keys from the Paper Trading dashboard (they start with 'PK').")
        self.timeout = timeout
        self.session = requests.Session()
        if not self.injected:
            self.session.headers.update({"APCA-API-KEY-ID": self.key_id,
                                         "APCA-API-SECRET-KEY": self.secret})

    def _request(self, method: str, path: str, **kwargs):
        r = self.session.request(method, f"{PAPER_URL}{path}", timeout=self.timeout, **kwargs)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def status(self) -> dict:
        """Everything needed to confirm the connection works, in one call set."""
        acct = self.account()
        clock = self.clock()
        return {
            "account": acct.get("account_number", "?"),
            "status": acct.get("status"),
            "equity": float(acct.get("equity", 0)),
            "cash": float(acct.get("cash", 0)),
            "buying_power": float(acct.get("buying_power", 0)),
            "shorting_enabled": acct.get("shorting_enabled"),
            "trading_blocked": acct.get("trading_blocked"),
            "pattern_day_trader": acct.get("pattern_day_trader"),
            "market_open": clock.get("is_open"),
            "next_open": clock.get("next_open"),
            "positions": self.positions(),
            "open_orders": len(self.open_orders()),
        }

    def account(self) -> dict:
        return self._request("GET", "/account")

    def clock(self) -> dict:
        return self._request("GET", "/clock")

    def position_qty(self, symbol: str) -> float:
        pos = self._request("GET", f"/positions/{symbol}")
        return float(pos["qty"]) if pos else 0.0

    def open_orders(self, symbol: str | None = None) -> list[dict]:
        params = {"status": "open"} | ({"symbols": symbol} if symbol else {})
        return self._request("GET", "/orders", params=params) or []

    def positions(self) -> dict[str, float]:
        """{symbol: shares}; negative = short."""
        return {p["symbol"]: float(p["qty"]) for p in self._request("GET", "/positions") or []}

    def get_order(self, order_id: str) -> dict:
        """One order's status and fill (filled_avg_price, filled_qty, filled_at)."""
        return self._request("GET", f"/orders/{order_id}") or {}

    def latest_prices(self) -> dict[str, float]:
        """Current price of every held position."""
        return {p["symbol"]: float(p["current_price"]) for p in self._request("GET", "/positions") or []}

    def asset(self, symbol: str) -> dict:
        """Tradability flags, e.g. {"tradable": True, "shortable": True, "easy_to_borrow": True}."""
        return self._request("GET", f"/assets/{symbol}") or {}

    def submit_market_order(self, symbol: str, qty: float, side: str) -> dict:
        """Market order, good for the day. Submitted after the close, Alpaca
        queues it for the next open - matching how the backtest fills.
        Fractional quantities are allowed for fractionable stocks (day market
        orders only, which is what this sends)."""
        return self._request("POST", "/orders", json={
            "symbol": symbol, "qty": format_qty(qty), "side": side,
            "type": "market", "time_in_force": "day",
        })
