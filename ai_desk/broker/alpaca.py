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


class AlpacaPaper:
    def __init__(self, key_id: str | None = None, secret: str | None = None, timeout: float = 15):
        load_dotenv()
        self.key_id = key_id or os.environ.get("APCA_API_KEY_ID")
        self.secret = secret or os.environ.get("APCA_API_SECRET_KEY")
        if not self.key_id or not self.secret:
            raise RuntimeError("Alpaca keys not found. Copy .env.example to .env and add your paper keys.")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"APCA-API-KEY-ID": self.key_id,
                                     "APCA-API-SECRET-KEY": self.secret})

    def _request(self, method: str, path: str, **kwargs):
        r = self.session.request(method, f"{PAPER_URL}{path}", timeout=self.timeout, **kwargs)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

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

    def asset(self, symbol: str) -> dict:
        """Tradability flags, e.g. {"tradable": True, "shortable": True, "easy_to_borrow": True}."""
        return self._request("GET", f"/assets/{symbol}") or {}

    def submit_market_order(self, symbol: str, qty: int, side: str) -> dict:
        """Market order, good for the day. Submitted after the close, Alpaca
        queues it for the next open - matching how the backtest fills."""
        return self._request("POST", "/orders", json={
            "symbol": symbol, "qty": str(qty), "side": side,
            "type": "market", "time_in_force": "day",
        })
