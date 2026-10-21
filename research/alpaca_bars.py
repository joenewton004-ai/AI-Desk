"""Years of intraday bars from Alpaca's market-data API, cached for the intraday research.

    python research/alpaca_bars.py check           (is data.alpaca.markets reachable with keys?)
    python research/alpaca_bars.py 5Min 2016-01-01 (and 1Min 2024-10-01, ...)

Writes data/backtest/alpaca_<timeframe>.pkl in the same layout as the Yahoo caches
(dict of open/high/low/close/volume DataFrames, New York time, regular hours only), so
research/vwap_ema.py, ict.py and orb.py can read it. Feed: "sip" (all US exchanges; free plans
allow history older than 15 minutes), falling back to "iex" (one exchange - its volume is a
small slice of the total, which matters for VWAP and volume rules: say so if it's used).
Keys: APCA_API_KEY_ID / APCA_API_SECRET_KEY from the environment, or added on the way out by the
environment's network secret. Paper keys work for market data. Prices are split-adjusted
("adjustment=split") so a split can't fake a gap; dividends aren't (intraday studies don't need it).
"""

from __future__ import annotations

import os
import pickle
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.broker.alpaca import load_dotenv  # noqa: E402

CACHE = ROOT / "data" / "backtest"
URL = "https://data.alpaca.markets/v2/stocks/bars"


def session() -> requests.Session:
    load_dotenv()
    s = requests.Session()
    k, sec = os.environ.get("APCA_API_KEY_ID"), os.environ.get("APCA_API_SECRET_KEY")
    if k and sec:
        s.headers.update({"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": sec})
    return s


def check(feed: str = "sip") -> tuple[int, str]:
    r = session().get(URL, params={"symbols": "SPY", "timeframe": "1Day", "start": "2020-01-02", "end": "2020-01-10",
                                   "feed": feed}, timeout=20)
    return r.status_code, r.text[:200]


def fetch(symbols: list[str], timeframe: str, start: str, end: str, feed: str = "sip") -> dict[str, pd.DataFrame]:
    path = CACHE / f"alpaca_{timeframe}.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    s = session()
    rows = []
    for i in range(0, len(symbols), 20):
        chunk = symbols[i:i + 20]
        token = None
        while True:
            params = {"symbols": ",".join(chunk), "timeframe": timeframe, "start": start, "end": end, "feed": feed,
                      "adjustment": "split", "limit": 10000}
            if token:
                params["page_token"] = token
            for attempt in range(6):
                r = s.get(URL, params=params, timeout=60)
                if r.status_code == 429:                 # 200 requests a minute on the free plan
                    time.sleep(5 * 2 ** attempt)
                    continue
                break
            r.raise_for_status()
            j = r.json()
            for sym, bars in (j.get("bars") or {}).items():
                rows += [(sym, b["t"], b["o"], b["h"], b["l"], b["c"], b["v"]) for b in bars]
            token = j.get("next_page_token")
            if not token:
                break
        print(f"  {timeframe}: {min(i + 20, len(symbols))}/{len(symbols)} symbols, {len(rows):,} bars", flush=True)
    df = pd.DataFrame(rows, columns=["symbol", "t", "open", "high", "low", "close", "volume"])
    df["t"] = pd.to_datetime(df["t"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    mins = df["t"].dt.hour * 60 + df["t"].dt.minute
    df = df[(mins >= 570) & (mins < 960)]                      # regular hours, 9:30-16:00
    out = {k: df.pivot_table(index="t", columns="symbol", values=k, aggfunc="last").astype("float32")
           for k in ("open", "high", "low", "close", "volume")}
    path.write_bytes(pickle.dumps(out))
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["check"]:
        for feed in ("sip", "iex"):
            print(feed, *check(feed))
    else:
        tf, start = sys.argv[1], sys.argv[2]
        end = sys.argv[3] if len(sys.argv) > 3 else "2026-10-21"
        five = pickle.loads((CACHE / "intraday_5m.pkl").read_bytes())
        hour = pickle.loads((CACHE / "intraday_1h.pkl").read_bytes())
        syms = sorted(set(five["close"].columns) | set(hour["close"].columns))
        fetch(syms, tf, start, end)
