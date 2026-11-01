"""Check the workbook's tax estimate against hand-worked cases (see TESTS.md).

Run: python test_tax.py   (needs LibreOffice: soffice on PATH)
For each case: load the built workbook, clear the EXAMPLE rows, type the case's entries, save a copy,
let LibreOffice recalculate it (headless xlsx -> xlsx round trip), then read the results back.
"""
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import openpyxl

HERE = Path(__file__).parent
BOOK = HERE / "UK_Sole_Trader_Tracker_2026-27.xlsx"

# name, settings, income rows (amount, category), expense rows (amount, category), miles, expected
CASES = [
    ("A: profit £8,000", "Actual expenses", "Off", [(8000, "Sales / fees (turnover)")], [], 0,
     dict(profit=8000, it=0, c4=0, total=0)),
    ("B: profit £30,000 (£34,000 income - £4,000 expenses)", "Best for me (auto)", "Off",
     [(30000, "Sales / fees (turnover)"), (4000, "Other business income")],
     [(2500, "Rent, rates, power, insurance"), (1500, "Phone, stationery, office costs"),
      (999, "Not allowable (personal, entertaining)")], 0,
     dict(profit=30000, it=3486.00, c4=1045.80, total=4531.80)),
    ("C: profit £60,000 (£66,000 income - 12,000 business miles)", "Best for me (auto)", "On",
     [(66000, "Sales / fees (turnover)")], [], 12000,
     dict(profit=60000, it=11432.00, c4=2456.60, total=13888.60)),
    # extra checks beyond the three asked for
    ("D: profit £110,000 (allowance taper)", "Actual expenses", "Off", [(110000, "Sales / fees (turnover)")], [], 0,
     dict(profit=110000, it=33432.00, c4=3456.60, total=36888.60)),
    ("E: £1,500 income, £200 expenses -> trading allowance wins", "Best for me (auto)", "Off",
     [(1500, "Sales / fees (turnover)")], [(200, "Goods for resale / materials")], 0,
     dict(profit=500, it=0, c4=0, total=0)),
]


def hand(profit):
    """Independent Python version of the 2026/27 rUK rules, for the record."""
    pa = 12570 if profit <= 100000 else max(0, 12570 - (profit - 100000) // 2)
    ti = max(0, profit - pa)
    it = min(ti, 37700) * .2 + max(0, min(ti, 125140) - 37700) * .4 + max(0, ti - 125140) * .45
    c4 = max(0, min(profit, 50270) - 12570) * .06 + max(0, profit - 50270) * .02
    return round(it, 2), round(c4, 2)


def run_case(tmp, i, name, method, mileage, incs, exps, miles):
    wb = openpyxl.load_workbook(BOOK)
    st, inc, exp, mil = wb["Settings"], wb["Income"], wb["Expenses"], wb["Mileage"]
    st["B9"], st["B8"] = method, mileage
    for ws, cols in ((inc, "ABCDEFG"), (exp, "ABCDEFG"), (mil, "ABCDEF")):
        for r in range(5, 15):
            for c in cols:
                ws[f"{c}{r}"].value = None
    for k, (amt, cat) in enumerate(incs):
        inc[f"A{5+k}"], inc[f"B{5+k}"], inc[f"D{5+k}"], inc[f"E{5+k}"] = date(2026, 6, 1), "Test", amt, cat
    for k, (amt, cat) in enumerate(exps):
        exp[f"A{5+k}"], exp[f"B{5+k}"], exp[f"D{5+k}"], exp[f"E{5+k}"] = date(2026, 9, 1), "Test", amt, cat
    if miles:  # two journeys, entered out of date order on purpose
        mil["A5"], mil["E5"] = date(2027, 2, 1), miles - 4000
        mil["A6"], mil["E6"] = date(2026, 5, 1), 4000
    src = tmp / f"case{i}.xlsx"
    wb.save(src)
    out = tmp / "out"
    out.mkdir(exist_ok=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "xlsx", "--outdir", str(out), str(src)],
                   check=True, capture_output=True, timeout=180)
    te = openpyxl.load_workbook(out / src.name, data_only=True)["Tax Estimate"]
    return dict(profit=te["C14"].value, it=te["C22"].value, c4=te["C27"].value, total=te["C32"].value,
                method=te["C13"].value, examples=te["C37"].value)


def main():
    if not shutil.which("soffice"):
        sys.exit("LibreOffice (soffice) not found - can't recalculate")
    fails = 0
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for i, (name, method, mileage, incs, exps, miles, exp) in enumerate(CASES):
            got = run_case(tmp, i, name, method, mileage, incs, exps, miles)
            py_it, py_c4 = hand(exp["profit"])
            assert (py_it, py_c4) == (exp["it"], exp["c4"]), f"hand table vs python mismatch in {name}"
            ok = all(abs((got[k] or 0) - v) < 0.005 for k, v in exp.items()) and got["examples"] == 0
            fails += not ok
            print(f"{'PASS' if ok else 'FAIL'}  {name}: method={got['method']}, profit {got['profit']}, "
                  f"income tax {got['it']}, class 4 {got['c4']}, total {got['total']} "
                  f"(expected {exp['total']})")
    print("all passed" if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
