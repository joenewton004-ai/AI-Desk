"""Methodology register and amendment log.

The register describes every method as it is RIGHT NOW (generated from the
code, so it can't drift from what actually trades), the live allocation, and
the evidence behind each one. Amendments are proposed changes, tracked from
idea to decision:

    proposed -> testing -> accepted | rejected      (accepted ones get applied in code)

Rule: no method changes without a backtest or paper-trading evidence and the
user's approval (see CLAUDE.md). Files: journal/methods.json (generated),
journal/amendments.jsonl (the log).
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import uuid
from datetime import datetime, timezone

from ai_desk import tradebook
from ai_desk.portfolio.methods import METHODS, PRESETS

LIVE_PRESET = "desk"
STATUSES = ("proposed", "testing", "accepted", "rejected")

EVIDENCE = {
    "quality_screen": {
        "summary": "Point-in-time 2014-2026: top 25 re-picked quarterly 17.9%/yr (Sharpe 0.89) vs same-universe "
                   "11.4% and SPY 13.8%; edge vs universe t~1.8. Survivors-only prices.",
        "docs": ["research/THESIS.md", "research/output/screen_backtest.md"],
        "status": "promising, not proven",
    },
    "bottleneck": {
        "summary": "Only the price-flow part is testable: 100-day MA, re-picked every 2 weeks 17.0%/yr "
                   "(Sharpe 0.60, -46% worst drop) vs SPY 13.7% (0.75); an isolated best setting. "
                   "Fundamental fingerprints, insider signal and theme map untested.",
        "docs": ["research/BOTTLENECK.md", "research/output/bottleneck_backtest.md"],
        "status": "experiment",
    },
    "index_momentum": {
        "summary": "SPY 1994-2026: 10.6%/yr vs 10.8% buy & hold, worst drop -34% vs -55%; robust across "
                   "periods, markets and costs. Cost ~1%/yr in 2014-2026 (fast rebounds).",
        "docs": ["research/FINDINGS.md"],
        "status": "proven as crash insurance",
    },
    "index_rotation": {
        "summary": "2004-2026, 6 indices (SPY QQQ IWM DIA EFA EEM): top 2 11.6%/yr, Sharpe 0.60 vs the SPY sleeve "
                   "9.4%, 0.58 - more risk, same Sharpe; gains all from 2004-12, relies on QQQ, fragile to "
                   "lookback; walk-forward 8.3% (0.45) vs 10.2% (0.61). 'Avoid the worst' (drop_worst, rank weights): "
                   "Sharpe 0.54-0.58, walk-forward 8.0% (0.44). No improvement inside the desk.",
        "docs": ["research/INDEX_ROTATION.md", "research/output/index_rotation.md"],
        "status": "tested, no edge over SPY sleeve",
    },
    "sma_crossover": {
        "summary": "50/200 on SPY: same insurance as momentum, near-identical results. Not in the live mix.",
        "docs": ["research/METHODS.md"], "status": "works, redundant",
    },
    "pairs": {
        "summary": "Duopoly pairs long/short: market-neutral but ~1%/yr above T-bills, cost-sensitive. "
                   "Not in the live mix.",
        "docs": ["research/METHODS.md"], "status": "weak",
    },
}


def _params(cls) -> dict:
    out = {}
    for f in dataclasses.fields(cls):
        if f.name.startswith("_") or f.name in ("screen_glob", "lock_path"):
            continue
        v = f.default if f.default is not dataclasses.MISSING else (
            f.default_factory() if f.default_factory is not dataclasses.MISSING else None)
        out[f.name.rstrip("_")] = v
    return out


def _summary(cls) -> str:
    doc = inspect.getdoc(cls) or ""
    return doc.split("\n\n")[0].replace("\n", " ")


def amendments() -> list[dict]:
    return tradebook._read("amendments.jsonl")


def propose(method: str, proposal: str, rationale: str, author: str = "you") -> dict:
    row = {"id": uuid.uuid4().hex[:8], "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "method": method, "proposal": proposal, "rationale": rationale, "author": author,
           "status": "proposed", "evidence": "", "decided_utc": None}
    tradebook._append("amendments.jsonl", row)
    return row


def decide(amendment_id: str, status: str, evidence: str = "") -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    rows = amendments()
    for r in rows:
        if r["id"] == amendment_id:
            r["status"] = status
            r["evidence"] = evidence or r.get("evidence", "")
            if status in ("accepted", "rejected"):
                r["decided_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            tradebook._write("amendments.jsonl", rows)
            return r
    raise KeyError(f"no amendment {amendment_id}")


def register(write: bool = True) -> dict:
    live = dict(PRESETS[LIVE_PRESET])
    methods = []
    for name, cls in METHODS.items():
        methods.append({
            "name": name, "in_live_mix": name in live, "allocation": live.get(name, 0.0),
            "description": _summary(cls), "parameters": _params(cls),
            "status": EVIDENCE.get(name, {}).get("status", "untested"),
            "evidence_summary": EVIDENCE.get(name, {}).get("summary", ""),
            "docs": EVIDENCE.get(name, {}).get("docs", []),
            "amendments": [a for a in amendments() if a["method"] == name],
        })
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "live_preset": LIVE_PRESET, "live_allocation": live, "presets": PRESETS, "methods": methods}
    if write:
        tradebook.DIR.mkdir(parents=True, exist_ok=True)
        (tradebook.DIR / "methods.json").write_text(json.dumps(out, indent=1, default=str))
    return out
