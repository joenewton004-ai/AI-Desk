"""NVIDIA opening-range buy - SHADOW only: records what the trade would have done each day, sends no orders.

The rule (research/CANDLES.md, the one intraday lead): on 5-minute bars, the high and low of NVDA's first 15 minutes
(9:30-9:45 New York) are the opening range. The first later bar that trades above the range high is a buy (a buy-stop
at that level, or the bar's open if it gapped above); the stop is the range low; anything still held is sold at the
15:55 bar's close. One trade a day, long only. Backtest 2016-2026: +0.15% a trade after 0.02% costs each way (t 3.2),
but the same rule lost slightly on QQQ and the 10 largest companies of 2016 - most likely a hindsight effect of
picking the stock that rose ~100x. Shadowing it shows whether the live days look like the backtest before any money
is risked (the owner asked to incorporate it, 2026-10-27; shadow chosen by default).

    python -m ai_desk orb record [--date YYYY-MM-DD]   (the evening run's `portfolio prepare` records each day)
    python -m ai_desk orb backfill [--days 60]
    python -m ai_desk orb status

Log: journal/nvda_orb.jsonl (one row per trading day; "source" = live (recorded that evening) or backfill).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SYMBOL = "NVDA"
RANGE_MINUTES = 15
LAST_BAR = 15 * 60 + 55
COST = 0.0002                       # each way, as in the research
BACKTEST = {"net_per_trade": 0.00151, "win_rate": 0.49, "trades_per_year": 123}
BACKTEST_GAP_UP = 0.00155          # research/ORB_VARIANTS.md (long-only first break, 2016-2026)
LOG = Path("journal/nvda_orb.jsonl")


def evaluate(bars: pd.DataFrame, minutes: int = RANGE_MINUTES) -> dict:
    """Pure: one day's 5-minute bars (New York times, regular session) -> the shadow trade.
    A bar that touches both the entry and the stop counts as stopped (conservative), as in the research."""
    b = bars.sort_index()
    t = b.index.hour * 60 + b.index.minute
    rng = b[(t >= 9 * 60 + 30) & (t < 9 * 60 + 30 + minutes)]
    if rng.empty or t.min() > 9 * 60 + 30:
        return {"status": "no opening range"}
    hi, lo = float(rng["high"].max()), float(rng["low"].min())
    out = {"range_high": hi, "range_low": lo, "range_pct": hi / lo - 1}
    after = b[(t >= 9 * 60 + 30 + minutes) & (t <= LAST_BAR)]
    o, h, l, c = (after[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    for j in range(len(after)):
        if h[j] > hi:
            entry = max(o[j], hi)
            exit_px, why, when = None, None, None
            for k in range(j, len(after)):
                if l[k] <= lo:
                    exit_px = min(o[k], lo) if k > j else lo
                    why, when = "stop", after.index[k]
                    break
            if exit_px is None:
                exit_px, why, when = c[-1], "close", after.index[-1]
            gross = exit_px / entry - 1
            return {**out, "status": "traded", "entry_time": str(after.index[j].time())[:5], "entry": round(entry, 4),
                    "stop": lo, "exit_time": str(when.time())[:5], "exit": round(float(exit_px), 4), "exit_why": why,
                    "gross": round(gross, 6), "net": round(gross - 2 * COST, 6),
                    "R": round((exit_px - entry) / (entry - lo), 3) if entry > lo else None}
    return {**out, "status": "no breakout"}


def fetch_day(day: str) -> pd.DataFrame:
    """NVDA 5-minute bars for one day from Alpaca's market data (SIP), regular session, New York time."""
    from ai_desk.broker.alpaca import AlpacaPaper
    s = AlpacaPaper().session
    r = s.get(f"https://data.alpaca.markets/v2/stocks/{SYMBOL}/bars",
              params={"timeframe": "5Min", "start": f"{day}T00:00:00Z", "end": f"{day}T23:59:59Z", "limit": 10000,
                      "adjustment": "split", "feed": "sip"}, timeout=30)
    r.raise_for_status()
    rows = r.json().get("bars") or []
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(rows).rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    df.index = pd.to_datetime(df.pop("t"), utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    t = df.index.hour * 60 + df.index.minute
    return df[(t >= 9 * 60 + 30) & (t < 16 * 60)][["open", "high", "low", "close", "volume"]].astype(float)


def previous_close(day: str) -> float | None:
    """NVDA's official close on the trading day before `day` (Alpaca daily bars)."""
    from ai_desk.broker.alpaca import AlpacaPaper
    start = (pd.Timestamp(day) - pd.Timedelta(days=10)).date().isoformat()
    r = AlpacaPaper().session.get(f"https://data.alpaca.markets/v2/stocks/{SYMBOL}/bars",
                                  params={"timeframe": "1Day", "start": f"{start}T00:00:00Z", "end": f"{day}T00:00:00Z",
                                          "adjustment": "split", "feed": "sip", "limit": 20}, timeout=30)
    r.raise_for_status()
    bars = [b for b in (r.json().get("bars") or []) if b["t"][:10] < day]
    return float(bars[-1]["c"]) if bars else None


def rows() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(x) for x in LOG.read_text().splitlines() if x.strip()]


def _save(all_rows: list[dict]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("".join(json.dumps(r) + "\n" for r in sorted(all_rows, key=lambda r: r["date"])))


def record(day: str | None = None, source: str = "live") -> dict | None:
    """Evaluate one finished trading day and append it (once). None if there were no bars (weekend/holiday)."""
    day = day or datetime.now(timezone.utc).astimezone(pd.Timestamp.now(tz="America/New_York").tz).date().isoformat()
    have = {r["date"]: r for r in rows()}
    if day in have:
        return have[day]
    bars = fetch_day(day)
    if bars.empty or (bars.index.hour * 60 + bars.index.minute).max() < LAST_BAR:
        return None                                  # market closed, or the day isn't over yet
    prev = previous_close(day)
    first_open = float(bars["open"].iloc[0])
    row = {"date": day, "source": source, "recorded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "prev_close": prev, "gap_up": bool(prev is not None and first_open > prev), **evaluate(bars)}
    _save(list(have.values()) + [row])
    return row


def backfill(days: int = 60) -> int:
    """Shadow the last `days` weekdays before today (labelled source=backfill)."""
    n = 0
    for d in pd.bdate_range(end=pd.Timestamp.today().normalize() - pd.Timedelta(days=1), periods=days):
        if record(d.date().isoformat(), source="backfill"):
            n += 1
    return n


def summary(all_rows: list[dict] | None = None, gap_up_only: bool = False) -> dict:
    """Pure: trades, win rate and average net per trade so far, next to the backtest. gap_up_only: the tweak from
    research/ORB_VARIANTS.md - only days NVDA opened above the previous close."""
    rs = [r for r in (all_rows if all_rows is not None else rows()) if r.get("status") == "traded"
          and (r.get("gap_up") or not gap_up_only)]
    net = np.array([r["net"] for r in rs], dtype=float)
    days = len(all_rows if all_rows is not None else rows())
    return {"days": days, "trades": len(rs), "win_rate": float((net > 0).mean()) if len(rs) else None,
            "avg_net": float(net.mean()) if len(rs) else None, "total_net": float(net.sum()) if len(rs) else 0.0,
            "backtest_avg_net": BACKTEST["net_per_trade"], "backtest_win_rate": BACKTEST["win_rate"]}
