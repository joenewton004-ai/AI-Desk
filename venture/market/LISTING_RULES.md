# Etsy listing rules (learned from Etsy's own errors - check every new title/tag against these)

| Rule | Source | Date |
|---|---|---|
| Title: at most **140 characters** | Etsy form | 2026-11-01 |
| Title: at most **3 words in ALL CAPS** (e.g. UK, VAT, CSV, MTD, HMRC each count) | Etsy error: "Your title can't have more than 3 words in all caps." | 2026-11-01 |
| Tags: 13 tags, each at most **20 characters** | Etsy form | 2026-11-01 |

Check a title before giving it to the owner: `python venture/market/check_listing.py "<title>"`.
Add a row here whenever Etsy rejects something.
