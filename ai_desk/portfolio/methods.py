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
        return w.to_frame(self.symbol)


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

    * re-picked every `rebalance_days` (default weekly) from a fresh scan
    * sized by inverse volatility - calmer stocks get more, wilder ones less -
      capped at 2x an equal share, so one stock can't dominate the sleeve
    * EXIT RULE, checked on every run: any holding whose price closes below
      its moving average is sold, even between re-picks. The average is the
      one the scan used to buy (saved with the picks); exit_ma overrides it.
    """

    name = "bottleneck"
    scan_command = "python -m ai_desk bottleneck scan"
    top: int = 8
    rebalance_days: int = 7
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
        return 200

    def _exits(self, picks, closes):
        n = self._ma_days()
        avg = closes[picks].rolling(n, min_periods=n).mean().iloc[-1]
        last = closes[picks].iloc[-1]
        return set(last.index[(last < avg) & avg.notna()])


METHODS: dict[str, type[Method]] = {
    m.name: m for m in (IndexMomentum, SMACrossoverMethod, PairsMethod, QualityScreen, Bottleneck)
}
# shorthands: `thesis` is the 50/50 structure in research/THESIS.md; `aggressive`
# tilts to the stock screen (70/30) - more return and bigger drawdowns in the backtest
PRESETS = {
    "thesis": [("quality_screen", 0.5), ("index_momentum", 0.5)],
    "aggressive": [("quality_screen", 0.7), ("index_momentum", 0.3)],
    # the live desk: quality compounders + bottleneck momentum + SPY with crash insurance
    "desk": [("quality_screen", 0.5), ("bottleneck", 0.2), ("index_momentum", 0.3)],
}


@dataclass
class Blend(Method):
    """Several methods, each scaled by its share of the account."""

    name = "blend"
    parts: list = field(default_factory=list)      # [(Method, weight)]

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
        return set().union(*(m.frozen() for m, _ in self.parts))

    def status(self):
        return [n for m, _ in self.parts for n in m.status()]

    def on_executed(self):
        for m, _ in self.parts:
            m.on_executed()


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
            expanded += [(n, w * (float(share) if share else 1.0)) for n, w in PRESETS[name]]
        else:
            expanded.append((name, float(share) if share else None))
    if len(expanded) == 1 and expanded[0][1] is None:
        return _make(expanded[0][0], params)
    parts = [(_make(n, params), w if w is not None else 1 / len(expanded)) for n, w in expanded]
    return Blend(parts=parts)
