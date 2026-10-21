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
        "status": "accepted 2026-10-20 (amendment 00e1f2b8); live from 2026-10-21 (brought forward, amendment 54b8755e)",
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
    "overnight_drift": {
        "label": "Overnight",
        "plain": "Holds the 20 large US stocks that have earned the most overnight over the past year - bought in the "
                 "closing auction (3:32pm New York), sold at the next open by the evening run, every trading day. "
                 "Replaced SPY momentum (amendment 330e76e0, accepted 2026-10-21).",
        "screen": "Top 20 by average overnight return (close to next open) over 12 months; price over $10, $20M a day "
                  "traded; equal weight; re-picked monthly.",
        "metrics": "Fill cost vs the official close/open (break-even about 0.045% per trade; the desk-level case needs "
                   "about 0.02%). Backtest 2014-2026 at 0.02%: 16.7%/yr, Sharpe 0.81, worst drop -28%.",
        "watch": "Costs first: `overnight review`. No crash switch - it stays invested in falling markets (March 2020: -20%).",
    },
}


def desk_allocation(today=None) -> dict[str, float]:
    """The whole desk's split: after the overnight swap (amendment 330e76e0) SPY momentum's 30% goes to the
    overnight sleeve, which trades in the same account outside the desk method."""
    import pandas as pd

    from ai_desk.portfolio.methods import overnight_swap
    sw = overnight_swap()
    live = dict(preset(LIVE_PRESET, today))
    today = (pd.Timestamp(today) if today else pd.Timestamp.today()).normalize()
    if sw and today >= pd.Timestamp(sw["from"]):
        return live | {"overnight_drift": float(sw.get("share", 0.3))}
    return live


def sleeve_guide() -> list[dict]:
    """One row per live sleeve: 'name - allocation - screening parameters', plus a plain description and its metrics."""
    live = desk_allocation()
    rows = []
    for name, share in live.items():
        t = SLEEVE_TEXT[name]
        if name not in METHODS:                    # the overnight sleeve trades in its own account (ai_desk/overnight.py)
            rows.append({"sleeve": name, "label": t["label"], "allocation": share,
                         "line": f"{t['label']} - {share:.0%} - {t['screen']}", "plain": t["plain"], "screen": t["screen"],
                         "metrics": t["metrics"], "watch": t["watch"]})
            continue
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


# Methods researched as rules but never built as tradeable code (no class in METHODS).
RESEARCH_METHODS = {
    "asymmetric_bets": {
        "description": "Michael Sikand's 'asymmetric bets' style (Autopilot pilot), as testable rules: a stock in a hot "
                       "industry, fast revenue growth, cheaper than its industry peers on price-to-sales, 30-75% off "
                       "its 12-month high; hold the top 5 at 20% each, re-picked monthly.",
        "parameters": {"theme": "industry in top quarter by 6-month momentum", "growth": "revenue growth top third, >15%",
                       "discount": "P/S below industry median", "off_high": "30-75% below 12-month high",
                       "holdings": 5, "rebalance": "monthly"},
        "status": "tested, no edge (not in the live mix)",
        "summary": "2014-2026 on the 750 largest US companies: 0.4%/yr, Sharpe 0.00 vs the average stock 11.1% (0.59) "
                   "and SPY 13.6% (0.81); every variant lost to the average stock. Buying 30-75% off the high cost "
                   "0.61%/month (52-week-high effect); only the industry-momentum rule helped. Survivors-only prices.",
        "docs": ["research/ASYMMETRIC.md", "research/output/asymmetric.md"],
    },
    "vcp_swing": {
        "description": "Swing trading on VCP breakouts (Minervini's volatility contraction pattern, from the vcp-screener "
                       "skill in tradermonty/claude-trading-skills) as fixed rules: a stock in a strong uptrend, a quiet "
                       "tightening pause, then a breakout above its 20-day high on 1.5x volume; bought at the next open.",
        "parameters": {"positions": "up to 10 of 10%", "stop": "8% below entry", "exit": "close below the 50-day average",
                       "target": "+25%", "max_hold": "40 trading days", "universe": "750 largest US companies"},
        "status": "tested, no edge (not in the live mix)",
        "summary": "2014-2026: 2.8%/yr, Sharpe 0.13 vs the average stock 12.1% (0.59) and SPY 13.7% (0.72); 1,123 trades, "
                   "39% winners, +0.38% per trade; loses money at 0.30% costs; no setting tested gets above 5.6%/yr. "
                   "Beats random strong-trend picks, so the pattern adds a little. Survivors-only prices.",
        "docs": ["research/SWING.md", "research/output/swing.md"],
    },
    "ict_daytrading": {
        "description": "ICT (Inner Circle Trader) day-trading models as fixed rules on the 100 largest US companies: the "
                       "Silver Bullet (5-min fair value gap after a liquidity sweep, 10-11am New York) and the Judas swing "
                       "(fade a first-hour fake-out beyond the prior day's high/low), optionally with the quality score "
                       "choosing the side (long strong companies, short weak ones) or a 50-day trend filter.",
        "parameters": {"target": "2R", "stop": "beyond the sweep", "exit": "end of day", "costs": "0.03% each way",
                       "universe": "100 largest US companies"},
        "status": "tested, no edge (not in the live mix)",
        "summary": "Silver Bullet (60 days, 2,974 trades): +0.01R before costs, -0.06% per trade after (t -3.5). Judas swing "
                   "(3 years, 21,483 trades): -0.01R, -0.07% after costs (t -10), negative in all 13 quarters. Same as a "
                   "coin-flip direction. Financial bias, long only, reaches break-even at best; trend filter worse.",
        "docs": ["research/ICT.md", "research/output/ict.md"],
    },
    "lynch_rules": {
        "description": "Peter Lynch's checkable rules (One Up on Wall Street, 1989): PEG under 1 (P/E / earnings growth %), "
                       "the dividend-adjusted Lynch ratio (growth + yield) / P/E of 2+, growth categories (stalwarts, "
                       "fast growers 18-30%), low debt, inventory not outpacing sales, no share dilution.",
        "parameters": {"growth": "3-year net-income growth (trailing)", "peg": "< 1", "lynch_ratio": ">= 2",
                       "debt_equity": "< 0.5 or net cash", "rebalance": "quarterly", "universe": "750 largest US companies"},
        "status": "tested, no edge (not in the live mix)",
        "summary": "2014-2026 point-in-time SEC data: every Lynch version made 9.2-10.6%/yr (Sharpe 0.42-0.53) vs the average "
                   "stock 11.5% (0.61), SPY 13.8% (0.83) and the desk's quality screen 17.9% (0.89). PEG under 1 alone: "
                   "-0.07%/quarter vs the average stock, flipping sign between 2014-19 and 2020-26. Survivors-only prices.",
        "docs": ["research/LYNCH.md", "research/output/lynch.md"],
    },
    "short_term_effects": {
        "description": "Five documented short-term effects with next-open fills: weekly pullback bought at Monday's open, "
                       "post-earnings drift after the 10-Q filing, the 52-week high (monthly and swing), overnight vs "
                       "daytime returns, and the opening range breakout on stocks in play (60-day preview).",
        "parameters": {"costs": "0.02% / 0.05% / 0.10% each way", "fills": "the open after the decision close",
                       "universe": "750 largest US companies (100 for the breakout preview)"},
        "status": "tested, no edge as strategies (not in the live mix)",
        "summary": "Pullback 11.1%/yr at 0.02% costs (Sharpe 0.49) vs the average stock 12.1% (0.59). Earnings drift: the "
                   "worst-surprise fifth lags by 0.55% over 60 days (t -2.6), the best doesn't lead - a possible filter. "
                   "52-week high: lower risk, lower return. Overnight returns: +9%/yr gross, negative after costs. "
                   "Breakout: negative even before costs. Survivors-only prices.",
        "docs": ["research/SWING_EDGES.md", "research/output/swing_edges.md", "research/output/orb.md"],
    },
    "overnight_drift": {
        "description": "Overnight momentum (Lou, Polk & Skouras 2019): each month take the 20 large stocks with the highest "
                       "average overnight return (close to next open) over the past 12 months; hold them only overnight - "
                       "buy at the close, sell at the next open - via the closing and opening auctions.",
        "parameters": {"stocks": 20, "look_back": "12 months", "re_pick": "monthly", "hold": "close to next open, daily",
                       "orders": "market-on-close buy, market-on-open sell"},
        "status": "accepted as the desk's 30% sleeve (amendment 330e76e0) - live from `overnight activate`",
        "summary": "Persistence out of sample: the top tenth beats the bottom by 7.3 bp a night (t 6.4, 82% of 150 months, "
                   "both halves). Strategy 2014-2026: 27.7%/yr at zero cost, 15.5% (Sharpe 0.70) at 0.02% each way vs the "
                   "average stock 12.6% (0.62); break-even about 0.045% each way; loses at 0.05%. Survivors-only prices.",
        "docs": ["research/OVERNIGHT.md", "research/output/overnight.md", "ai_desk/overnight.py"],
    },
    "vwap_ema": {
        "description": "Two intraday indicator strategies on the 100-150 largest US companies: (A) EMA9/VWAP crossover, "
                       "both sides and long only; (B) Trend + Momentum + Confirmation - 20 EMA above 50 EMA, price above "
                       "VWAP, volume 1.5x average, break of the previous day's or opening-range high; stop at the swing "
                       "low/20 EMA, 2R target.",
        "parameters": {"bars": "5-min (60 days), 1-min (30 days), hourly (3 years)", "costs": "0.03% each way",
                       "exit": "signal, stop/target or the close"},
        "status": "tested, no edge (not in the live mix)",
        "summary": "A: about zero before costs, -0.06% to -0.08% per trade after (t -10 to -12). B: negative even before "
                   "costs, -0.07% to -0.14% after; random entries on the same days did better (+0.14% hourly) - the "
                   "setup confirms after the move. 3R, pullback entry and no-volume variants don't help.",
        "docs": ["research/VWAP_EMA.md", "research/output/vwap_ema.md"],
    },
    "minervini_sepa": {
        "description": "Mark Minervini's SEPA as fixed rules: Trend Template (above rising, stacked 50/150/200-day "
                       "averages, near highs) + RS rating 70+, EPS +25% and sales +20% on a year earlier (SEC filings, "
                       "point-in-time), a tight-base breakout entry, a 7.5% stop raised to break-even at +15%, then a "
                       "50-day exit; optional SPY 200-day market filter.",
        "parameters": {"rs": "70+", "eps_growth": "25%+", "sales_growth": "20%+", "stop": "7.5%",
                       "break_even": "+15%", "positions": "10 x 10%", "fills": "next open"},
        "status": "tested: no edge (not in the live mix)",
        "summary": "2014-2026, survivors-only: full SEPA 5.2%/yr, Sharpe 0.30, worst -24% (37% invested); Trend Template "
                   "alone 11.8%, 0.45, -48%; vs equal-weight universe 12.1%, 0.59 and SPY 13.7%, 0.72. Growth alone "
                   "+0.52%/month vs the universe (t 2.0) is the only lead.",
        "docs": ["research/MINERVINI.md", "research/output/minervini.md"],
    },
    "leveraged_spy": {
        "description": "A 2x/3x S&P 500 fund (SSO/UPRO, simulated back to 1994 and checked against the real funds) "
                       "traded on SPY's signals with strict risk rules: SPY above its 200-day average, leverage capped "
                       "at 25% / SPY's volatility, out while the VIX is above 30, a 10% stop with a trend re-entry.",
        "parameters": {"leverage": "2x or 3x", "trend": "200-day average, 1% band", "vol_cap": "25% annual",
                       "vix": "out above 30", "stop": "10% from entry", "fills": "next open"},
        "status": "tested: risk control works, no edge (not in the live mix)",
        "summary": "1994-2026: 3x strict 12.7%/yr, Sharpe 0.53, worst -37%; 2x strict 11.6%, 0.53, -31%; vs SPY 10.8%, "
                   "0.51, -55% and 3x buy and hold 14.9%, 0.49, -98%. 2010-2026 plain SPY was better (Sharpe 0.77 vs "
                   "0.58-0.61). Walk-forward tuning did worse than a fixed 200-day.",
        "docs": ["research/LEVERAGED.md", "research/output/leveraged.md"],
    },
    "drawdown_breaker": {
        "description": "Account-level circuit breaker (drawdown-circuit-breaker skill, tradermonty/claude-trading-skills): "
                       "after a 2% day, 5% week or 8% month, no new buys (or: go to cash) until the next day / Monday / month.",
        "parameters": {"day_limit": 0.02, "week_limit": 0.05, "month_limit": 0.08, "modes": "freeze buys | go to cash"},
        "status": "tested, no benefit; rejected 2026-10-21",
        "summary": "On the desk 2014-2026 (daily): no breaker 16.4%/yr, Sharpe 0.81, worst -33.4%; freeze 15.9%, 0.79, -33.4%; "
                   "go to cash 11.1%, 0.61, -35.7%. The desk buys only at re-picks, so freezing rarely matters, and "
                   "cutting to cash misses the rebounds. Survivors-only prices.",
        "docs": ["research/CIRCUIT_BREAKER.md", "research/output/circuit_breaker.md"],
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
    live = desk_allocation()
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
    for name, m in RESEARCH_METHODS.items():
        methods.append({"name": name, "in_live_mix": name in live, "allocation": live.get(name, 0.0),
                        "description": m["description"],
                        "parameters": m["parameters"], "status": m["status"], "evidence_summary": m["summary"],
                        "docs": m["docs"], "amendments": [a for a in amendments() if a["method"] == name]})
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "live_preset": LIVE_PRESET, "live_allocation": live, "presets": PRESETS, "methods": methods}
    if write:
        tradebook.DIR.mkdir(parents=True, exist_ok=True)
        (tradebook.DIR / "methods.json").write_text(json.dumps(out, indent=1, default=str))
    return out
