"""Paste a REAL Etsy monthly statement CSV into the tracker and print how each row is read and sorted.
Usage: python test_real_csv.py <statement.csv>"""
import csv, sys, tempfile, pathlib
import openpyxl
from test_profit import recalc, BOOK, set_calc

rows = list(csv.reader(open(sys.argv[1], encoding="utf-8-sig")))
wb = openpyxl.load_workbook(BOOK)
ep, oc = wb["Etsy Paste"], wb["Other Costs"]
for r in range(4, ep.max_row + 1):
    for c in range(1, 16):
        ep.cell(r, c).value = None
for r in range(5, 13):
    for c in "ABCDEF":
        oc[f"{c}{r}"].value = None
set_calc(wb, [])
for i, row in enumerate(r for r in rows if any(r)):
    for j, v in enumerate(row):
        ep.cell(4 + i, 1 + j).value = v          # pasted as text, like a raw paste
res = recalc(wb, pathlib.Path(tempfile.mkdtemp()), "real")
sl = res["Statement Lines"]
print([sl.cell(4, c).value for c in range(1, 14)])
for r in range(5, 5 + len(rows)):
    v = [sl.cell(r, c).value for c in range(1, 14)]
    if any(x not in (None, "") for x in v): print(v)
mo, hc = res["Monthly P&L"], res["HMRC Checks"]
print("P&L totals row 17:", {mo.cell(4, c).value: mo.cell(17, c).value for c in range(3, 24) if mo.cell(17, c).value})
print("unsorted", hc["C22"].value, "bad dates", hc["C23"].value, "missing cols", hc["C25"].value, "net diff", hc["C26"].value)
