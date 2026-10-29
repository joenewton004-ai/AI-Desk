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
    "rsi_dip": {
        "label": "RSI dips",
        "plain": "Buys one of the 100 largest US companies after a short, sharp fall inside an uptrend: price above its "
                 "200-day average with RSI(14) below 30. Each dip is 10% of the desk, bought at the next open and sold "
                 "at the open after it closes back above its 5-day average (at most 10 trading days); at most 5 at "
                 "once. About 40 dips a year - most of the time it holds nothing. Amendment c52ce018 (accepted "
                 "2026-10-27) replaced the quality screen and momentum sleeves with it.",
        "screen": "Top 100 US companies by market value; close above the 200-day average and RSI(14) below 30; lowest "
                  "RSI first.",
        "metrics": "Return per dip after costs. Backtest 2014-2026 (survivors-only): +1.0% a dip in 2014-19 and +1.2% in "
                   "2020-26, 11 of 13 years positive; the desk with it and the overnight sleeve: 28.1%/yr, Sharpe 1.78 "
                   "at 0.02% overnight costs, 15.2%/yr and 0.99 at 0.05%.",
        "watch": "Average return per dip after real fills at the open; how often 5 slots are full; dips that keep falling.",
    },
    "overnight_drift": {
        "label": "Overnight",
        "plain": "Holds the 20 large US stocks with the highest return over the past 12 months, re-ranked every day "
                 "(amendment 82c84226; until 2026-10-23: the highest average overnight return, monthly) - bought in the "
                 "last minutes before the close (3:55-3:59pm New York), sold at the next open by the evening run, every trading day. "
                 "Replaced SPY momentum (amendment 330e76e0, accepted 2026-10-21). Sits in cash on nights when SPY is below its "
                 "200-day average or its picks have fallen 2.0% or more since the open (amendments 7a8b29ec, 9b951502).",
        "screen": "Top 20 by 12-month return (adjusted closes); price over $10, $20M a day traded; equal weight; "
                  "re-ranked every evening on that day's close, bought the next afternoon.",
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
    from ai_desk import overnight
    from ai_desk.portfolio.methods import DESK_REARRANGE
    sw = overnight_swap()
    live = dict(preset(LIVE_PRESET, today))
    today = (pd.Timestamp(today) if today else pd.Timestamp.today()).normalize()
    if today >= pd.Timestamp(DESK_REARRANGE["date"]):
        # amendment c52ce018: dips take 10% each (at most 5, ~5% on average); overnight buys with the rest
        return {"overnight_drift": 0.95, "rsi_dip": 0.05}
    if sw and today >= pd.Timestamp(sw["from"]):
        return live | {"overnight_drift": float(sw.get("share", overnight.SHARE))}
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
                 "index_momentum": lambda: f"{p['symbol']}, {p['lookback']}-day momentum, checked monthly",
                 "rsi_dip": lambda: f"{p['slot']:.0%} a dip, at most {p['max_positions']}; about 5% on average"}[name]()
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
                   "coin-flip direction. Financial bias, long only, reaches break-even at best; trend filter worse. "
                   "Re-run on 2016-2026 Alpaca 5-minute bars (222 of 224 top-100 names): Silver Bullet 129,658 trades, "
                   "+0.02R before costs, -0.051% after (t -21), negative every year; Judas swing 80,366 trades, -0.00R, "
                   "-0.053% after; both halves.",
        "docs": ["research/ICT.md", "research/output/ict.md", "research/output/ict_long.md"],
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
        "parameters": {"stocks": 20, "ranking": "plain 12-month return (82c84226; was average overnight return)",
                       "look_back": "12 months", "re_pick": "daily (82c84226; was monthly)", "hold": "close to next open, daily",
                       "orders": "market buy at 3:55-3:59pm (market-on-close until 2026-10-21: paper filled only part), market sell at the open",
                       "regime": "cash for the night when SPY < its 200-day average (7a8b29ec) or tonight's picks are down "
                                 "2.0%+ since the open (9b951502, 82c84226)"},
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
    "tjr_model": {
        "description": "TJR's ICT-style index-futures day trading (NQ/ES, New York open) as fixed rules: a sweep of the "
                       "prior day / Asia / London / overnight high or low between 9:30 and 11:00, a break of structure "
                       "(or inverse FVG) within 30 minutes, entry next bar, stop beyond the sweep, 2R/3R/opposite-"
                       "liquidity target; optional 1-hour 50-period bias.",
        "parameters": {"instruments": "NQ=F, ES=F", "window": "9:30-11:00 New York", "confirm": "30 minutes",
                       "stop": "beyond the sweep", "target": "2R / 3R / opposite liquidity", "bars": "5m (60 days), 1h (2 years)"},
        "status": "tested: no edge (not in the live mix)",
        "summary": "5-minute bars, 49 days, 76 trades: -0.18R to +0.05R a trade after costs (t -1.0 to 0.3), inside the "
                   "random-direction range (-0.26R to +0.12R). Hourly bars, 2024-2026, 264 trades: -0.06R (t -1.3). Same "
                   "result as the ICT test. His rules aren't published; discretion can't be tested. Re-run on QQQ/SPY "
                   "5-minute bars 2016-2026 (stand-ins for NQ/ES; no Asia/London levels): 3,401 trades, +0.007R before "
                   "costs, -0.088R after (t -3.9) = random direction (-0.087R); both halves.",
        "docs": ["research/TJR.md", "research/output/tjr.md", "research/output/tjr_long.md"],
    },
    "soros_macro_trend": {
        "description": "The rule-based core of George Soros-style global macro: follow each market's trend across asset "
                       "classes (SPY, QQQ, IWM, DIA, EFA, EEM, TLT, IEF, GLD) - hold markets whose 12-month return beat "
                       "T-bills; variants long/short, volatility-sized, top 3, 3-month trend. His discretionary bets "
                       "aren't public or testable.",
        "parameters": {"markets": "9 ETFs", "trend": "12 months vs T-bills", "rebalance": "monthly", "costs": "0.05%"},
        "status": "tested: risk control, no return edge (not in the live mix)",
        "summary": "2006-2026: long-only trend 7.3%/yr, Sharpe 0.79, worst drop -9% (2008 -1%, 2022 -7%) vs SPY 11.1%, "
                   "0.67, -51% and 60/40 8.2%, 0.72, -29%; both halves. Long/short: Sharpe 0.40 (+25% in 2008).",
        "docs": ["research/SOROS.md", "research/output/soros.md"],
    },
    "cameron_gap_and_go": {
        "description": "Ross Cameron (Warrior Trading)-style gap-and-go day trading, tested on the 750 largest US stocks "
                       "(no small-cap history available): buy gap-ups at the open, sell at the close; 5-minute first-"
                       "pullback entries on gap-ups.",
        "parameters": {"gap": "4% / 10% / 20%", "hold": "open to close", "costs": "0.10% each way"},
        "status": "tested: no edge on large caps; his small-cap universe untestable here (not in the live mix)",
        "summary": "2014-2026: gaps of 4%+ -0.13% a trade after costs (t -4.1), 10%+ -0.35%; 5-minute first pullback "
                   "-0.44% (144 trades). Only with hindsight (5x full-day volume) +1.5%. FTC settlement 2022 ($3m) over "
                   "advertising of his results.",
        "docs": ["research/CAMERON.md", "research/output/cameron.md"],
    },
    "candle_rsi": {
        "description": "Daily candle patterns (hammer, bullish engulfing, reversal close) mixed with an SMA trend filter "
                       "(200-day, 50>200) and RSI (RSI(2)<10, RSI(14)<30), exit above the 5-day SMA or after 5 days: 72 "
                       "rules picked on a development period, judged on a holdout and a second market (6 equity ETFs "
                       "1993-2026; point-in-time top-100 stocks 2014-2026, survivors-only prices).",
        "parameters": {"bars": "daily", "entry": "next open", "exit": "open after close > SMA5 (max 10 days) / 5 days",
                       "costs": "0.02% ETFs, 0.05% stocks each way"},
        "status": "tested: candles add no edge (not in the live mix); one RSI-only lead for a desk test",
        "summary": "No candle rule passed the pre-registered holdout tests; a candle never reliably beat the same rule "
                   "without it. Lead (not pre-registered): top-100 stocks above SMA200 with RSI(14)<30, sell above SMA5: "
                   "+1.0%/trade 2014-19, +1.2% 2020-26 (t ~5 each), RSI 25/30/35 and 4x costs all positive, 11 of 13 "
                   "years; ~40 trades a year, 6% invested; survivors-only. In the desk (amendment 661549dd): +0.035 Sharpe, "
                   "+0.9%/yr at 0.05% costs; at 0.20% no better in 2020-26 - fails its pre-set rule.",
        "docs": ["research/CANDLE_RSI.md", "research/output/candle_rsi.md", "research/DESK_RSI.md",
                 "research/output/desk_rsi.md"],
    },
    "candle_patterns": {
        "description": "Day-trading candle patterns on 5-minute candles from 10 years of Alpaca minute bars (SPY, then "
                       "NVDA): engulfing, hammer/shooting star (plain, VWAP reversal, VWAP trend; 30-minute or stop/2R "
                       "exits), inside-bar breakouts, opening-range breakouts (15/30 min), Gao et al. intraday momentum; "
                       "against a same-time random-day placebo. ORB re-checked on QQQ + the 10 largest companies of 2016.",
        "parameters": {"bars": "5-minute, 9:30-16:00", "entry": "next candle's open / stop order at the level",
                       "costs": "0.01% (SPY), 0.02% each way", "period": "2016-01-04 to 2026-10-26"},
        "status": "tested: no edge (not in the live mix)",
        "summary": "SPY: all 32 versions lose after costs; gross within +/-0.01% of the placebo. NVDA ORB long +0.15% a "
                   "trade (t 3.2, both halves) - but on QQQ + the 10 largest companies of 2016 it's -0.002% (5 of 11 "
                   "positive): a hindsight effect of picking the stock that rose 100x.",
        "docs": ["research/CANDLES.md", "research/output/candles.md"],
    },
    "short_edge": {
        "description": "Our own edge with shorting: own_edge.py's search turned to what lags (top-500 stocks, 25 ETFs, "
                       "~35 indicators, 5-day horizon), then long/short books: model top 20 / bottom 20, pullback long vs "
                       "the best short, walk-forward, ETF top 3 / bottom 3.",
        "parameters": {"costs": "0.05% each way per leg (ETFs 0.02%)", "borrow": "0.5%/yr (stress 2%)"},
        "status": "tested: no edge (not in the live mix)",
        "summary": "The search's best shorts fade to ~0 in the holdout; model L/S 17.7%/yr, Sharpe 0.59 (long-only 0.75), "
                   "beta 0.46, alpha t 1.1; walk-forward t 1.4; ETF L/S Sharpe 0.27, worst -70%. Survivors-only data "
                   "understates the short side.",
        "docs": ["research/SHORT_EDGE.md", "research/output/short_edge.md"],
    },
    "spy_short": {
        "description": "Shorting SPY: short-side swing rules (RSI(2) > 90, 10-day highs, three up days, tweezer top; "
                       "with/without the 200-day filter), long-above/short-below the 200-day, and an SPY hedge on the "
                       "overnight sleeve. Borrow 0.5%/yr, dividends paid, 0.01% costs each way.",
        "parameters": {"hold": "up to 5 days", "hedge": "beta from 2014-2019, applied 2020-2026"},
        "status": "tested: no edge (not in the live mix)",
        "summary": "No short rule passes (best: short RSI(2)>90 below the 200-day, +0.42%, t 1.8, 2.6/yr). Short below "
                   "the 200-day: 4.2%/yr, Sharpe 0.18, worst -47% vs cash 8.9%/0.55/-24%. Hedging the overnight sleeve "
                   "(beta 1.21) cuts its Sharpe 1.54 -> 0.66: its return is mostly the market's overnight premium.",
        "docs": ["research/SPY_SHORT.md", "research/output/spy_short.md"],
    },
    "own_edge": {
        "description": "Our own search: ~35 indicators (returns 1d-12m, RSI, moving averages, volatility, volume, range, "
                       "52-week levels, gaps, overnight/intraday, market state, calendar) on the top 500 stocks and 25 "
                       "ETFs, 5-day horizon; singles, pairs and a LightGBM model searched on development years, then one "
                       "holdout test.",
        "parameters": {"search": "stocks 2014-19, ETFs 1999-2012", "holdout": "stocks 2020-26, ETFs 2013-26",
                       "costs": "0.05% stocks / 0.02% ETFs each way"},
        "status": "tested: no new edge (not in the live mix)",
        "summary": "Best singles all collapse in the holdout; ETFs nothing. Stocks: 'pullback in a long-term winner' pairs "
                   "+0.12-0.18%/wk (t 1.0-1.6); the model +0.41%/wk (t 2.4) but a third is extra market exposure (alpha "
                   "+0.26%, t 1.7) and walk-forward t 1.5. Survivors-only.",
        "docs": ["research/OWN_EDGE.md", "research/output/own_edge.md", "research/output/own_edge_checks.md"],
    },
    "candles_daily_spy": {
        "description": "23 textbook daily candlestick patterns on SPY 1993-2026 (10 bullish after a down week, 10 bearish "
                       "after an up week, doji/inside/outside day), measured 1 and 5 days from the next open vs SPY's "
                       "normal drift, cross-checked on QQQ/IWM/DIA.",
        "parameters": {"horizons": "1 and 5 trading days", "context": "5-day trend", "costs": "0.01% each way"},
        "status": "tested: no edge (not in the live mix)",
        "summary": "1 of 40 passes (~2 by chance): tweezer top, SPY -0.32% over 5 days (t -2.7), also QQQ/IWM, not DIA; "
                   "small and bearish (the desk is long only). Hammers, engulfing, stars, dojis: nothing or flips.",
        "docs": ["research/CANDLES_DAILY_SPY.md", "research/output/candles_daily_spy.md"],
    },
    "swing_etf": {
        "description": "Swing trades up to a week on SPY/QQQ/IWM/DIA and GLD/SLV/USO/UNG daily bars (SPY from 1993): "
                       "RSI(2)/RSI(14) dips, three down days, IBS, 10-day low, 20-day breakout, weekly reversal/momentum, "
                       "turn of the month, gap down; next-open fills, long only, judged against holding the ETF.",
        "parameters": {"hold": "up to 5 trading days", "costs": "0.01-0.05% each way", "trend": "200-day average"},
        "status": "tested: an edge on index ETFs (RSI(2) dip, 10-day low), not in the live mix",
        "summary": "SPY RSI(2)<10 above the 200-day: 73% wins, +0.51% a trade, +0.36% vs holding (t 3.4), but +0.56% -> "
                   "+0.18% from 1993-2009 to 2010-26 (faded since publication); strategy 6.6%/yr, Sharpe 0.69, worst "
                   "-11%, in the market 10%. Commodity ETFs: nothing.",
        "docs": ["research/SWING_ETF.md", "research/output/swing_etf.md"],
    },
    "intraday_etf": {
        "description": "Day-trading rules on SPY/QQQ/IWM/DIA and GLD/SLV/USO/UNG minute bars 2016-2026: intraday "
                       "momentum (Gao et al. 2018; Baltussen et al. 2021), gap fade, first-hour fade, VWAP snap-back, "
                       "opening-range breakout (long, long+short), open-to-close long/short.",
        "parameters": {"costs": "0.01-0.05% each way by ETF", "fills": "minute close", "pass": "lead ETF t>=2 in both "
                       "halves + rest of the family positive in both"},
        "status": "tested: no edge (not in the live mix)",
        "summary": "18 of 18 fail. Before costs every rule averages within +-0.05% a trade; fades win 60-68% of the time "
                   "and still lose; nearest miss: long ORB on index ETFs, +0.01-0.03% after costs, t 0.9-1.6.",
        "docs": ["research/INTRADAY_ETF.md", "research/output/intraday_etf.md"],
    },
    "skill_desk_orb": {
        "description": "Jakeschincariol/day-trader-skill's opening-range day trade, automatic: 15-minute range, buy the "
                       "next open after a 5-minute close above it, stop at the range middle, target 2R, flat by 15:55; "
                       "$50 max loss a trade, $4,000 an order, 3 trades a day, -$150 daily limit, $5,000 account.",
        "parameters": {"universe": "top 100 US companies", "fills": "next 5-minute open", "costs": "0.02% each way",
                       "account": "separate $5,000 ledger, no orders"},
        "status": "separate ledger from 2026-10-28 (owner's choice; no orders, not part of the desk)",
        "summary": "2016-2026: -9.7%/yr at 0.02% costs (Sharpe -0.59), -26.8% at 0.05%; +0.03R a trade before costs. "
                   "1R target: -12.8%. Every breakout: -0.037% a trade, t -13, both halves.",
        "docs": ["research/SKILL_DESK.md", "research/output/skill_desk.md"],
    },
    "congress_copy": {
        "description": "Copy members of Congress's disclosed stock purchases (STOCK Act PTRs, House Clerk, electronic "
                       "filings 2014-2026): buy at the first open after the report was FILED, hold 20/60/120 days. "
                       "Variants: $15k+/$50k+, clusters of 2+ members, fresh reports, own account, Nancy Pelosi, sales.",
        "parameters": {"entry": "next open after the filing date", "holds": "20/60/120 trading days",
                       "costs": "0.05% each way", "benchmarks": "equal-weight cache universe, SPY"},
        "status": "tested: no edge (not in the live mix)",
        "summary": "Copy book (every purchase, 60 days) 13.9%/yr, Sharpe 0.71 vs SPY 13.7%, 0.75; no rule beyond t 1 "
                   "($50k+ +2.2% per 60 days, t 0.8; Pelosi +0.2%, 41 trades). Even from the trade date purchases "
                   "trail. House only, paper scans skipped, survivors-only prices.",
        "docs": ["research/CONGRESS.md", "research/output/congress.md"],
    },
    "green_line": {
        "description": "The 'big green line' (@pb_ema on Instagram, attributed there to Charlie Munger): hold the S&P 500 "
                       "while it closes above a moving average, T-bills below it. Tested at the usual lengths (50/100/"
                       "200/250-day EMA, 200-day SMA, 10-month SMA at month-ends, 200-day EMA with a 2% band) on SPY "
                       "(1994-) and the S&P 500 index (1970-, no dividends).",
        "parameters": {"line": "50-250 day EMA / 200-day SMA / 10-month SMA", "fills": "next open",
                       "costs": "0.05% per switch", "cash": "T-bills"},
        "status": "tested: risk control, no return edge (not in the live mix)",
        "summary": "SPY 1994-2026: buy and hold 10.8%/yr, Sharpe 0.51, worst -55%; 200-day SMA 8.6%, 0.53, -25%; "
                   "10-month SMA 9.6%, 0.59, -24% (better before 2010, worse after); 50-day EMA 7.4%, 0.48. Halves the "
                   "worst drop for 1-3%/yr less return; the desk already uses SPY's 200-day as an overnight check.",
        "docs": ["research/GREEN_LINE.md", "research/output/green_line.md"],
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
