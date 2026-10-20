"""Market data loading.

Every loader returns a DataFrame indexed by date with lowercase columns:
open, high, low, close, volume. Prices are split/dividend adjusted where
the source supports it, so returns include dividends.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["open", "high", "low", "close", "volume"]


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(1, axis=1)
    df = df.rename(columns=str.lower)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"price data is missing columns: {missing}")
    df = df[COLUMNS].copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "date"
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df.dropna(subset=["open", "close"])


def load_yahoo(symbol: str, start: str, end: str | None = None,
               cache_dir: str | Path = "data", refresh: bool = False) -> pd.DataFrame:
    """Download daily bars from Yahoo Finance, caching them as CSV.

    The cache means repeated backtests don't re-download and you get the
    same data every run (reproducibility matters when comparing ideas).
    """
    cache = Path(cache_dir) / f"{symbol.upper()}_{start}_{end or 'latest'}.csv"
    if cache.exists() and not refresh and end is not None:
        return load_csv(cache)

    import yfinance as yf  # imported lazily so tests don't need network

    raw = yf.Ticker(symbol).history(start=start, end=end, auto_adjust=True)
    if raw.empty:
        raise RuntimeError(f"no data returned for {symbol} - check the symbol and your connection")
    df = _normalise(raw)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache)
    return df


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load bars from a CSV with a date column plus open/high/low/close/volume."""
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return _normalise(df)


def synthetic_prices(n_days: int = 2520, seed: int = 7, start_price: float = 100.0,
                     start: str = "2010-01-01") -> pd.DataFrame:
    """Generate fake daily bars that switch between bull and bear regimes.

    Useful for tests and for trying the tools offline. Results on synthetic
    data say NOTHING about real markets.
    """
    rng = np.random.default_rng(seed)
    regimes = [(0.10, 0.14), (-0.15, 0.30)]  # (annual drift, annual vol)
    state, rets = 0, []
    for _ in range(n_days):
        if rng.random() < (0.004 if state == 0 else 0.015):
            state = 1 - state
        mu, sigma = regimes[state]
        rets.append(rng.normal(mu / 252, sigma / np.sqrt(252)))
    close = start_price * np.exp(np.cumsum(rets))
    prev = np.concatenate([[start_price], close[:-1]])
    gap = rng.normal(0, 0.003, n_days)
    open_ = prev * np.exp(gap)
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.004, n_days)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.004, n_days)))
    idx = pd.bdate_range(start=start, periods=n_days, name="date")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.integers(1_000_000, 5_000_000, n_days)}, index=idx)


def load_prices(symbol: str, start: str = "2005-01-01", end: str | None = None,
                source: str = "yahoo", **kwargs) -> pd.DataFrame:
    """Single entry point used by the CLI. source: yahoo | synthetic | path/to/file.csv"""
    if source == "yahoo":
        df = load_yahoo(symbol, start, end, **kwargs)
    elif source == "synthetic":
        df = synthetic_prices()
    else:
        df = load_csv(source)
    return df.loc[start:end]


def load_cash_rate(source: str = "yahoo", start: str = "1990-01-01", end: str | None = None,
                   **kwargs) -> pd.Series | None:
    """Annual T-bill rate as a decimal (0.045 = 4.5%), from Yahoo's ^IRX
    (13-week Treasury bill). For a CSV source, looks for IRX.csv in the same
    folder. Returns None if unavailable (cash then earns 0%)."""
    if source == "synthetic":
        return None
    if source == "yahoo":
        df = load_yahoo("^IRX", start, end, **kwargs)
    else:
        path = Path(source).with_name("IRX.csv")
        if not path.exists():
            return None
        df = load_csv(path)
    return (df["close"] / 100).rename("cash_rate")


# extra series a strategy can ask for via `requires`, and where to get them
EXTRA_SERIES = {"vix": "^VIX"}


def add_required_columns(prices: pd.DataFrame, columns, source: str = "yahoo",
                         **kwargs) -> pd.DataFrame:
    """Join extra daily series (e.g. the VIX close) onto the price table.

    Each value is the series' close on that date, carried forward over
    missing days, so it is known by that day's close - no lookahead.
    """
    out = prices.copy()
    for col in columns:
        if col in out.columns:
            continue
        if col not in EXTRA_SERIES:
            raise ValueError(f"don't know where to load '{col}' from")
        if source == "synthetic":
            # stand-in: VIX-like series from trailing realised vol
            from ai_desk.indicators import realized_vol
            series = (realized_vol(prices["close"], 20) * 110).bfill()
        else:
            symbol = EXTRA_SERIES[col]
            if source == "yahoo":
                extra = load_yahoo(symbol, str(prices.index[0].date()), None, **kwargs)
            else:
                extra = load_csv(Path(source).with_name(f"{symbol.lstrip('^')}.csv"))
            series = extra["close"]
        out[col] = series.reindex(out.index).ffill()
    return out


def load_many(symbols: list[str], start: str = "2005-01-01", end: str | None = None,
              source: str = "yahoo") -> dict[str, pd.DataFrame]:
    """Daily bars for several symbols as wide tables {"open": df, "close": df},
    one column per symbol, on the dates where every symbol traded.

    source: yahoo (one batched download, with retries) | synthetic |
            a folder of <SYMBOL>.csv files (e.g. market_data/)
    """
    symbols = list(dict.fromkeys(s.upper() for s in symbols))
    if source == "yahoo":
        import yfinance as yf

        from ai_desk.fundamentals.yahoo import with_retry

        raw = with_retry(lambda: yf.download(symbols, start=start, end=end, auto_adjust=True,
                                             progress=False, threads=True))
        if raw.empty:
            raise RuntimeError(f"no data returned for {symbols}")
        opens, closes = raw["Open"], raw["Close"]
        if isinstance(opens, pd.Series):              # a single symbol comes back flat
            opens, closes = opens.to_frame(symbols[0]), closes.to_frame(symbols[0])
        opens.index = closes.index = pd.to_datetime(closes.index).tz_localize(None)
    else:
        frames = {}
        for i, s in enumerate(symbols):
            if source == "synthetic":
                df = synthetic_prices(seed=7 + i)
            else:
                df = load_csv(Path(source) / f"{s.lstrip('^')}.csv")
            frames[s] = df
        opens = pd.DataFrame({s: f["open"] for s, f in frames.items()})
        closes = pd.DataFrame({s: f["close"] for s, f in frames.items()})
    missing = [s for s in symbols if s not in closes.columns or closes[s].isna().all()]
    if missing:
        raise RuntimeError(f"no price data for {missing}")
    both = closes[symbols].dropna().index.intersection(opens[symbols].dropna().index)
    opens, closes = opens.loc[both, symbols], closes.loc[both, symbols]
    sl = slice(start, end)
    return {"open": opens.loc[sl], "close": closes.loc[sl]}
