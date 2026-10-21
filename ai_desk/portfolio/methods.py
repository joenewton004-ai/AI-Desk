"""Portfolio methods: ways to turn market data into target portfolio weights.

Every method answers one question: "given data up to today's close, what
fraction of the account should each symbol be?" Weights are decided at the
close and traded at the next open (same rule as the single-asset backtest).
A weight of 0.25 = 25% of equity; negative = short.

Pick one with --method, or blend several: --method quality_screen:0.5
--method index_momentum:0.5 (see `build`). Add a new method by subclassing
Method and registering it in METHODS.
"""

from __future__ import annotations

import glob
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ai_desk.strategies.momentum import TimeSeriesMomentum
from ai_desk.strategies.sma_crossover import SMACrossover

# Markets dominated by two companies. Their prices are driven by the same
# industry forces, so the gap between them tends to swing around a level
# rather than wander off - the premise of pairs trading. (It doesn't always
# hold: see research/METHODS.md.)
DUOPOLY_PAIRS = [
    ("V", "MA"),        # card networks
    ("KO", "PEP"),      # cola
    ("HD", "LOW"),      # home improvement
    ("UPS", "FDX"),     # US parcel delivery
    ("MCO", "SPGI"),    # credit ratings
    ("BKNG", "EXPE"),   # online travel
]


@dataclass
class Method(ABC):
    name = "base"
    can_short = False
    backtestable = True

    @abstractmethod
    def symbols(self) -> list[str]:
        """Every symbol whose prices this method needs."""

    @abstractmethod
    def weights(self, closes: pd.DataFrame) -> pd.DataFrame:
        """Target weights decided at each date's close (rows = dates,
        columns = symbols). Must use only data up to that row."""

    def latest(self, closes: pd.DataFrame) -> pd.Series:
        return self.weights(closes).iloc[-1]

    def frozen(self) -> set[str]:
        """Symbols whose existing positions must not be resized this run
        (e.g. stocks held until their next scheduled re-pick)."""
        return set()

    def status(self) -> list[str]:
        """Plain-English notes about the method's state, shown in the plan."""
        return []

    def on_executed(self) -> None:
        """Called after orders are actually sent (e.g. to save new holdings)."""

    # --- for the trade journal ---
    def sleeves(self, closes: pd.DataFrame) -> dict[str, pd.Series]:
        """Target weights split by sleeve, so each trade can be attributed."""
        return {self.name: self.latest(closes)}

    def rationale(self, symbol: str) -> dict:
        """The numbers behind wanting `symbol`, at decision time."""
        return {}

    def exit_reason(self, symbol: str) -> str | None:
        """Why this method no longer wants `symbol` (None if it does, or never did)."""
        return None

    def describe(self) -> str:
        args = ", ".join(f"{k}={v}" for k, v in asdict(self).items())
        return f"{self.name}({args})"


def _parse_symbols(value) -> list[str]:
    if isinstance(value, str):
        return [s.strip().upper() for s in value.replace(" ", ",").split(",") if s.strip()]
    return [s.upper() for s in value]


@dataclass
class IndexMomentum(Method):
    """The thesis's index sleeve: hold `symbol` while its 12-month return is
    positive (checked monthly), otherwise cash."""

    name = "index_momentum"
    symbol: str = "SPY"
    lookback: int = 252

    def symbols(self):
        return [self.symbol]

    def weights(self, closes):
        px = pd.DataFrame({"close": closes[self.symbol]})
        w = TimeSeriesMomentum(lookback=self.lookback).target_exposure(px)
        s = closes[self.symbol].dropna()
        self._last = {"trailing_12m_return": round(float(s.iloc[-1] / s.iloc[-1 - self.lookback] - 1), 4)
                      if len(s) > self.lookback else None, "signal": float(w.iloc[-1])}
        return w.to_frame(self.symbol)

    def rationale(self, symbol):
        return dict(getattr(self, "_last", {})) if symbol == self.symbol else {}

    def exit_reason(self, symbol):
        last = getattr(self, "_last", {})
        if symbol == self.symbol and last.get("signal") == 0:
            return f"momentum switch off: {self.symbol} 12-month return {last.get('trailing_12m_return'):+.1%}"
        return None


@dataclass
class IndexRotation(Method):
    """Index rotation ("dual momentum"): each month, rank major index funds by
    momentum (12-month return, or a blend of lookbacks) and hold the best `top`
    - or, with drop_worst=N, everything except the N weakest. Only funds with
    positive momentum are held; a failing slot sits in cash (earning T-bills).
    weighting: equal slices, or "rank" (the leader gets the biggest slice).
    With symbols=SPY and top=1 this is index_momentum."""

    name = "index_rotation"
    symbols_: list = field(default_factory=lambda: ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM"])
    top: int = 1
    lookback: int = 252
    drop_worst: int = 0          # >0: hold all but the N weakest (overrides top)
    weighting: str = "equal"     # equal | rank
    lookbacks: str = ""          # e.g. "63,126,252": average of 3-, 6- and 12-month returns

    def __post_init__(self):
        self.symbols_ = _parse_symbols(self.symbols_)
        if self.weighting not in ("equal", "rank"):
            raise ValueError("weighting must be equal or rank")
        if self.drop_worst >= len(self.symbols_):
            raise ValueError("drop_worst must leave at least one index")

    def symbols(self):
        return self.symbols_

    def _slots(self) -> int:
        return len(self.symbols_) - self.drop_worst if self.drop_worst > 0 else self.top

    def _lookbacks(self) -> list[int]:
        return [int(x) for x in str(self.lookbacks).split(",") if x.strip()] or [self.lookback]

    def weights(self, closes):
        c = closes[self.symbols_]
        mom = sum(c / c.shift(lb) - 1 for lb in self._lookbacks()) / len(self._lookbacks())
        k = self._slots()
        rank = mom.rank(axis=1, ascending=False, method="first")
        hold = (rank <= k) & (mom > 0)
        if self.weighting == "rank":
            slice_ = (k + 1 - rank).clip(lower=0) / (k * (k + 1) / 2)     # k, k-1, ... 1 parts of the whole
        else:
            slice_ = rank * 0 + 1 / k
        w = slice_.where(hold, 0.0).fillna(0.0)
        # decide on the first trading day of each month only (like index_momentum)
        idx = c.index
        new_month = pd.Series(idx.month, index=idx).diff().fillna(1) != 0
        w = w.where(new_month, np.nan).ffill().fillna(0.0)
        last = mom.iloc[-1]
        self._last = {"momentum": {k_: round(float(v), 4) for k_, v in last.dropna().items()},
                      "held": [k_ for k_ in w.columns if w[k_].iloc[-1] > 0]}
        return w

    def rationale(self, symbol):
        last = getattr(self, "_last", {})
        if symbol not in self.symbols_:
            return {}
        r = last.get("momentum", {})
        ranked = sorted(r, key=r.get, reverse=True)
        return {"momentum": r.get(symbol), "lookbacks": ",".join(map(str, self._lookbacks())),
                "rank": ranked.index(symbol) + 1 if symbol in ranked else None, "of": len(ranked)}

    def exit_reason(self, symbol):
        last = getattr(self, "_last", {})
        if symbol not in self.symbols_ or symbol in last.get("held", [symbol]):
            return None
        r = last.get("momentum", {}).get(symbol)
        if r is not None and r <= 0:
            return f"momentum switch off: {symbol} momentum {r:+.1%}"
        if self.drop_worst:
            return f"rotation: {symbol} is among the {self.drop_worst} weakest indices"
        return f"rotation: {symbol} no longer in the top {self.top}"


@dataclass
class SMACrossoverMethod(Method):
    """Moving-average crossover on each symbol. Each gets an equal slice
    (1/N of the account) and holds it while its fast average is above its
    slow one; a symbol that's "off" leaves its slice in cash."""

    name = "sma_crossover"
    symbols_: list = field(default_factory=lambda: ["SPY"])
    fast: int = 50
    slow: int = 200

    def __post_init__(self):
        self.symbols_ = _parse_symbols(self.symbols_)

    def symbols(self):
        return self.symbols_

    def weights(self, closes):
        strat = SMACrossover(fast=self.fast, slow=self.slow)
        slice_ = 1 / len(self.symbols_)
        return pd.DataFrame({s: strat.target_exposure(pd.DataFrame({"close": closes[s]})) * slice_
                             for s in self.symbols_})


@dataclass
class PairsMethod(Method):
    """Duopoly pairs trading.

    For each pair (A, B), track the spread = log(price A / price B). When it
    is unusually wide - more than `entry_z` standard deviations from its
    rolling `lookback`-day mean - bet on it narrowing:
      * long_short (default): short the one that ran ahead, buy the laggard,
        equal dollars each side - market moves largely cancel out
      * long_only: just hold the laggard (no shorting needed; keeps market risk)
    Close the trade when the spread is back within `exit_z`, or after
    `max_days` (a gap that won't close may mean something really changed).
    Each pair gets 1/N of the account.
    """

    name = "pairs"
    can_short = True
    pairs: list = field(default_factory=lambda: list(DUOPOLY_PAIRS))
    lookback: int = 60
    entry_z: float = 2.0
    exit_z: float = 0.5
    max_days: int = 60
    mode: str = "long_short"

    def __post_init__(self):
        if isinstance(self.pairs, str):     # "V/MA,KO/PEP"
            self.pairs = [tuple(p.upper().split("/")) for p in self.pairs.split(",") if p]
        if self.mode not in ("long_short", "long_only"):
            raise ValueError("mode must be long_short or long_only")
        self.can_short = self.mode == "long_short"

    def symbols(self):
        return list(dict.fromkeys(s for p in self.pairs for s in p))

    def zscores(self, closes: pd.DataFrame) -> pd.DataFrame:
        out = {}
        for a, b in self.pairs:
            spread = np.log(closes[a] / closes[b])
            mean = spread.rolling(self.lookback, min_periods=self.lookback).mean()
            std = spread.rolling(self.lookback, min_periods=self.lookback).std()
            out[f"{a}/{b}"] = (spread - mean) / std
        return pd.DataFrame(out)

    def weights(self, closes):
        z = self.zscores(closes)
        w = pd.DataFrame(0.0, index=closes.index, columns=self.symbols())
        slice_ = 1 / len(self.pairs)
        for (a, b), col in zip(self.pairs, z.columns):
            state, held = 0, 0          # state: +1 = A rich (short A / long B), -1 = B rich
            zs = z[col].to_numpy()
            pos_a, pos_b = np.zeros(len(zs)), np.zeros(len(zs))
            for i, zi in enumerate(zs):
                if np.isnan(zi):
                    state, held = 0, 0
                elif state == 0 and abs(zi) > self.entry_z:
                    state, held = (1 if zi > 0 else -1), 0
                elif state != 0 and (abs(zi) < self.exit_z or held >= self.max_days
                                     or np.sign(zi) == -state and abs(zi) > self.entry_z):
                    state, held = 0, 0
                if state != 0:
                    held += 1
                if self.mode == "long_short":
                    pos_a[i], pos_b[i] = -state * slice_ / 2, state * slice_ / 2
                else:   # long_only: hold the laggard with the pair's whole slice
                    pos_a[i], pos_b[i] = (slice_ if state == -1 else 0.0), (slice_ if state == 1 else 0.0)
            w[a] += pos_a
            w[b] += pos_b
        return w


@dataclass
class LockedScreen(Method):
    """Shared logic for sleeves that buy the top N of a saved scan and HOLD
    them until a scheduled re-pick.

    Picks are LOCKED when orders are sent (saved in `lock_path` with the
    date). Until the re-pick date, later runs keep the same stocks and leave
    their sizes alone (they drift, as in the backtests) - except stocks an
    exit rule says to sell. When a re-pick is due (or with rebalance=True),
    the latest scan (no older than `max_age_days`) supplies a new top N:
    dropouts are sold, new names bought, and all are re-sized. A dry run never
    changes the lock.
    """

    backtestable = False
    top: int = 25
    rebalance: bool = False
    max_age_days: int = 10
    screen_glob: str = ""
    lock_path: str = ""
    scan_command = ""

    def __post_init__(self):
        self._cache = None

    # --- hooks for subclasses ---
    def _period(self) -> pd.DateOffset:
        raise NotImplementedError

    def _target_weights(self, picks: list[str], closes: pd.DataFrame) -> pd.Series:
        return pd.Series(1 / len(picks), index=picks)

    def _exits(self, picks: list[str], closes: pd.DataFrame) -> set[str]:
        """Picks to sell now, even between re-picks."""
        return set()

    # --- shared logic ---
    def _lock(self) -> dict | None:
        p = Path(self.lock_path)
        return json.loads(p.read_text()) if p.exists() else None

    def _next_repick(self, lock: dict) -> pd.Timestamp:
        return pd.Timestamp(lock["locked_on"]) + self._period()

    def _fresh_picks(self) -> tuple[list[str], str]:
        files = sorted(glob.glob(self.screen_glob))
        if not files:
            raise RuntimeError(("a re-pick is due but " if self._lock() else "") +
                               f"no scan results were found - run: {self.scan_command}")
        path = Path(files[-1])
        date = pd.Timestamp(path.stem.split("_")[-1])
        if (pd.Timestamp.today().normalize() - date).days > self.max_age_days:
            raise RuntimeError(f"a re-pick is due but the latest scan is from {date.date()} - run "
                               f"`{self.scan_command}` first (must be under {self.max_age_days} days old)")
        return list(pd.read_csv(path, index_col=0).index[:self.top]), path.name

    def repick_status(self, today: pd.Timestamp | None = None) -> dict:
        """Is a re-pick due, and does it need a fresh scan first? (For the scheduled evening run.)"""
        today = (today or pd.Timestamp.today()).normalize()
        lock = self._lock()
        files = sorted(glob.glob(self.screen_glob))
        scan_date = pd.Timestamp(Path(files[-1]).stem.split("_")[-1]) if files else None
        due = lock is None or today >= self._next_repick(lock)
        return {"sleeve": self.name, "due": bool(due),
                "next_repick": None if lock is None else self._next_repick(lock).date().isoformat(),
                "scan_date": None if scan_date is None else scan_date.date().isoformat(),
                # re-pick from a scan run today, so it reflects the latest close
                "needs_scan": bool(due and (scan_date is None or scan_date < today)),
                "scan_command": self.scan_command}

    def _picks(self) -> list[str]:
        if self._cache is not None:
            return self._cache["picks"]
        lock = self._lock()
        today = pd.Timestamp.today().normalize()
        if lock and not self.rebalance and today < self._next_repick(lock):
            self._cache = {"picks": lock["picks"], "due": False, "weights": lock.get("weights"),
                           "exited": set(lock.get("exited", [])),
                           "note": f"{self.name}: holding the {len(lock['picks'])} stocks picked on "
                                   f"{lock['locked_on']} (from {lock['screen_file']}); next re-pick due "
                                   f"{self._next_repick(lock).date()}"}
        else:
            picks, src = self._fresh_picks()
            why = "forced re-pick (--rebalance)" if self.rebalance and lock else \
                "re-pick due" if lock else "first pick"
            changes = ""
            if lock:
                out, new = sorted(set(lock["picks"]) - set(picks)), sorted(set(picks) - set(lock["picks"]))
                changes = f"; selling {', '.join(out) or 'none'}; buying {', '.join(new) or 'none'}"
            self._cache = {"picks": picks, "due": True, "src": src, "weights": None,
                           "note": f"{self.name}: {why} - top {len(picks)} from {src}{changes}. "
                                   "Holdings are locked when orders are sent"}
        return self._cache["picks"]

    def symbols(self):
        return self._picks()

    def weights(self, closes):
        picks = self._picks()
        if self._cache.get("weights"):                  # between re-picks: the sizes chosen at purchase
            w = pd.Series(self._cache["weights"]).reindex(picks).fillna(0.0)
        else:
            w = self._target_weights(picks, closes)
            self._cache["weights"] = w.to_dict()
        # once sold by the exit rule, a stock stays out until the next re-pick
        # (no buying back on a bounce - that would whipsaw)
        exits = self._exits(picks, closes) | self._cache.get("exited", set())
        self._cache["exits"] = exits
        w = w.copy()
        w[list(exits)] = 0.0
        return pd.DataFrame([w.to_numpy()] * len(closes), index=closes.index, columns=w.index)

    def frozen(self):
        self._picks()
        if self._cache["due"]:
            return set()
        return set(self._cache["picks"]) - self._cache.get("exits", set())

    def status(self):
        self._picks()
        notes = [self._cache["note"]]
        new_exits = self._cache.get("exits", set()) - self._cache.get("exited", set())
        if new_exits:
            notes.append(f"{self.name}: selling {', '.join(sorted(new_exits))} - price below its moving average")
        if hasattr(self, "_ma_days"):
            notes.append(f"{self.name}: exit rule = close below the {self._ma_days()}-day average; "
                         f"re-pick every {getattr(self, 'rebalance_days', '?')} days")
        if self._cache.get("exited"):
            notes.append(f"{self.name}: {', '.join(sorted(self._cache['exited']))} already sold by the exit rule; "
                         "out until the next re-pick")
        return notes

    RATIONALE_COLS = ("score", "quality_score", "growth_score", "value_score", "strength_score", "momentum_score",
                      "flow_score", "bottleneck_score", "asymmetry_score", "smart_money_score", "industry", "segment",
                      "source", "roic_avg", "rev_cagr", "rev_growth", "gm_change", "backlog_growth", "rs_6m",
                      "forward_pe", "fcf_yield", "insider_buyers", "strengths", "weaknesses")

    def rationale(self, symbol):
        self._picks()
        src = self._cache.get("src") or (self._lock() or {}).get("screen_file")
        path = Path(self.screen_glob).parent / src if src else None
        if not path or not path.exists():
            return {}
        df = pd.read_csv(path, index_col=0)
        if symbol not in df.index:
            return {}
        row = df.loc[symbol]
        out = {"rank": int(df.index.get_loc(symbol)) + 1, "source_file": src}
        for c in self.RATIONALE_COLS:
            if c in row and pd.notna(row[c]):
                v = row[c]
                out[c] = round(float(v), 4) if isinstance(v, (int, float, np.floating, np.integer)) else str(v)
        return out

    def exit_reason(self, symbol):
        self._picks()
        if symbol in self._cache.get("exits", set()):
            return f"exit rule: closed below its {getattr(self, '_ma_days', lambda: 0)()}-day average"
        lock = self._lock()
        if self._cache["due"] and lock and symbol in lock["picks"] and symbol not in self._cache["picks"]:
            return f"dropped out of the top {self.top} at the scheduled re-pick"
        return None

    def on_executed(self):
        if self._cache and not self._cache["due"] and self._cache.get("exits"):
            lock = self._lock()
            lock["exited"] = sorted(set(lock.get("exited", [])) | self._cache["exits"])
            Path(self.lock_path).write_text(json.dumps(lock, indent=1))
        if self._cache and self._cache["due"]:
            p = Path(self.lock_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"picks": self._cache["picks"], "screen_file": self._cache["src"],
                                     "weights": self._cache.get("weights"),
                                     "locked_on": str(pd.Timestamp.today().date())}, indent=1))


@dataclass
class QualityScreen(LockedScreen):
    """Top 25 of the quality stock screen, equal weight, re-picked every
    quarter (backtested: quarterly beat annual - research/screen_backtest.py).
    Positions drift between re-picks; no stop-loss (none was backtested)."""

    name = "quality_screen"
    scan_command = "python -m ai_desk screen"
    top: int = 25
    rebalance_months: int = 3
    screen_glob: str = "output/screen_*.csv"
    lock_path: str = "data/portfolio/quality_screen.json"

    def _period(self):
        return pd.DateOffset(months=self.rebalance_months)


@dataclass
class Bottleneck(LockedScreen):
    """Top 8 of the bottleneck scan (python -m ai_desk bottleneck scan).

    * re-picked every `rebalance_days` (default 14: every 2 weeks beat weekly for
      every moving average tested - research/BOTTLENECK.md) from a fresh scan
    * sized by inverse volatility - calmer stocks get more, wilder ones less -
      capped at 2x an equal share, so one stock can't dominate the sleeve
    * EXIT RULE, checked on every run: any holding whose price closes below
      its moving average is sold, even between re-picks. The average is the
      one the scan used to buy (saved with the picks); exit_ma overrides it.
    """

    name = "bottleneck"
    scan_command = "python -m ai_desk bottleneck scan"
    top: int = 8
    rebalance_days: int = 14
    exit_ma: int = 0                  # 0 = use the scan's moving average (stored with the picks)
    max_age_days: int = 3
    screen_glob: str = "output/bottleneck_*.csv"
    lock_path: str = "data/portfolio/bottleneck.json"

    def _period(self):
        return pd.DateOffset(days=self.rebalance_days)

    def _target_weights(self, picks, closes):
        vol = closes[picks].pct_change().iloc[-63:].std() * np.sqrt(252)
        inv = 1 / vol.replace(0, np.nan)
        w = (inv / inv.sum()).fillna(1 / len(picks))
        cap = 2 / len(picks)
        for _ in range(10):                          # cap, then share the excess with the rest
            over = w > cap
            if not over.any():
                break
            spare = (w[over] - cap).sum()
            w[over] = cap
            w[~over] += spare * w[~over] / w[~over].sum()
        return w

    def _ma_days(self) -> int:
        if self.exit_ma:
            return self.exit_ma
        src = (self._cache or {}).get("src") or (self._lock() or {}).get("screen_file")
        path = Path(self.screen_glob).parent / src if src else None
        if path and path.exists():
            cols = pd.read_csv(path, index_col=0, nrows=1)
            if "ma_days" in cols:
                return int(cols["ma_days"].iloc[0])
        return 100

    def _exits(self, picks, closes):
        n = self._ma_days()
        avg = closes[picks].rolling(n, min_periods=n).mean().iloc[-1]
        last = closes[picks].iloc[-1]
        return set(last.index[(last < avg) & avg.notna()])


@dataclass
class Momentum(Bottleneck):
    """Top 20 large companies by 6-month price gain (skipping the latest week), above their
    200-day average, equal weight (python -m ai_desk momentum scan).

    * re-picked every 4 weeks (research/WEEKLY.md: monthly beat weekly re-picks)
    * EXIT RULE, checked on every run: a holding that closes below its 100-day average is
      sold and stays out until the next re-pick (the bottleneck sleeve's rule, kept by choice)
    * replaced the bottleneck sleeve's engine - amendment 00e1f2b8, accepted 2026-10-20
      (research/MOMENTUM_SLEEVE.md)
    """

    name = "momentum"
    scan_command = "python -m ai_desk momentum scan"
    top: int = 20
    rebalance_days: int = 28
    exit_ma: int = 100
    max_age_days: int = 3
    screen_glob: str = "output/momentum_*.csv"
    lock_path: str = "data/portfolio/momentum.json"
    replaces_lock: str = "data/portfolio/bottleneck.json"

    def _target_weights(self, picks, closes):
        return pd.Series(1 / len(picks), index=picks)

    def _fresh_picks(self):
        picks, src = super()._fresh_picks()
        path = Path(self.screen_glob).parent / src
        df = pd.read_csv(path, index_col=0)
        if "passes" in df:                         # only stocks above their 200-day average
            df = df[df["passes"].astype(bool)]
        return list(df.index[:self.top]), src

    def exit_reason(self, symbol):
        own = super().exit_reason(symbol)
        if own:
            return own
        old = Path(self.replaces_lock)
        if old.exists() and symbol in json.loads(old.read_text()).get("picks", []) and symbol not in self._picks():
            return "sleeve switched from bottleneck to plain momentum (amendment 00e1f2b8)"
        return None


METHODS: dict[str, type[Method]] = {
    m.name: m for m in (IndexMomentum, IndexRotation, SMACrossoverMethod, PairsMethod, QualityScreen, Bottleneck,
                        Momentum)
}
# shorthands: `thesis` is the 50/50 structure in research/THESIS.md; `aggressive`
# tilts to the stock screen (70/30) - more return and bigger drawdowns in the backtest
PRESETS = {
    "thesis": [("quality_screen", 0.5), ("index_momentum", 0.5)],
    "aggressive": [("quality_screen", 0.7), ("index_momentum", 0.3)],
    # the live desk: quality compounders + a momentum sleeve + SPY with crash insurance
    "desk": [("quality_screen", 0.5), ("momentum", 0.2), ("index_momentum", 0.3)],
}
# Amendment 00e1f2b8 (accepted 2026-10-20): the 20% sleeve's engine changes from bottleneck to plain
# momentum at the bottleneck sleeve's next scheduled re-pick, so its current picks aren't sold early.
DESK_SWITCH = {"date": "2026-11-03", "before": [("quality_screen", 0.5), ("bottleneck", 0.2), ("index_momentum", 0.3)]}


# Amendment 330e76e0 (accepted 2026-10-21): the 30% SPY momentum sleeve is replaced by the overnight sleeve, which
# trades in its own paper account (ai_desk/overnight.py). From the activation date (`overnight activate`, written to
# OVERNIGHT_SWAP once that account works) the desk's own account holds only the other sleeves, rescaled to 100%.
OVERNIGHT_SWAP = Path("data/portfolio/overnight_live.json")
SWAPPED_OUT = "index_momentum"


def overnight_swap() -> dict | None:
    return json.loads(OVERNIGHT_SWAP.read_text()) if OVERNIGHT_SWAP.exists() else None


def without_swapped_sleeve(parts: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Drop the SPY momentum sleeve and scale the rest up to 100% (50/20 -> 71/29)."""
    keep = [(n, w) for n, w in parts if n != SWAPPED_OUT]
    total = sum(w for _, w in keep)
    return [(n, w / total) for n, w in keep]


def preset(name: str, today: pd.Timestamp | None = None, swap: dict | None | bool = True) -> list[tuple[str, float]]:
    """A preset's parts as of `today` (the desk switches sleeves on DESK_SWITCH['date'], and drops SPY momentum
    from the overnight swap's activation date). swap: True = read OVERNIGHT_SWAP; a dict = use it; None = no swap."""
    today = (today or pd.Timestamp.today()).normalize()
    parts = list(DESK_SWITCH["before"]) if name == "desk" and today < pd.Timestamp(DESK_SWITCH["date"]) \
        else list(PRESETS[name])
    sw = overnight_swap() if swap is True else swap
    if name == "desk" and sw and today >= pd.Timestamp(sw["from"]):
        parts = without_swapped_sleeve(parts)
    return parts


@dataclass
class Blend(Method):
    """Several methods, each scaled by its share of the account."""

    name = "blend"
    parts: list = field(default_factory=list)      # [(Method, weight)]
    unfreeze_once: bool = False                    # resize locked holdings this one run (a sleeve's share changed)

    def __post_init__(self):
        total = sum(w for _, w in self.parts)
        if not 0 < total <= 1.0 + 1e-9:
            raise ValueError(f"method weights must add up to at most 1 (got {total:g})")
        self.can_short = any(m.can_short for m, _ in self.parts)
        self.backtestable = all(m.backtestable for m, _ in self.parts)

    def symbols(self):
        return list(dict.fromkeys(s for m, _ in self.parts for s in m.symbols()))

    def weights(self, closes):
        total = pd.DataFrame(0.0, index=closes.index, columns=self.symbols())
        for m, share in self.parts:
            total = total.add(m.weights(closes) * share, fill_value=0.0)
        return total[self.symbols()]

    def describe(self):
        return " + ".join(f"{w:.0%} {m.describe()}" for m, w in self.parts)

    def frozen(self):
        if self.unfreeze_once:
            return set()
        return set().union(*(m.frozen() for m, _ in self.parts))

    def status(self):
        return [n for m, _ in self.parts for n in m.status()]

    def on_executed(self):
        for m, _ in self.parts:
            m.on_executed()
        if self.unfreeze_once:                     # the one-off resize after the overnight swap is done
            sw = overnight_swap()
            if sw and not sw.get("rescaled"):
                OVERNIGHT_SWAP.write_text(json.dumps({**sw, "rescaled": True}, indent=1))

    def sleeves(self, closes):
        return {m.name: m.latest(closes) * share for m, share in self.parts}

    def rationale(self, symbol):
        return {m.name: r for m, _ in self.parts if (r := m.rationale(symbol))}

    def exit_reason(self, symbol):
        reasons = [r for m, _ in self.parts if (r := m.exit_reason(symbol))]
        return "; ".join(reasons) or None


def _make(name: str, params: dict) -> Method:
    if name not in METHODS:
        raise ValueError(f"unknown method '{name}'. Choose from: {', '.join([*METHODS, *PRESETS])}")
    cls = METHODS[name]
    fields = {f for f in cls.__dataclass_fields__}
    def field_name(k):   # users write "symbols"; the field is symbols_ (symbols() is a method)
        return "symbols_" if k == "symbols" and "symbols_" in fields else k

    mine = {field_name(k.split(".", 1)[1]): v for k, v in params.items() if k.startswith(name + ".")}
    mine |= {field_name(k): v for k, v in params.items() if "." not in k and field_name(k) in fields}
    unknown = set(mine) - fields
    if unknown:
        raise ValueError(f"{name} has no parameter(s) {sorted(unknown)}; it takes {sorted(fields)}")
    return cls(**mine)


def build(specs: list[str], params: dict | None = None) -> Method:
    """`["pairs"]` or `["quality_screen:0.5", "index_momentum:0.5"]` or `["thesis"]`.
    params: {"pairs.entry_z": 2.5, "symbols": "SPY,QQQ"} - prefix with the
    method name to target one method in a blend."""
    params = params or {}
    expanded = []
    for spec in specs:
        name, _, share = spec.partition(":")
        if name in PRESETS:
            expanded += [(n, w * (float(share) if share else 1.0)) for n, w in preset(name)]
        else:
            expanded.append((name, float(share) if share else None))
    if len(expanded) == 1 and expanded[0][1] is None:
        return _make(expanded[0][0], params)
    parts = [(_make(n, params), w if w is not None else 1 / len(expanded)) for n, w in expanded]
    sw = overnight_swap()
    resize = bool("desk" in [x.partition(":")[0] for x in specs] and sw and not sw.get("rescaled")
                  and pd.Timestamp.today().normalize() >= pd.Timestamp(sw["from"]))
    return Blend(parts=parts, unfreeze_once=resize)
