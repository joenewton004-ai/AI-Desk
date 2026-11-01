# Episode 1 - YouTube upload checklist

Files: venture/studio/video/ep01/ - long.mp4, short1-3.mp4, thumbnail.png (rebuild with build.py if missing).
Do the channel set-up once, then the long video, then one Short every 2 days.

## 0. Channel set-up (once)
- [ ] Studio -> Customisation -> Branding: profile picture `brand/profile_800.png`, banner `brand/banner_2560x1440.png`
- [ ] Customisation -> Basic info: description (paste below), country United Kingdom
  > Famous trading strategies, tested honestly. We turn popular setups into fixed rules and run them on years of real
  > market data, with costs. Educational research, not financial advice. Narrated with an AI clone of my own voice.
- [ ] Settings -> Channel -> Advanced: "Is your channel made for kids?" -> **No**

## 1. Long video - long.mp4
| Field | Value |
|---|---|
| Title | `I Tested ICT's Silver Bullet on 129,658 Trades (10 Years of Data)` |
| Thumbnail | `video/ep01/thumbnail.png` |
| Audience | No, it's not made for kids |
| Visibility | **Unlisted first** -> watch it through once on your phone -> then Public |
| Category | Education |
| Language | English (United Kingdom); captions: let YouTube auto-generate, then check numbers in Subtitles |
| Tags | ICT, Inner Circle Trader, ICT Silver Bullet, Silver Bullet strategy, Judas swing, fair value gap, liquidity sweep, backtest, day trading backtest, trading strategy tested, does ICT work, smart money concepts, day trading, stock market research, trading costs |
| Altered or synthetic content | **No** - YouTube exempts a clone of your own voice; the description says so anyway |
| Paid promotion | No |
| Comments | On; hold potentially inappropriate comments for review |
| End screen | Subscribe element + "Best for viewer" video (from ep. 2 on) over the last 10 s |

### Description (paste as is)
```
Does ICT's Silver Bullet actually have an edge? We turned two of the best-known Inner Circle Trader setups - the Silver Bullet and the Judas swing - into fixed rules and ran them on ten years of 5-minute bars (January 2016 to October 2026) for the 100 largest US companies, with costs of 0.03% each way and a coin-flip control.

Results:
- Silver Bullet: 129,658 trades, +0.02R before costs, -0.051% per trade after costs; lost money in 42 of 44 quarters.
- Judas swing: 80,366 trades, -0.00R before costs, -0.053% per trade after costs; lost in 39 of 44 quarters.
- Same trades with a coin-flip direction: -0.061% and -0.062% after costs.
- Long-only in high-quality companies was the least bad version, still -0.035% per trade after costs.

Limits: these are community descriptions of ICT made into fixed rules, not ICT's own course material. A trader's discretion isn't tested. Tested on large US stocks, not futures, forex or small caps.

Chapters:
0:00 The result
0:13 What we're testing
0:51 ICT in plain English
1:27 Silver Bullet and Judas swing rules
2:11 How we tested it
3:35 Results
5:14 Did financials or trend help?
5:44 Why day trading is so hard
6:31 What this test can't tell you
7:08 Takeaway

Narrated with an AI clone of my own voice.
Educational research, not financial advice. I'm not a financial adviser; past results don't predict future ones.
```
(Chapter times are from the finished video's slide timings, not the script's estimates.)

## 2. Shorts - one every 2 days after the long video is public
For each: upload from the phone or Studio, Audience "not made for kids", then **Related video -> the long video** (this
puts a link to it under the Short). Add `#Shorts` at the end of the description.

| File | Title | Description |
|---|---|---|
| short1.mp4 | `ICT's Silver Bullet vs a coin flip (129,658 trades)` | `10 years, the 100 biggest US stocks, costs included. Full test on the channel. Narrated with an AI clone of my own voice. Educational, not financial advice. #Shorts #ICT #daytrading` |
| short2.mp4 | `42 losing quarters out of 44` | `ICT's Silver Bullet, after costs, every quarter 2016-2026. Full test on the channel. Narrated with an AI clone of my own voice. Educational, not financial advice. #Shorts #ICT #backtest` |
| short3.mp4 | `Why ICT setups look perfect on social media` | `Charts picked after the fact vs 129,658 trades taken by the rules. Full test on the channel. Narrated with an AI clone of my own voice. Educational, not financial advice. #Shorts #ICT #trading` |

## 3. Don'ts (FCA finfluencer rules + YouTube)
- No broker, prop-firm or trading-app links or codes. No "buy X" or "use this strategy".
- Don't re-upload the same Short twice (YouTube's repetitive-content rule).
- Don't reply to comments with trading advice; "this is research, not advice" is the line.

## 4. After publishing
- [ ] Send Claude the video link -> station + Studio log updated
- [ ] Pin a comment: "What should we test next? ICT's other models, TJR, the 200-day moving average...?"
- [ ] Day 2 and day 7: send a screenshot of Studio -> Analytics (views, average view duration, subscribers)
