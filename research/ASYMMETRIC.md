# Michael Sikand's "asymmetric bets": how he picks, and does it test?

_October 2026. Code: `research/asymmetric.py`. Tables: [`output/asymmetric.md`](output/asymmetric.md).
Educational research, not financial advice. His posts and performance figures are self-reported
on social media, gross of fees and not independently verified. Verify anything here at the source._

## Who and what

Michael Sikand runs model portfolios ("Pilots") on Autopilot, a US copy-trading app. Followers'
accounts mirror his allocations. The two main portfolios are **Asymmetric Bets** (about 5 holdings,
15-30% each) and **Photonics Is Next** (an AI-infrastructure photonics basket). He also runs smaller
themed ones, such as a defense portfolio he reported down about 30%. Autopilot's disclosures say
he doesn't manage client accounts or hold client money, and that Autopilot implements the models.
He describes his playbook as: *"find mispriced stocks tied to mega themes with strong fundamentals
and then develop a trading strategy to maximize return."*

## His reasoning, pick by pick (from his posts, Feb-Jul 2026)

| Pick | What he said | The pattern |
|---|---|---|
| **AAOI** (largest photonics holding) | "Only vertically integrated US laser manufacturer with capacity left"; management target of $471M monthly transceiver revenue by Q2 2027; held through a 40% fall "on no information" that the ramp is off track | Supply bottleneck + management target + hold through drawdowns |
| **Soitec** (SOI.PA) | "95%+ market share" in photonics wafers, competitor exiting, co-packaged optics needs "4x the wafer content", at 3.6-4x EV/revenue, 75% off its all-time high | Monopoly + content-per-unit growth + cheap vs history + far off highs |
| **AVEX** (drone IPO, 20% of fund) | "Battle-tested" products, vertically integrated software, 1K/month capacity, "large discount to comps like KTOS, ONDS, RCAT"; peer price-to-sales used to size the upside | New IPO + discount to peers |
| **BRUN** (neocloud, 20%) | Priced "like CoreWeave", should be "like Nebius"; about 6.8x EV/FY27 ARR; bought after a 90%+ month; named risks (going-concern flag, late 10-Q); sold soon after at +10% on lock-up risk | Peer re-rating + momentum entry + quick exit on a dated risk |
| **FLY** (Firefly, 15%) | "Misunderstood", 35% off its high, "unique set of assets" | Off highs + narrative |
| **AVAV** (defense) | Called "the bottom" after revenue beat by 15% and EPS by 24% | Earnings surprise as a catalyst |
| **APP** (AppLovin) | "Under 20 forward P/E, growing 50% quarter-over-quarter" | Growth at a low multiple |
| Photonics basket | Nvidia's investments in LITE/COHR/MRVL as a signal of scarce capacity; Bank of America and Goldman TAM forecasts | Follow the biggest buyer's capex |

**The repeatable ideas:**
1. Start from a **mega theme** where money is flowing (AI infrastructure, defense, space).
2. Find the **bottleneck or monopoly** inside it: scarce capacity, dominant share, rising content per unit.
3. Buy it **cheap against its peers** (price-to-sales or EV/revenue vs comps), often **well off its highs**.
4. Look for a **catalyst**: an earnings beat, a contract, a peer re-rating or a short squeeze.
5. **Concentrate**: 5 positions, 15-30% each, with cash (SGOV) as the alternative.
6. **Hold through drawdowns** if "fundamentals are intact", but exit quickly on dated risks such as lock-ups.

That is close to our own bottleneck sleeve (theme, bottleneck, asymmetry). It's discretionary:
the narrative, the management read and the timing all come from him.

## What the testable part does

Four of his rules can be measured point-in-time. They were tested monthly from 2014 to 2026 on the
750 largest US companies, with 0.10% costs, empty slots in T-bills and survivors-only prices (which
flatter this a lot):

| Rules | Return/yr | Sharpe | Worst drop | Beat the average stock |
|---|---|---|---|---|
| Theme + growth + discount + off highs, 5 stocks | 0.4% | 0.00 | −41% | 4 of 13 years |
| Same, 10 stocks | 1.8% | 0.04 | −24% | 3 of 13 |
| Without "off highs" | 4.3% | 0.21 | −44% | 5 of 13 |
| Growth + discount only | 3.7% | 0.20 | −57% | 5 of 13 |
| Theme + growth only | 2.3% | 0.14 | −52% | 5 of 13 |
| Average stock (equal weight) | 11.1% | 0.59 | −28% | - |
| SPY | 13.6% | 0.81 | −24% | - |

Each rule on its own (next-month return of passing stocks minus the average stock):

| Rule | Excess per month | Months it helped |
|---|---|---|
| Theme (industry in top quarter by 6-month momentum) | +0.14% | 54% |
| Fast revenue growth | +0.03% | 51% |
| Cheap vs industry peers (P/S) | −0.05% | 47% |
| **30-75% off the 12-month high** | **−0.61%** | **44%** |

- **Applied mechanically, the style lost to the average stock in every version.**
- **Buying stocks far off their highs is the main drag.** This matches well-known research: stocks
  near their 52-week high keep outperforming, and those far below it lag (George & Hwang, 2004).
  It's the mirror image of the momentum effect our new momentum sleeve uses.
- **Industry momentum (the "theme") is the only rule that helped.** Our momentum sleeve already
  captures it more cleanly.
- **Cheap-vs-peers and fast growth did nothing on their own.** That is consistent with
  `research/WINNERS.md`.

## So how is he up so much?

None of these can be proven from here, but likely reasons are:
1. **One theme in one window.** AI photonics in 2026 was a sector-wide boom, so almost any
   concentrated basket of it doubled.
2. **Concentration.** Five positions of 20% each means results are dominated by one or two stocks
   (AAOI was up 254%). That cuts both ways: the defense portfolio is down about 30%.
3. **A short, self-reported record.** These are months, not years, gross of fees. We see the
   winners he posts; the Autopilot app shows the full history.
4. **Judgement our rules can't capture.** Timing, management reads and quick exits on dated risks
   may add something, or may be luck. A few months can't tell.
5. **Incentives.** Pilots grow by attracting followers, and bold calls attract followers.

## Verdict

- **Not added to the live desk.** The testable version of his process has no edge, and its
  "buy when far off the high" part actively hurts.
- **Recorded in the methodology register** as a tested method, for the record.
- **The parts of his thinking that hold up are already in the desk:** theme momentum (the momentum
  sleeve) and concentrated conviction in great businesses (the quality screen).
- **If you want to follow him anyway,** Autopilot lets you copy him directly. Treat it as a
  high-risk satellite position, and compare it with SPY over a year or more, not a few months.

## Sources (accessed 2026-10-20; verify at the source)

- His Autopilot pitch and Photonics Is Next update (July 2026):
  [x.com/michaelsikand/status/2074226194053058784](https://x.com/michaelsikand/status/2074226194053058784)
- Soitec thesis: [x.com/michaelsikand/status/2037254062421533091](https://x.com/michaelsikand/status/2037254062421533091)
- AVEX: [x.com/michaelsikand/status/2046270360627315057](https://x.com/michaelsikand/status/2046270360627315057)
- BRUN buy and exit: [x.com/michaelsikand/status/2061488431851827559](https://x.com/michaelsikand/status/2061488431851827559),
  [x.com/michaelsikand/status/2062270262419358075](https://x.com/michaelsikand/status/2062270262419358075)
- FLY: [x.com/michaelsikand/status/2043816381830111683](https://x.com/michaelsikand/status/2043816381830111683)
- AAOI: [x.com/michaelsikand/status/2074944367022977448](https://x.com/michaelsikand/status/2074944367022977448)
- AVAV: [x.com/michaelsikand/status/2072024859563987322](https://x.com/michaelsikand/status/2072024859563987322)
- AppLovin: [substack.com/@asymmetricalbets/note/c-313443295](https://substack.com/@asymmetricalbets/note/c-313443295)
- Autopilot's description of Asymmetric Bets: [x.com/joinautopilot/status/2041545957490274645](https://x.com/joinautopilot/status/2041545957490274645)
- 52-week-high effect: George, T. & Hwang, C. (2004), "The 52-Week High and Momentum Investing", *Journal of Finance*.
