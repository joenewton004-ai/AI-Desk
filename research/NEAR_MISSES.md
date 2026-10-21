# Picks vs near misses: when the watchlist beats the picks, should we change the scoring?

_October 2026. Code: `research/near_misses.py`. Tables: [`output/near_misses.md`](output/near_misses.md).
Survivors-only prices (they flatter picks and near misses about equally). Research, not advice._

## Why ask

The watchlist's first day (2026-10-20 close) had the near misses ahead of the picks in both
sleeves: quality screen +1.00% vs +0.32%, bottleneck +0.31% vs −0.13%. One day is noise. The
useful question is whether near misses beat picks *historically*, and whether a different
scoring would have chosen better. This tests that at every past re-pick since 2014.

## Results

**Quality screen.** Picks are the top 25 gate-passers by score; near misses are the other ~150 gate-passers.
Results are over the next quarter, across 50 quarters.

| | Avg next-quarter return | Picks beat them |
|---|---|---|
| Picks (top 25) | +4.75% | |
| Near misses ranked 26-50 | +4.00% | 60% of quarters |
| Near misses ranked 51+ | +2.93% | 68% of quarters |
| All near misses | +3.15% | 64% (gap +1.6%/quarter, t = 2.5) |

- **The ranking holds up.** It worked in both halves, more strongly since 2020 (t = 2.1, vs 1.4 in 2014-19).
- **Ranks 26-50 are closest to the picks.** They are similar companies, so that's expected.

**Momentum sleeve (live from 2026-11-03).** Top 20 vs ranks 21-40, next 4 weeks, 163 re-picks.

| Group | Avg 4-week return |
|---|---|
| Picks (top 20) | +2.17% |
| Near misses (ranks 21-40) | +0.91% |

- **Picks won 66% of the time** (t = 4.0), and in both halves.
- **The edge is at the very top.** Within the strong-trend stocks, momentum rank barely predicts
  returns (rank correlation +0.004). The gain comes from the strongest few names: being in the top
  20 matters, but ranking rank 25 against rank 60 doesn't.

**Scoring weights (quality screen).** Which categories lined up with the next quarter's return
among gate-passers:

| Category | Weight now | Link to next quarter | 2014-19 | 2020-26 |
|---|---|---|---|---|
| Quality | 35% | +0.033 (t = 1.9) | +0.061 | +0.007 |
| Growth | 25% | +0.013 | +0.011 | +0.015 |
| Value | 20% | −0.008 | −0.068 | +0.047 |
| Strength | 10% | +0.005 | | |
| Momentum | 10% | +0.013 | +0.027 | −0.000 |
| Overall score | | +0.033 (t = 2.1) | +0.023 | +0.043 |

Re-weighting the score:

| Weights | Top-25 return/quarter | Beat current weights |
|---|---|---|
| Current | +4.75% | |
| Equal | +4.82% | 48% of quarters |
| More momentum | +4.83% | 46% |
| More value | +4.10% | 46% |
| Quality only | +4.23% | 44% |

- **No reweighting beats the current one in both halves.**
  - Equal weights won only after 2020 and lost before.
  - More momentum adds +0.08% a quarter but loses more often than it wins.
  - Value flips sign between the halves.
- **Value is the one to watch.** It hurt in 2014-19 and helped in 2020-26. That's the kind of flip
  that makes a short live window look like "the scoring is wrong".

## Verdict

**No change to the parameters or scoring.** Over 12 years the picks beat the near misses about
two-thirds of the time in both sleeves. That means the near misses will also win about one
re-pick in three by chance. A cohort where they win is expected, not a sign of a broken ranking.

**What would justify a change (fixed in advance):** near misses beating the picks beyond chance
over a full cohort (the daily check's "worth a test"), repeated across several cohorts. Any change
would then be backtested here before it becomes an amendment.

## The daily check

`python -m ai_desk journal watchlist` (in the scheduled 4:20pm run) now also prints, for each current cohort:
- **The gap:** picks minus near misses since the decision close.
- **How unusual it is:** how often a random group of the same size from the same cohort did as well
  as the picks (a permutation test).
- **What explains it:** the sector with the biggest effect, and which score lined up with returns so far.
- **A verdict under fixed rules:** "too early" before the re-pick (63 trading days for the quality
  screen, 20 for momentum, 10 for bottleneck). After the re-pick: "worth a test" only beyond chance,
  else "within noise" or "ranking held up".

Each day is logged to `journal/watchlist_daily.jsonl` and shown on the dashboard's Watchlist tab.
