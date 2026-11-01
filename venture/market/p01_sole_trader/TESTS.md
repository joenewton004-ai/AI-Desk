# Tax estimate tests (2026/27, England/Wales/NI)

Run `python test_tax.py`. For each case it clears the EXAMPLE rows in the built workbook, types the case's
entries, lets LibreOffice 24.2 recalculate the file headless (xlsx -> xlsx round trip) and reads the Tax
Estimate tab back. The expected figures are the hand calculations below (also re-done in plain Python inside the
test as a cross-check).

Rates used: personal allowance £12,570 (tapered £1 per £2 over £100,000); 20% on the first £37,700 of taxable
income, 40% to £125,140, 45% above; Class 4 NI 6% on profits £12,570-£50,270, 2% above; Class 2 not payable
(profits >= £7,105 are treated as paid; voluntary Class 2 left off).

## Case A - profit £8,000 (income £8,000, no expenses)
- Income Tax: £8,000 is under the £12,570 personal allowance -> **£0**
- Class 4: profit under £12,570 -> **£0**
- Class 2: £8,000 >= £7,105, treated as paid -> £0
- **Total £0.00**

## Case B - profit £30,000 (£30,000 sales + £4,000 other income - £4,000 allowable expenses; a £999 "not allowable" line is ignored)
- Trading allowance option: £34,000 - £1,000 = £33,000, worse than £30,000 -> actual expenses used
- Taxable income: 30,000 - 12,570 = 17,430
- Income Tax: 17,430 x 20% = **£3,486.00**
- Class 4: (30,000 - 12,570) x 6% = 17,430 x 0.06 = **£1,045.80**
- **Total £4,531.80**

## Case C - profit £60,000 (£66,000 income - 12,000 business miles, entered out of date order)
- Mileage: 10,000 x 55p + 2,000 x 25p = 5,500 + 500 = £6,000 -> profit 66,000 - 6,000 = 60,000
- Taxable income: 60,000 - 12,570 = 47,430
- Basic: 37,700 x 20% = 7,540.00
- Higher: (47,430 - 37,700) = 9,730 x 40% = 3,892.00
- Income Tax **£11,432.00**
- Class 4: (50,270 - 12,570) x 6% = 37,700 x 0.06 = 2,262.00; (60,000 - 50,270) = 9,730 x 2% = 194.60 -> **£2,456.60**
- **Total £13,888.60**

## Extra case D - profit £110,000 (allowance taper)
- Personal allowance: 12,570 - (110,000 - 100,000)/2 = 7,570; taxable 102,430
- Basic 7,540.00; higher (102,430 - 37,700) = 64,730 x 40% = 25,892.00 -> Income Tax **£33,432.00**
- Class 4: 2,262.00 + (110,000 - 50,270) x 2% = 2,262.00 + 1,194.60 = **£3,456.60**
- **Total £36,888.60**

## Extra case E - £1,500 income, £200 expenses, method "Best for me (auto)"
- Actual: 1,300; trading allowance: 500 -> sheet must pick the trading allowance; profit £500; **total £0**

## Result (run 2026-11-01, LibreOffice 24.2.7.2)
```
PASS  A: profit £8,000: method=Actual expenses, profit 8000, income tax 0, class 4 0, total 0 (expected 0)
PASS  B: profit £30,000 (£34,000 income - £4,000 expenses): method=Actual expenses, profit 30000, income tax 3486, class 4 1045.8, total 4531.8 (expected 4531.8)
PASS  C: profit £60,000 (£66,000 income - 12,000 business miles): method=Actual expenses, profit 60000, income tax 11432, class 4 2456.6, total 13888.6 (expected 13888.6)
PASS  D: profit £110,000 (allowance taper): method=Actual expenses, profit 110000, income tax 33432, class 4 3456.6, total 36888.6 (expected 36888.6)
PASS  E: £1,500 income, £200 expenses -> trading allowance wins: method=Trading allowance, profit 500, income tax 0, class 4 0, total 0 (expected 0)
all passed
```
No mismatches. The shipped file (with the example rows) recalculates to: income £3,511.35, allowable expenses
£519.49, mileage £46.75 (85 miles x 55p), trading allowance chosen, taxable profit £2,511.35, tax £0.

**Not tested here:** opening the file in Google Sheets and in desktop Excel (no access in this session). The
formulas are all ones both support, but the owner should open it once in each before listing, and check the
dropdowns and the amber example-row colouring survive the Google Sheets import.

Not tax or accounting advice.
