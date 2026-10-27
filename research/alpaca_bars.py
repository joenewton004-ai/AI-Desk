"""Download minute bars from Alpaca's market-data API (data.alpaca.markets) and cache them.

    python research/alpaca_bars.py SPY NVDA

Alpaca's free plan serves the consolidated (SIP) feed - every US exchange - from 2016, except the latest 15 minutes.
The keys come from the environment's network secret, as for the paper broker; nothing here can place orders.
Bars are split-adjusted, in New York time, regular session only (9:30-15:59 bar starts). Cached per symbol in
data/backtest/alpaca_1m_<SYMBOL>.pkl and topped up when END moves.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.broker.alpaca import AlpacaPaper  # noqa: E402

CACHE = ROOT / "data" / "backtest"
DATA_URL = "https://data.alpaca.markets/v2/stocks/{sym}/bars"
START, END = "2016-01-01", "2026-10-26"            # END = the last full trading day when this was run


def regular_session(df: pd.DataFrame) -> pd.DataFrame:
    """Pure: keep the bars that start 9:30-15:59 New York time."""
    t = df.index.hour * 60 + df.index.minute
    return df[(t >= 9 * 60 + 30) & (t < 16 * 60)]


def _get(session, url: str, params: dict, tries: int = 6) -> dict:
    for k in range(tries):
        r = session.get(url, params=params, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** k)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return {}


def download(sym: str, start: str, end: str, session=None) -> pd.DataFrame:
    """Every 1-minute bar from `start` to the end of `end` (UTC paging), regular session only."""
    session = session or AlpacaPaper().session
    params = {"timeframe": "1Min", "start": f"{start}T00:00:00Z", "end": f"{end}T23:59:59Z", "limit": 10000,
              "adjustment": "split", "feed": "sip", "sort": "asc"}
    rows: list[dict] = []
    while True:
        j = _get(session, DATA_URL.format(sym=sym), params)
        rows += j.get("bars") or []
        tok = j.get("next_page_token")
        if not tok:
            break
        params["page_token"] = tok
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "trades", "vwap"])
    df = pd.DataFrame(rows).rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume",
                                            "n": "trades", "vw": "vwap"})
    df.index = pd.to_datetime(df.pop("t"), utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return regular_session(df.astype(float))


def minute_bars(sym: str, start: str = START, end: str = END) -> pd.DataFrame:
    """Cached minute bars; downloads a year at a time and only what's missing."""
    path = CACHE / f"alpaca_1m_{sym}.pkl"
    have = pd.read_pickle(path) if path.exists() else None
    if have is not None and len(have) and have.index[0] <= pd.Timestamp(start) + pd.Timedelta(days=7) \
            and have.index[-1].normalize() >= pd.Timestamp(end):
        return have.loc[start:f"{end} 23:59"]
    s = (have.index[-1].normalize() + pd.Timedelta(days=1)) if have is not None and len(have) else pd.Timestamp(start)
    parts = [have] if have is not None and len(have) else []
    while s <= pd.Timestamp(end):
        e = min(pd.Timestamp(year=s.year, month=12, day=31), pd.Timestamp(end))
        part = download(sym, s.date().isoformat(), e.date().isoformat())
        print(f"{sym} {s.date()}..{e.date()}: {len(part):,} bars", flush=True)
        parts.append(part)
        s = e + pd.Timedelta(days=1)
    df = pd.concat(parts)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_pickle(path)
    return df.loc[start:f"{end} 23:59"]


if __name__ == "__main__":
    for s in sys.argv[1:] or ["SPY", "NVDA"]:
        d = minute_bars(s)
        print(f"{s}: {len(d):,} bars, {d.index[0]} to {d.index[-1]}, {d.index.normalize().nunique():,} days")
