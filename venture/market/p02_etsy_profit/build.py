"""Build the UK Etsy Seller Profit Tracker 2026/27 (.xlsx).

Run: python build.py  -> UK_Etsy_Seller_Profit_Tracker_2026-27.xlsx next to this file.
Same look and layout rules as product #1 (p01_sole_trader/build.py). Formulas are kept to ones Excel, Google Sheets
and LibreOffice all support (SUMIFS, COUNTIFS, SUMPRODUCT, IF, INDEX/MATCH, IFERROR, ROUND, SEARCH, VALUE, DATE,
EDATE). No macros, no Excel tables, no dynamic arrays. Fee rates live on Settings rows 15-26 with their sources;
see SOURCES.md.
"""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).with_name("UK_Etsy_Seller_Profit_Tracker_2026-27.xlsx")
CHECKED = "1 Nov 2026"
OWNER = "[OWNER TO WRITE IN OWN WORDS]"

# ---- look (identical to product #1) ----------------------------------------------------------
DARK = "1F4E5A"
MID = "2E7D8C"
LIGHT = "E6F2F4"
GREY = "F2F2F2"
AMBER = "FFF2CC"
RED = "C00000"
WHITE = "FFFFFF"
FONT = "Calibri"

GBP = '£#,##0.00;[Red]-£#,##0.00'
GBP0 = '£#,##0;[Red]-£#,##0'
GBP_TOT = '£#,##0.00;-£#,##0.00'  # total rows (white on dark): no red
DATE = 'dd/mm/yyyy'
PCT = '0.0%'
PCT2 = '0.00%'
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


def header(ws, row, labels, col0=1, height=32):
    for i, lab in enumerate(labels):
        c = ws.cell(row, col0 + i, lab)
        c.font = Font(name=FONT, bold=True, color=WHITE)
        c.fill = fill(DARK)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BOX
    ws.row_dimensions[row].height = height


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


def note(c, size=9, color="595959", italic=True):
    c.font = Font(name=FONT, size=size, italic=italic, color=color)


def protect(ws):
    # Light protection: no password. Review > Unprotect sheet removes it.
    ws.protection.sheet = True
    ws.protection.formatColumns = False
    ws.protection.formatRows = False
    ws.protection.sort = False
    ws.protection.autoFilter = False


def yes_no(ws, ref):
    dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(ref)


# ---- categories --------------------------------------------------------------------------------
# Sole Trader Tracker (product #1) expense categories used here - exact labels from p01 build.py
P1_TURN = "Sales / fees (turnover)"
P1_GOODS = "Goods for resale / materials"
P1_BANK = "Interest, bank and card charges"
P1_OFFICE = "Phone, stationery, office costs"
P1_ADS = "Advertising and marketing"
P1_OTHER = "Other allowable expenses"
P1_NOT = "Not allowable (personal, entertaining)"
P1_EXP = [P1_GOODS, P1_BANK, P1_OFFICE, P1_ADS, P1_OTHER]

# Etsy statement categories: (category, group, product #1 category, why)
SALES, REFUNDS = "Sales", "Refunds"
C_TRANS, C_PROC, C_ROF, C_LIST = "Transaction fees", "Processing fees", "Regulatory operating fee", "Listing & renewal fees"
C_OFF, C_ADS, C_OTHERFEE, C_VAT, C_LABEL = ("Offsite Ads fees", "Etsy Ads", "Other Etsy fees", "VAT on Etsy fees",
                                            "Postage labels")
IGN_DEP, IGN_TAX, IGN_HDR = "Ignore - deposit / transfer", "Ignore - tax collected for HMRC", "Ignore - header row"
UNSORTED = "Not sorted - check"
CATS = [
    (SALES, "Income", P1_TURN, "Gross sales (items + postage charged) are turnover - not the payouts to your bank."),
    (REFUNDS, "Income", P1_TURN, "Refunds reduce turnover (enter them as a minus amount in the Tracker)."),
    (C_TRANS, "Etsy fee", P1_OTHER, "A selling commission, not a financial charge -> other allowable expenses."),
    (C_PROC, "Etsy fee", P1_BANK, "Card payment processing is a card charge (SA103S box 17 / SA103F box 26)."),
    (C_ROF, "Etsy fee", P1_OTHER, "A platform charge on each order -> other allowable expenses."),
    (C_LIST, "Etsy fee", P1_OTHER, "A platform charge per listing / renewal -> other allowable expenses."),
    (C_OFF, "Advertising", P1_ADS, "A fee for ads Etsy runs for you -> advertising."),
    (C_ADS, "Advertising", P1_ADS, "Pay-per-click ads on Etsy -> advertising."),
    (C_OTHERFEE, "Etsy fee", P1_OTHER, "Subscriptions and other Etsy charges -> other allowable expenses."),
    (C_VAT, "Etsy fee", P1_OTHER, "VAT you can't reclaim is part of the fee's cost. Kept in one line for simplicity: "
                                   "it shares SA103S box 19 with the fees above."),
    (C_LABEL, "Postage", P1_OFFICE, "HMRC groups postage with phone, stationery and office costs."),
    (IGN_DEP, "Ignore", "-", "Money moving from Etsy to your bank (or you topping Etsy up) is not income or a cost."),
    (IGN_TAX, "Ignore", "-", "Tax Etsy collects from buyers and pays to HMRC itself is not your money."),
    (IGN_HDR, "Ignore", "-", "A repeated header row from pasting a second month."),
]
# Classification rules, first match wins: (Type is, Title contains, category). "*" = any Type.
RULES = [
    ("VAT", "", C_VAT),
    ("*", "offsite", C_OFF),
    ("Fee", "transaction fee", C_TRANS),
    ("Fee", "processing fee", C_PROC),
    ("Fee", "regulatory", C_ROF),
    ("Fee", "listing", C_LIST),
    ("Fee", "renew", C_LIST),
    ("Fee", "", C_OTHERFEE),
    ("Tax", "buyer", IGN_TAX),
    ("Tax", "fee", C_VAT),
    ("Sale", "", SALES),
    ("Refund", "", REFUNDS),
    ("Marketing", "", C_ADS),
    ("Shipping", "", C_LABEL),
    ("Postage", "", C_LABEL),
    ("Subscription", "", C_OTHERFEE),
    ("Deposit", "", IGN_DEP),
    ("Payment", "", IGN_DEP),
    ("Type", "", IGN_HDR),
]
N_RULES = 30
# Other costs (typed by the seller): (category, product #1 category)
OC_CATS = [
    ("Stock and materials", P1_GOODS),
    ("Packaging", P1_GOODS),
    ("Postage paid (outside Etsy)", P1_OFFICE),
    ("Advertising outside Etsy", P1_ADS),
    ("Software and subscriptions", P1_OFFICE),
    ("Other allowable costs", P1_OTHER),
    ("Not allowable (personal)", P1_NOT),
]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# ---- cell addresses ----------------------------------------------------------------------------
S = dict(start="Settings!$B$6", end="Settings!$B$7", vatno="Settings!$B$8", big="Settings!$B$9",
         ownvat="Settings!$B$10", other="Settings!$B$11",
         tf="Settings!$B$15", pp="Settings!$B$16", pf="Settings!$B$17", rof="Settings!$B$18", lf="Settings!$B$19",
         oa="Settings!$B$20", oa12="Settings!$B$21", cap="Settings!$B$22", vat="Settings!$B$23",
         n30="Settings!$B$24", m1700="Settings!$B$25", ta="Settings!$B$26")
CSV_FIELDS = ["Date", "Type", "Title", "Info", "Amount", "Fees & Taxes", "Net"]
CSV_ROW0 = 30  # Settings rows 30-36: field, header name, found-in-column
COLIDX = {f: f"Settings!$C${CSV_ROW0 + i}" for i, f in enumerate(CSV_FIELDS)}
CAT_RANGE = f"Settings!$G$5:$G${4 + len(CATS)}"
GRP_RANGE = f"Settings!$H$5:$H${4 + len(CATS)}"
P1C_RANGE = f"Settings!$I$5:$I${4 + len(CATS)}"
R_NUM, R_TYPE, R_KW, R_CAT = (f"Settings!${c}$5:${c}${4 + N_RULES}" for c in "KLMN")
MON_RANGE = "Settings!$P$5:$P$16"
OC_LIST = f"Settings!$R$5:$R${4 + len(OC_CATS)}"
OC_P1 = f"Settings!$S$5:$S${4 + len(OC_CATS)}"

PASTE_ROWS = (5, 1504)
OC_ROWS = (5, 504)
CALC_ROWS = (5, 54)
SL = "'Statement Lines'"
SL_DATE = f"{SL}!$H${PASTE_ROWS[0]}:$H${PASTE_ROWS[1]}"
SL_VAL = f"{SL}!$K${PASTE_ROWS[0]}:$K${PASTE_ROWS[1]}"
SL_NET = f"{SL}!$L${PASTE_ROWS[0]}:$L${PASTE_ROWS[1]}"
SL_CAT = f"{SL}!$M${PASTE_ROWS[0]}:$M${PASTE_ROWS[1]}"
SL_GRP = f"{SL}!$N${PASTE_ROWS[0]}:$N${PASTE_ROWS[1]}"
SL_P1 = f"{SL}!$O${PASTE_ROWS[0]}:$O${PASTE_ROWS[1]}"
SL_EX = f"{SL}!$P${PASTE_ROWS[0]}:$P${PASTE_ROWS[1]}"
OC = "'Other Costs'"
OC_DATE = f"{OC}!$A${OC_ROWS[0]}:$A${OC_ROWS[1]}"
OC_AMT = f"{OC}!$D${OC_ROWS[0]}:$D${OC_ROWS[1]}"
OC_CAT = f"{OC}!$E${OC_ROWS[0]}:$E${OC_ROWS[1]}"
OC_EX = f"{OC}!$F${OC_ROWS[0]}:$F${OC_ROWS[1]}"
OC_P1C = f"{OC}!$G${OC_ROWS[0]}:$G${OC_ROWS[1]}"


# ---- sample Etsy statement (made-up, built with the same fee rules) ------------------------------
def r2(x):
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def money(x):
    if x is None:
        return "--"
    return f"-£{-x:,.2f}" if x < 0 else f"£{x:,.2f}"


def dtxt(d):
    return f"{d.strftime('%B')} {d.day}, {d.year}"


# (date, order no, item, price, postage charged, offsite ad?, postage label paid or None)
SAMPLE_ORDERS = [
    (date(2026, 5, 3), 3401118826, "Monthly budget planner (digital)", 12.00, 0.00, False, None),
    (date(2026, 5, 9), 3401204417, "Hand-poured soy candle", 25.00, 3.95, False, 3.20),
    (date(2026, 5, 17), 3401377051, "Linen tote bag", 40.00, 4.95, True, 3.50),
    (date(2026, 5, 28), 3401590263, "Monthly budget planner (digital)", 12.00, 0.00, False, None),
    (date(2026, 6, 4), 3401712980, "Hand-poured soy candle", 25.00, 3.95, False, 3.20),
    (date(2026, 6, 12), 3401866342, "Monthly budget planner (digital)", 12.00, 0.00, False, None),
    (date(2026, 6, 15), 3401901457, "Budget planner bundle (digital)", 18.00, 0.00, False, None),
    (date(2026, 6, 21), 3402003175, "Hand-poured soy candle", 25.00, 3.95, False, 3.20),
    (date(2026, 6, 25), 3402118604, "Monthly budget planner (digital)", 12.00, 0.00, False, None),
]
REFUNDED = 3402003175   # refunded in full on 27 June 2026
TF, PP, PF, ROF, LF, OA, VAT = 0.065, 0.04, 0.20, 0.0048, 0.16, 0.15, 0.20


def sample_rows():
    """Rows in the Etsy statement layout: Date, Type, Title, Info, Currency, Amount, Fees & Taxes, Net, Tax Details.
    Amounts are text like '£12.00' / '-£0.78' / '--', as in the CSV. Non-VAT-registered seller (VAT on fees)."""
    rows = []

    def fee(d, typ, ttl, info, amt):
        rows.append((dtxt(d), typ, ttl, info, "GBP", "--", money(-amt), money(-amt), "--"))
        rows.append((dtxt(d), "VAT", "VAT: " + ttl, info, "GBP", "--", money(-r2(amt * VAT)), money(-r2(amt * VAT)),
                     "--"))

    for n, d in enumerate([date(2026, 5, 1)] * 3):
        fee(d, "Fee", "Listing fee", f"Listing #18{n}0442761", LF)
    for d, no, item, price, post, off, label in SAMPLE_ORDERS:
        total = price + post
        rows.append((dtxt(d), "Sale", f"Payment for Order #{no}", f"Order #{no}", "GBP", money(total), "--",
                     money(total), "--"))
        fee(d, "Fee", f"Transaction fee: {item}", f"Order #{no}", r2(price * TF))
        if post:
            fee(d, "Fee", "Transaction fee: Shipping", f"Order #{no}", r2(post * TF))
        fee(d, "Fee", "Processing fee", f"Order #{no}", r2(total * PP + PF))
        fee(d, "Fee", "Regulatory operating fee", f"Order #{no}", r2(total * ROF))
        fee(d, "Fee", "Listing fee", f"Auto-renew sold, Order #{no}", LF)
        if off:
            fee(d, "Marketing", "Offsite Ads fee", f"Order #{no}", min(r2(total * OA), 76.0))
        if label:
            rows.append((dtxt(date(d.year, d.month, d.day + 1)), "Shipping", "Royal Mail postage label",
                         f"Order #{no}", "GBP", "--", money(-label), money(-label), "--"))
        if d == date(2026, 5, 17):
            fee(date(2026, 5, 31), "Marketing", "Etsy Ads", "Etsy Ads, May 2026", 3.20)
            rows.append((dtxt(date(2026, 5, 31)), "Deposit", "£87.41 sent to your bank account", "", "GBP", "--",
                         "--", "--", "--"))
            # June's file pasted below May's, header row and all
            rows.append(("Date", "Type", "Title", "Info", "Currency", "Amount", "Fees & Taxes", "Net", "Tax Details"))
        if no == REFUNDED:
            rd = date(2026, 6, 27)
            rows.append((dtxt(rd), "Refund", f"Refund to buyer for Order #{no}", f"Order #{no}", "GBP",
                         money(-total), "--", money(-total), "--"))
            for ttl, amt in ((f"Credit for transaction fee: {item}", r2(price * TF)),
                             ("Credit for transaction fee: Shipping", r2(post * TF))):
                rows.append((dtxt(rd), "Fee", ttl, f"Order #{no}", "GBP", "--", money(amt), money(amt), "--"))
                rows.append((dtxt(rd), "VAT", "VAT: " + ttl, f"Order #{no}", "GBP", "--", money(r2(amt * VAT)),
                             money(r2(amt * VAT)), "--"))
    fee(date(2026, 6, 30), "Marketing", "Etsy Ads", "Etsy Ads, June 2026", 2.75)
    rows.append((dtxt(date(2026, 6, 30)), "Deposit", "£41.06 sent to your bank account", "", "GBP", "--", "--", "--",
                 "--"))
    return rows


SAMPLE_HEAD = ("Date", "Type", "Title", "Info", "Currency", "Amount", "Fees & Taxes", "Net", "Tax Details")

wb = Workbook()

# ================================================================================================
# Start Here (structure and facts only - the owner writes the how-to paragraphs)
# ================================================================================================
ws = wb.active
ws.title = "Start Here"
title(ws, "UK Etsy Seller Profit Tracker 2026/27",
      f"Rules: Etsy UK fees and HMRC limits as checked {CHECKED}; tax year 6 April 2026 to 5 April 2027. "
      "Not tax or accounting advice - check GOV.UK, Etsy or an accountant.", "C")
widths(ws, {"A": 4, "B": 110, "C": 4})
lines = [
    ("h", "What this is"),
    ("o", OWNER),
    ("p", "- For a UK Etsy seller, VAT-registered or not. Works in Excel and Google Sheets."),
    ("p", "- Tabs: Price Calculator, Etsy Paste, Statement Lines, Other Costs, Monthly P&L, HMRC Checks, "
          "To Sole Trader Tracker, Settings."),
    ("h", "Set up"),
    ("o", OWNER),
    ("p", "- Settings: 'I give Etsy a VAT number' (Yes = Etsy charges no VAT on its fees)."),
    ("p", "- Settings: 'Shop sales $10,000+ in the last 12 months' (Yes = Offsite Ads at 12% instead of 15%)."),
    ("p", "- Settings: fee rates are editable light-blue cells, each with its source and the date it was checked."),
    ("h", "Price Calculator"),
    ("o", OWNER),
    ("p", "- One row per product: price, postage charged, item cost, packaging, postage paid, Offsite Ad sale Yes/No."),
    ("p", "- Grey columns work out each Etsy fee, VAT on fees, net profit, margin and the break-even price."),
    ("h", "Each month: your Etsy statement"),
    ("o", OWNER),
    ("p", "- Etsy: Shop Manager > Finances > Monthly statements > choose the month > Download CSV."),
    ("p", "- Etsy Paste tab: paste the whole file, header row included, with its first cell in A4."),
    ("p", "- Later months go below the last filled row (a repeated header row is ignored)."),
    ("p", "- Columns are found by their header name (Settings rows 30-36), so their order doesn't matter."),
    ("p", "- Statement Lines sorts every row into a category. Rows marked 'Not sorted - check' are left out: add a rule "
          "on Settings (columns K-N)."),
    ("p", "- Other Costs tab: stock, packaging, postage and other costs that are not on the Etsy statement."),
    ("h", "Clearing the examples (amber rows)"),
    ("p", "- Etsy Paste: select A5:O124 and press Delete (a made-up May and June 2026 statement)."),
    ("p", "- Other Costs: select A5:F12 and press Delete. Price Calculator: select A5:H8 and press Delete."),
    ("p", "- HMRC Checks shows how many example rows are still in."),
    ("h", "HMRC Checks"),
    ("o", OWNER),
    ("p", "- Digital platform reporting: Etsy reports a seller to HMRC for a calendar year with 30 or more sales, or "
          "about £1,700 (EUR 2,000) or more. Counted from the statements pasted in."),
    ("p", "- Trading allowance: total trading income for the tax year against £1,000."),
    ("h", "To Sole Trader Tracker"),
    ("o", OWNER),
    ("p", "- Monthly totals per category, using the category names of the UK Sole Trader Tracker 2026/27."),
    ("p", "- Enter gross sales and the fees separately - not the Etsy payouts to your bank as well (that would count "
          "the same money twice)."),
    ("h", "What it does not cover"),
    ("p", "- Etsy payment accounts in a currency other than GBP; currency conversion fees; gift wrap (add it to "
          "postage charged); Etsy Plus and other extras unless they appear on the statement."),
    ("p", "- VAT returns. VAT-registered sellers: the 'VAT I pay HMRC on my own sales' setting is a rough planning "
          "figure only."),
    ("p", "- Income Tax and National Insurance - the UK Sole Trader Tracker 2026/27 estimates those."),
    ("h", "Google Sheets"),
    ("o", OWNER),
    ("p", "- File > Import > Upload, or open the .xlsx from Google Drive and choose File > Save as Google Sheets. "
          "Sheet protection is not carried across."),
    ("h", "Rules used"),
    ("p", f"- Etsy UK fees and HMRC thresholds as checked on {CHECKED} (Settings tab, with sources). Etsy can change "
          "its fees: type a new rate on Settings."),
    ("h", "Small print"),
    ("p", "Not tax or accounting advice - check GOV.UK, Etsy or an accountant. Figures are estimates from what you "
          "enter. You are responsible for your own tax return."),
]
r = 4
for kind, text in lines:
    c = ws.cell(r, 2, text)
    if kind == "h":
        c.font = Font(name=FONT, size=12, bold=True, color=DARK)
        r += 1
    elif kind == "o":
        c.font = Font(name=FONT, size=11, bold=True, color=RED)
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
title(st, "Settings", "Light blue cells are yours to change. Fee rates are editable: Etsy changes them - check "
                      "each one against the source shown.", "S")
widths(st, {"A": 50, "B": 14, "C": 66, "D": 12, "E": 26, "F": 3, "G": 30, "H": 12, "I": 34, "J": 3,
            "K": 5, "L": 13, "M": 18, "N": 30, "O": 3, "P": 8, "Q": 3, "R": 28, "S": 34})
section(st, 4, "Your shop", 5)
rows = [
    (5, "Shop name", "My Etsy Shop", None, ""),
    (6, "Tax year starts", date(2026, 4, 6), DATE, "Leave as 06/04/2026 for the 2026/27 tax year."),
    (7, "Tax year ends", "=EDATE(B6,12)-1", DATE, ""),
    (8, "I give Etsy a VAT number", "No", None,
     "No = Etsy adds 20% VAT to its fees (a real cost). Yes = no VAT charged on fees (VAT-registered sellers)."),
    (9, "Shop sales $10,000+ in the last 12 months", "No", None,
     "Yes = Offsite Ads at 12% (and you can't opt out). No = 15%, and you can opt out in Shop Manager."),
    (10, "VAT I pay HMRC on my own sales (% of VAT-inclusive price)", 0, PCT2,
     "Leave 0% if not VAT-registered. Standard-rated: 16.67% (20/120). Flat Rate Scheme: your flat rate. "
     "Digital items where Etsy collects the VAT: 0%. Planning figure only - ask your accountant."),
    (11, "Other trading income this tax year, outside Etsy (£)", 0, GBP,
     "For the £1,000 trading allowance check on HMRC Checks (e.g. craft fairs, another platform)."),
]
for row, lab, val, fmt, txt in rows:
    st.cell(row, 1, lab).font = Font(name=FONT, bold=True)
    c = st.cell(row, 2, val)
    if isinstance(val, str) and val.startswith("="):
        style_formula(c, fmt)
    else:
        style_input(c, fmt)
    st.cell(row, 3, txt)
    note(st.cell(row, 3))
    st.cell(row, 3).alignment = Alignment(wrap_text=True, vertical="top")
st.row_dimensions[10].height = 38
yes_no(st, "B8")
yes_no(st, "B9")
dv = DataValidation(type="date", operator="between", formula1="DATE(2026,4,6)", formula2="DATE(2026,4,6)",
                    showErrorMessage=True, error="This edition is built for the 2026/27 tax year (starts 06/04/2026).")
st.add_data_validation(dv)
dv.add("B6")
dv = DataValidation(type="decimal", operator="between", formula1="0", formula2="0.5", allow_blank=False)
st.add_data_validation(dv)
dv.add("B10")

section(st, 13, f"Etsy UK fees and HMRC limits - editable, checked {CHECKED} (full links in SOURCES.md)", 5)
for col, lab in enumerate(["Item", "Value", "Source", "Checked", "Status"], 1):
    st.cell(14, col, lab).font = Font(name=FONT, bold=True)
EX = "Search excerpt of Etsy page - check on Etsy"
GOVX = "Search excerpt of GOV.UK - check on GOV.UK"
rates = [
    (15, "Transaction fee (on item price + postage + gift wrap)", 0.065, PCT2,
     "Etsy Fees & Payments Policy (etsy.com/uk/legal/fees)", EX),
    (16, "Payment processing, UK - percentage of order total", 0.04, PCT2,
     "Etsy Help: Payment Processing Fees - table lists United Kingdom 4% + 0.20 GBP", EX),
    (17, "Payment processing, UK - fixed amount per order", 0.20, GBP, "same page", EX),
    (18, "Regulatory operating fee, UK (from 22 June 2026; was 0.32%)", 0.0048, PCT2,
     "Etsy Community announcement 'Regulatory Operating Fee updates for some markets'; Etsy Help article 1500011073202",
     EX),
    (19, "Listing / auto-renew fee per sale, in £", 0.16, GBP,
     "Etsy charges $0.20 (USD) per listing and per auto-renewal after a sale, converted to £ at the day's rate "
     "(about £0.15-£0.16). Type what your statement shows.", EX),
    (20, "Offsite Ads fee (shop under $10,000 a year)", 0.15, PCT2,
     "Etsy Help: How Etsy's Offsite Ads Work - 15%, on the order total", EX),
    (21, "Offsite Ads fee (shop $10,000+ in last 12 months)", 0.12, PCT2, "same page - 12%, can't opt out", EX),
    (22, "Offsite Ads cap per order, in £", 76, GBP,
     "Etsy caps the fee at $100 (USD) per order; £76 at about $1 = £0.76 - adjust to the current rate", EX),
    (23, "VAT on Etsy's fees (UK seller with no VAT number)", 0.20, PCT2,
     "Etsy Help: How VAT Is Collected on Seller Fees; UK standard VAT rate 20%", EX),
    (24, "HMRC platform reporting: sales in a calendar year", 30, '0',
     "GOV.UK: Selling goods or services on a digital platform - not reported if fewer than 30 sales AND under "
     "EUR 2,000", GOVX),
    (25, "HMRC platform reporting: money received in a calendar year (£)", 1700, GBP0,
     "same page - EUR 2,000, 'approximately £1,700'", GOVX),
    (26, "Trading allowance (gross trading income in a tax year)", 1000, GBP0,
     "GOV.UK: Tax-free allowances on property and trading income (checked for product #1)", "Checked for product #1"),
]
for row, lab, val, fmt, src, status in rates:
    st.cell(row, 1, lab).font = Font(name=FONT)
    st.cell(row, 1).alignment = Alignment(vertical="top")
    style_input(st.cell(row, 2, val), fmt)
    st.cell(row, 2).alignment = Alignment(vertical="top")
    st.cell(row, 3, src)
    note(st.cell(row, 3), italic=False)
    st.cell(row, 3).alignment = Alignment(wrap_text=True, vertical="top")
    st.cell(row, 4, CHECKED)
    note(st.cell(row, 4), italic=False)
    st.cell(row, 5, status)
    note(st.cell(row, 5), color=RED if "check" in status else "595959", italic=False)
    st.cell(row, 5).alignment = Alignment(wrap_text=True, vertical="top")
    st.row_dimensions[row].height = 26
st.row_dimensions[19].height = 40

section(st, 28, "Etsy statement CSV - column names (change them if your file's header row is different)", 5)
for col, lab in enumerate(["Field", "Header in your CSV", "Found in column", "", ""], 1):
    st.cell(29, col, lab).font = Font(name=FONT, bold=True)
for i, f in enumerate(CSV_FIELDS):
    rr = CSV_ROW0 + i
    st.cell(rr, 1, f).font = Font(name=FONT)
    style_input(st.cell(rr, 2, f))
    c = st.cell(rr, 3, f"=IFERROR(MATCH(B{rr},'Etsy Paste'!$A$4:$Z$4,0),\"NOT FOUND\")")
    style_formula(c)
    c.alignment = Alignment(horizontal="left")
st.cell(37, 1, "Net is only used for a cross-check (HMRC Checks). Value = Amount + Fees & Taxes.")
note(st.cell(37, 1))
st.cell(38, 1, "Header names come from third-party guides to Etsy's monthly statement, not from Etsy itself - "
               "compare them with your own file.")
note(st.cell(38, 1), color=RED)
st.cell(40, 1, "Not tax or accounting advice - check GOV.UK, Etsy or an accountant.")
note(st.cell(40, 1), color=RED)

# lists
section(st, 3, "Statement categories", 3, col0=7)
for col, lab in zip((7, 8, 9), ("Category", "Group", "Sole Trader Tracker category")):
    st.cell(4, col, lab).font = Font(name=FONT, bold=True)
for i, (cat, grp, p1, _) in enumerate(CATS):
    st.cell(5 + i, 7, cat)
    st.cell(5 + i, 8, grp)
    st.cell(5 + i, 9, p1)
section(st, 3, "Sorting rules - first match wins", 4, col0=11)
for col, lab in zip((11, 12, 13, 14), ("#", "Type is (* = any)", "Title contains", "Category")):
    st.cell(4, col, lab).font = Font(name=FONT, bold=True)
    st.cell(4, col).alignment = Alignment(wrap_text=True)
st.row_dimensions[4].height = 30
for i in range(N_RULES):
    rr = 5 + i
    st.cell(rr, 11, i + 1).font = Font(name=FONT, color="595959")
    for col in (12, 13, 14):
        style_input(st.cell(rr, col))
    if i < len(RULES):
        t, k, cat = RULES[i]
        st.cell(rr, 12, t)
        st.cell(rr, 13, k)
        st.cell(rr, 14, cat)
dv = DataValidation(type="list", formula1=CAT_RANGE, allow_blank=True)
st.add_data_validation(dv)
dv.add(f"N5:N{4 + N_RULES}")
st.cell(6 + N_RULES, 11, "Rules 1-19 are guesses at Etsy's wording - check against your own statement. Type is "
                         "matched in full; Title contains is a part match. Neither cares about capitals.")
note(st.cell(6 + N_RULES, 11))
section(st, 3, "Months", 1, col0=16)
for i, m in enumerate(MONTHS):
    st.cell(5 + i, 16, m)
section(st, 3, "Other cost categories", 2, col0=18)
st.cell(4, 18, "Category").font = Font(name=FONT, bold=True)
st.cell(4, 19, "Sole Trader Tracker category").font = Font(name=FONT, bold=True)
for i, (cat, p1) in enumerate(OC_CATS):
    st.cell(5 + i, 18, cat)
    st.cell(5 + i, 19, p1)
protect(st)

# ================================================================================================
# Price Calculator
# ================================================================================================
pc = wb.create_sheet("Price Calculator")
title(pc, "Price calculator - what you keep from one order",
      "Light blue: type your figures. Grey: worked out. Amber rows are EXAMPLES - clear A5:H8 before you start. "
      "Uses the rates and switches on Settings.", "V")
heads = ["Product", "Price (£)", "Postage charged (£)", "Item cost (£)", "Packaging (£)", "Postage you pay (£)",
         "Offsite Ad sale?", "Example?", "Order total (£)", "Transaction fee 6.5%", "Processing 4% + 20p",
         "Regulatory fee 0.48%", "Listing / renewal", "Offsite Ads", "Etsy fees before VAT", "VAT on fees",
         "Your VAT to HMRC", "Total Etsy cost", "Your costs", "Net profit", "Margin", "Break-even price"]
header(pc, 4, heads, height=46)
widths(pc, {"A": 36, **{get_column_letter(c): 11.5 for c in range(2, 23)}, "H": 9, "T": 12, "V": 12})
pc.freeze_panes = "B5"
for rr in range(CALC_ROWS[0], CALC_ROWS[1] + 1):
    for col in "ABCDEFGH":
        style_input(pc[f"{col}{rr}"], GBP if col in "BCDEF" else None)
    blank = f'$B{rr}=""'
    vat_eff = f'IF({S["vatno"]}="Yes",0,{S["vat"]})'
    off_rate = f'IF({S["big"]}="Yes",{S["oa12"]},{S["oa"]})'
    f = {
        "I": f"=IF({blank},\"\",B{rr}+C{rr})",
        "J": f"=IF({blank},\"\",ROUND(I{rr}*{S['tf']},2))",
        "K": f"=IF({blank},\"\",ROUND(I{rr}*{S['pp']}+{S['pf']},2))",
        "L": f"=IF({blank},\"\",ROUND(I{rr}*{S['rof']},2))",
        "M": f"=IF({blank},\"\",{S['lf']})",
        "N": f"=IF({blank},\"\",IF(G{rr}=\"Yes\",MIN(ROUND(I{rr}*{off_rate},2),{S['cap']}),0))",
        "O": f"=IF({blank},\"\",SUM(J{rr}:N{rr}))",
        "P": f"=IF({blank},\"\",ROUND(O{rr}*{vat_eff},2))",
        "Q": f"=IF({blank},\"\",ROUND(I{rr}*{S['ownvat']},2))",
        "R": f"=IF({blank},\"\",O{rr}+P{rr})",
        "S": f"=IF({blank},\"\",D{rr}+E{rr}+F{rr})",
        "T": f"=IF({blank},\"\",I{rr}-R{rr}-Q{rr}-S{rr})",
        "U": f"=IF({blank},\"\",IF(I{rr}>0,T{rr}/I{rr},0))",
        # price P where profit = 0, ignoring pennies rounding and the Offsite Ads cap:
        # (P+C)(1-k) = F + costs, k = (tf+pp+rof+offsite)(1+vat) + own VAT, F = (pf+listing)(1+vat)
        "V": (f"=IF({blank},\"\",MAX(0,ROUND((({S['pf']}+{S['lf']})*(1+{vat_eff})+S{rr})/"
              f"(1-({S['tf']}+{S['pp']}+{S['rof']}+IF(G{rr}=\"Yes\",{off_rate},0))*(1+{vat_eff})-{S['ownvat']})"
              f"-C{rr},2)))"),
    }
    for col, formula in f.items():
        pc[f"{col}{rr}"] = formula
        style_formula(pc[f"{col}{rr}"], PCT if col == "U" else GBP, bold=col in "TV")
pc.conditional_formatting.add(f"A{CALC_ROWS[0]}:V{CALC_ROWS[1]}",
                              FormulaRule(formula=[f'$H{CALC_ROWS[0]}="EXAMPLE"'], fill=fill(AMBER)))
calc_ex = [
    ("Monthly budget planner (digital)", 12.00, 0, 0, 0, 0, "No"),
    ("Hand-poured soy candle", 25.00, 3.95, 6.00, 0.80, 3.20, "No"),
    ("Linen tote bag (buyer came from an Offsite Ad)", 40.00, 4.95, 12.00, 1.00, 3.50, "Yes"),
    ("Greeting card", 3.50, 1.00, 0.60, 0.15, 0.85, "No"),
]
for i, vals in enumerate(calc_ex):
    rr = 5 + i
    for col, v in zip("ABCDEFG", vals):
        pc[f"{col}{rr}"] = ("EXAMPLE - " + v) if col == "A" else v
    pc[f"H{rr}"] = "EXAMPLE"
dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True)
pc.add_data_validation(dv)
dv.add(f"G{CALC_ROWS[0]}:G{CALC_ROWS[1]}")
pc["A57"] = ("Order total = price + postage charged (add gift wrap to postage). Fees are rounded to the penny per "
             "order. Listing / renewal = the $0.20 auto-renew Etsy charges when an item sells, in £ (Settings).")
pc["A58"] = ("Break-even price = the lowest item price that covers Etsy's fees, VAT on them and your costs, at the same "
             "postage charge (ignores penny rounding and the Offsite Ads cap). Margin = net profit / order total.")
pc["A59"] = ("Etsy's own currency conversion fee, Etsy Ads and any VAT Etsy collects from buyers are not included. "
             "Not tax or accounting advice.")
for rr in (57, 58, 59):
    note(pc[f"A{rr}"])
protect(pc)

# ================================================================================================
# Etsy Paste (unprotected paste area)
# ================================================================================================
ep = wb.create_sheet("Etsy Paste")
title(ep, "Paste your Etsy monthly statement here (header row in row 4)",
      "Click A4 and paste the whole CSV, header row included. Next month: paste below the last filled row. Amber "
      "rows are a made-up EXAMPLE statement - clear A5:O124 first.", "O")
widths(ep, {"A": 18, "B": 11, "C": 44, "D": 30, "E": 9, "F": 11, "G": 12, "H": 11, "I": 12, "J": 10, "K": 10,
            "L": 10, "M": 3, "N": 3, "O": 22})
for i, h in enumerate(SAMPLE_HEAD):
    c = ep.cell(4, 1 + i, h)
    c.font = Font(name=FONT, bold=True)
    c.fill = fill(LIGHT)
    c.border = BOX
ep["O4"] = "Example? (not an Etsy column)"
ep["O4"].font = Font(name=FONT, bold=True, color="595959")
ep["O4"].alignment = Alignment(wrap_text=True)
ep.row_dimensions[4].height = 30
for i, row in enumerate(sample_rows()):
    rr = 5 + i
    for j, v in enumerate(row):
        ep.cell(rr, 1 + j, v).font = Font(name=FONT)
    ep.cell(rr, 15, "EXAMPLE")
N_SAMPLE = len(sample_rows())
assert N_SAMPLE <= 120, N_SAMPLE
ep.freeze_panes = "A5"
ep.conditional_formatting.add(f"A{PASTE_ROWS[0]}:O{PASTE_ROWS[1]}",
                              FormulaRule(formula=[f'$O{PASTE_ROWS[0]}="EXAMPLE"'], fill=fill(AMBER)))
# no protection: the whole sheet is a paste area

# ================================================================================================
# Statement Lines (one line per pasted row, worked out)
# ================================================================================================
sl = wb.create_sheet("Statement Lines")
title(sl, "Statement lines - each pasted row, read and sorted",
      "Fills itself in from Etsy Paste (same row numbers). Columns are found by header name (Settings rows 30-36). "
      "'Not sorted - check' rows are left out of the totals.", "P")
header(sl, 4, ["Date (as in file)", "Type", "Title", "Info", "Amount (as in file)", "Fees & Taxes (as in file)",
               "Net (as in file)", "Date", "Amount £", "Fees & taxes £", "Value £", "Net £ (check)", "Category",
               "Group", "Sole Trader Tracker category", "Example?"], height=46)
widths(sl, {"A": 17, "B": 10, "C": 38, "D": 22, "E": 11, "F": 11, "G": 11, "H": 11, "I": 11, "J": 11, "K": 11,
            "L": 11, "M": 26, "N": 11, "O": 30, "P": 10})
sl.freeze_panes = "A5"


def raw(field, rr):
    x = f"INDEX('Etsy Paste'!$A{rr}:$Z{rr},1,{COLIDX[field]})"
    return f'=IFERROR(IF({x}="","",{x}),"")'


def num(ref):
    return (f'IF({ref}="",0,IF(ISNUMBER({ref}),{ref},IFERROR(VALUE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE('
            f'TRIM({ref}),"£",""),",",""),"$","")),0)))')


def parse_date(a):
    t = f"TRIM({a})"
    sp = f'FIND(" ",{t})'
    month_first = (f'DATE(VALUE(RIGHT({t},4)),MATCH(LEFT({t},3),{MON_RANGE},0),'
                   f'VALUE(SUBSTITUTE(MID({t},{sp}+1,2),",","")))')
    day_first = f'DATE(VALUE(RIGHT({t},4)),MATCH(MID({t},{sp}+1,3),{MON_RANGE},0),VALUE(LEFT({t},{sp}-1)))'
    iso = f'DATE(VALUE(LEFT({t},4)),VALUE(MID({t},6,2)),VALUE(MID({t},9,2)))'
    return (f'=IF({a}="","",IF(ISNUMBER({a}),{a},IFERROR({month_first},IFERROR({day_first},'
            f'IFERROR(IF(MID({t},5,1)="-",{iso},NA()),IFERROR(DATEVALUE({t}),"check"))))))')


for rr in range(PASTE_ROWS[0], PASTE_ROWS[1] + 1):
    for col, field in zip("ABCDEFG", CSV_FIELDS):
        sl[f"{col}{rr}"] = raw(field, rr)
    sl[f"H{rr}"] = parse_date(f"A{rr}")
    sl[f"I{rr}"] = "=" + num(f"E{rr}")
    sl[f"J{rr}"] = "=" + num(f"F{rr}")
    sl[f"K{rr}"] = f"=I{rr}+J{rr}"
    sl[f"L{rr}"] = "=" + num(f"G{rr}")
    cond = (f"({R_CAT}<>\"\")*((({R_TYPE}=\"*\")+({R_TYPE}=$B{rr}))>0)"
            f"*((({R_KW}=\"\")+ISNUMBER(SEARCH({R_KW},$C{rr})))>0)")
    score = f"SUMPRODUCT(MAX({cond}*({N_RULES + 1}-{R_NUM})))"
    sl[f"M{rr}"] = (f'=IF(AND($B{rr}="",$C{rr}="",K{rr}=0),"",IF({score}=0,"{UNSORTED}",'
                    f'INDEX({R_CAT},{N_RULES + 1}-{score})))')
    sl[f"N{rr}"] = f'=IF(M{rr}="","",IFERROR(INDEX({GRP_RANGE},MATCH(M{rr},{CAT_RANGE},0)),"Check"))'
    sl[f"O{rr}"] = f'=IF(M{rr}="","",IFERROR(INDEX({P1C_RANGE},MATCH(M{rr},{CAT_RANGE},0)),"-"))'
    sl[f"P{rr}"] = f"=IF('Etsy Paste'!$O{rr}=\"EXAMPLE\",\"EXAMPLE\",\"\")"
    for col in "ABCDEFGHIJKLMNOP":
        style_formula(sl[f"{col}{rr}"], DATE if col == "H" else (GBP if col in "IJKL" else None))
sl.conditional_formatting.add(f"A{PASTE_ROWS[0]}:P{PASTE_ROWS[1]}",
                              FormulaRule(formula=[f'$P{PASTE_ROWS[0]}="EXAMPLE"'], fill=fill(AMBER)))
sl.conditional_formatting.add(f"M{PASTE_ROWS[0]}:M{PASTE_ROWS[1]}",
                              FormulaRule(formula=[f'$M{PASTE_ROWS[0]}="{UNSORTED}"'], font=Font(color=RED, bold=True)))
protect(sl)

# ================================================================================================
# Other Costs
# ================================================================================================
oc = wb.create_sheet("Other Costs")
title(oc, "Other costs", "Costs that are not on your Etsy statement: stock, packaging, postage you paid elsewhere, "
                         "software. Amber rows are EXAMPLES - clear A5:F12 before you start.", "G")
header(oc, 4, ["Date", "Supplier", "Description", "Amount (£)", "Category", "Example?", "Sole Trader Tracker category"])
widths(oc, {"A": 13, "B": 24, "C": 40, "D": 14, "E": 30, "F": 11, "G": 34})
oc.freeze_panes = "A5"
for rr in range(OC_ROWS[0], OC_ROWS[1] + 1):
    for col in "ABCDEF":
        style_input(oc[f"{col}{rr}"], DATE if col == "A" else (GBP if col == "D" else None))
    oc[f"G{rr}"] = f'=IF(E{rr}="","",IFERROR(INDEX({OC_P1},MATCH(E{rr},{OC_LIST},0)),"check"))'
    style_formula(oc[f"G{rr}"])
oc.conditional_formatting.add(f"A{OC_ROWS[0]}:G{OC_ROWS[1]}",
                              FormulaRule(formula=[f'$F{OC_ROWS[0]}="EXAMPLE"'], fill=fill(AMBER)))
oc_ex = [
    (date(2026, 4, 20), "Wax & Wick Supplies", "Soy wax, wicks, fragrance oil", 18.60, "Stock and materials"),
    (date(2026, 5, 2), "Bags of Linen Ltd", "4 linen tote blanks", 22.00, "Stock and materials"),
    (date(2026, 5, 6), "Packaging Direct", "Boxes, tissue, mailers", 8.40, "Packaging"),
    (date(2026, 5, 22), "Post Office", "Postage for a craft-fair order", 2.70, "Postage paid (outside Etsy)"),
    (date(2026, 6, 1), "Canva", "Canva Pro - June", 10.99, "Software and subscriptions"),
    (date(2026, 6, 8), "Meta", "Instagram ads - June", 5.00, "Advertising outside Etsy"),
    (date(2026, 6, 14), "Craft Fair Committee", "Stall fee", 12.00, "Other allowable costs"),
    (date(2026, 6, 19), "Cafe Nero", "Coffee (not allowable)", 3.40, "Not allowable (personal)"),
]
for i, (d, su, de, am, ca) in enumerate(oc_ex):
    rr = 5 + i
    for col, v in zip("ABCDEF", (d, su, "EXAMPLE - " + de, am, ca, "EXAMPLE")):
        oc[f"{col}{rr}"] = v
dv = DataValidation(type="list", formula1=OC_LIST, allow_blank=True)
oc.add_data_validation(dv)
dv.add(f"E{OC_ROWS[0]}:E{OC_ROWS[1]}")
protect(oc)

# ================================================================================================
# Monthly P&L
# ================================================================================================
mo = wb.create_sheet("Monthly P&L")
title(mo, "Monthly profit and loss", "Tax months run from the 6th to the 5th, so the 12 rows add up to the tax year. "
                                     "Etsy figures come from Statement Lines; other costs from Other Costs.", "X")
ETSY_COST_COLS = [C_TRANS, C_PROC, C_ROF, C_LIST, C_OFF, C_ADS, C_OTHERFEE, C_VAT, C_LABEL]
OC_COLS = [c for c, _ in OC_CATS if c != "Not allowable (personal)"]
heads = (["Month from", "Month to", "Sales", "Refunds", "Net sales"] + ETSY_COST_COLS + ["Total Etsy charges"]
         + OC_COLS + ["Total other costs", "Net profit", "Profit so far this year"])
header(mo, 4, heads, height=48)
assert len(heads) == 24
widths(mo, {"A": 11, "B": 11, **{get_column_letter(c): 12 for c in range(3, 25)}})
mo.freeze_panes = "C5"


def sl_sum(cat, a, b, sign=""):
    return f"{sign}SUMIFS({SL_VAL},{SL_DATE},\">=\"&{a},{SL_DATE},\"<=\"&{b},{SL_CAT},\"{cat}\")"


for n in range(12):
    rr = 5 + n
    a, b = f"$A{rr}", f"$B{rr}"
    mo[f"A{rr}"] = f"=EDATE({S['start']},{n})"
    mo[f"B{rr}"] = f"=EDATE({S['start']},{n + 1})-1"
    style_formula(mo[f"A{rr}"], 'd mmm yy')
    style_formula(mo[f"B{rr}"], 'd mmm yy')
    mo[f"C{rr}"] = "=" + sl_sum(SALES, a, b)
    mo[f"D{rr}"] = "=" + sl_sum(REFUNDS, a, b)
    mo[f"E{rr}"] = f"=C{rr}+D{rr}"
    for k, cat in enumerate(ETSY_COST_COLS):
        mo[f"{get_column_letter(6 + k)}{rr}"] = "=" + sl_sum(cat, a, b, "-")
    mo[f"O{rr}"] = f"=SUM(F{rr}:N{rr})"
    for k, cat in enumerate(OC_COLS):
        mo[f"{get_column_letter(16 + k)}{rr}"] = (f"=SUMIFS({OC_AMT},{OC_DATE},\">=\"&{a},{OC_DATE},\"<=\"&{b},"
                                                  f"{OC_CAT},\"{cat}\")")
    mo[f"V{rr}"] = f"=SUM(P{rr}:U{rr})"
    mo[f"W{rr}"] = f"=E{rr}-O{rr}-V{rr}"
    mo[f"X{rr}"] = f"=SUM($W$5:W{rr})"
    for c in range(3, 25):
        L = get_column_letter(c)
        style_formula(mo[f"{L}{rr}"], GBP, bold=L in "EOVW")
mo["A17"] = "Year total"
for col in range(1, 25):
    mo.cell(17, col).fill = fill(DARK)
    mo.cell(17, col).font = Font(name=FONT, bold=True, color=WHITE)
for col in range(3, 24):
    L = get_column_letter(col)
    mo[f"{L}17"] = f"=SUM({L}5:{L}16)"
    mo[f"{L}17"].number_format = GBP_TOT
mo["A19"] = ("Costs are shown as positive numbers; a fee credit (e.g. on a refund) reduces them. Etsy payouts to "
             "your bank are ignored - they are your own money moving, not income.")
mo["A20"] = "'Not allowable (personal)' costs are left out. Not tax or accounting advice."
for rr in (19, 20):
    note(mo[f"A{rr}"])
protect(mo)

# ================================================================================================
# HMRC Checks
# ================================================================================================
hc = wb.create_sheet("HMRC Checks")
title(hc, "HMRC checks", "Platform reporting (calendar year) and the £1,000 trading allowance (tax year), from the "
                         "statements pasted in. Not tax or accounting advice.", "E")
widths(hc, {"A": 3, "B": 52, "C": 16, "D": 18, "E": 78})
section(hc, 4, "1. Will Etsy report me to HMRC? (digital platform reporting, calendar year)", 4, col0=2)
header(hc, 5, ["Calendar year", "Sales (orders)", "Money from sales (£)", "Status"], col0=2)
for i in range(2):
    rr = 6 + i
    hc[f"B{rr}"] = f"=YEAR({S['start']})+{i}"
    style_formula(hc[f"B{rr}"], '0', bold=True)
    hc[f"B{rr}"].alignment = Alignment(horizontal="left")
    y0, y1 = f"DATE(B{rr},1,1)", f"DATE(B{rr},12,31)"
    hc[f"C{rr}"] = (f"=COUNTIFS({SL_CAT},\"{SALES}\",{SL_DATE},\">=\"&{y0},{SL_DATE},\"<=\"&{y1},{SL_VAL},\">0\")")
    hc[f"D{rr}"] = (f"=SUMIFS({SL_VAL},{SL_CAT},\"{SALES}\",{SL_DATE},\">=\"&{y0},{SL_DATE},\"<=\"&{y1})"
                    f"+SUMIFS({SL_VAL},{SL_CAT},\"{REFUNDS}\",{SL_DATE},\">=\"&{y0},{SL_DATE},\"<=\"&{y1})")
    hc[f"E{rr}"] = (f'=IF(OR(C{rr}>={S["n30"]},D{rr}>={S["m1700"]}),"Over a limit: expect Etsy to report your "&B{rr}'
                    f'&" sales to HMRC (by 31 January "&(B{rr}+1)&")","Under both limits so far: "&C{rr}&" of "&'
                    f'{S["n30"]}&" sales, £"&TEXT(D{rr},"#,##0")&" of £"&TEXT({S["m1700"]},"#,##0"))')
    style_formula(hc[f"C{rr}"], '0')
    style_formula(hc[f"D{rr}"], GBP)
    style_formula(hc[f"E{rr}"], bold=True)
hc["B8"] = ("Etsy is not expected to report you if you make fewer than 30 sales AND receive less than about £1,700 "
            "(EUR 2,000) in the calendar year (GOV.UK). Being reported does not by itself mean you owe tax; being "
            "under the limits does not mean you don't.")
hc["B9"] = ("Counts only the statements pasted in. Sales = 'Sale' rows (one per order); money = sales less refunds. "
            "HMRC's exact measure may differ slightly (check GOV.UK).")
for rr in (8, 9):
    hc.merge_cells(f"B{rr}:E{rr}")
    note(hc[f"B{rr}"])
    hc[f"B{rr}"].alignment = Alignment(wrap_text=True, vertical="top")
    hc.row_dimensions[rr].height = 30

section(hc, 11, "2. The £1,000 trading allowance (tax year 6 April 2026 to 5 April 2027)", 4, col0=2)


def hrow(rr, label, formula, fmt=GBP, txt="", bold=False):
    hc[f"B{rr}"] = label
    hc[f"B{rr}"].font = Font(name=FONT, bold=bold)
    hc[f"C{rr}"] = formula
    style_formula(hc[f"C{rr}"], fmt, bold=bold)
    if txt:
        hc[f"D{rr}"] = txt
        note(hc[f"D{rr}"], italic=False)


hrow(12, "Etsy net sales this tax year", "='Monthly P&L'!$E$17", txt="Sales less refunds (Monthly P&L)")
hrow(13, "Other trading income this tax year", f"={S['other']}", txt="From Settings")
hrow(14, "Total trading income (before any costs)", "=C12+C13", bold=True)
hrow(15, "Status", f'=IF(C14<={S["ta"]},"£1,000 or less: covered by the trading allowance - you may not need to '
                   f'tell HMRC (check GOV.UK)","Over £1,000: you need to register for Self Assessment and report it")',
     fmt=None, bold=True)
hc.merge_cells("C15:E15")
hrow(16, "Profit using your actual costs", "='Monthly P&L'!$W$17+C13",
     txt="Monthly P&L net profit + other trading income (its costs aren't in this file)")
hrow(17, "Profit using the £1,000 allowance instead", f"=MAX(C14-{S['ta']},0)",
     txt="The allowance replaces all costs and can't make a loss")
hrow(18, "Lower taxable profit", '=IF(C17<C16,"Trading allowance","Actual costs")', fmt=None, bold=True)

section(hc, 20, "3. Data checks (should all be 0 / OK)", 4, col0=2)
EX_TOTAL = (f"COUNTIF({SL_EX},\"EXAMPLE\")+COUNTIF({OC_EX},\"EXAMPLE\")"
            f"+COUNTIF('Price Calculator'!$H${CALC_ROWS[0]}:$H${CALC_ROWS[1]},\"EXAMPLE\")")
hrow(21, "EXAMPLE rows still in (Etsy Paste, Other Costs, Price Calculator)", "=" + EX_TOTAL, fmt='0',
     txt="Clear the amber rows before you start (see Start Here)")
hrow(22, "Statement rows not sorted (left out of totals)", f"=COUNTIF({SL_CAT},\"{UNSORTED}\")", fmt='0',
     txt="Add a rule on Settings (columns K-N), then they are counted")
hrow(23, "Statement rows with a date that couldn't be read", f"=COUNTIFS({SL_DATE},\"check\",{SL_GRP},\"<>Ignore\")",
     fmt='0', txt="Type the date in as dd/mm/yyyy on Etsy Paste")
hrow(24, "Statement rows dated outside this tax year (not in Monthly P&L)",
     f"=COUNTIFS({SL_DATE},\"<\"&{S['start']},{SL_GRP},\"<>Ignore\")"
     f"+COUNTIFS({SL_DATE},\">\"&{S['end']},{SL_GRP},\"<>Ignore\")", fmt='0',
     txt="Still counted in the calendar-year reporting check above")
hrow(25, "CSV columns not found (Settings rows 30-36)",
     f"=COUNTIF(Settings!$C${CSV_ROW0}:$C${CSV_ROW0 + 6},\"NOT FOUND\")", fmt='0',
     txt="Type your file's header names on Settings")
hrow(26, "Net column vs Amount + Fees & Taxes (difference)", f"=ROUND(SUM({SL_NET})-SUM({SL_VAL}),2)",
     txt="0 means every row's Net = Amount + Fees & Taxes")
hrow(27, "Other Costs with no category or no date", f"=SUMPRODUCT(({OC_AMT}<>\"\")*(({OC_CAT}=\"\")+({OC_DATE}=\"\")>0))",
     fmt='0', txt="They are left out until filled in")
protect(hc)

# ================================================================================================
# To Sole Trader Tracker (product #1)
# ================================================================================================
tp = wb.create_sheet("To Sole Trader Tracker")
title(tp, "Totals ready for the UK Sole Trader Tracker 2026/27",
      "Each column uses that tracker's category names. Enter turnover on its Income tab and each cost on its Expenses "
      "tab (e.g. one line per month, dated the month's last day).", "J")
header(tp, 4, ["Month from", "Month to", "Income: " + P1_TURN] + ["Expenses: " + c for c in P1_EXP]
       + ["Total expenses", "Profit check vs Monthly P&L"], height=48)
widths(tp, {"A": 11, "B": 11, "C": 18, "D": 17, "E": 17, "F": 17, "G": 17, "H": 17, "I": 15, "J": 18})
tp.freeze_panes = "C5"
for n in range(12):
    rr = 5 + n
    tp[f"A{rr}"] = f"='Monthly P&L'!A{rr}"
    tp[f"B{rr}"] = f"='Monthly P&L'!B{rr}"
    style_formula(tp[f"A{rr}"], 'd mmm yy')
    style_formula(tp[f"B{rr}"], 'd mmm yy')
    a, b = f"$A{rr}", f"$B{rr}"
    tp[f"C{rr}"] = f"=SUMIFS({SL_VAL},{SL_DATE},\">=\"&{a},{SL_DATE},\"<=\"&{b},{SL_P1},\"{P1_TURN}\")"
    for k, cat in enumerate(P1_EXP):
        L = get_column_letter(4 + k)
        tp[f"{L}{rr}"] = (f"=-SUMIFS({SL_VAL},{SL_DATE},\">=\"&{a},{SL_DATE},\"<=\"&{b},{SL_P1},\"{cat}\")"
                          f"+SUMIFS({OC_AMT},{OC_DATE},\">=\"&{a},{OC_DATE},\"<=\"&{b},{OC_P1C},\"{cat}\")")
    tp[f"I{rr}"] = f"=SUM(D{rr}:H{rr})"
    tp[f"J{rr}"] = f"=IF(ROUND(C{rr}-I{rr}-'Monthly P&L'!W{rr},2)=0,\"OK\",\"Differs - check\")"
    for c in range(3, 11):
        L = get_column_letter(c)
        style_formula(tp[f"{L}{rr}"], GBP if c < 10 else None, bold=L in "CI")
tp["A17"] = "Year total"
for col in range(1, 11):
    tp.cell(17, col).fill = fill(DARK)
    tp.cell(17, col).font = Font(name=FONT, bold=True, color=WHITE)
for col in range(3, 10):
    L = get_column_letter(col)
    tp[f"{L}17"] = f"=SUM({L}5:{L}16)"
    tp[f"{L}17"].number_format = GBP_TOT
tp["J17"] = "=IF(ROUND(C17-I17-'Monthly P&L'!W17,2)=0,\"OK\",\"Differs - check\")"

section(tp, 19, "Which Tracker category each line goes to, and why", 10)
header(tp, 20, ["Line in this file", "", "Sole Trader Tracker category", "", "", "Why"], height=20)
tp.merge_cells("A20:B20")
tp.merge_cells("C20:E20")
tp.merge_cells("F20:J20")
mapping = [(c, p1, why) for c, g, p1, why in CATS if g != "Ignore"] + [
    ("Other Costs: " + c, p1, "") for c, p1 in OC_CATS]
mapping[-1] = (mapping[-1][0], mapping[-1][1], "Not allowable - the Tracker records it but leaves it out.")
for i, (line, p1, why) in enumerate(mapping):
    rr = 21 + i
    tp[f"A{rr}"] = line
    tp[f"C{rr}"] = p1
    tp[f"F{rr}"] = why
    for col in "ACF":
        tp[f"{col}{rr}"].font = Font(name=FONT, size=10)
        tp[f"{col}{rr}"].alignment = Alignment(wrap_text=True, vertical="top")
    tp.merge_cells(f"A{rr}:B{rr}")
    tp.merge_cells(f"C{rr}:E{rr}")
    tp.merge_cells(f"F{rr}:J{rr}")
    tp.row_dimensions[rr].height = 28 if len(why) > 70 else 16
end = 21 + len(mapping)
tp[f"A{end + 1}"] = ("On the short self-employment pages (SA103S) advertising and other allowable expenses share box 19, "
                     "so the choice between them doesn't change the return. Profit is the same whichever category a "
                     "cost is in. Not tax or accounting advice.")
note(tp[f"A{end + 1}"])
tp[f"A{end + 2}"] = ("Etsy payouts to your bank: don't enter them as income as well as these totals - that would count "
                     "the same sales twice.")
note(tp[f"A{end + 2}"], color=RED)
protect(tp)

# tab colours (product #1 scheme: dark = start, grey = settings, mid = inputs, orange = summaries, red = checks)
colours = {"Start Here": DARK, "Settings": "7F7F7F", "Price Calculator": MID, "Etsy Paste": MID,
           "Statement Lines": "7F7F7F", "Other Costs": MID, "Monthly P&L": "C55A11", "HMRC Checks": RED,
           "To Sole Trader Tracker": "C55A11"}
for w in wb.worksheets:
    w.sheet_properties.tabColor = colours[w.title]
    w.sheet_view.zoomScale = 100
    w.page_setup.orientation = "landscape"
    w.page_setup.paperSize = w.PAPERSIZE_A4
    w.sheet_properties.pageSetUpPr.fitToPage = True
    w.page_setup.fitToWidth = 1
    w.page_setup.fitToHeight = 0
    w.print_title_rows = "4:4" if w.title in ("Etsy Paste", "Statement Lines", "Other Costs", "Price Calculator") \
        else None
wb.active = 0
wb.properties.title = "UK Etsy Seller Profit Tracker 2026/27"
wb.properties.creator = "BoxByBoxSheets"

if __name__ == "__main__":
    wb.save(OUT)
    print("saved", OUT, "- sample statement rows:", N_SAMPLE)
