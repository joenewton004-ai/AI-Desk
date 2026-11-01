"""Build the UK Sole Trader Bookkeeping & Self Assessment Tracker 2026/27 (.xlsx).

Run: python build.py  -> UK_Sole_Trader_Tracker_2026-27.xlsx next to this file.
Formulas are kept to ones Excel and Google Sheets both support (SUMIFS, SUMPRODUCT, IF, MIN, MAX,
ROUND, EDATE, INDEX/MATCH, COUNTIF, IFERROR). No macros, no Excel tables, no dynamic arrays.
Rates live on the Settings sheet (rows 15-31) with their sources; see SOURCES.md.
"""
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).with_name("UK_Sole_Trader_Tracker_2026-27.xlsx")
CHECKED = "1 Nov 2026"

# ---- look ------------------------------------------------------------------------------------
DARK = "1F4E5A"     # dark teal: titles, headers
MID = "2E7D8C"      # section bars
LIGHT = "E6F2F4"    # input cells
GREY = "F2F2F2"     # formula cells
AMBER = "FFF2CC"    # example rows
RED = "C00000"
WHITE = "FFFFFF"
FONT = "Calibri"

GBP = '£#,##0.00;[Red]-£#,##0.00'
GBP0 = '£#,##0;[Red]-£#,##0'
DATE = 'dd/mm/yyyy'
PCT = '0.0%'
thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)


def fill(c):
    return PatternFill("solid", start_color=c, end_color=c)


def title(ws, text, sub=None, width_to="H"):
    ws["A1"] = text
    ws["A1"].font = Font(name=FONT, size=16, bold=True, color=WHITE)
    for col in range(1, ws[width_to + "1"].column + 1):
        ws.cell(1, col).fill = fill(DARK)
    ws.row_dimensions[1].height = 30
    ws["A1"].alignment = Alignment(vertical="center")
    if sub:
        ws["A2"] = sub
        ws["A2"].font = Font(name=FONT, size=10, italic=True, color="595959")
    ws.sheet_view.showGridLines = False


def header(ws, row, labels, col0=1):
    for i, lab in enumerate(labels):
        c = ws.cell(row, col0 + i, lab)
        c.font = Font(name=FONT, bold=True, color=WHITE)
        c.fill = fill(DARK)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BOX
    ws.row_dimensions[row].height = 32


def section(ws, row, text, cols=4, col0=1):
    for col in range(col0, col0 + cols):
        ws.cell(row, col).fill = fill(MID)
    c = ws.cell(row, col0, text)
    c.font = Font(name=FONT, bold=True, color=WHITE)


def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w


def style_input(c, fmt=None):
    c.fill = fill(LIGHT)
    c.border = BOX
    c.protection = Protection(locked=False)
    c.font = Font(name=FONT)
    if fmt:
        c.number_format = fmt


def style_formula(c, fmt=None, bold=False):
    c.fill = fill(GREY)
    c.border = BOX
    c.font = Font(name=FONT, bold=bold)
    if fmt:
        c.number_format = fmt


def protect(ws):
    # Light protection: no password. Review > Unprotect sheet removes it.
    ws.protection.sheet = True
    ws.protection.formatColumns = False
    ws.protection.formatRows = False
    ws.protection.sort = False
    ws.protection.autoFilter = False


# ---- lists -------------------------------------------------------------------------------------
# (dropdown label, SA103S box, SA103F box)
EXP_CATS = [
    ("Goods for resale / materials", "11", "17"),
    ("Car, van and travel", "12", "20"),
    ("Wages and staff costs", "13", "19"),
    ("Rent, rates, power, insurance", "14", "21"),
    ("Repairs and maintenance", "15", "22"),
    ("Accountancy, legal, professional", "16", "28"),
    ("Interest, bank and card charges", "17", "25 / 26"),
    ("Phone, stationery, office costs", "18", "23"),
    ("Advertising and marketing", "19", "24"),
    ("Other allowable expenses", "19", "30"),
    ("Not allowable (personal, entertaining)", "-", "-"),
]
N_ALLOW = 10  # first 10 are allowable
INC_CATS = [("Sales / fees (turnover)", "9", "15"), ("Other business income", "10", "16"),
            ("Not business income (ignore)", "-", "-")]
PAY = ["Bank transfer", "Card", "Cash", "PayPal", "Platform payout", "Cheque", "Other"]
TURNOVER, OTHER_INC, NOT_INC = (c[0] for c in INC_CATS)
NOT_ALLOW = EXP_CATS[-1][0]

INC_ROWS = (5, 504)
EXP_ROWS = (5, 1004)
MIL_ROWS = (5, 504)


def rng(sheet, col, rows):
    return f"'{sheet}'!${col}${rows[0]}:${col}${rows[1]}" if " " in sheet else f"{sheet}!${col}${rows[0]}:${col}${rows[1]}"


I_D, I_A, I_E = rng("Income", "D", INC_ROWS), rng("Income", "A", INC_ROWS), rng("Income", "E", INC_ROWS)
E_D, E_A, E_E = rng("Expenses", "D", EXP_ROWS), rng("Expenses", "A", EXP_ROWS), rng("Expenses", "E", EXP_ROWS)
M_E, M_A = rng("Mileage", "E", MIL_ROWS), rng("Mileage", "A", MIL_ROWS)

# Settings cell addresses
S_START, S_END, S_MILE, S_METHOD, S_C2 = ("Settings!$B$6", "Settings!$B$7", "Settings!$B$8",
                                          "Settings!$B$9", "Settings!$B$10")
R = {  # rate name -> Settings cell
    "pa": "Settings!$B$16", "taper": "Settings!$B$17", "brb": "Settings!$B$18", "hrl": "Settings!$B$19",
    "br": "Settings!$B$20", "hr": "Settings!$B$21", "ar": "Settings!$B$22",
    "lpl": "Settings!$B$23", "upl": "Settings!$B$24", "c4m": "Settings!$B$25", "c4u": "Settings!$B$26",
    "spt": "Settings!$B$27", "c2w": "Settings!$B$28", "ta": "Settings!$B$29",
    "m1": "Settings!$B$30", "m2": "Settings!$B$31", "mband": "Settings!$B$32",
    "mtd": "Settings!$B$33", "short": "Settings!$B$34",
}


def mileage_value(miles_expr):
    """Simplified mileage allowance for a cumulative business-mile figure."""
    m = miles_expr
    return f"(MIN({m},{R['mband']})*{R['m1']}+MAX({m}-{R['mband']},0)*{R['m2']})"


def miles_between(lo_op, lo, hi):
    return f"SUMIFS({M_E},{M_A},\"{lo_op}\"&{lo},{M_A},\"<=\"&{hi})"


def period_mileage(p_start, p_end):
    """Allowance earned in [p_start, p_end]: f(miles from year start to end) - f(miles before p_start).
    Independent of the order rows were typed in."""
    to_end = f"SUMIFS({M_E},{M_A},\">=\"&{S_START},{M_A},\"<=\"&{p_end})"
    before = f"SUMIFS({M_E},{M_A},\">=\"&{S_START},{M_A},\"<\"&{p_start})"
    return f"IF({S_MILE}=\"On\",ROUND({mileage_value(to_end)}-{mileage_value(before)},2),0)"


wb = Workbook()

# ================================================================================================
# Start Here
# ================================================================================================
ws = wb.active
ws.title = "Start Here"
title(ws, "UK Sole Trader Bookkeeping & Self Assessment Tracker 2026/27",
      f"Rules: 2026/27 tax year (6 April 2026 to 5 April 2027), checked {CHECKED}. "
      "Not tax or accounting advice - check GOV.UK or an accountant.", "C")
widths(ws, {"A": 4, "B": 110, "C": 4})
lines = [
    ("h", "What this is"),
    ("p", "A simple record book for one sole-trader business. Type in what you earn and what you spend, and the "
          "workbook adds it up by month, by Making Tax Digital quarter and for the year. It then gives a rough "
          "estimate of the Income Tax and Class 4 National Insurance on your profit, and shows which box on the "
          "Self Assessment self-employment pages (SA103S or SA103F) each total belongs in."),
    ("p", "It is an estimate to help you plan and put money aside. It is not tax advice and it does not file "
          "anything with HMRC. If your affairs are not simple, talk to an accountant."),
    ("h", "Set up (two minutes)"),
    ("p", "1. Open the Settings tab. Type your business name. Leave the tax year start as 06/04/2026."),
    ("p", "2. Choose whether you claim mileage (On or Off) and how expenses are treated. 'Best for me (auto)' picks "
          "whichever gives you the lower taxable profit: your actual expenses, or the £1,000 trading allowance."),
    ("p", "3. Clear the examples. The amber rows on Income, Expenses and Mileage are made-up EXAMPLE entries so you "
          "can see how it works. Select the amber cells in columns A to G (Income), A to G (Expenses) and A to F "
          "(Mileage) and press Delete. The grey columns are formulas - leave them alone."),
    ("h", "Every week or month"),
    ("p", "Income tab: one line per payment you receive - date, customer, what it was for, amount, category, how "
          "you were paid. Use 'Other business income' for things like a grant or renting out part of your workspace. "
          "Money that isn't from the business (a gift, a transfer from your savings) can go in as 'Not business "
          "income (ignore)' or simply be left out."),
    ("p", "Expenses tab: one line per business cost. Pick the category from the dropdown - the categories follow "
          "the expense boxes on HMRC's self-employment pages. If something is part personal (a phone you also use "
          "privately), enter only the business share. Client entertaining is not allowable: use the 'Not allowable' "
          "category if you want a record of it."),
    ("p", "Mileage tab (if you use HMRC's simplified mileage rates): one line per business journey. The rate is "
          "worked out for you on the total business miles in the year. If you claim mileage for a car or van, don't "
          "also enter its fuel, insurance, repairs or road tax as expenses - the flat rate covers those. Parking and "
          "tolls can still go in Expenses."),
    ("p", "Refunds: if you refund a customer, enter it on Income as a minus amount (for example -25). If a "
          "supplier refunds you, enter it on Expenses as a minus amount in the same category."),
    ("p", "Records are on the cash basis (money in and out when it actually moves), which is HMRC's default for "
          "sole traders from 2024/25. Keep your receipts and invoices: HMRC can ask to see them."),
    ("h", "What the other tabs do"),
    ("p", "Monthly - totals for each tax month (the 6th of one month to the 5th of the next, so the 12 months add "
          "up to exactly one tax year)."),
    ("p", "Quarterly - the four standard Making Tax Digital update periods with their deadlines. MTD updates are "
          "year-to-date, so the second table shows the running totals you would send. You still need MTD-compatible "
          "software (bridging software can read a spreadsheet) to send updates - this file can't send them."),
    ("p", "Tax Estimate - profit, Income Tax and Class 4 NI for the year, plus a few checks (example rows left in, "
          "dates outside the tax year, expenses with no category)."),
    ("p", "SA103 Box Map - each total next to the box it goes in on the short (SA103S) and full (SA103F) pages."),
    ("h", "What the estimate does NOT cover - please read"),
    ("p", "- Scotland: Scottish Income Tax rates and bands are different and are not included. If you are a Scottish "
          "taxpayer the Income Tax figure here will be wrong (Class 4 NI is UK-wide and is still right)."),
    ("p", "- Other income: it assumes this business is your only income. A job, pension, rent, savings interest or "
          "dividends change your tax, and your employer's PAYE already takes tax on wages."),
    ("p", "- Payments on account: HMRC may ask you to pay half of next year's bill in advance (31 January and "
          "31 July). This sheet estimates only the 2026/27 bill itself, not when you pay it."),
    ("p", "- Not included: student loan or postgraduate loan repayments, High Income Child Benefit Charge, pension "
          "contributions, Marriage Allowance, losses brought forward, capital allowances, VAT, partnerships, more than "
          "one business."),
    ("p", "- Class 2 NI: since April 2024 most self-employed people don't pay it. With profits of £7,105 or more you "
          "get the State Pension year without paying. Below that you can choose to pay voluntarily (£3.65 a week in "
          "2026/27) - turn it on in Settings if you want it in the estimate."),
    ("h", "Where the rules come from"),
    ("p", f"Every rate is on the Settings tab with where it came from, checked against GOV.UK on {CHECKED}. "
          "Rates can change. If the government changes a 2026/27 rate after that date, you can type the new figure "
          "on Settings (Review > Unprotect sheet - there is no password)."),
    ("p", "Box numbers are taken from HMRC's latest published pages (the 2025/26 SA103S and SA103F). HMRC publishes "
          "the 2026/27 pages around April 2027 - check the box numbers on the form before you file."),
    ("h", "Google Sheets"),
    ("p", "File > Import > Upload, then 'Replace spreadsheet' (or open the .xlsx from Google Drive and choose File > "
          "Save as Google Sheets). Everything works there; the sheet protection is not carried across, so take care "
          "not to type over the grey formula cells."),
    ("h", "Small print"),
    ("p", "Not tax or accounting advice - check GOV.UK or an accountant. The figures are an estimate based on what "
          "you enter and on the 2026/27 rates for England, Wales and Northern Ireland. You are responsible for your "
          "own tax return."),
]
r = 4
for kind, text in lines:
    c = ws.cell(r, 2, text)
    if kind == "h":
        c.font = Font(name=FONT, size=12, bold=True, color=DARK)
        r += 1
    else:
        c.font = Font(name=FONT, size=11)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = max(16, 15 * (len(text) // 105 + 1))
    r += 1
protect(ws)

# ================================================================================================
# Settings
# ================================================================================================
st = wb.create_sheet("Settings")
title(st, "Settings", "Light blue cells are yours to fill in. Rates below are locked (no password) - see "
                      "SOURCES on each row.", "L")
widths(st, {"A": 42, "B": 22, "C": 70, "D": 3, "E": 38, "F": 10, "G": 10, "H": 3, "I": 30, "J": 10, "K": 3,
            "L": 24})
section(st, 4, "Your business", 3)
rows = [
    (5, "Business name", "My Business", None),
    (6, "Tax year starts", date(2026, 4, 6), DATE),
    (7, "Tax year ends", "=EDATE(B6,12)-1", DATE),
    (8, "Claim mileage (simplified rates)?", "On", None),
    (9, "Expenses method", "Best for me (auto)", None),
    (10, "Include voluntary Class 2 NI in estimate?", "No", None),
]
for row, lab, val, fmt in rows:
    st.cell(row, 1, lab).font = Font(name=FONT, bold=True)
    c = st.cell(row, 2, val)
    if isinstance(val, str) and val.startswith("="):
        style_formula(c, fmt)
    else:
        style_input(c, fmt)
st["C6"] = "Leave as 06/04/2026 for the 2026/27 tax year."
st["C8"] = "On = Mileage tab is counted (cars and vans). Off = ignored."
st["C9"] = ("Best for me (auto) / Actual expenses / Trading allowance. The £1,000 trading allowance "
            "replaces ALL expenses and mileage.")
st["C10"] = "Only matters if profit is under £7,105. Adds 52 weeks x £3.65."
for rr in (6, 8, 9, 10):
    st.cell(rr, 3).font = Font(name=FONT, size=9, italic=True, color="595959")

dv = DataValidation(type="list", formula1='"On,Off"', allow_blank=False)
st.add_data_validation(dv); dv.add("B8")
dv = DataValidation(type="list", formula1='"Best for me (auto),Actual expenses,Trading allowance"')
st.add_data_validation(dv); dv.add("B9")
dv = DataValidation(type="list", formula1='"Yes,No"')
st.add_data_validation(dv); dv.add("B10")
dv = DataValidation(type="date", operator="between", formula1="DATE(2026,4,6)", formula2="DATE(2026,4,6)",
                    showErrorMessage=True, error="This edition is built for the 2026/27 tax year (starts 06/04/2026).")
st.add_data_validation(dv); dv.add("B6")

section(st, 14, f"2026/27 rates and thresholds (England, Wales, NI) - checked on GOV.UK {CHECKED}", 3)
st.cell(15, 1, "Item").font = Font(name=FONT, bold=True)
st.cell(15, 2, "2026/27 value").font = Font(name=FONT, bold=True)
st.cell(15, 3, "Source (full links in SOURCES.md)").font = Font(name=FONT, bold=True)
rates = [
    (16, "Personal allowance", 12570, GBP0, "GOV.UK Income Tax rates and allowances; frozen to 2027/28 (and to 2031)"),
    (17, "Personal allowance taper starts (income)", 100000, GBP0, "£1 of allowance lost per £2 of income above this"),
    (18, "Basic rate band (taxable income)", 37700, GBP0, "GOV.UK: basic rate limit £37,700 for 2026/27 and 2027/28"),
    (19, "Higher rate band ends (taxable income)", 125140, GBP0, "GOV.UK: 40% from £37,701 to £125,140"),
    (20, "Basic rate", 0.20, PCT, "GOV.UK / Finance Act 2026"),
    (21, "Higher rate", 0.40, PCT, "GOV.UK / Finance Act 2026"),
    (22, "Additional rate", 0.45, PCT, "GOV.UK / Finance Act 2026"),
    (23, "Class 4 NI lower profits limit", 12570, GBP0, "GOV.UK Budget 2026 Annex A; GAD report table C.1"),
    (24, "Class 4 NI upper profits limit", 50270, GBP0, "GOV.UK Budget 2026 Annex A; GAD report table C.1"),
    (25, "Class 4 NI main rate", 0.06, PCT, "GOV.UK Budget 2026 Annex A"),
    (26, "Class 4 NI rate above upper limit", 0.02, PCT, "GOV.UK Budget 2026 Annex A"),
    (27, "Class 2 small profits threshold", 7105, GBP0, "GOV.UK NI rates and allowances (up from £6,845)"),
    (28, "Class 2 voluntary rate (per week)", 3.65, GBP, "GOV.UK Voluntary National Insurance: rates"),
    (29, "Trading allowance", 1000, GBP0, "GOV.UK Tax-free allowances on property and trading income"),
    (30, "Mileage rate, first 10,000 business miles (car/van)", 0.55, GBP,
     "HMRC BIM75005 + GOV.UK 'Increasing mileage rates': 55p from 6 Apr 2026 (was 45p)"),
    (31, "Mileage rate, after 10,000 miles (car/van)", 0.25, GBP, "HMRC BIM75005: stays 25p"),
    (32, "Mileage band (miles)", 10000, '#,##0', "HMRC BIM75005"),
    (33, "MTD threshold for 2026/27 qualifying income", 20000, GBP0,
     "GOV.UK: 2026/27 income over £20,000 -> MTD from 6 Apr 2028"),
    (34, "Short form (SA103S) turnover limit", 90000, GBP0, "HMRC SA103S notes: turnover under £90,000"),
]
for row, lab, val, fmt, src in rates:
    st.cell(row, 1, lab).font = Font(name=FONT)
    c = st.cell(row, 2, val)
    style_formula(c, fmt)
    st.cell(row, 3, src).font = Font(name=FONT, size=9, color="595959")
st["A36"] = ("Motorcycles (24p a mile) are not included. Scottish Income Tax rates are not included. "
             "Not tax or accounting advice - check GOV.UK or an accountant.")
st["A36"].font = Font(name=FONT, size=9, italic=True, color=RED)

# Lists (dropdown sources)
section(st, 3, "Expense categories (dropdown)", 3, col0=5)
st.cell(4, 5, "Category"); st.cell(4, 6, "SA103S"); st.cell(4, 7, "SA103F")
for col in (5, 6, 7):
    st.cell(4, col).font = Font(name=FONT, bold=True)
for i, (lab, s, f) in enumerate(EXP_CATS):
    st.cell(5 + i, 5, lab); st.cell(5 + i, 6, s); st.cell(5 + i, 7, f)
section(st, 3, "Income categories", 2, col0=9)
st.cell(4, 9, "Category").font = Font(name=FONT, bold=True)
st.cell(4, 10, "SA103S").font = Font(name=FONT, bold=True)
for i, (lab, s, f) in enumerate(INC_CATS):
    st.cell(5 + i, 9, lab); st.cell(5 + i, 10, s)
section(st, 3, "Payment methods", 1, col0=12)
st.cell(4, 12, "Method").font = Font(name=FONT, bold=True)
for i, p in enumerate(PAY):
    st.cell(5 + i, 12, p)
EXP_LIST = f"Settings!$E$5:$E${4 + len(EXP_CATS)}"
INC_LIST = f"Settings!$I$5:$I${4 + len(INC_CATS)}"
PAY_LIST = f"Settings!$L$5:$L${4 + len(PAY)}"
protect(st)


# ================================================================================================
# Data sheets
# ================================================================================================
def data_sheet(name, sub, heads, wspec, rows, input_cols, fmts, marker_col, last_col):
    ws = wb.create_sheet(name)
    title(ws, name, sub, last_col)
    header(ws, 4, heads)
    widths(ws, wspec)
    ws.freeze_panes = "A5"
    for rr in range(rows[0], rows[1] + 1):
        for col in input_cols:
            style_input(ws[f"{col}{rr}"], fmts.get(col))
    # amber for rows marked EXAMPLE (disappears once the examples are cleared)
    ws.conditional_formatting.add(
        f"A{rows[0]}:{last_col}{rows[1]}",
        FormulaRule(formula=[f'${marker_col}{rows[0]}="EXAMPLE"'], fill=fill(AMBER)))
    return ws


# ---- Income -------------------------------------------------------------------------------------
inc = data_sheet("Income", "One line per payment received. Amber rows are EXAMPLES - clear cells A5:G14 before "
                           "you start (select them, press Delete).",
                 ["Date", "Customer", "Description", "Amount (£)", "Category", "Payment method", "Example?"],
                 {"A": 13, "B": 26, "C": 40, "D": 14, "E": 28, "F": 22, "G": 11},
                 INC_ROWS, "ABCDEFG", {"A": DATE, "D": GBP}, "G", "G")
inc_ex = [
    (date(2026, 4, 14), "Harper & Co", "Logo design - deposit", 250.00, TURNOVER, "Bank transfer"),
    (date(2026, 4, 30), "Etsy", "April shop payout", 412.60, TURNOVER, "Platform payout"),
    (date(2026, 5, 19), "Harper & Co", "Logo design - balance", 550.00, TURNOVER, "Bank transfer"),
    (date(2026, 6, 2), "M. Okafor", "Wedding stationery set", 380.00, TURNOVER, "Card"),
    (date(2026, 7, 11), "Market stall", "Craft fair sales", 265.50, TURNOVER, "Cash"),
    (date(2026, 8, 21), "Bright Lane Cafe", "Menu and signage design", 720.00, TURNOVER, "Bank transfer"),
    (date(2026, 9, 30), "Etsy", "September shop payout", 598.25, TURNOVER, "Platform payout"),
    (date(2026, 11, 8), "Studio sublet", "Desk space rented to a friend", 150.00, OTHER_INC, "Bank transfer"),
    (date(2027, 1, 15), "T. Reid", "Business cards and flyers", 185.00, TURNOVER, "PayPal"),
    (date(2027, 3, 3), "Own savings", "Transfer from my savings (not income)", 500.00, NOT_INC, "Bank transfer"),
]
for i, (d, cu, de, am, ca, pm) in enumerate(inc_ex):
    rr = 5 + i
    for col, v in zip("ABCDEFG", (d, cu, "EXAMPLE - " + de, am, ca, pm, "EXAMPLE")):
        inc[f"{col}{rr}"] = v
for col, lst in (("E", INC_LIST), ("F", PAY_LIST)):
    dv = DataValidation(type="list", formula1=lst, allow_blank=True)
    inc.add_data_validation(dv); dv.add(f"{col}{INC_ROWS[0]}:{col}{INC_ROWS[1]}")
protect(inc)

# ---- Expenses -----------------------------------------------------------------------------------
exp = data_sheet("Expenses", "One line per business cost. Amber rows are EXAMPLES - clear cells A5:G14 before you "
                             "start. Column H fills itself in.",
                 ["Date", "Supplier", "Description", "Amount (£)", "Category (HMRC box)", "Paid by", "Example?",
                  "SA103S box"],
                 {"A": 13, "B": 24, "C": 40, "D": 14, "E": 36, "F": 18, "G": 11, "H": 11},
                 EXP_ROWS, "ABCDEFG", {"A": DATE, "D": GBP}, "G", "H")
exp_ex = [
    (date(2026, 4, 8), "Adobe", "Creative Cloud - April", 22.99, "Phone, stationery, office costs", "Card"),
    (date(2026, 4, 20), "Paper Supplies Ltd", "Card stock and envelopes", 86.40, "Goods for resale / materials",
     "Card"),
    (date(2026, 5, 3), "Trainline", "Train to client meeting", 34.10, "Car, van and travel", "Card"),
    (date(2026, 6, 15), "Simply Business", "Public liability insurance", 96.00, "Rent, rates, power, insurance",
     "Card"),
    (date(2026, 7, 2), "Meta", "Instagram ads - July", 40.00, "Advertising and marketing", "Card"),
    (date(2026, 8, 9), "PrinterFix", "Printer repair", 65.00, "Repairs and maintenance", "Bank transfer"),
    (date(2026, 9, 1), "Vodafone", "Phone bill - business share 60%", 18.00, "Phone, stationery, office costs",
     "Bank transfer"),
    (date(2026, 10, 12), "Starling", "Business account fee", 7.00, "Interest, bank and card charges",
     "Bank transfer"),
    (date(2026, 12, 4), "The Ivy", "Lunch with a client (not allowable)", 58.50, NOT_ALLOW, "Card"),
    (date(2027, 2, 20), "J. Smith Accountants", "Year-end bookkeeping check", 150.00,
     "Accountancy, legal, professional", "Bank transfer"),
]
for i, (d, su, de, am, ca, pm) in enumerate(exp_ex):
    rr = 5 + i
    for col, v in zip("ABCDEFG", (d, su, "EXAMPLE - " + de, am, ca, pm, "EXAMPLE")):
        exp[f"{col}{rr}"] = v
for rr in range(EXP_ROWS[0], EXP_ROWS[1] + 1):
    c = exp[f"H{rr}"]
    c.value = (f'=IF(E{rr}="","",IFERROR(INDEX(Settings!$F$5:$F${4 + len(EXP_CATS)},'
               f'MATCH(E{rr},{EXP_LIST},0)),"check"))')
    style_formula(c)
    c.alignment = Alignment(horizontal="center")
dv = DataValidation(type="list", formula1=EXP_LIST, allow_blank=True)
exp.add_data_validation(dv); dv.add(f"E{EXP_ROWS[0]}:E{EXP_ROWS[1]}")
dv = DataValidation(type="list", formula1=PAY_LIST, allow_blank=True)
exp.add_data_validation(dv); dv.add(f"F{EXP_ROWS[0]}:F{EXP_ROWS[1]}")
protect(exp)

# ---- Mileage ------------------------------------------------------------------------------------
mil = data_sheet("Mileage", "Business journeys by car or van at HMRC's simplified rates (55p a mile for the first "
                            "10,000 business miles in 2026/27, then 25p). Amber rows are EXAMPLES - clear A5:F7.",
                 ["Date", "From", "To", "Purpose", "Business miles", "Example?", "Miles this tax year to date",
                  "Allowance (£)"],
                 {"A": 13, "B": 22, "C": 22, "D": 36, "E": 12, "F": 11, "G": 14, "H": 14},
                 MIL_ROWS, "ABCDEF", {"A": DATE, "E": '#,##0.0'}, "F", "H")
mil_ex = [
    (date(2026, 5, 3), "Home", "Harper & Co, Leeds", "Client meeting (return trip)", 42),
    (date(2026, 7, 11), "Home", "Town hall craft fair", "Market stall (return trip)", 18),
    (date(2026, 10, 5), "Home", "Paper Supplies Ltd", "Collect stock (return trip)", 25),
]
for i, (d, fr, to, pu, mi) in enumerate(mil_ex):
    rr = 5 + i
    for col, v in zip("ABCDEF", (d, fr, to, "EXAMPLE - " + pu, mi, "EXAMPLE")):
        mil[f"{col}{rr}"] = v
r0 = MIL_ROWS[0]
for rr in range(MIL_ROWS[0], MIL_ROWS[1] + 1):
    # miles before this journey's date + same-date journeys up to and including this row
    g = mil[f"G{rr}"]
    g.value = (f'=IF(OR(E{rr}="",A{rr}=""),"",IF(OR(A{rr}<{S_START},A{rr}>{S_END}),"outside year",'
               f'SUMIFS({M_E},{M_A},">="&{S_START},{M_A},"<"&A{rr})+SUMIFS(E${r0}:E{rr},A${r0}:A{rr},A{rr})))')
    style_formula(g, '#,##0.0')
    h = mil[f"H{rr}"]
    h.value = (f'=IF(OR(G{rr}="",G{rr}="outside year"),"",ROUND({mileage_value(f"G{rr}")}-'
               f'{mileage_value(f"(G{rr}-E{rr})")},2))')
    style_formula(h, GBP)
dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
mil.add_data_validation(dv); dv.add(f"E{MIL_ROWS[0]}:E{MIL_ROWS[1]}")
mil["J4"] = "Status"
mil["J4"].font = Font(name=FONT, bold=True, color=DARK)
mil["J5"] = f'=IF({S_MILE}="On","Mileage is ON - counted in your totals","Mileage is OFF in Settings - not counted")'
mil["J5"].font = Font(name=FONT, bold=True, color=RED)
mil["J7"] = "If you claim mileage for a vehicle, don't also put its fuel, insurance,"
mil["J8"] = "repairs or road tax in Expenses. Parking and tolls are fine."
mil["J9"] = "Motorcycles (24p) are not handled here."
for rr in (7, 8, 9):
    mil[f"J{rr}"].font = Font(name=FONT, size=9, italic=True)
mil.column_dimensions["I"].width = 3
mil.column_dimensions["J"].width = 60
protect(mil)


# ================================================================================================
# Monthly
# ================================================================================================
def period_row(ws, rr, s_ref, e_ref, inc_col="C", cat_col0=4):
    """Income, 10 allowable categories, total, mileage, profit for dates in [s_ref, e_ref]."""
    inc_f = (f"=SUMIFS({I_D},{I_A},\">=\"&{s_ref},{I_A},\"<=\"&{e_ref})"
             f"-SUMIFS({I_D},{I_A},\">=\"&{s_ref},{I_A},\"<=\"&{e_ref},{I_E},\"{NOT_INC}\")")
    ws[f"{inc_col}{rr}"] = inc_f
    style_formula(ws[f"{inc_col}{rr}"], GBP)
    for k in range(N_ALLOW):
        col = get_column_letter(cat_col0 + k)
        ws[f"{col}{rr}"] = (f"=SUMIFS({E_D},{E_A},\">=\"&{s_ref},{E_A},\"<=\"&{e_ref},"
                            f"{E_E},{get_column_letter(cat_col0 + k)}$HDR)")
        style_formula(ws[f"{col}{rr}"], GBP)
    tot = get_column_letter(cat_col0 + N_ALLOW)
    mcol = get_column_letter(cat_col0 + N_ALLOW + 1)
    pcol = get_column_letter(cat_col0 + N_ALLOW + 2)
    ws[f"{tot}{rr}"] = f"=SUM({get_column_letter(cat_col0)}{rr}:{get_column_letter(cat_col0 + N_ALLOW - 1)}{rr})"
    style_formula(ws[f"{tot}{rr}"], GBP, bold=True)
    ws[f"{mcol}{rr}"] = "=" + period_mileage(s_ref, e_ref)
    style_formula(ws[f"{mcol}{rr}"], GBP)
    ws[f"{pcol}{rr}"] = f"={inc_col}{rr}-{tot}{rr}-{mcol}{rr}"
    style_formula(ws[f"{pcol}{rr}"], GBP, bold=True)
    return tot, mcol, pcol


def fix_hdr(ws, hdr_row):
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and "$HDR" in c.value:
                c.value = c.value.replace("$HDR", f"${hdr_row}")


CAT_HEADS = [c[0] for c in EXP_CATS[:N_ALLOW]]
mo = wb.create_sheet("Monthly")
title(mo, "Monthly summary", "Tax months run from the 6th to the 5th, so the 12 rows add up to the tax year. "
                             "Income excludes 'Not business income'. Expenses exclude 'Not allowable'.", "Q")
heads = ["Month from", "Month to", "Business income"] + CAT_HEADS + ["Total allowable expenses",
                                                                      "Mileage allowance", "Profit (before tax)",
                                                                      "Profit so far this year"]
header(mo, 4, heads)
mo.row_dimensions[4].height = 48
widths(mo, {"A": 12, "B": 12, "C": 14, **{get_column_letter(4 + k): 13 for k in range(N_ALLOW)},
            "N": 15, "O": 13, "P": 15, "Q": 15})
mo.freeze_panes = "C5"
for n in range(12):
    rr = 5 + n
    mo[f"A{rr}"] = f"=EDATE({S_START},{n})"
    mo[f"B{rr}"] = f"=EDATE({S_START},{n + 1})-1"
    style_formula(mo[f"A{rr}"], 'd mmm yy'); style_formula(mo[f"B{rr}"], 'd mmm yy')
    tot, mcol, pcol = period_row(mo, rr, f"$A{rr}", f"$B{rr}")
    mo[f"Q{rr}"] = f"=SUM($P$5:P{rr})"
    style_formula(mo[f"Q{rr}"], GBP)
fix_hdr(mo, 4)
mo["A17"] = "Year total"
mo["A17"].font = Font(name=FONT, bold=True, color=WHITE)
for col in range(1, 18):
    mo.cell(17, col).fill = fill(DARK)
for col in range(3, 17):
    L = get_column_letter(col)
    mo[f"{L}17"] = f"=SUM({L}5:{L}16)"
    mo[f"{L}17"].number_format = GBP
    mo[f"{L}17"].font = Font(name=FONT, bold=True, color=WHITE)
mo["A19"] = ("Not tax or accounting advice - check GOV.UK or an accountant. Mileage is worked out on total "
             "business miles to date, so the 25p rate starts in the month you pass 10,000 miles.")
mo["A19"].font = Font(name=FONT, size=9, italic=True, color="595959")
protect(mo)

# ================================================================================================
# Quarterly (MTD)
# ================================================================================================
qu = wb.create_sheet("Quarterly")
title(qu, "Making Tax Digital - quarterly periods 2026/27",
      "Standard update periods (GOV.UK). From 2026/27 each quarterly update is year-to-date (cumulative). "
      "This file can't send updates - you need MTD-compatible or bridging software.", "R")
header(qu, 4, ["Quarter", "From", "To", "Update due by", "Business income"] + CAT_HEADS +
       ["Total allowable expenses", "Mileage allowance", "Profit (before tax)"])
qu.row_dimensions[4].height = 48
widths(qu, {"A": 9, "B": 12, "C": 12, "D": 13, "E": 14, **{get_column_letter(6 + k): 13 for k in range(N_ALLOW)},
            "P": 15, "Q": 13, "R": 15})
qu.freeze_panes = "E5"
for q in range(4):
    rr = 5 + q
    qu[f"A{rr}"] = f"Q{q + 1}"
    style_formula(qu[f"A{rr}"])
    qu[f"B{rr}"] = f"=EDATE({S_START},{3 * q})"
    qu[f"C{rr}"] = f"=EDATE({S_START},{3 * q + 3})-1"
    qu[f"D{rr}"] = f"=DATE(YEAR(C{rr}),MONTH(C{rr})+1,7)"
    for col in "BCD":
        style_formula(qu[f"{col}{rr}"], 'd mmm yyyy')
    period_row(qu, rr, f"$B{rr}", f"$C{rr}", inc_col="E", cat_col0=6)
fix_hdr(qu, 4)
qu["A9"] = "Total"
for col in range(1, 19):
    qu.cell(9, col).fill = fill(DARK)
    qu.cell(9, col).font = Font(name=FONT, bold=True, color=WHITE)
for col in range(5, 19):
    L = get_column_letter(col)
    qu[f"{L}9"] = f"=SUM({L}5:{L}8)"
    qu[f"{L}9"].number_format = GBP

section(qu, 11, "Year-to-date figures for each update (what a cumulative MTD update contains)", 18)
header(qu, 12, ["Update", "From", "To", "Update due by", "Business income"] + CAT_HEADS +
       ["Total allowable expenses", "Mileage allowance", "Profit (before tax)"])
qu.row_dimensions[12].height = 48
for q in range(4):
    rr = 13 + q
    qu[f"A{rr}"] = f"Q{q + 1} YTD"
    style_formula(qu[f"A{rr}"])
    qu[f"B{rr}"] = f"={S_START}"
    qu[f"C{rr}"] = f"=C{5 + q}"
    qu[f"D{rr}"] = f"=D{5 + q}"
    for col in "BCD":
        style_formula(qu[f"{col}{rr}"], 'd mmm yyyy')
    for col in range(5, 19):
        L = get_column_letter(col)
        qu[f"{L}{rr}"] = f"=SUM({L}$5:{L}{5 + q})"
        style_formula(qu[f"{L}{rr}"], GBP, bold=(col in (16, 18)))
notes = [
    "The final declaration (the tax return itself) for 2026/27 is due by 31 January 2028, and so is the tax.",
    "Calendar quarters (to 30 June, 30 September, 31 December, 31 March) can be chosen in your software before "
    "the first update instead; the deadlines are the same. This sheet uses the standard periods.",
    "HMRC says it will not give penalty points for late quarterly updates in 2026/27 (the first year).",
    "Who must use MTD: 2024/25 qualifying income over £50,000 -> from 6 Apr 2026; 2025/26 over £30,000 -> from "
    "6 Apr 2027; 2026/27 over £20,000 -> from 6 Apr 2028. Qualifying income = self-employment + property income "
    "before expenses.",
    "With turnover under £90,000 you can send one total for expenses instead of the categories.",
    "Not tax or accounting advice - check GOV.UK or an accountant.",
]
for i, t in enumerate(notes):
    qu[f"A{19 + i}"] = t
    qu[f"A{19 + i}"].font = Font(name=FONT, size=9, italic=True, color="595959")
protect(qu)

# ================================================================================================
# Tax Estimate
# ================================================================================================
te = wb.create_sheet("Tax Estimate")
title(te, "Tax estimate 2026/27 (England, Wales and Northern Ireland)",
      "An estimate of the year's Income Tax and Class 4 NI on this business only. Not tax or accounting advice - "
      "check GOV.UK or an accountant.", "D")
widths(te, {"A": 3, "B": 52, "C": 40, "D": 70})
yr_inc = (f"SUMIFS({I_D},{I_A},\">=\"&{S_START},{I_A},\"<=\"&{S_END},{I_E},\"{{cat}}\")")
yr_miles = f"SUMIFS({M_E},{M_A},\">=\"&{S_START},{M_A},\"<=\"&{S_END})"
T = {}  # label -> row


def trow(rr, label, formula, fmt=GBP, note="", bold=False, key=None):
    te[f"B{rr}"] = label
    te[f"B{rr}"].font = Font(name=FONT, bold=bold)
    te[f"C{rr}"] = formula
    style_formula(te[f"C{rr}"], fmt, bold=bold)
    if note:
        te[f"D{rr}"] = note
        te[f"D{rr}"].font = Font(name=FONT, size=9, color="595959")
    if key:
        T[key] = f"$C${rr}"


section(te, 4, "1. Profit", 3, col0=2)
trow(5, "Turnover (sales and fees)", "=" + yr_inc.format(cat=TURNOVER), key="turn", note="SA103S box 9")
trow(6, "Other business income", "=" + yr_inc.format(cat=OTHER_INC), key="oth", note="SA103S box 10")
trow(7, "Total business income", "=C5+C6", key="inc", bold=True)
trow(8, "Allowable expenses (Expenses tab)", "=Monthly!$N$17", key="exp", note="Excludes 'Not allowable'")
trow(9, "Mileage allowance (Mileage tab)",
     f"=IF({S_MILE}=\"On\",ROUND({mileage_value(yr_miles)},2),0)", key="mil",
     note="0 if mileage is Off in Settings")
trow(10, "Profit using actual expenses", "=C7-C8-C9", key="pa_act")
trow(11, "Profit using the £1,000 trading allowance instead", f"=MAX(C7-{R['ta']},0)", key="pa_ta",
     note="The allowance replaces all expenses and mileage, and can't make a loss")
trow(12, "Better option for you", '=IF(C11<C10,"Trading allowance","Actual expenses")', fmt=None,
     note="The one with the lower taxable profit")
trow(13, "Method used in this estimate",
     f'=IF({S_METHOD}="Actual expenses","Actual expenses",IF({S_METHOD}="Trading allowance",'
     f'"Trading allowance",C12))', fmt=None, note="Change in Settings")
trow(14, "Taxable profit", '=IF(C13="Trading allowance",C11,MAX(C10,0))', key="p", bold=True,
     note="A loss counts as 0 here. Losses can be used in other ways - ask an accountant")

section(te, 16, "2. Income Tax", 3, col0=2)
trow(17, "Personal allowance after taper",
     f"=IF(C14<={R['taper']},{R['pa']},MAX(0,{R['pa']}-ROUNDDOWN((C14-{R['taper']})/2,0)))",
     note="Falls by £1 for every £2 of income over £100,000")
trow(18, "Taxable income", "=MAX(0,C14-C17)")
trow(19, "Basic rate 20%", f"=ROUND(MIN(C18,{R['brb']})*{R['br']},2)", note="On the first £37,700 of taxable income")
trow(20, "Higher rate 40%", f"=ROUND(MAX(0,MIN(C18,{R['hrl']})-{R['brb']})*{R['hr']},2)",
     note="£37,701 to £125,140")
trow(21, "Additional rate 45%", f"=ROUND(MAX(0,C18-{R['hrl']})*{R['ar']},2)", note="Over £125,140")
trow(22, "Income Tax", "=C19+C20+C21", bold=True, key="it")

section(te, 24, "3. National Insurance", 3, col0=2)
trow(25, "Class 4 at 6% (£12,570 to £50,270)", f"=ROUND(MAX(0,MIN(C14,{R['upl']})-{R['lpl']})*{R['c4m']},2)")
trow(26, "Class 4 at 2% (over £50,270)", f"=ROUND(MAX(0,C14-{R['upl']})*{R['c4u']},2)")
trow(27, "Class 4 NI", "=C25+C26", bold=True)
trow(28, "Class 2 NI position",
     f'=IF(C14>={R["spt"]},"Treated as paid - nothing to pay","Below £7,105 - voluntary Class 2 is optional")',
     fmt=None, note="Profits of £7,105+ get the NI year free. Below that you can choose to pay")
trow(29, "Voluntary Class 2 (only if switched on in Settings)",
     f'=IF(AND({S_C2}="Yes",C14<{R["spt"]}),ROUND(52*{R["c2w"]},2),0)')

section(te, 31, "4. Estimated bill for 2026/27", 3, col0=2)
trow(32, "Income Tax + National Insurance", "=ROUND(C22+C27+C29,2)", bold=True, key="total")
te["C32"].font = Font(name=FONT, bold=True, size=13)
te["C32"].fill = fill(AMBER)
trow(33, "As a share of business income", "=IF(C7>0,C32/C7,0)", fmt=PCT,
     note="A rough guide for how much of each payment to put aside")
trow(34, "Due by", '="31 January 2028"', fmt=None,
     note="Payments on account may also be due - not estimated here (see below)")

section(te, 36, "5. Checks", 3, col0=2)
trow(37, "EXAMPLE rows still in Income / Expenses / Mileage",
     f'=COUNTIF({rng("Income", "G", INC_ROWS)},"EXAMPLE")+COUNTIF({rng("Expenses", "G", EXP_ROWS)},"EXAMPLE")'
     f'+COUNTIF({rng("Mileage", "F", MIL_ROWS)},"EXAMPLE")', fmt='0',
     note="Should be 0 once you start - clear the amber rows (see Start Here)")
trow(38, "Entries dated outside the tax year (not counted)",
     f"=SUMPRODUCT(({I_A}<>\"\")*(({I_A}<{S_START})+({I_A}>{S_END})>0))"
     f"+SUMPRODUCT(({E_A}<>\"\")*(({E_A}<{S_START})+({E_A}>{S_END})>0))"
     f"+SUMPRODUCT(({M_A}<>\"\")*(({M_A}<{S_START})+({M_A}>{S_END})>0))", fmt='0',
     note="Check the dates if this isn't 0")
trow(39, "Amounts with no date (not counted)",
     f"=SUMPRODUCT(({I_D}<>\"\")*({I_A}=\"\"))+SUMPRODUCT(({E_D}<>\"\")*({E_A}=\"\"))"
     f"+SUMPRODUCT(({M_E}<>\"\")*({M_A}=\"\"))", fmt='0')
trow(40, "Expenses with no category (not counted)",
     f"=SUMPRODUCT(({E_D}<>\"\")*({E_E}=\"\"))", fmt='0', note="Pick a category, or they are left out")
trow(41, "Short pages (SA103S) or full pages (SA103F)?",
     f'=IF(C5<{R["short"]},"Short (SA103S) is usually fine","Use the full pages (SA103F)")', fmt=None,
     note="Short pages: turnover under £90,000 and simple affairs (see HMRC's notes)")
trow(42, "Making Tax Digital",
     f'=IF(C7>{R["mtd"]},"Over £20,000: expect MTD from 6 April 2028 (if self-employment is all your qualifying '
     f'income)","£20,000 or under on this business alone")', fmt=None,
     note="Qualifying income = gross self-employment + property income, before expenses")
trow(43, "Total income for the £1,000 test",
     f'=IF(C7<={R["ta"]},"£1,000 or less: you may not need to tell HMRC (see GOV.UK)",'
     f'"Over £1,000: register for Self Assessment")', fmt=None)

section(te, 45, "What this estimate does not include", 3, col0=2)
caveats = [
    "Scotland: Scottish Income Tax rates and bands differ and are NOT included. Class 4 NI is the same UK-wide.",
    "Other income (a job, pension, rent, savings, dividends) - it assumes this business is your only income.",
    "Payments on account: if your bill is over £1,000, HMRC usually asks for two advance payments towards next "
    "year (31 Jan and 31 Jul). This sheet estimates the 2026/27 liability only.",
    "Student loan repayments, High Income Child Benefit Charge, pension relief, Marriage Allowance, capital "
    "allowances, losses, VAT.",
    "Not tax or accounting advice - check GOV.UK or an accountant.",
]
for i, t in enumerate(caveats):
    te[f"B{46 + i}"] = "- " + t
    te[f"B{46 + i}"].font = Font(name=FONT, size=10)
    te.merge_cells(f"B{46 + i}:D{46 + i}")
    te[f"B{46 + i}"].alignment = Alignment(wrap_text=True)
    te.row_dimensions[46 + i].height = 28
protect(te)

# ================================================================================================
# SA103 box map
# ================================================================================================
bm = wb.create_sheet("SA103 Box Map")
title(bm, "Where each total goes on your tax return",
      "Box numbers from HMRC's latest published pages (2025/26 SA103S and SA103F). Check them on the 2026/27 form "
      "when HMRC publishes it (around April 2027).", "F")
header(bm, 4, ["SA103S box", "SA103F box", "What it is", "Your 2026/27 figure", "How it's worked out", "Check"])
widths(bm, {"A": 11, "B": 11, "C": 44, "D": 18, "E": 60, "F": 26})
bm.freeze_panes = "A5"
TA_ON = "'Tax Estimate'!$C$13=\"Trading allowance\""
box_rows = [
    ("9", "15", "Turnover", "='Tax Estimate'!$C$5", "Income tab, category 'Sales / fees (turnover)'", ""),
    ("10", "16", "Any other business income", "='Tax Estimate'!$C$6", "Income tab, 'Other business income'", ""),
    ("10.1", "16.1", "Trading income allowance",
     f"=IF({TA_ON},MIN({R['ta']},'Tax Estimate'!$C$7),0)",
     "Only if you use the £1,000 allowance - then leave the expense boxes empty", ""),
]
for k, (lab, s, f) in enumerate(EXP_CATS[:N_ALLOW]):
    col = get_column_letter(4 + k)
    if lab == "Car, van and travel":
        formula = f"=IF({TA_ON},0,Monthly!${col}$17+'Tax Estimate'!$C$9)"
        how = "Expenses 'Car, van and travel' + mileage allowance"
    else:
        formula = f"=IF({TA_ON},0,Monthly!${col}$17)"
        how = f"Expenses '{lab}'"
    check = ""
    if lab == "Advertising and marketing":
        check = "Short form: part of box 19"
    if lab == "Interest, bank and card charges":
        check = "Full form: 25 loan interest, 26 bank/card charges"
    box_rows.append((s, f, lab, formula, how, check))
box_rows += [
    ("20", "31", "Total allowable expenses", f"=IF({TA_ON},0,'Tax Estimate'!$C$8+'Tax Estimate'!$C$9)",
     "Turnover under £90,000: you may put just this total in box 20", ""),
    ("21", "-", "Net profit", "=MAX(0,D5+D6-D7-D18)", "Boxes 9 + 10 - 10.1 - 20, if positive",
     "Full form: see its profit boxes"),
    ("22", "-", "Net loss", "=MAX(0,D18-D5-D6)", "If expenses are more than income",
     "Losses: talk to an accountant"),
]
for i, (s, f, lab, formula, how, check) in enumerate(box_rows):
    rr = 5 + i
    for col, v in zip("ABCEF", (s, f, lab, how, check)):
        bm[f"{col}{rr}"] = v
        bm[f"{col}{rr}"].border = BOX
        bm[f"{col}{rr}"].font = Font(name=FONT, bold=(col == "A"))
    bm[f"A{rr}"].alignment = bm[f"B{rr}"].alignment = Alignment(horizontal="center")
    bm[f"D{rr}"] = formula
    style_formula(bm[f"D{rr}"], GBP, bold=True)
# sanity: total expenses row must be row 18 for the net profit formula
assert bm["C18"].value == "Total allowable expenses", bm["C18"].value
bm["A25"] = ("Two categories share SA103S box 19 (advertising + other allowable expenses) - add them. "
             "Client entertaining is never allowable. Not tax or accounting advice - check GOV.UK or an accountant.")
bm["A25"].font = Font(name=FONT, size=9, italic=True, color="595959")
bm["A26"] = ("Box 20 on the short pages = total of boxes 11 to 19 (HMRC notes). Full pages also have disallowable "
             "columns (boxes 32-46): this file leaves non-allowable costs out instead.")
bm["A26"].font = Font(name=FONT, size=9, italic=True, color="595959")
protect(bm)

# tab colours
for w, colr in zip(wb.worksheets, [DARK, "7F7F7F", MID, MID, MID, "C55A11", "C55A11", RED, "7F7F7F"]):
    w.sheet_properties.tabColor = colr
for w in wb.worksheets:
    w.sheet_view.zoomScale = 100
    w.page_setup.orientation = "landscape"
    w.page_setup.paperSize = w.PAPERSIZE_A4
    w.sheet_properties.pageSetUpPr.fitToPage = True
    w.page_setup.fitToWidth = 1
    w.page_setup.fitToHeight = 0
    w.print_title_rows = "4:4" if w.title in ("Income", "Expenses", "Mileage") else None
wb.active = 0
wb.properties.title = "UK Sole Trader Bookkeeping & Self Assessment Tracker 2026/27"
wb.properties.creator = "Venture Station"

if __name__ == "__main__":
    wb.save(OUT)
    print("saved", OUT)
