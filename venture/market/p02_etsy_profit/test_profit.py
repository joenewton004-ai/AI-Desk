"""Check the Etsy profit tracker against hand-worked figures (see TESTS.md).

Run: python test_profit.py   (needs LibreOffice: soffice on PATH; run build.py first)
Each run: load the built workbook, change inputs, save a copy, let LibreOffice recalculate it (headless
xlsx -> xlsx round trip), read the results back with openpyxl (data_only).
  Run 1 - default settings (no VAT number, shop under $10k): price cases A, B, C + the sample statement totals.
  Run 2 - 'I give Etsy a VAT number' = Yes and 'shop $10k+' = Yes: price cases D, E.
  Run 3 - the sample statement with its columns pasted in reverse order: same totals (columns found by header).
  Run 4 - all EXAMPLE rows cleared: example count 0, totals 0.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import openpyxl

HERE = Path(__file__).parent
BOOK = HERE / "UK_Etsy_Seller_Profit_Tracker_2026-27.xlsx"

# price, postage charged, item cost, packaging, postage paid, offsite -> expected (hand calcs in TESTS.md)
# columns I..V: order total, transaction, processing, regulatory, listing, offsite, fees, VAT, own VAT,
# total Etsy, your costs, profit, margin, break-even
KEYS = ["total", "trans", "proc", "rof", "list", "off", "fees", "vat", "own_vat", "etsy", "costs", "profit",
        "margin", "breakeven"]
RUN1 = [
    ("A: £12 digital item, no ads, not VAT-registered", (12, 0, 0, 0, 0, "No"),
     dict(total=12, trans=0.78, proc=0.68, rof=0.06, list=0.16, off=0, fees=1.68, vat=0.34, etsy=2.02, costs=0,
          profit=9.98, margin=9.98 / 12, breakeven=0.50)),
    ("B: £25 candle + £3.95 postage, not VAT-registered", (25, 3.95, 6.00, 0.80, 3.20, "No"),
     dict(total=28.95, trans=1.88, proc=1.36, rof=0.14, list=0.16, off=0, fees=3.54, vat=0.71, etsy=4.25,
          costs=10.00, profit=14.70, margin=14.70 / 28.95, breakeven=8.07)),
    ("C: £40 tote + £4.95 postage via Offsite Ads (15%)", (40, 4.95, 12.00, 1.00, 3.50, "Yes"),
     dict(total=44.95, trans=2.92, proc=2.00, rof=0.22, list=0.16, off=6.74, fees=12.04, vat=2.41, etsy=14.45,
          costs=16.50, profit=14.00, margin=14.00 / 44.95, breakeven=19.65)),
]
RUN2 = [
    ("D: case A with a VAT number given to Etsy", (12, 0, 0, 0, 0, "No"),
     dict(total=12, fees=1.68, vat=0, etsy=1.68, profit=10.32, breakeven=0.40)),
    ("E: case C, VAT number given, shop $10k+ (Offsite Ads 12%)", (40, 4.95, 12.00, 1.00, 3.50, "Yes"),
     dict(total=44.95, off=5.39, fees=10.69, vat=0, etsy=10.69, profit=17.76, breakeven=16.94)),
]
# Sample statement, hand-worked by order in TESTS.md. Monthly P&L year totals (row 17), costs positive.
PL_COLS = dict(C="Sales", D="Refunds", E="Net sales", F="Transaction fees", G="Processing fees",
               H="Regulatory operating fee", I="Listing & renewal fees", J="Offsite Ads fees", K="Etsy Ads",
               L="Other Etsy fees", M="VAT on Etsy fees", N="Postage labels", O="Total Etsy charges",
               V="Total other costs", W="Net profit")
PL_EXPECT = dict(C=197.80, D=-28.95, E=168.85, F=10.99, G=9.72, H=0.97, I=1.92, J=6.74, K=5.95, L=0, M=7.25,
                 N=13.10, O=56.64, V=79.69, W=32.52)
# Tax months: 6 Apr-5 May has the 3 May order; 6 May-5 Jun has 9 May - 4 Jun; 6 Jun-5 Jul the rest
PL_MONTH_NET_SALES = {5: 12.00, 6: 114.85, 7: 42.00}
TP_EXPECT = dict(C=168.85, D=49.00, E=9.72, F=26.79, G=17.69, H=33.13, I=136.33)
HMRC_EXPECT = dict(sales_2026=9, money_2026=168.85, unsorted=0, bad_dates=0, missing_cols=0, net_diff=0)


def recalc(wb, tmp, name):
    src = tmp / f"{name}.xlsx"
    wb.save(src)
    out = tmp / "out"
    out.mkdir(exist_ok=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "xlsx", "--outdir", str(out), str(src)],
                   check=True, capture_output=True, timeout=300)
    return openpyxl.load_workbook(out / src.name, data_only=True)


def close(a, b):
    return abs((a or 0) - b) < 0.005


def set_calc(wb, cases):
    pc = wb["Price Calculator"]
    for r in range(5, 9):
        for c in "ABCDEFGH":
            pc[f"{c}{r}"].value = None
    for i, (name, vals, _) in enumerate(cases):
        pc[f"A{5 + i}"] = name
        for col, v in zip("BCDEFG", vals):
            pc[f"{col}{5 + i}"] = v


def check_calc(res, cases, report):
    pc = res["Price Calculator"]
    fails = 0
    for i, (name, _, exp) in enumerate(cases):
        got = {k: pc.cell(5 + i, 9 + j).value for j, k in enumerate(KEYS)}
        bad = {k: (got[k], v) for k, v in exp.items() if not close(got[k], v)}
        fails += bool(bad)
        report(not bad, f"{name}: profit {got['profit']}, Etsy cost {got['etsy']}, break-even {got['breakeven']}"
               + (f"  MISMATCH {bad}" if bad else ""))
    return fails


def check_statement(res, report, label):
    mo, tp, hc = res["Monthly P&L"], res["To Sole Trader Tracker"], res["HMRC Checks"]
    fails = 0
    bad = {PL_COLS[c]: (mo[f"{c}17"].value, v) for c, v in PL_EXPECT.items() if not close(mo[f"{c}17"].value, v)}
    bad.update({f"net sales row {r}": (mo[f"E{r}"].value, v) for r, v in PL_MONTH_NET_SALES.items()
                if not close(mo[f"E{r}"].value, v)})
    bad.update({f"tracker {c}": (tp[f"{c}17"].value, v) for c, v in TP_EXPECT.items()
                if not close(tp[f"{c}17"].value, v)})
    got_h = dict(sales_2026=hc["C6"].value, money_2026=hc["D6"].value, unsorted=hc["C22"].value,
                 bad_dates=hc["C23"].value, missing_cols=hc["C25"].value, net_diff=hc["C26"].value)
    bad.update({k: (got_h[k], v) for k, v in HMRC_EXPECT.items() if not close(got_h[k], v)})
    if tp["J17"].value != "OK":
        bad["tracker vs P&L"] = tp["J17"].value
    fails += bool(bad)
    report(not bad, f"{label}: net sales {mo['E17'].value}, Etsy charges {mo['O17'].value}, net profit "
           f"{mo['W17'].value}, 2026 sales {hc['C6'].value}" + (f"  MISMATCH {bad}" if bad else ""))
    return fails


def main():
    if not shutil.which("soffice"):
        sys.exit("LibreOffice (soffice) not found - can't recalculate")
    fails = 0

    def report(ok, msg):
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        # run 1
        wb = openpyxl.load_workbook(BOOK)
        set_calc(wb, RUN1)
        res = recalc(wb, tmp, "run1")
        fails += check_calc(res, RUN1, report)
        fails += check_statement(res, report, "Sample statement totals")
        # run 2
        wb = openpyxl.load_workbook(BOOK)
        wb["Settings"]["B8"] = "Yes"
        wb["Settings"]["B9"] = "Yes"
        set_calc(wb, RUN2)
        res = recalc(wb, tmp, "run2")
        fails += check_calc(res, RUN2, report)
        # run 3: reverse the 9 statement columns
        wb = openpyxl.load_workbook(BOOK)
        ep = wb["Etsy Paste"]
        last = ep.max_row
        grid = [[ep.cell(r, c).value for c in range(1, 10)] for r in range(4, last + 1)]
        for i, row in enumerate(grid):
            for j, v in enumerate(reversed(row)):
                ep.cell(4 + i, 1 + j).value = v
        res = recalc(wb, tmp, "run3")
        fails += check_statement(res, report, "Same statement, columns in reverse order")
        # run 4: clear examples
        wb = openpyxl.load_workbook(BOOK)
        ep, oc = wb["Etsy Paste"], wb["Other Costs"]
        for r in range(5, ep.max_row + 1):
            for c in range(1, 16):
                ep.cell(r, c).value = None
        for r in range(5, 13):
            for c in "ABCDEF":
                oc[f"{c}{r}"].value = None
        set_calc(wb, [])
        res = recalc(wb, tmp, "run4")
        hc, mo = res["HMRC Checks"], res["Monthly P&L"]
        ok = hc["C21"].value == 0 and close(mo["W17"].value, 0) and close(mo["E17"].value, 0) \
            and res["Statement Lines"]["M5"].value in (None, "")
        fails += not ok
        report(ok, f"Examples cleared: example rows {hc['C21'].value}, net profit {mo['W17'].value}")
    print("all passed" if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
