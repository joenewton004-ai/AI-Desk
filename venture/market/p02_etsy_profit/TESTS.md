# Profit tracker tests (Etsy UK fees as checked 1 Nov 2026)

Run `python build.py` then `python test_profit.py`. Each run changes the inputs in a copy of the built workbook, lets
LibreOffice recalculate it headless (xlsx -> xlsx round trip) and reads the results back with openpyxl. Last run
(2026-11-01): **8 of 8 passed**.

Rates used (Settings defaults): transaction fee 6.5% of the order total (item + postage); payment processing 4% of the
order total + £0.20; regulatory operating fee 0.48% of the order total; listing / auto-renew fee £0.16 per sale
($0.20 converted); Offsite Ads 15% (12% for a $10k+ shop), capped at £76; VAT 20% on all of Etsy's fees unless the
seller gives Etsy a VAT number. Each fee is rounded to the penny. Own VAT on sales 0%.

Break-even price = the item price P at which profit is 0 for the same postage charge S and costs C:
(P + S) x (1 - k) = F + C, where k = (6.5% + 4% + 0.48% [+ Offsite rate]) x (1 + VAT) and F = (£0.20 + £0.16) x (1 + VAT).
So P = (F + C) / (1 - k) - S, rounded to the penny (ignores penny rounding of each fee and the Offsite Ads cap).

## Price calculator

### Case A - £12 digital item, no postage, no Offsite Ads, no VAT number (VAT charged on fees)
| | |
|---|---|
| Order total | £12.00 |
| Transaction 12.00 x 6.5% = 0.78 | £0.78 |
| Processing 12.00 x 4% + 0.20 = 0.48 + 0.20 | £0.68 |
| Regulatory 12.00 x 0.48% = 0.0576 | £0.06 |
| Listing / renewal | £0.16 |
| Fees before VAT | £1.68 |
| VAT 1.68 x 20% = 0.336 | £0.34 |
| Total Etsy cost | £2.02 |
| **Net profit** 12.00 - 2.02 | **£9.98** (margin 83.2%) |
| Break-even: k = 0.1098 x 1.2 = 0.13176; F = 0.36 x 1.2 = 0.432; 0.432 / 0.86824 = 0.4976 | **£0.50** |

This matches the worked example in `venture/research/ETSY_MARKET.md` (about £2.02 to Etsy, £9.98 kept).

### Case B - £25 candle + £3.95 postage; item £6.00, packaging £0.80, postage paid £3.20; no ads; no VAT number
| | |
|---|---|
| Order total 25.00 + 3.95 | £28.95 |
| Transaction 28.95 x 6.5% = 1.88175 | £1.88 |
| Processing 28.95 x 4% + 0.20 = 1.158 + 0.20 = 1.358 | £1.36 |
| Regulatory 28.95 x 0.48% = 0.13896 | £0.14 |
| Listing / renewal | £0.16 |
| Fees before VAT | £3.54 |
| VAT 3.54 x 20% = 0.708 | £0.71 |
| Total Etsy cost | £4.25 |
| Your costs 6.00 + 0.80 + 3.20 | £10.00 |
| **Net profit** 28.95 - 4.25 - 10.00 | **£14.70** (margin 50.8%) |
| Break-even: (0.432 + 10.00) / 0.86824 - 3.95 = 12.0151 - 3.95 | **£8.07** |

### Case C - £40 tote + £4.95 postage, buyer came from an Offsite Ad (15%); item £12, packaging £1, postage paid £3.50; no VAT number
| | |
|---|---|
| Order total 40.00 + 4.95 | £44.95 |
| Transaction 44.95 x 6.5% = 2.92175 | £2.92 |
| Processing 44.95 x 4% + 0.20 = 1.798 + 0.20 = 1.998 | £2.00 |
| Regulatory 44.95 x 0.48% = 0.21576 | £0.22 |
| Listing / renewal | £0.16 |
| Offsite Ads 44.95 x 15% = 6.7425 (under the £76 cap) | £6.74 |
| Fees before VAT | £12.04 |
| VAT 12.04 x 20% = 2.408 | £2.41 |
| Total Etsy cost | £14.45 |
| Your costs 12.00 + 1.00 + 3.50 | £16.50 |
| **Net profit** 44.95 - 14.45 - 16.50 | **£14.00** (margin 31.1%) |
| Break-even: k = 0.2598 x 1.2 = 0.31176; (0.432 + 16.50) / 0.68824 - 4.95 = 24.6018 - 4.95 | **£19.65** |

### Case D - case A with "I give Etsy a VAT number" = Yes
Fees £1.68, VAT £0, total £1.68, **profit £10.32**. Break-even 0.36 / (1 - 0.1098) = 0.4044 -> **£0.40**.

### Case E - case C with a VAT number and a $10k+ shop (Offsite Ads 12%)
Offsite 44.95 x 12% = 5.394 -> £5.39; fees 2.92 + 2.00 + 0.22 + 0.16 + 5.39 = £10.69; VAT £0; **profit 44.95 - 10.69 -
16.50 = £17.76**. Break-even (0.36 + 16.50) / (1 - 0.2298) - 4.95 = 21.8904 - 4.95 -> **£16.94**.

## Sample statement import

The workbook ships with a made-up statement (113 rows, May and June 2026, a non-VAT-registered seller) pasted in Etsy
Paste, built with the fee rules above. Each fee row has a matching "VAT: ..." row at 20%, rounded per row. June's rows
were pasted below May's with a second header row (ignored). Hand-worked per order:

| Order date | Order total | Transaction (item + postage) | Processing | Regulatory | Renewal | Offsite Ads | VAT on these |
|---|---|---|---|---|---|---|---|
| 3 May | 12.00 | 0.78 + 0.00 | 0.68 | 0.06 | 0.16 | 0 | 0.34 |
| 9 May | 28.95 | 1.63 + 0.26 | 1.36 | 0.14 | 0.16 | 0 | 0.71 |
| 17 May | 44.95 | 2.60 + 0.32 | 2.00 | 0.22 | 0.16 | 6.74 | 2.40 |
| 28 May | 12.00 | 0.78 + 0.00 | 0.68 | 0.06 | 0.16 | 0 | 0.34 |
| 4 Jun | 28.95 | 1.63 + 0.26 | 1.36 | 0.14 | 0.16 | 0 | 0.71 |
| 12 Jun | 12.00 | 0.78 + 0.00 | 0.68 | 0.06 | 0.16 | 0 | 0.34 |
| 15 Jun | 18.00 | 1.17 + 0.00 | 0.92 | 0.09 | 0.16 | 0 | 0.46 |
| 21 Jun (refunded 27 Jun) | 28.95 | 1.63 + 0.26 | 1.36 | 0.14 | 0.16 | 0 | 0.71 |
| 25 Jun | 12.00 | 0.78 + 0.00 | 0.68 | 0.06 | 0.16 | 0 | 0.34 |
| **Sum** | **197.80** | **12.88** | **9.72** | **0.97** | **1.44** | **6.74** | **6.35** |

(VAT is worked per fee row: e.g. 3 May = 0.16 + 0.14 + 0.01 + 0.03 = 0.34. The 17 May transaction fee is split item
2.60 + postage 0.32 on the statement, so it differs by a penny from the calculator's single 2.92.)

Other rows: 3 new listings on 1 May (3 x 0.16 = 0.48, VAT 3 x 0.03 = 0.09); Etsy Ads 3.20 (VAT 0.64) and 2.75 (VAT
0.55); postage labels 3.20 + 3.50 + 3.20 + 3.20 = 13.10; the 27 June refund -28.95 with transaction fee credits
+1.63 + 0.26 = +1.89 and VAT credits +0.33 + 0.05 = +0.38; two deposits (ignored).

| Year total (Monthly P&L row 17) | Workings | Expected |
|---|---|---|
| Sales | 197.80 | £197.80 |
| Refunds | | -£28.95 |
| Net sales | 197.80 - 28.95 | £168.85 |
| Transaction fees | 12.88 - 1.89 | £10.99 |
| Processing fees | | £9.72 |
| Regulatory operating fee | | £0.97 |
| Listing & renewal fees | 1.44 + 0.48 | £1.92 |
| Offsite Ads fees | | £6.74 |
| Etsy Ads | 3.20 + 2.75 | £5.95 |
| VAT on Etsy fees | 6.35 + 0.09 + 0.64 + 0.55 - 0.38 | £7.25 |
| Postage labels | | £13.10 |
| Total Etsy charges | | £56.64 |
| Total other costs (Other Costs examples, excluding the £3.40 not-allowable coffee) | 18.60 + 22.00 + 8.40 + 2.70 + 10.99 + 5.00 + 12.00 | £79.69 |
| **Net profit** | 168.85 - 56.64 - 79.69 | **£32.52** |

Tax months: net sales 6 Apr-5 May £12.00; 6 May-5 Jun £114.85 (9 May to 4 Jun); 6 Jun-5 Jul £42.00 (70.95 - 28.95).

To Sole Trader Tracker year totals: turnover £168.85; goods for resale / materials 18.60 + 22.00 + 8.40 = £49.00;
interest, bank and card charges (processing) £9.72; phone, stationery, office 13.10 + 2.70 + 10.99 = £26.79;
advertising 6.74 + 5.95 + 5.00 = £17.69; other allowable 10.99 + 0.97 + 1.92 + 7.25 + 12.00 = £33.13; total £136.33
(= 56.64 + 79.69); profit check "OK".

HMRC Checks: 9 sales in calendar 2026, £168.85; unsorted rows 0; unreadable dates 0; columns not found 0; Net vs
Amount + Fees difference 0.

## Other runs
- **Columns in reverse order** (Tax Details first, Date last, header row included): every total above unchanged -
  the columns are found by header name.
- **Examples cleared** (Etsy Paste rows emptied, Other Costs A5:F12 and Price Calculator A5:H8 cleared): example
  count 0, net sales and profit £0, Statement Lines blank.

The first full test run found a real bug, fixed before release: the "VAT: Offsite Ads fee" row was sorted as an Offsite
Ads fee (the "offsite" rule came first). The VAT rule is now rule 1.

Not checked here: Microsoft Excel and Google Sheets themselves (only LibreOffice). See CHECKLIST.md.
