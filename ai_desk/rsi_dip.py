"""RSI dip sleeve (amendment c52ce018, accepted 2026-10-27): buy big US companies on a short, sharp dip inside an uptrend.

Rule (research/CANDLE_RSI.md, research/DESK_5050.md variant C): one of the 100 largest US companies closes ABOVE its
200-day average with RSI(14) BELOW 30 -> buy at the next open, 10% of the desk; sell at the open after it first
closes above its 5-day average, or after 10 trading days. At most 5 at once; same-day signals lowest RSI first.
The overnight sleeve buys with whatever money the dips aren't using.

    python -m ai_desk rsidip scan     (the evening run's `portfolio prepare` runs it)

The scan writes output/rsi_dip_<date>.csv (every company in the top 100 plus anything the sleeve holds), from that
day's closes. The desk method (portfolio.methods.RSIDip) reads it with the sleeve's state in data/portfolio/rsi_dip.json.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from ai_desk.indicators import rsi, sma

AMENDMENT = "c52ce018"     # accepted 2026-10-27 (research/DESK_5050.md, variant C)
TOP = 100
RSI_DAYS, RSI_MAX = 14, 30.0
TREND_DAYS, EXIT_DAYS, MAX_DAYS = 200, 5, 10
SLOT, MAX_POSITIONS = 0.10, 5
MIN_CAP = 50e9            # the top 100 sit well above this; it keeps the screener call small
STATE = Path("data/portfolio/rsi_dip.json")
SCAN_GLOB = "output/rsi_dip_*.csv"


def evaluate(closes: pd.DataFrame) -> pd.DataFrame:
    """Pure: each column's latest close, 5- and 200-day averages, RSI(14) and dip signal, from data up to the last row."""
    c = closes.ffill()
    last = c.iloc[-1]
    df = pd.DataFrame({
        "close": last,
        "sma_5": sma(c, EXIT_DAYS).iloc[-1],
        "sma_200": sma(c, TREND_DAYS).iloc[-1],
        "rsi_14": pd.Series({s: rsi(c[s].dropna(), RSI_DAYS).iloc[-1] if c[s].notna().sum() > RSI_DAYS else np.nan
                             for s in c.columns}),
    })
    df["above_200"] = df["close"] > df["sma_200"]
    df["above_5"] = df["close"] > df["sma_5"]
    df["signal"] = df["above_200"] & (df["rsi_14"] < RSI_MAX)
    df.index.name = "symbol"
    return df.sort_values("rsi_14")


def trading_days_since(index: pd.DatetimeIndex, since: str, until: pd.Timestamp) -> int:
    """Pure: closes after `since` up to and including `until` (the signal day itself doesn't count)."""
    return int(((index > pd.Timestamp(since)) & (index <= until)).sum())


def decide(table: pd.DataFrame, held: dict[str, dict], days_held: dict[str, int], universe: set[str],
           max_positions: int = MAX_POSITIONS) -> dict:
    """Pure: which holdings to sell and which signals to buy at the next open.

    held: symbol -> its state ({"signal_date": ...}); days_held: closes since each signal day.
    Exit: closed above its 5-day average (from the first close after the buy) or held 10 trading days.
    Entry: a signal in the top-100 universe, not already held, lowest RSI first, up to the free slots."""
    exits, keep = {}, []
    for s in held:
        row = table.loc[s] if s in table.index else None
        n = days_held.get(s, 0)
        if row is None or not np.isfinite(row["close"]):
            keep.append(s)                                  # no price tonight: hold, decide tomorrow
        elif n >= 1 and bool(row["above_5"]):
            exits[s] = f"closed above its {EXIT_DAYS}-day average ({row['close']:.2f} > {row['sma_5']:.2f})"
        elif n >= MAX_DAYS:
            exits[s] = f"{MAX_DAYS}-day limit reached"
        else:
            keep.append(s)
    free = max(0, max_positions - len(keep))
    cands = table[table["signal"] & table.index.isin(sorted(universe)) & ~table.index.isin(list(held))]
    entries = list(cands.sort_values("rsi_14").index[:free])
    return {"keep": keep, "exits": exits, "entries": entries}


def universe(min_cap: float = MIN_CAP, top: int = TOP) -> list[str]:
    from ai_desk.fundamentals.universe import large_caps
    return large_caps(min_cap, limit=250).sort_values("market_cap", ascending=False)["symbol"].head(top).tolist()


def scan(extra: list[str] | None = None) -> pd.DataFrame:
    """Download ~15 months of closes for the top 100 (+ held symbols) and evaluate them on the last full day."""
    from ai_desk.bottleneck.scan import daily_closes
    from ai_desk.live import drop_incomplete_bar

    uni = universe()
    syms = list(dict.fromkeys(uni + list(extra or [])))
    closes = drop_incomplete_bar(daily_closes(syms, period="15mo"))
    df = evaluate(closes)
    df["in_top100"] = df.index.isin(uni)
    df["signal"] = df["signal"] & df["in_top100"]
    df.attrs["asof"] = closes.index[-1]
    df["asof"] = closes.index[-1].date().isoformat()
    return df


def save(df: pd.DataFrame, out_dir: str = "output") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"rsi_dip_{date.today().isoformat()}.csv"
    df.to_csv(path)
    return path


def latest_scan(max_age_days: int = 3) -> tuple[pd.DataFrame | None, str]:
    """The newest scan and its file name; None if there is none or it's older than `max_age_days`."""
    import glob
    files = sorted(glob.glob(SCAN_GLOB))
    if not files:
        return None, "no RSI dip scan found - run: python -m ai_desk rsidip scan"
    p = Path(files[-1])
    d = pd.Timestamp(p.stem.split("_")[-1])
    if (pd.Timestamp.today().normalize() - d).days > max_age_days:
        return None, f"the latest RSI dip scan is from {d.date()} - too old"
    return pd.read_csv(p, index_col=0), p.name
