# Product 2 - Etsy listing fields (go-live sheet)

UK Etsy Seller Profit Tracker 2026/27 · shop BoxByBoxSheets · status: **ready to list** (real-statement check passed 2026-11-01)

Everything needed to fill Etsy's listing form, in form order. Copy-paste text lives in this folder:
title, tags and the long description in `LISTING.md`, the description as plain text (no `**`) in `DESCRIPTION.txt`.
Etsy form menus are from memory (etsy.com is blocked from Claude's sessions) - if a menu differs, pick the closest
and note it under "As actually listed".

## Photos and video
| Field | Value |
|---|---|
| Photos (in this order; #1 = thumbnail) | `../brand/thumbs/p02_thumb.png` (thumbnail), then `images/01_price_calculator.png`, `02_statement_import.png`, `03_monthly_pl.png`, `04_hmrc_checks.png`, `05_tabs.png` |
| Video | none yet (later: 10-15 s screen recording of the price calculator) |

## Listing details
| Field | Value |
|---|---|
| Title | `UK Etsy Seller Profit Tracker 2026/27 \| Etsy Fee Calculator \| Statement CSV Import \| VAT on Fees \| Excel & Google Sheets` (120 chars) |
| Who made it? | I did |
| What is it? | A finished product |
| When was it made? | 2020-2026 |
| Category | Paper & Party Supplies > Paper > Calendars & Planners (same as product 1) |
| Attributes | Planner type: Budget / Finance (if offered); Format: Digital. Leave the rest blank |
| AI / creative-help question | Yes - AI-assisted, designed by the seller (matches the "Honest notes" in the description) |
| Description | paste `DESCRIPTION.txt` |
| Personalisation | Off |
| Renewal | Automatic |
| Type | Digital files |
| Digital file | `UK_Etsy_Seller_Profit_Tracker_2026-27.xlsx` - the OWNER'S copy with the Start Here text written in their own words |

## Inventory and pricing
| Field | Value |
|---|---|
| Price | **£8.99** (keeps about £7.38 after Etsy fees + VAT on fees, non-VAT-registered) |
| Quantity | 999 |
| SKU | **BBS-P02-2627** |
| Variations | None |

## Details
| Field | Value |
|---|---|
| Tags (13) | etsy profit tracker · etsy fee calculator · etsy seller uk · etsy spreadsheet · etsy fees uk · seller bookkeeping · etsy shop finances · profit calculator · pricing calculator · small business uk · sole trader uk · google sheets · excel template |
| Materials | Excel, Google Sheets, xlsx |
| Shop section | Tax & Bookkeeping |
| Production partner | None |

## Shop-level (already set for product 1 - just confirm)
- Offsite Ads OFF (Shop Manager > Settings > Offsite Ads)
- Returns: no returns on digital files; "message me if something doesn't work and I'll fix it"

## After it goes live
- [ ] Fill in "As actually listed" below (listing number, date, anything entered differently)
- [ ] Add the listing fee (£0.15 + £0.03 VAT) to venture/ledger.csv when it shows on the statement
- [ ] First statement with a sale: run `python test_real_csv.py <statement.csv>` to check Sale/Refund/Deposit rows
- [ ] Bundle listing with product 1 at £17.99 (SKU BBS-B01-2627) - images to make

## As actually listed
| Field | Value |
|---|---|
| Listing number | |
| Date live | |
| Differences from above | |
