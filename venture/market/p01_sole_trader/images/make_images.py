"""Etsy listing images for product 1, from real renders of the workbook.

Renders a copy of the workbook with LibreOffice (example amounts x10 so the tax tabs show a typical year -
the images say "shown with sample figures"), crops each tab, then lays out 5 images at 2000x1500 with Playwright.
Run: python venture/market/p01_sole_trader/images/make_images.py
"""
import base64, glob, os, shutil, subprocess, sys, tempfile
import openpyxl
from openpyxl.utils import get_column_letter as L
from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "UK_Sole_Trader_Tracker_2026-27.xlsx")
TABS = ['Start Here', 'Settings', 'Income', 'Expenses', 'Mileage', 'Monthly', 'Quarterly', 'Tax Estimate', 'SA103 Box Map']
ROWS = {'Income': 18, 'Expenses': 18, 'Mileage': 12, 'Start Here': 30}

def render(tmp):
    wb = openpyxl.load_workbook(SRC)
    for name in ('Income', 'Expenses'):
        ws = wb[name]
        for r in range(5, 15):
            c = ws.cell(r, 4)
            if isinstance(c.value, (int, float)):
                c.value = round(c.value * 10, 2)
    for ws in wb:
        ws.page_setup.orientation = 'landscape'
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 1
        ws.page_margins.left = ws.page_margins.right = ws.page_margins.top = ws.page_margins.bottom = 0.2
        ws.oddHeader.center.text = ''; ws.oddFooter.center.text = ''
        ws.print_area = f"A1:{L(ws.max_column)}{ROWS.get(ws.title, ws.max_row)}"
    x = os.path.join(tmp, 'demo.xlsx'); wb.save(x)
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', tmp, x], check=True, capture_output=True)
    subprocess.run(['pdftoppm', '-r', '200', '-png', os.path.join(tmp, 'demo.pdf'), os.path.join(tmp, 'pg')], check=True)
    out = {}
    for i, f in enumerate(sorted(glob.glob(os.path.join(tmp, 'pg-*.png')))):
        im = Image.open(f).convert('RGB')
        im = im.crop(ImageChops.difference(im, Image.new('RGB', im.size, 'white')).getbbox())
        p = os.path.join(tmp, f'tab{i}.png'); im.save(p); out[TABS[i]] = p
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

def page(eyebrow, title, body, h=None):
    return f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="top"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1></div>
<div class="stage">{body}</div>
<div class="foot"><span>UK Sole Trader Tracker 2026/27 · Excel &amp; Google Sheets · Instant download</span>
<span class="badge">Shown with sample figures · Not tax advice</span></div></body></html>"""

def shot(p, maxh):
    return f'<div class="shot"><img src="{uri(p)}" style="max-height:{maxh}px"></div>'

def main():
    tmp = tempfile.mkdtemp()
    t = render(tmp)
    def crop_top(name, frac):
        im = Image.open(t[name]); c = im.crop((0, 0, im.width, int(im.height * frac)))
        p = t[name] + f'.{frac}.png'; c.save(p); return p
    im = Image.open(t['Settings']); sp = t['Settings'] + '.left.png'
    im.crop((0, int(im.height * 0.48), int(im.width * 0.52), im.height)).save(sp); t['Settings (rates, with sources)'] = sp
    pages = [
        ("01_tax_estimate", page("2026/27 · England, Wales &amp; NI", "Your tax bill, worked out as you go",
                                  shot(crop_top('Tax Estimate', 0.64), 1010))),
        ("02_expenses", page("Expenses", "Categories match HMRC's expense boxes", shot(t['Expenses'], 1010))),
        ("03_quarterly", page("Making Tax Digital", "Quarterly and year-to-date totals, ready to copy",
                              shot(t['Quarterly'], 1010))),
        ("04_box_map", page("Self Assessment", "Know which box each number goes in", shot(t['SA103 Box Map'], 1010))),
        ("05_tabs", page("9 tabs in one file", "Income, expenses, mileage, monthly and more",
                         '<div class="grid">' + ''.join(
                             f'<div class="cell"><b>{n}</b><img src="{uri(t[n])}"></div>'
                             for n in ('Income', 'Mileage', 'Monthly', 'Settings (rates, with sources)')) + '</div>')),
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
    import json
    subprocess.run(['node', js, json.dumps(jobs)], check=True)
    shutil.rmtree(tmp)

if __name__ == '__main__':
    main()
