# EP01 Shorts v2 - edit notes

Built by `build.py` in this folder (re-run after any audio, mood or narration change; nothing is typed by hand: timings from
ffprobe, numbers from research/output/ict_long.md and research/ICT.md). Draft only: not committed, not uploaded.

Layout (1080x1920, 30 fps): card #222c3b at x 60-940 / y 250-830 (visual for the current part), caption at x 60-900 / y 850-1100 (72 px, shrinks to 56 px if needed, max 3 lines, key numbers orange), avatar "Up" (triangle 420 px tall, apex y 1110, bottom y 1530, centre x 330), logo mark + "Educational, not financial advice" right of it (y 1300-1510). Nothing below y 1530 (YouTube Shorts title/UI area).

Timing: paragraph slot = its mp3 duration + the probed gap (0.4963 s). Sentence starts (split on `(?<=[.?!])\s+`) and caption-chunk starts are estimated from character share, so they can be ~0.3-0.5 s off. Mouth alternates closed/open every 0.15 s while a sentence is spoken (closed in the paragraph gap; shocked keeps its O-mouth); the avatar rises 3 px for 0.1 s on each mood change. No zoom anywhere.

## short1.mp4 (0:36.63, video 36.633 s vs joined mp3 36.624 s; 18 distinct stills)

| start | mood | card | caption (sentence) |
|---|---|---|---|
| 0:00.00 | neutral | trades | **P1** We tested ICT's Silver Bullet on ten years of data - 129,658 trades on the 100 biggest US stocks. |
| 0:05.27 | | | ~ caption continues: "129,658 trades on the 100 biggest US stocks." |
| 0:10.14 | thinking | sb_R | **P2** Before costs, it made 0.02 of what it risked per trade. |
| 0:14.30 | thinking | sb_R | Flipping a coin for the direction made about zero. |
| 0:18.52 | sceptical | sb_after | **P3** After a cheap 0.03% cost each way, both lost money. |
| 0:22.81 | sceptical | sb_after | ICT beat the coin by one hundredth of a percent a trade. |
| 0:27.92 | neutral | rules | **P4** These are community rules made precise, not a trader's judgement. |
| 0:30.57 | | | ~ caption continues: "not a trader's judgement." |
| 0:32.22 | neutral | end_test | Full test on the channel. |
| 0:33.91 | neutral | end_test | Educational, not financial advice. |

Cards used: `trades` = big number 129,658 trades, 10 years, 100 biggest US stocks; `sb_R` = before costs, avg R: Silver Bullet +0.02R vs coin flip -0.00R on a -1R..+1R axis; `sb_after` = after costs per trade: SB -0.051% vs coin -0.061%; ICT beat the coin by 0.010%; `rules` = "Fixed-rule version. Discretion not tested."; `end_test` = logo + "Full test on Backtest Bench"

Caption font sizes used: 72 px; fit problems: 0.

## short2.mp4 (0:29.70, video 29.700 s vs joined mp3 29.701 s; 20 distinct stills)

| start | mood | card | caption (sentence) |
|---|---|---|---|
| 0:00.00 | neutral | grid_empty | **P1** Ten years. |
| 0:00.89 | neutral | grid_empty | Forty-four quarters. |
| 0:02.59 | neutral | grid_empty | Here's every quarter of ICT's Silver Bullet, after costs, on large US stocks. |
| 0:06.24 | | | ~ caption continues: "after costs, on large US stocks." |
| 0:09.33 | shocked | grid_sb | **P2** Forty-two losing quarters. |
| 0:11.13 | pleased | grid_sb | Two winning ones. |
| 0:12.34 | sceptical | years | Every single year from 2016 to 2026 was negative. |
| 0:15.68 | thinking | grid_js | The Judas swing? |
| 0:16.82 | shocked | grid_js | Thirty-nine losing quarters out of forty-four. |
| 0:19.97 | thinking | random | Liquid stocks' intraday charts are close to random once you count costs. |
| 0:22.34 | | | ~ caption continues: "close to random once you count costs." |
| 0:24.85 | neutral | end_break | Full breakdown on the channel. |
| 0:26.93 | neutral | end_break | Educational, not financial advice. |

Cards used: `grid_empty` = 44-quarter grid, outlines only (2016-2026); `grid_sb` = Silver Bullet quarter grid: 42 red, 2 green; `years` = Silver Bullet by year 2016-2026, all bars negative; `grid_js` = Judas quarter grid: 39 of 44 red; `random` = coin + "Close to random once you count costs"; `end_break` = logo + "Full breakdown on Backtest Bench"

Caption font sizes used: 72 px; fit problems: 0.

## short3.mp4 (0:33.07, video 33.067 s vs joined mp3 33.071 s; 18 distinct stills)

| start | mood | card | caption (sentence) |
|---|---|---|---|
| 0:00.00 | pleased | perfect | **P1** This is what an ICT setup looks like on social media. |
| 0:03.97 | shocked | messy | **P2** This is what 129,658 of them look like when a computer takes every one by the rules. |
| 0:07.19 | | | ~ caption continues: "a computer takes every one by the rules." |
| 0:10.13 | thinking | sb_R | Before costs: roughly break-even, like a coin flip. |
| 0:13.89 | sceptical | grid_sb | After costs: a loss in 42 of 44 quarters. |
| 0:16.93 | sceptical | hindsight | Charts picked after the fact always look good - that's hindsight, not a strategy. |
| 0:20.45 | | | ~ caption continues: "that's hindsight, not a strategy." |
| 0:22.87 | thinking | measure | Our test can't measure a trader's discretion. |
| 0:26.20 | neutral | measure | It can measure the setups. |
| 0:28.16 | neutral | end_video | Full video on the channel. |
| 0:30.11 | neutral | end_video | Educational, not financial advice. |

Cards used: `perfect` = flawless ICT setup chart (illustration); `messy` = 15 rule-taken days, one perfect (illustration), "129,658 of them"; `sb_R` = before costs, avg R: Silver Bullet +0.02R vs coin flip -0.00R on a -1R..+1R axis; `grid_sb` = Silver Bullet quarter grid: 42 red, 2 green; `hindsight` = "Always looks good. That's hindsight, not a strategy."; `measure` = x discretion not measured / check the setups measured; `end_video` = logo + "Full video on Backtest Bench"

Caption font sizes used: 72 px; fit problems: 0.

## short4.mp4 (0:34.47, video 34.467 s vs joined mp3 34.482 s; 19 distinct stills)

| start | mood | card | caption (sentence) |
|---|---|---|---|
| 0:00.00 | neutral | judas_title | **P1** ICT's other famous setup is the Judas swing. |
| 0:02.92 | thinking | judas_rule | The first hour fakes out past yesterday's high or low, then closes back inside, and you trade against the fake-out. |
| 0:06.48 | | | ~ caption continues: "then closes back inside," |
| 0:08.10 | | | ~ caption continues: "and you trade against the fake-out." |
| 0:10.87 | neutral | js_trades | **P2** We tested it on ten years of data. |
| 0:15.07 | shocked | js_trades | 80,366 trades. |
| 0:17.24 | sceptical | js_R | **P3** Before costs: zero. |
| 0:19.06 | sceptical | js_R | Exactly what a coin flip makes. |
| 0:21.97 | shocked | grid_js | After costs, it lost money in 39 of 44 quarters. |
| 0:26.83 | thinking | rules_js | **P4** Fixed rules, not a trader's judgement. |
| 0:29.65 | neutral | end_test | Full test on the channel. |
| 0:31.53 | neutral | end_test | Educational, not financial advice. |

Cards used: `judas_title` = "Judas swing" title, hourly bars; `judas_rule` = Judas rule diagram: first hour fakes past yesterday's high, closes back inside, trade against it (illustration); `js_trades` = big number 80,366 trades; `js_R` = before costs avg R: Judas -0.00R vs coin -0.00R; `grid_js` = Judas quarter grid: 39 of 44 red; `rules_js` = "Fixed rules. Not a trader's judgement."; `end_test` = logo + "Full test on Backtest Bench"

Caption font sizes used: 72 px; fit problems: 0.

## short5.mp4 (0:35.20, video 35.200 s vs joined mp3 35.187 s; 16 distinct stills)

| start | mood | card | caption (sentence) |
|---|---|---|---|
| 0:00.00 | pleased | rescue | **P1** We tried to rescue ICT's Silver Bullet. |
| 0:03.15 | thinking | fix_trend | First, a trend filter - ICT's higher-timeframe bias. |
| 0:07.73 | sceptical | trend_res | **P2** It made things worse: minus 0.058% a trade after costs, against minus 0.051% without it. |
| 0:13.77 | | | ~ caption continues: "against minus 0.051% without it." |
| 0:17.71 | thinking | fix_fin | **P3** Then we only went long in high-quality companies, judged by their financials. |
| 0:20.81 | | | ~ caption continues: "judged by their financials." |
| 0:22.49 | pleased | ladder | That was the best version we found. |
| 0:25.13 | shocked | ladder | **P4** And it still lost 0.035% a trade after costs. |
| 0:29.44 | sceptical | least_bad | Least bad isn't good. |
| 0:31.50 | neutral | least_bad | Educational, not financial advice. |

Cards used: `rescue` = "Can it be rescued?" pure SB -0.051% a trade after costs; `fix_trend` = Fix 1: longs above / shorts below the 50-day average; `trend_res` = bars: pure -0.051% vs + trend filter -0.058%; `fix_fin` = Fix 2: longs only, top third by financials; `ladder` = bars: pure -0.051%, trend -0.058%, long-only quality -0.035% (orange); `least_bad` = big -0.035% "least bad isn't good"

Caption font sizes used: 72 px; fit problems: 0.

## short6.mp4 (0:31.03, video 31.033 s vs joined mp3 31.033 s; 16 distinct stills)

| start | mood | card | caption (sentence) |
|---|---|---|---|
| 0:00.00 | thinking | why | **P1** Why is day trading the biggest stocks so hard? |
| 0:03.94 | sceptical | costs | Costs. |
| 0:04.94 | neutral | move | **P2** A typical intraday move is half a percent to one percent. |
| 0:10.21 | thinking | move_cost | Even at a cheap 0.03% each way, a round trip costs 0.06%. |
| 0:15.88 | shocked | edge_cost | **P3** ICT's direction call was worth about 0.01% a trade. |
| 0:20.77 | sceptical | edge_cost | A sixth of the cost. |
| 0:23.14 | sceptical | costs_win | **P4** When you're fighting over hundredths of a percent, costs win. |
| 0:24.75 | | | ~ caption continues: "hundredths of a percent, costs win." |
| 0:26.90 | neutral | end_test | Full test on the channel. |
| 0:28.48 | neutral | end_test | Educational, not financial advice. |

Cards used: `why` = "Why is it so hard?"; `costs` = big red COSTS; `move` = typical intraday move bar 0.5% to 1%; `move_cost` = same + red 0.06% round-trip slice (0.03% each way); `edge_cost` = bars: direction call 0.01% vs round-trip cost 0.06% ("a sixth"); `costs_win` = "Costs win."; `end_test` = logo + "Full test on Backtest Bench"

Caption font sizes used: 72 px; fit problems: 0.

## Not done / to check

- Lato is not installed here; text renders in Carlito (metric-compatible fallback in the brand font stack).
- Sentence/caption cut points are character-share estimates, not forced alignment; nudge `CARD_PLAN` or `MAX_CHARS` if a cut lands early/late.
- 2026 Q4 / 2026 in the grids and year bars are partial (data ends 2026-10-26); said in the card source line.
- Charts of setups (perfect, messy, Judas rule) are illustrations, labelled on the card.
- No music; hard cuts only.
