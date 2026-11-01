# BoxByBoxSheets - listings index

| SKU | Product | Price | Status | Go-live sheet |
|---|---|---|---|---|
| BBS-P01-2627 | UK Sole Trader Tracker 2026/27 | £11.99 (-> £14.99) | Live 2026-11-01 | [p01_sole_trader/LISTING_FIELDS.md](p01_sole_trader/LISTING_FIELDS.md) |
| BBS-P02-2627 | UK Etsy Seller Profit Tracker 2026/27 | £8.99 | Live 2026-11-01 | [p02_etsy_profit/LISTING_FIELDS.md](p02_etsy_profit/LISTING_FIELDS.md) |
| BBS-B01-2627 | Bundle: P01 + P02 | £17.99 | Live 2026-11-01 | [b01_bundle/LISTING_FIELDS.md](b01_bundle/LISTING_FIELDS.md) |

SKU pattern: BBS-<P product / B bundle><nn>-<tax year>. Brand assets: brand/. Etsy statements: statements/.

Thumbnails: every listing's photo #1 is a plain brand card from brand/thumbs/ (`node brand/thumbs/shoot.js` re-renders
them from thumbs.html). Content is centred so Etsy's square crops keep it. New products get a card in the same style.
