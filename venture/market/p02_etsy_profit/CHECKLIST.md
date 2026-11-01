# Product 2 - must pass before listing

Owner checks (none of the Etsy pages or GOV.UK could be opened from this session - search excerpts only):

**Highest risk - the statement import**
- [ ] Download one real monthly statement (Shop Manager > Finances > Monthly statements > Download CSV). Paste it
      into a copy of the workbook at Etsy Paste A4 and check:
  - [ ] Header names match Settings rows 30-36 (Date, Type, Title, Info, Amount, Fees & Taxes, Net). Is there a
        "Tax Details" column? (Not seen in any source; harmless either way.)
  - [ ] The Type values and fee titles really are like the sorting rules (Settings K5:N34): "Fee" + "Transaction fee",
        "Processing fee", "Regulatory operating fee", "Listing fee"; how VAT on fees appears (a "VAT" type? a "Tax"
        type? the "Tax Details" column?); how Offsite Ads and Etsy Ads appear; refunds and fee credits.
  - [ ] HMRC Checks shows 0 "not sorted", 0 unreadable dates, 0 columns not found, and a Net difference of £0.
  - [ ] Monthly P&L sales and fees match the totals on Etsy's own monthly statement page.
  - Fix any mismatch in the default rules (build.py `RULES`) and the sample statement, then re-run the tests.
- [ ] Tell Claude what the real file looked like (redacted) so SOURCES.md can be marked verified.

**Fees (Settings rows 15-26 - each says "check on Etsy")**
- [ ] Transaction fee 6.5% incl. postage and gift wrap - etsy.com/uk/legal/fees.
- [ ] Payment processing UK 4% + £0.20, charged on the order total incl. postage - Etsy Help "Payment Processing Fees".
- [ ] Regulatory operating fee 0.48% from 22 June 2026, on the order total - Etsy Help / announcement.
- [ ] Listing / auto-renew fee: what £ amount a real statement shows for $0.20 (workbook uses £0.16).
- [ ] Offsite Ads 15% / 12%, $100 cap (workbook uses £76), and its base (order total? including postage?).
- [ ] VAT on fees: 20% on ALL fees incl. payment processing for sellers with no VAT number; none with a VAT number.
- [ ] HMRC platform reporting: 30 sales / EUR 2,000 (about £1,700), calendar year - GOV.UK "Selling goods or services
      on a digital platform". Does HMRC count money before or after fees? (The sheet uses sales less refunds.)

**Things the calculator simplifies - decide if the listing needs to say more**
- [ ] VAT Etsy collects from buyers (digital items, some imports) is left out; fees are worked on item + postage.
      Check on a real digital sale whether Etsy's fees are charged on the VAT-inclusive total.
- [ ] VAT-registered sellers: the "VAT I pay HMRC on my own sales" % is a rough planning figure only.
- [ ] The category mapping to product #1 (SOURCES.md): processing -> bank and card charges, other Etsy fees and VAT
      on fees -> other allowable expenses, postage -> office costs. An accountant's view would be welcome.
- [ ] Product #1's example Income rows record "Etsy payouts" as turnover - with this file, buyers should enter gross
      sales and fees instead. Consider changing product #1's example and adding a line to its Start Here.

**The file**
- [ ] Write the Start Here how-to paragraphs in your own words (every red "[OWNER TO WRITE IN OWN WORDS]" line; Etsy
      bans AI-made functional guides from 2026-10-22). Edit `lines` in build.py, then rebuild and re-run the tests.
- [ ] Open the .xlsx in desktop Excel: no repair prompt, dropdowns work, amber example rows, protection on.
- [ ] Import into Google Sheets and confirm Statement Lines sorts the sample (column M). The sorting uses
      `SUMPRODUCT(MAX(...))`, which works in LibreOffice and should in Excel and Sheets - **not tested in either**.
      Then paste a statement into Sheets the way a buyer would (File > Import, or copy-paste) - Sheets may turn
      "£12.00" into numbers and dates into dates; both are handled, but check.
- [ ] Clear the examples as Start Here says and type one month of your own; note anything clunky.
- [ ] Look at the 5 images in images/ - real renders with the sample figures.
- [ ] Set the price (suggested £8.99) and the bundle price with product #1.
