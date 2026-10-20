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
class QualityScreen(Method):
    """Top N of the latest stock screen (output/screen_*.csv), equal weight.

    Not backtestable here: the screen's history needs point-in-time SEC data -
    see research/screen_backtest.py for that test."""

    name = "quality_screen"
    backtestable = False
    top: int = 25
    max_age_days: int = 10
    screen_glob: str = "output/screen_*.csv"

    def _picks(self) -> list[str]:
        files = sorted(glob.glob(self.screen_glob))
        if not files:
            raise RuntimeError("no screen results found - run: python -m ai_desk screen")
        path = Path(files[-1])
        date = pd.Timestamp(path.stem.removeprefix("screen_"))
        if (pd.Timestamp.today().normalize() - date).days > self.max_age_days:
            raise RuntimeError(f"latest screen is from {date.date()} - rerun `python -m ai_desk screen` "
                               f"(older than {self.max_age_days} days)")
        return list(pd.read_csv(path, index_col=0).index[:self.top])

    def symbols(self):
        return self._picks()

    def weights(self, closes):
        picks = self._picks()
        return pd.DataFrame(1 / len(picks), index=closes.index, columns=picks)


METHODS: dict[str, type[Method]] = {
    m.name: m for m in (IndexMomentum, SMACrossoverMethod, PairsMethod, QualityScreen)
}
# --method thesis is shorthand for the 50/50 structure in research/THESIS.md
PRESETS = {"thesis": [("quality_screen", 0.5), ("index_momentum", 0.5)]}


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
