"""Download and cache fundamentals from Yahoo Finance.

Yahoo rate-limits heavy use (HTTP 401/429), so every call retries with
backoff, downloads run a few at a time, and results are cached on disk for
a week - financial statements only change once a quarter.
"""

from __future__ import annotations

import io
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

CACHE = Path("data/fundamentals")
INFO_FIELDS = ["longName", "sector", "industry", "marketCap", "enterpriseValue", "forwardPE",
               "trailingPE", "forwardEps", "trailingPegRatio", "financialCurrency", "quoteType",
               "sharesOutstanding", "currentPrice"]
STATEMENTS = {"income": "income_stmt", "balance": "balance_sheet",
              "cashflow": "cashflow", "q_income": "quarterly_income_stmt"}


def with_retry(fn, tries: int = 6, base_delay: float = 4.0):
    """Call fn(), retrying with exponential backoff (4s, 8s, 16s...) on errors."""
    for attempt in range(tries):
        try:
            return fn()
        except Exception:  # noqa: BLE001 - yfinance raises many error types for throttling
            if attempt == tries - 1:
                raise
            time.sleep(base_delay * 2 ** attempt)


def _cache_path(symbol: str, cache_dir: Path) -> Path:
    return cache_dir / f"{symbol.upper()}.json"


def _complete(raw: dict) -> bool:
    """yfinance often returns EMPTY tables instead of raising when Yahoo
    throttles. A record without statements or a market cap is a failed
    download, not a company with no data - never cache or trust it."""
    return bool(raw.get("income") and raw.get("balance") and (raw.get("info") or {}).get("marketCap"))


def load_cached(symbol: str, cache_dir: Path = CACHE, max_age_days: float = 7) -> dict | None:
    p = _cache_path(symbol, cache_dir)
    if not p.exists():
        return None
    raw = json.loads(p.read_text())
    if not _complete(raw):
        return None
    age = datetime.now(timezone.utc) - datetime.fromisoformat(raw["fetched"])
    if age.days > max_age_days:
        return None
    return _decode(raw)


def _decode(raw: dict) -> dict:
    out = {"symbol": raw["symbol"], "fetched": raw["fetched"], "info": raw["info"]}
    for key in STATEMENTS:
        out[key] = pd.read_json(io.StringIO(raw[key]), orient="split") if raw.get(key) else pd.DataFrame()
    return out


def fetch_company(symbol: str, cache_dir: Path = CACHE, max_age_days: float = 7) -> dict:
    """Statements + key info for one company, from cache when fresh."""
    cached = load_cached(symbol, cache_dir, max_age_days)
    if cached is not None:
        return cached

    raw = with_retry(lambda: _download(symbol))
    p = _cache_path(symbol, cache_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(raw))
    return _decode(raw)


def _download(symbol: str) -> dict:
    import yfinance as yf

    t = yf.Ticker(symbol)
    raw = {"symbol": symbol.upper(), "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    info = t.info or {}
    raw["info"] = {k: info.get(k) for k in INFO_FIELDS}
    for key, attr in STATEMENTS.items():
        df = getattr(t, attr)
        raw[key] = df.to_json(orient="split", date_format="iso") if df is not None and not df.empty else None
    if not _complete(raw):
        raise RuntimeError(f"incomplete data for {symbol} (Yahoo throttling?)")
    return raw


def fetch_many(symbols: list[str], cache_dir: Path = CACHE, max_age_days: float = 7,
               workers: int = 3, progress: bool = True) -> dict[str, dict]:
    out, failed = {}, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_company, s, cache_dir, max_age_days): s for s in symbols}
        for i, fut in enumerate(as_completed(futures), 1):
            s = futures[fut]
            try:
                out[s] = fut.result()
            except Exception as e:  # noqa: BLE001
                failed.append(s)
                if progress:
                    print(f"  [!] {s}: {str(e)[:80]}")
            if progress and (i % 25 == 0 or i == len(symbols)):
                print(f"  fundamentals: {i}/{len(symbols)}")
    if failed:
        print(f"  {len(failed)} companies failed to download: {', '.join(failed[:20])}")
    return out


def price_momentum(symbols: list[str], months: int = 12, skip_months: int = 1) -> pd.Series:
    """12-1 month price momentum: return from 12 months ago to 1 month ago.
    Skipping the latest month avoids short-term reversal noise (standard practice)."""
    import yfinance as yf

    data = with_retry(lambda: yf.download(symbols, period="14mo", auto_adjust=True,
                                          progress=False, threads=True))
    close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]].set_axis(symbols, axis=1)
    close = close.dropna(how="all")
    end = close.index[-1] - pd.DateOffset(months=skip_months)
    start = close.index[-1] - pd.DateOffset(months=months)
    p_end = close.loc[:end].ffill().iloc[-1]
    p_start = close.loc[:start].ffill().iloc[-1]
    return (p_end / p_start - 1).rename("momentum_12_1")
