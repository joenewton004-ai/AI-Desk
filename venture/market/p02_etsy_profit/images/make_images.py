"""Etsy listing images for product 2, from real renders of the workbook (adapted from p01's make_images.py).

Renders the built workbook as it ships (its amber EXAMPLE rows = the sample figures the images say they show) with
LibreOffice, crops each tab, then lays out 5 images at 2000x1500 with Playwright (Node).
Run: python venture/market/p02_etsy_profit/images/make_images.py   (run build.py first)
"""
import base64, glob, json, os, shutil, subprocess, tempfile
import openpyxl
from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "UK_Etsy_Seller_Profit_Tracker_2026-27.xlsx")
AREAS = {  # print area per tab (the tab order in the file decides the PDF page order)
    'Start Here': 'A1:C40', 'Settings': 'A1:E40', 'Price Calculator': 'A1:V9', 'Etsy Paste': 'A1:I32',
    'Statement Lines': 'A1:O32', 'Other Costs': 'A1:G13', 'Monthly P&L': 'A1:X17', 'HMRC Checks': 'A1:E27',
    'To Sole Trader Tracker': 'A1:J17',
}
# columns hidden in the demo copy only (the file itself is unchanged), per render pass
HIDE = [
    {'Price Calculator': 'HJKLMNOPQRSTUV', 'Statement Lines': 'DEFGIJLNP', 'Monthly P&L': 'PQRSTUX'},
    {'Price Calculator': 'BCDEFGHIQ'},
]


def render(tmp, hide):
    tmp = os.path.join(tmp, str(len(os.listdir(tmp))))
    os.makedirs(tmp)
    wb = openpyxl.load_workbook(SRC)
    for name, cols in hide.items():
        for c in cols:
            wb[name].column_dimensions[c].hidden = True
    for ws in wb:
        ws.page_setup.orientation = 'landscape'
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 1
        ws.page_margins.left = ws.page_margins.right = ws.page_margins.top = ws.page_margins.bottom = 0.2
        ws.oddHeader.center.text = ''; ws.oddFooter.center.text = ''
        ws.print_title_rows = None
        ws.print_area = AREAS[ws.title]
    x = os.path.join(tmp, 'demo.xlsx'); wb.save(x)
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', tmp, x], check=True, capture_output=True)
    subprocess.run(['pdftoppm', '-r', '200', '-png', os.path.join(tmp, 'demo.pdf'), os.path.join(tmp, 'pg')], check=True)
    out = {}
    pages = sorted(glob.glob(os.path.join(tmp, 'pg-*.png')))
    assert len(pages) == len(wb.sheetnames), (len(pages), wb.sheetnames)
    for name, f in zip(wb.sheetnames, pages):
        im = Image.open(f).convert('RGB')
        im = im.crop(ImageChops.difference(im, Image.new('RGB', im.size, 'white')).getbbox())
        p = os.path.join(tmp, f'{len(out)}.png'); im.save(p); out[name] = p
    return out


def uri(p):
    return 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode()


CSS = """
*{box-sizing:border-box;margin:0}
body{width:2000px;height:1500px;background:#eef3f4;font-family:'Lato','Carlito','DejaVu Sans',sans-serif;color:#17363f;
  display:grid;grid-template-rows:auto 1fr auto;overflow:hidden}
.top{background:#1f4e5c;color:#fff;padding:56px 80px 48px}
.eyebrow{font-size:30px;letter-spacing:.14em;text-transform:uppercase;color:#9fd3dc}
h1{font-size:84px;line-height:1.05;margin-top:14px;font-weight:800}
.stage{padding:56px 80px 0;display:flex;align-items:flex-start;justify-content:center;overflow:hidden}
.shot{background:#fff;padding:18px;box-shadow:0 18px 50px rgba(23,54,63,.18);border-radius:10px;max-width:100%}
.shot img{display:block;max-width:100%;max-height:100%}
.foot{display:flex;justify-content:space-between;padding:30px 80px 40px;font-size:28px;color:#4d6970}
.badge{background:#ffe9b0;color:#5a4300;padding:6px 16px;border-radius:999px;font-weight:700}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:36px;width:100%}
.cell{background:#fff;padding:14px;border-radius:10px;box-shadow:0 12px 30px rgba(23,54,63,.14);overflow:hidden;height:470px}
.cell b{display:block;font-size:30px;margin:4px 6px 12px}
.cell img{width:100%;object-fit:cover;object-position:top left;height:390px}
"""


def page(eyebrow, title, body):
    return f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="top"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1></div>
<div class="stage">{body}</div>
<div class="foot"><span>UK Etsy Seller Profit Tracker 2026/27 · Excel &amp; Google Sheets · Instant download</span>
<span class="badge">Shown with sample figures · Not tax advice</span></div></body></html>"""


def shot(p, maxh):
    return f'<div class="shot"><img src="{uri(p)}" style="max-height:{maxh}px"></div>'


def main():
    tmp = tempfile.mkdtemp()
    t = render(tmp, HIDE[0])
    t['Price Calculator (fees)'] = render(tmp, HIDE[1])['Price Calculator']
    im = Image.open(t['Settings']); sp = t['Settings'] + '.rates.png'
    im.crop((0, int(im.height * 0.30), im.width, int(im.height * 0.68))).save(sp)
    t['Settings (fee rates, with sources)'] = sp
    pages = [
        ("01_price_calculator", page("UK fees · VAT on fees · Offsite Ads", "What you really keep from each sale",
                                     '<div style="display:flex;flex-direction:column;gap:36px;align-items:center">'
                                     + shot(t['Price Calculator'], 480) + shot(t['Price Calculator (fees)'], 480)
                                     + '</div>')),
        ("02_statement_import", page("Etsy monthly statement CSV", "Paste it in - every fee sorted for you",
                                     shot(t['Statement Lines'], 1010))),
        ("03_monthly_pl", page("Tax months 6th to 5th", "Monthly profit after every Etsy fee",
                               shot(t['Monthly P&L'], 1010))),
        ("04_hmrc_checks", page("HMRC", "Platform reporting limits and the £1,000 allowance",
                                shot(t['HMRC Checks'], 1010))),
        ("05_tabs", page("9 tabs in one file", "Settings, costs, and totals for your tax records",
                         '<div class="grid">' + ''.join(
                             f'<div class="cell"><b>{n}</b><img src="{uri(t[n])}"></div>'
                             for n in ('Settings (fee rates, with sources)', 'To Sole Trader Tracker', 'Etsy Paste',
                                       'Other Costs')) + '</div>')),
    ]
    jobs = []
    for name, html in pages:
        h = os.path.join(tmp, name + '.html'); open(h, 'w').write(html)
        jobs.append([h, os.path.join(HERE, name + '.png')])
    js = os.path.join(tmp, 'shot.js')
    open(js, 'w').write("""const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:2000,height:1500}});
for(const [h,o] of JSON.parse(process.argv[2])){await p.goto('file://'+h);await p.screenshot({path:o});console.log('wrote',o)}
await b.close()})();""")
    subprocess.run(['node', js, json.dumps(jobs)], check=True)
    shutil.rmtree(tmp)


if __name__ == '__main__':
    main()
