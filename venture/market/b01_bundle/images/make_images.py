"""Etsy images for the bundle (BBS-B01-2627): product 1 + product 2. Real renders via each product's own
make_images.render(). Run: python venture/market/b01_bundle/images/make_images.py"""
import importlib.util, json, os, shutil, subprocess, tempfile
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
MARKET = os.path.join(HERE, '..', '..')

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m

p1 = load('p1img', os.path.join(MARKET, 'p01_sole_trader', 'images', 'make_images.py'))
p2 = load('p2img', os.path.join(MARKET, 'p02_etsy_profit', 'images', 'make_images.py'))
uri = p1.uri
CSS = p1.CSS + """
.two{display:grid;grid-template-columns:1fr 1fr;gap:40px;width:100%;align-items:start}
.card{background:#fff;border-radius:12px;box-shadow:0 14px 36px rgba(23,54,63,.16);padding:16px;overflow:hidden}
.card h2{font-size:38px;margin:4px 6px 14px;color:#1f4e5c}
.card img{width:100%;height:auto;display:block;object-fit:contain;object-position:top left}
.stack{display:grid;gap:34px;width:100%}
.flow{display:grid;grid-template-columns:1fr 120px 1fr;gap:20px;align-items:center;width:100%}
.arrow{font-size:120px;color:#f2b440;text-align:center;font-weight:900}
.list{display:grid;grid-template-columns:1fr 1fr;gap:40px;width:100%}
.list .card{padding:40px 48px}
.list ul{margin:18px 0 0;padding-left:40px;font-size:40px;line-height:1.55}
.steps{grid-column:1 / -1;display:grid;grid-template-columns:repeat(3,1fr);gap:40px}
.step{background:#1f4e5c;color:#fff;border-radius:12px;padding:36px 40px;font-size:38px;line-height:1.35}
.step b{display:block;color:#f2b440;font-size:64px;margin-bottom:10px}
.tag{display:inline-block;background:#1f4e5c;color:#fff;font-size:30px;padding:6px 18px;border-radius:999px}
"""

def page(eyebrow, title, body):
    return f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="top"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1></div>
<div class="stage">{body}</div>
<div class="foot"><span>UK Sole Trader + Etsy Seller bundle 2026/27 · Excel &amp; Google Sheets · Instant download</span>
<span class="badge">Shown with sample figures · Not tax advice</span></div></body></html>"""

def crop(p, box_frac, tmp, tag):
    im = Image.open(p); l, t, r, b = box_frac
    c = im.crop((int(im.width*l), int(im.height*t), int(im.width*r), int(im.height*b)))
    out = os.path.join(tmp, tag + '.png'); c.save(out); return out

def card(title, p, h):
    return f'<div class="card"><h2>{title}</h2><img src="{uri(p)}" style="max-height:{h}px"></div>'

def main():
    tmp = tempfile.mkdtemp(); os.makedirs(os.path.join(tmp, 'p2'))
    a = p1.render(tmp)
    b = p2.render(os.path.join(tmp, 'p2'), p2.HIDE[0])
    bf = p2.render(os.path.join(tmp, 'p2'), p2.HIDE[1])
    im = Image.open(a['Tax Estimate']); W, H = im.size
    top = im.crop((0, int(H*0.07), int(W*0.62), int(H*0.275))); bill = im.crop((0, int(H*0.555), int(W*0.62), int(H*0.638)))
    te_img = Image.new('RGB', (top.width, top.height + bill.height + 30), 'white'); te_img.paste(top, (0, 0)); te_img.paste(bill, (0, top.height + 30))
    te = os.path.join(tmp, 'te.png'); te_img.save(te)
    sl = crop(b['Statement Lines'], (0, 0, 1, 0.45), tmp, 'sl')
    pc = bf['Price Calculator']
    pages = [
        ("01_bundle_hero", page("2 spreadsheets · 1 tax year", "Price it, track it, file it",
            '<div class="stack">' + card("Etsy Seller Profit Tracker: what you keep from each order", pc, 330) + card("Sole Trader Tracker: profit and tax bill for the year", te, 520) + '</div>')),
        ("02_how_they_connect", page("Built to work together", "Etsy totals drop straight into your tax tracker",
            '<div class="flow">' + card("Etsy Seller Profit Tracker: totals by HMRC category", b['To Sole Trader Tracker'], 780)
            + '<div class="arrow">&rarr;</div>' + card("Sole Trader Tracker: Expenses", a['Expenses'], 780) + '</div>')),
        ("03_statement_to_pl", page("Etsy statement import", "Paste your Etsy CSV, see your real profit",
            '<div class="stack">' + card("Statement lines, read and sorted", sl, 420) + card("Monthly profit and loss", b['Monthly P&L'], 430) + '</div>')),
        ("04_tax_side", page("Self Assessment &amp; Making Tax Digital", "Your tax bill and the boxes it goes in",
            '<div class="two">' + card("Quarterly MTD totals", a['Quarterly'], 800) + card("Which box each number goes in", a['SA103 Box Map'], 800) + '</div>')),
        ("05_whats_included", page("What's included", "Two files, 18 tabs, one price",
            '<div class="list"><div class="card"><span class="tag">File 1</span><h2 style="font-size:52px;margin-top:20px">UK Etsy Seller Profit Tracker</h2><ul>'
            '<li>Price calculator with every UK Etsy fee</li><li>VAT on fees, Offsite Ads</li><li>Etsy statement CSV import</li>'
            '<li>Monthly profit and loss</li><li>HMRC platform-reporting counter</li></ul></div>'
            '<div class="card"><span class="tag">File 2</span><h2 style="font-size:52px;margin-top:20px">UK Sole Trader Tracker</h2><ul>'
            '<li>Income, expenses, mileage (55p)</li><li>Monthly and quarterly (MTD) totals</li><li>Income Tax + Class 4 NI estimate</li>'
            '<li>£1,000 trading allowance check</li><li>Self Assessment box map</li></ul></div><div class="steps"><div class="step"><b>1</b>Paste your monthly Etsy statement</div><div class="step"><b>2</b>Copy the monthly totals into the Sole Trader Tracker</div><div class="step"><b>3</b>See your profit and tax estimate all year</div></div></div>')),
    ]
    jobs = []
    for name, html in pages:
        h = os.path.join(tmp, name + '.html'); open(h, 'w', encoding='utf-8').write(html)
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
