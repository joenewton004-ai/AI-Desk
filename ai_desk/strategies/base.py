"""Strategy interface.

A strategy answers one question: "given everything known at today's close,
how much of the asset do I want to hold?" It returns a target exposure per
day between -1 (fully short) and 1 (fully long), where 0 is cash.

Strategies do NOT size positions for risk or place orders - that is the job
of the risk module and the broker. Keeping these separate means you can test
an edge on its own and swap risk rules without touching it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import ClassVar

import pandas as pd


@dataclass
class Strategy(ABC):
    name = "base"
    requires: ClassVar[tuple] = ()   # extra columns needed beyond OHLCV, e.g. ("vix",)

    @abstractmethod
    def target_exposure(self, prices: pd.DataFrame) -> pd.Series:
        """Exposure decided at each day's close. Must not use future data."""

    @property
    def params(self) -> dict:
        return asdict(self)

    def describe(self) -> str:
        args = ", ".join(f"{k}={v}" for k, v in self.params.items())
        return f"{self.name}({args})"
