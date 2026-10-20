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
from ai_desk.portfolio.methods import DESK_SWITCH, METHODS, PRESETS, preset

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
    "momentum": {
        "summary": "2014-2026, top 20 of the 750 largest by 6-month return, re-picked every 4 weeks, with the 100-day "
                   "exit: 19.8%/yr, Sharpe 0.76, worst drop -30% as a sleeve (vs the flow rotation's 17.8%, 0.63, -45%); "
                   "desk 16.5%/yr, Sharpe 0.92 vs 0.88. Survivors-only prices.",
        "docs": ["research/MOMENTUM_SLEEVE.md", "research/WEEKLY.md"],
        "status": "accepted 2026-10-20 (amendment 00e1f2b8); live from 2026-11-03",
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


# Plain-English guide to the three live sleeves. Allocation comes from PRESETS (the live mix), the
# top-N / re-pick / moving-average figures from the method classes, so they can't drift from the code.
SLEEVE_TEXT = {
    "quality_screen": {
        "label": "Quality screen",
        "plain": "Owns the 25 highest-scoring large, profitable, growing US companies, equal weight, and refreshes the list every quarter. Buy and hold between refreshes; no stop-loss (none was backtested).",
        "screen": ("US companies above $10B; must pass: average ROIC 12%+, no year of negative ROIC, revenue up in 60%+ of "
                   "years, positive free cash flow. Ranked by score: quality 35%, growth 25%, value 20%, financial "
                   "strength 10%, momentum 10%."),
        "metrics": "Return vs the equal-weight S&P 500 (RSP) first, then SPY. Backtest: 17.9%/yr, Sharpe 0.89 vs same-universe 11.4%.",
        "watch": "Each quarter's 25 picks vs RSP; whether the average pick is still cheap enough (forward P/E, FCF yield).",
    },
    "bottleneck": {
        "label": "Bottleneck (money-flow rotation)",
        "plain": "Finds where money is flowing and holds the 8 best stocks there, especially the scarce suppliers (e.g. power for AI data centres). Refreshes every 2 weeks and sells any stock that closes below its 100-day average.",
        "screen": ("Industries ranked by money flow (relative strength vs SPY); stocks above $10B (theme-map companies from $2B) must pass: revenue +10% "
                   "year on year, gross margin not falling, price above its 100-day average. Score: bottleneck 35%, "
                   "flow 25%, asymmetry 25%, insider buying 15%. Weighted by inverse volatility."),
        "metrics": "Return vs SPY after costs. Backtest (price flows only): 17.0%/yr, Sharpe 0.60, worst drop -46%. An isolated best setting - expect less.",
        "watch": "Do stocks keep falling after the 100-day exit? Does it beat SPY after its higher trading costs?",
    },
    "momentum": {
        "label": "Momentum",
        "plain": "Holds the 20 large US companies whose shares rose most over the last 6 months, equal weight, refreshed every 4 weeks. Any holding that closes below its 100-day average is sold and stays out until the next refresh.",
        "screen": ("US companies above $10B, trading above their 200-day average, ranked by their 6-month price gain "
                   "(skipping the latest week). Top 20, equal weight."),
        "metrics": "Return vs SPY after costs. Backtest 2014-2026: 19.8%/yr, Sharpe 0.76, worst drop -30%; replaced the bottleneck flow rotation (17.8%, 0.63, -45%).",
        "watch": "Does it keep beating SPY after costs? How often does the 100-day exit fire, and do exited stocks keep falling?",
    },
    "index_momentum": {
        "label": "SPY momentum (crash insurance)",
        "plain": "Holds SPY while its 12-month return is positive; moves to cash (earning T-bills) when it turns negative. Checked monthly, so it trades about once a year.",
        "screen": "Holds SPY while its 12-month return is above zero; otherwise cash.",
        "metrics": "Worst drop vs SPY buy and hold. Backtest 1994-2026: 10.6%/yr vs 10.8%, worst drop -34% vs -55%.",
        "watch": "It should lag in strong bull markets and justify itself in a long bear market. Judge it on the worst drop, not return.",
    },
}


def sleeve_guide() -> list[dict]:
    """One row per live sleeve: 'name - allocation - screening parameters', plus a plain description and its metrics."""
    live = dict(preset(LIVE_PRESET))
    rows = []
    for name, share in live.items():
        t = SLEEVE_TEXT[name]
        p = _params(METHODS[name])
        facts = {"quality_screen": lambda: f"top {p['top']}, re-pick every {p['rebalance_months']} months",
                 "bottleneck": lambda: f"top {p['top']}, re-pick every {p['rebalance_days']} days, exit below the 100-day average",
                 "momentum": lambda: f"top {p['top']}, re-pick every {p['rebalance_days']} days, exit below the {p['exit_ma']}-day average",
                 "index_momentum": lambda: f"{p['symbol']}, {p['lookback']}-day momentum, checked monthly"}[name]()
        if name == "bottleneck":
            t = {**t, "plain": f"Being replaced by plain momentum at its {DESK_SWITCH['date']} re-pick (amendment "
                               "00e1f2b8, accepted 2026-10-20). " + t["plain"]}
        rows.append({"sleeve": name, "label": t["label"], "allocation": share,
                     "line": f"{t['label']} - {share:.0%} - {facts}; {t['screen']}",
                     "plain": t["plain"], "screen": t["screen"], "metrics": t["metrics"], "watch": t["watch"]})
    return rows


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
    live = dict(preset(LIVE_PRESET))
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
