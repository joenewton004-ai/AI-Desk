# Sources for the Etsy fees and HMRC limits (checked 2026-11-01)

**How these were checked.** This session could not open etsy.com, help.etsy.com, www.gov.uk or third-party guide sites
directly (DNS blocked for every host tried). Every figure below comes from **search-engine excerpts** of the pages
listed (accessed 2026-11-01), plus the desk research in `venture/research/ETSY_MARKET.md` (also search excerpts).
Nothing was read on the page itself. **Before listing, the owner should open each link in a normal browser and tick
the figure off - every Etsy row is marked "check on Etsy" in the workbook's Settings tab.**

## Fees and rules used in the workbook

| Figure (Settings row) | Value | Status | Source |
|---|---|---|---|
| Transaction fee (15) | 6.5% of item price + postage + gift wrap | Search excerpt - **check on Etsy** | [Etsy UK Fees & Payments Policy](https://www.etsy.com/uk/legal/fees); third-party guides agree |
| Payment processing, UK (16-17) | 4% + £0.20 per order, on the order total | Search excerpt of Etsy's country table ("United Kingdom 4% + 0.20 GBP") - **check on Etsy** | [Etsy Help: Payment Processing Fees](https://help.etsy.com/hc/en-us/articles/115015628847-What-are-Payment-Processing-Fees-for-Selling-on-Etsy) |
| Regulatory operating fee, UK (18) | 0.48% of the order total from 22 June 2026 (was 0.32%) | Search excerpt of Etsy's own announcement; several third parties agree - **check on Etsy** | [Etsy Community: Regulatory Operating Fee updates for some markets](https://community.etsy.com/forum/announcements-290/topic/regulatory-operating-fee-updates-for-some-markets-181930/); [Etsy Help: What is a Regulatory Operating Fee?](https://help.etsy.com/hc/en-us/articles/1500011073202-What-is-a-Regulatory-Operating-Fee); [Alura news](https://www.alura.io/news/regulatory-operating-fee-june-2026); [ChannelX](https://channelx.world/2026/04/etsy-increase-uk-regulatory-operating-fee-2/) |
| Listing / auto-renew fee (19) | $0.20 per listing and per auto-renewal after a sale; entered as **£0.16** | $0.20 from Etsy's fee policy (excerpt). The £ figure is our conversion (about £0.15-£0.16 per guides; Etsy converts at the day's rate) - **owner: use the figure on a real statement** | [Etsy UK Fees policy](https://www.etsy.com/uk/legal/fees); [A2X: Etsy fees UK](https://www.a2xaccounting.com/blog/etsy-fees-uk) |
| Offsite Ads (20-22) | 15%; 12% once the shop has $10,000+ in the last 12 months (then compulsory for life); capped at $100 per order (entered as £76) | Search excerpt of Etsy Help - **check on Etsy**. The fee base (order total) is how Etsy and most guides word it; one guide adds "certain taxes". The £76 cap is our conversion at $1 = £0.76. | [Etsy Help: How Etsy's Offsite Ads Work](https://help.etsy.com/hc/articles/360000338367) |
| VAT on Etsy's fees (23) | 20% on all seller fees (incl. processing) for UK sellers who give Etsy no VAT number; none when a valid VAT number is given | Etsy's help page excerpt (says Etsy "may be required" to charge VAT and lists the fees on the invoice); the 20% and "includes processing fees" from accountants' guides - **check on Etsy and against a real invoice** | [Etsy Help: How VAT Is Collected on Seller Fees](https://help.etsy.com/hc/en-us/articles/360040584433-How-VAT-Is-Collected-on-Seller-Fees); [A2X: Etsy VAT on seller fees](https://www.a2xaccounting.com/ecommerce-accounting-hub/etsy-vat-seller-fees); [Elver: Guide to Etsy VAT](https://www.elverecommerceaccountants.co.uk/guide-to-etsy-vat/) |
| HMRC platform reporting (24-25) | Not reported if fewer than 30 sales AND less than EUR 2,000 ("approximately £1,700") in the calendar year; data for 1 Jan-31 Dec reported by 31 January | Search excerpt of GOV.UK (an archived copy of the page) and several accountants - **check on GOV.UK** | [GOV.UK: Selling goods or services on a digital platform](https://www.gov.uk/guidance/selling-goods-or-services-on-a-digital-platform); [GOV.UK: Check if you need to tell HMRC about income from online platforms](https://www.gov.uk/guidance/check-if-you-need-to-tell-hmrc-about-your-income-from-online-platforms); [Sage](https://www.sage.com/en-gb/blog/hmrc-digital-platform-reporting-rules-online-sellers/) |
| Trading allowance (26) | £1,000 of gross trading income a tax year | Verified on GOV.UK for product #1 (2026-11-01) | [GOV.UK: Income Tax rates](https://www.gov.uk/income-tax-rates); [Tax-free allowances on property and trading income](https://www.gov.uk/guidance/tax-free-allowances-on-property-and-trading-income) |

## Etsy's monthly statement CSV - NOT verified against a real file

| What the workbook assumes | Status | Source |
|---|---|---|
| Download path: Shop Manager > Finances > Monthly statements > choose month > Download CSV | Etsy Help excerpt + Craftybase | [Etsy Help: How to Calculate Your Etsy Payments Deposit Amount](https://help.etsy.com/hc/en-us/articles/360016389113-How-to-Calculate-Your-Etsy-Payments-Deposit-Amount); [Craftybase: How to get a CSV file from Etsy](https://craftybase.com/blog/how-to-get-csv-file-from-etsy) |
| Columns Date, Type, Title, Info, Currency, Amount, Fees & Taxes, Net | One third-party guide lists exactly these 8 (an older guide) | [Made on the Common: How to understand your monthly Etsy Payments statement](https://www.madeonthecommon.com/blog/download-etsy-payments) |
| "Tax Details" column | **Not found in any source.** Included in the sample only to show extra columns are ignored | - |
| Type values Sale, Refund, Fee, Marketing, Shipping, Deposit, Payment, Subscription | Sale, Refund, Subscription, Shipping/Postage labels, Deposit, Payment, Marketing from the same guide; "Fee" and "VAT" / "Tax" types and the fee **Title wording** ("Transaction fee: ...", "Processing fee", "Regulatory operating fee", "Listing fee", "Offsite Ads fee", "VAT: ...", "Credit for transaction fee ...") are **our guesses** | same guide; [Craftybase](https://craftybase.com/blog/how-to-download-your-tax-totals-from-etsy) |
| Dates like "May 3, 2026"; amounts as text like "£12.00", "-£0.78", "--" | Our assumption. The workbook also reads real numbers/dates, "3 May 2026", "2026-05-03" and dd/mm/yyyy | - |

**Design consequence:** because none of this could be verified, the workbook (1) finds columns by header name, with the
names editable on Settings rows 30-36, (2) sorts rows with an editable rule table (Type + "Title contains", first
match wins, Settings K5:N34), and (3) flags any row no rule matches as "Not sorted - check" and counts them on HMRC
Checks. **The owner must download one real statement and compare its headers, Type values and fee titles with the
rules before listing.**

## Category mapping to the Sole Trader Tracker (product #1)

| Line | Tracker category | Why |
|---|---|---|
| Sales, refunds | Sales / fees (turnover) | Gross sales are turnover - not the payouts |
| Processing fees | Interest, bank and card charges | Card payment processing is a card charge (SA103S box 17, SA103F box 26 - box numbers as researched for product #1) |
| Transaction, regulatory, listing, other Etsy fees; VAT on fees | Other allowable expenses | Selling commissions and platform charges, not finance charges. Unreclaimable VAT is part of the fee's cost; kept in one line for simplicity |
| Offsite Ads, Etsy Ads, other advertising | Advertising and marketing | |
| Postage labels, postage paid elsewhere, software | Phone, stationery, office costs | HMRC's office-costs box includes postage and software (general knowledge of the SA103 notes - not re-checked this session) |
| Stock, materials, packaging | Goods for resale / materials | |

On SA103S, advertising and other allowable expenses share box 19, so the advertising/other split doesn't change the
short return. Profit is the same whichever category a cost goes in.

Not tax or accounting advice.
