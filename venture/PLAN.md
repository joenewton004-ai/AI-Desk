# Venture Station - operating plan

Joint venture between the owner (finance, accounts, uploads, voice) and Claude (commander: plans,
makes the products/scripts, directs helper agents, reports the numbers).
Dashboard: https://claude.ai/artifact/PMz35C74KMLMkRHNB9gU5F

## Money rules (agreed 2026-11-01)
- Start-up cap: **£500 total**. Any spend that would take the total over £500 needs the owner's approval.
- Every pound in or out goes in `venture/ledger.csv` (date, module, item, amount_gbp, note). Spend is negative.
- No paid ads, tools or subscriptions without a line in the ledger and a reason.
- Business bank account open (2026-11-01). All business money goes through it.
- Running costs sit OUTSIDE the £500 start-up cap but count against profit:
  Claude Pro, about £18/month (confirm the amount from the first statement). Ledger it monthly, module "Command".
- Break-even on running costs: about 2 sales a month of product 1 (£14.99 keeps about £12.60 after Etsy fees + VAT).

## Active modules
| Module | What | First target | Kill rule (day 90 = 2027-01-30) |
|---|---|---|---|
| Market (Etsy) | Digital templates: Excel / Google Sheets / Power Platform | 10 listings live by day 21; first sale by day 45 | < £100 revenue by day 90 |
| Studio (YouTube + Shorts) | "We backtested it" - honest tests of famous strategies, from research/ | 1 long video + 3 Shorts a week from week 2 | < 300 subscribers or < 20k Shorts views by day 90 |

Proposed (not started): Gallery (Instagram carousels, reuses Studio), Press Room (newsletter).

## Ground rules
- Content is education, never financial advice; only numbers from the research write-ups, with their caveats.
- AI use is disclosed where platforms require it (Etsy, YouTube altered/synthetic content label).
- The owner holds every account and payout; Claude never asks for passwords or card details in chat.

## Week 1 (2026-11-02 to 2026-11-08)
Owner:
1. ~~Business bank account~~ (done 2026-11-01). Open a business Google account, an Etsy shop **BoxByBoxSheets** (Offsite Ads OFF) and a YouTube channel **Backtest Bench** (names chosen 2026-11-01; separate brands on purpose).
2. Record a 30-second voice test (phone is fine) so we can judge the sound.
Claude + crew:
1. Etsy market research -> `venture/research/ETSY_MARKET.md` (pick first 3 products).
2. Studio lineup + episode 1 script -> `venture/studio/`.
3. Build product #1 and its listing (title, 13 tags, description, mockup images).
4. Charts for episode 1 from the repo's data.

## Tests
### Etsy Ads test (approved by the owner 2026-11-01)
- £1/day for 14 days on all 3 listings = £14 max, from the start-up budget. Start date = the day the owner switches it on.
- BLOCKED until about 2026-11-16: Etsy makes new shops wait 15 days before using Etsy Ads (owner screenshot 2026-11-01).
  Reminder scheduled for 16 Nov.
- Measure from the Etsy Ads dashboard: views, clicks, orders, spend; plus favourites from Stats.
- Rule set in advance: after 14 days, fewer than 300 ad views OR no sales -> stop, and don't retry until the shop has
  reviews. If 1+ sale and cost per sale is below the profit on that sale (~£9.98 / £7.38 / ~£15) -> continue at £1/day.
- Ledger: ad spend appears on the Etsy statement as Marketing rows; add it from the statement.

### Voice: AI clone of the owner's own voice (owner's decision 2026-11-01)
- The owner has a stutter that makes reading full scripts hard, so narration uses an ElevenLabs clone of HIS OWN voice
  (never anyone else's). Research: venture/studio/VOICE_RESEARCH.md - own-voice clones are exempt from YouTube's AI label.
- Month 1: ElevenLabs Starter (~£4.50 + VAT, ~30k credits = episode 1 + Shorts with retakes), instant clone from
  1-3 minutes of clean audio. Upgrade to Creator (~£16.40 + VAT) only once the channel publishes weekly.
- Paid from the £500 start-up budget (not a running cost like Claude Pro). Ledger it from the receipt.
- Every video description says: "Narrated with an AI clone of my own voice."
- Kill rule from the research: drop it on any YouTube warning about inauthentic content / AI personas, or 3+ comments a
  month calling the voice robotic.

## Task list (open)
- [ ] **Link YouTube via the API (read-only stats)** - owner, added 2026-11-01. Steps (see venture/studio/UPLOAD_EP01.md
  discussion): Google Cloud project "Backtest Bench" on the business account -> enable YouTube Data API v3 -> API key
  restricted to that API -> add as a network secret for youtube.googleapis.com (or env var YOUTUBE_API_KEY) and allow
  the host -> Claude then pulls views/likes/comments/subscribers into the Studio module. Uploads stay manual (unreviewed
  API projects can only upload private videos). Full analytics (watch time, retention) would need OAuth - later.
- [ ] Etsy Ads test - switch on ~16 Nov (reminder scheduled).
- [x] Upload episode 1 - done 2026-11-01: https://www.youtube.com/watch?v=Cs3rKIFWGa4
- [ ] Episode 1 Shorts, ONE A DAY (owner 2026-11-01), new style with the "Up" avatar, each linked to episode 1:
  Mon 2 Nov S1 coin flip · Tue 3 S2 42 of 44 quarters · Wed 4 S3 why setups look perfect · Thu 5 S4 Judas swing ·
  Fri 6 S5 can it be rescued? · Sat 7 S6 why costs win.
- [ ] Episode 2 (long) goes out Sunday 8 Nov - topic to confirm (lineup #2: the "green line" rule).
- [ ] Day-2 and day-7 Analytics screenshots for episode 1 (~3 and 8 Nov).
