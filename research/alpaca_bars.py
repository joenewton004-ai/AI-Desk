"""Download minute bars from Alpaca's market-data API (data.alpaca.markets) and cache them.

    python research/alpaca_bars.py SPY NVDA                    (1-minute bars, regular session)
    python research/alpaca_bars.py --5min AAPL MSFT ...        (5-minute bars, regular session)
    python research/alpaca_bars.py --5min --extended QQQ SPY   (5-minute bars, 4am-8pm)

Alpaca's free plan serves the consolidated (SIP) feed - every US exchange - from 2016, except the latest 15 minutes.
The keys come from the environment's network secret, as for the paper broker; nothing here can place orders.
Bars are split-adjusted, in New York time, regular session only (9:30-15:59 bar starts) unless extended. Cached per
symbol in data/backtest/alpaca_<1m|5m>[_ext]_<SYMBOL>.pkl and topped up when END moves. Class shares use a dot
(BRK.B, BF.B).
"""

from __future__ import annotations

import sys
import threading
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


_PACE = {"lock": threading.Lock(), "next": 0.0}
MIN_GAP = 0.34                                       # seconds between requests, all threads: ~176/minute (limit 200)


def _get(session, url: str, params: dict, tries: int = 6) -> dict:
    for k in range(tries):
        with _PACE["lock"]:
            wait = _PACE["next"] - time.monotonic()
            _PACE["next"] = max(_PACE["next"], time.monotonic()) + MIN_GAP
        if wait > 0:
            time.sleep(wait)
        r = session.get(url, params=params, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** k)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return {}


def extended_session(df: pd.DataFrame) -> pd.DataFrame:
    """Pure: keep the bars that start 4:00-19:59 New York time (pre-market, regular, after-hours)."""
    t = df.index.hour * 60 + df.index.minute
    return df[(t >= 4 * 60) & (t < 20 * 60)]


def download(sym: str, start: str, end: str, session=None, timeframe: str = "1Min",
             extended: bool = False) -> pd.DataFrame:
    """Every bar from `start` to the end of `end` (UTC paging), regular session only unless `extended`."""
    session = session or AlpacaPaper().session
    params = {"timeframe": timeframe, "start": f"{start}T00:00:00Z", "end": f"{end}T23:59:59Z", "limit": 10000,
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
    df = df.astype(float)
    return extended_session(df) if extended else regular_session(df)


def minute_bars(sym: str, start: str = START, end: str = END) -> pd.DataFrame:
    """Cached 1-minute bars, regular session."""
    return bars(sym, start, end)


def bars(sym: str, start: str = START, end: str = END, timeframe: str = "1Min", extended: bool = False) -> pd.DataFrame:
    """Cached bars; downloads a year at a time and only what's missing."""
    tag = {"1Min": "1m", "5Min": "5m"}[timeframe] + ("_ext" if extended else "")
    path = CACHE / f"alpaca_{tag}_{sym}.pkl"
    have = pd.read_pickle(path) if path.exists() else None
    if have is not None:
        # the cache covers [attrs "from", attrs "to"]; older caches (no attrs) started at START
        lo = pd.Timestamp(have.attrs.get("from", have.index[0].normalize() if len(have) else START))
        hi = pd.Timestamp(have.attrs.get("to", have.index[-1].normalize() if len(have) else START))
        if lo > pd.Timestamp(start) + pd.Timedelta(days=7):
            have = None                                       # starts too late: download it all again
    if have is not None and hi >= pd.Timestamp(end):
        return have.loc[start:f"{end} 23:59"]
    s = hi + pd.Timedelta(days=1) if have is not None else pd.Timestamp(start)
    parts = [have] if have is not None and len(have) else []
    while s <= pd.Timestamp(end):
        e = min(pd.Timestamp(year=s.year, month=12, day=31), pd.Timestamp(end))
        part = download(sym, s.date().isoformat(), e.date().isoformat(), timeframe=timeframe, extended=extended)
        print(f"{sym} {s.date()}..{e.date()}: {len(part):,} bars", flush=True)
        parts.append(part)
        s = e + pd.Timedelta(days=1)
    df = pd.concat([p for p in parts if len(p)]) if any(len(p) for p in parts) else parts[-1]
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.attrs = {"from": str(have.attrs.get("from", start)) if have is not None else start, "to": end}
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_pickle(path)
    return df.loc[start:f"{end} 23:59"]


if __name__ == "__main__":
    from concurrent.futures import ThreadPoolExecutor

    args = sys.argv[1:]
    tf = "5Min" if "--5min" in args else "1Min"
    ext = "--extended" in args
    workers = int(next((a.split("=")[1] for a in args if a.startswith("--workers=")), 1))   # 4 stays well under
    syms = [a.replace("-", ".") for a in args if not a.startswith("--")] or ["SPY", "NVDA"]  # 200 requests/minute

    def one(s: str) -> None:
        try:
            d = bars(s, timeframe=tf, extended=ext)
        except Exception as e:  # noqa: BLE001 - an unknown or delisted symbol: say so and carry on
            print(f"{s}: failed ({e})", flush=True)
            return
        if len(d):
            print(f"{s}: {len(d):,} bars, {d.index[0]} to {d.index[-1]}, {d.index.normalize().nunique():,} days",
                  flush=True)
        else:
            print(f"{s}: no bars", flush=True)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, syms))
