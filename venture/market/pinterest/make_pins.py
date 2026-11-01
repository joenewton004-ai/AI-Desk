"""Pinterest pins (1000x1500, 2:3) for the BoxByBoxSheets listings. Brand cards + real workbook renders.
Run: python venture/market/pinterest/make_pins.py"""
import importlib.util, json, os, shutil, subprocess, tempfile
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); MARKET = os.path.join(HERE, '..')
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m
p1 = load('p1img', os.path.join(MARKET, 'p01_sole_trader', 'images', 'make_images.py'))
p2 = load('p2img', os.path.join(MARKET, 'p02_etsy_profit', 'images', 'make_images.py'))
uri = p1.uri
MARK = '<div class="mark"><i></i><i class="d"></i><i></i><i class="d"></i><i class="k"></i><i></i><i></i><i></i><i class="d"></i></div>'
CSS = """*{margin:0;box-sizing:border-box}
body{width:1000px;height:1500px;font-family:'Lato','Carlito','DejaVu Sans',sans-serif;background:#1f4e5c;color:#fff;overflow:hidden;position:relative}
.bg{position:absolute;inset:0;background-image:linear-gradient(#ffffff0d 2px,transparent 2px),linear-gradient(90deg,#ffffff0d 2px,transparent 2px);background-size:80px 80px}
.wrap{position:relative;height:100%;display:flex;flex-direction:column;padding:70px 64px 60px;gap:34px}
.head{display:flex;align-items:center;gap:22px}
.mark{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;width:84px;height:84px}
.mark i{display:block;background:#2e7b8b;border-radius:5px}.mark i.d{background:#cfe4e8}
.mark i.k{background:#f2b440;position:relative}
.mark i.k::after{content:"";position:absolute;left:30%;top:12%;width:28%;height:52%;border:solid #1f4e5c;border-width:0 5px 5px 0;transform:rotate(45deg)}
.brand{font-size:36px;font-weight:900}.brand span{color:#f2b440}
.kicker{align-self:flex-start;font-size:28px;font-weight:700;letter-spacing:.12em;padding:8px 22px;border-radius:999px;background:#f2b440;color:#1f4e5c}
h1{font-size:84px;line-height:1.04;font-weight:900;letter-spacing:-1px}
h1 em{font-style:normal;color:#f2b440}
.sub{font-size:36px;color:#cfe4e8;line-height:1.3}
.shot{background:#fff;border-radius:16px;padding:14px;overflow:hidden;margin:auto 0}
.shot img{width:100%;display:block;max-height:760px;object-fit:contain;object-position:top}
ul{font-size:54px;line-height:1.7;padding-left:44px;color:#fff}
.cta{margin-top:auto;font-size:30px;color:#cfe4e8;border-top:2px solid #ffffff33;padding-top:24px;display:flex;justify-content:space-between}
.cta b{color:#f2b440}"""

def pin(kicker, h1, sub, body, cta="Excel &amp; Google Sheets · instant download"):
    return f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="bg"></div><div class="wrap">
<div class="head">{MARK}<div class="brand">BoxByBox<span>Sheets</span></div></div>
<div class="kicker">{kicker}</div><h1>{h1}</h1><div class="sub">{sub}</div>{body}
<div class="cta"><span>{cta}</span><b>Find it on Etsy</b></div></div></body></html>"""

def shot(p): return f'<div class="shot"><img src="{uri(p)}"></div>'

def main():
    tmp = tempfile.mkdtemp(); os.makedirs(os.path.join(tmp, 'p2'))
    a = p1.render(tmp); b = p2.render(os.path.join(tmp, 'p2'), p2.HIDE[0]); bf = p2.render(os.path.join(tmp, 'p2'), p2.HIDE[1])
    im = Image.open(a['Tax Estimate']); W, H = im.size
    bill = im.crop((0, int(H*0.43), int(W*0.62), int(H*0.638))); te = os.path.join(tmp, 'bill.png'); bill.save(te)
    im = Image.open(bf['Price Calculator']); pc = os.path.join(tmp, 'pc.png'); im.crop((0, int(im.height*0.25), im.width, im.height)).save(pc)
    def cut(path, boxes, tag, gap=0):
        im = Image.open(path); W, H = im.size
        parts = [im.crop((int(W*l), int(H*t), int(W*r), int(H*bt))) for l, t, r, bt in boxes]
        out = Image.new('RGB', (sum(x.width for x in parts), max(x.height for x in parts)), 'white'); x0 = 0
        for x in parts: out.paste(x, (x0, 0)); x0 += x.width
        f = os.path.join(tmp, tag + '.png'); out.save(f); return f
    pc = cut(bf['Price Calculator'], [(0, 0.25, 0.215, 1), (0.775, 0.25, 1, 1)], 'pc2')
    qu = cut(a['Quarterly'], [(0, 0.12, 0.215, 0.43), (0.925, 0.12, 1, 0.43)], 'qu')
    sl = cut(b['Statement Lines'], [(0.1, 0.1, 0.75, 0.34)], 'sl')
    tp = cut(b['To Sole Trader Tracker'], [(0, 0, 0.5, 1)], 'tp')
    pins = {
      'p01_a_tax_bill': pin("UK · 2026/27", "How much tax should a <em>sole trader</em> put aside?", "A spreadsheet that works out your Income Tax and Class 4 NI as you go", shot(te)),
      'p01_b_features': pin("SELF ASSESSMENT", "Sole trader bookkeeping, <em>box by box</em>", "Built around HMRC's own expense boxes for 2026/27",
          "<ul><li>Income and expenses</li><li>Mileage at 55p a mile</li><li>Making Tax Digital quarters</li><li>Tax estimate all year</li><li>Which box each total goes in</li></ul>"),
      'p01_c_mtd': pin("MAKING TAX DIGITAL", "Your quarterly <em>MTD totals</em>, ready to copy", "Standard periods, deadlines and year-to-date figures", shot(qu)),
      'p02_a_fees': pin("UK ETSY SELLERS", "What you <em>really keep</em> from each Etsy sale", "Every UK fee, VAT on fees, profit and break-even price", shot(pc)),
      'p02_b_import': pin("ETSY STATEMENT IMPORT", "Paste your Etsy CSV, see your <em>real profit</em>", "Every line sorted into sales, refunds and each fee", shot(sl)),
      'p02_c_features': pin("UK · 2026/27", "Etsy fees in the UK, <em>finally clear</em>", "A profit tracker made for UK Etsy sellers",
          "<ul><li>6.5% transaction fee</li><li>4% + 20p processing</li><li>0.48% regulatory fee</li><li>20% VAT on fees</li><li>Offsite Ads</li></ul>"),
      'b01_a_bundle': pin("BUNDLE · 2 FILES", "Price it, track it, <em>file it</em>", "Sole Trader Tax Tracker + Etsy Seller Profit Tracker",
          "<ul><li>Paste your Etsy statement</li><li>Copy the monthly totals across</li><li>See profit and tax all year</li></ul>"),
      'b01_b_connect': pin("BUILT TO WORK TOGETHER", "Etsy totals that drop into your <em>tax tracker</em>", "Already in HMRC's categories", shot(tp)),
    }
    jobs = []
    for name, html in pins.items():
        h = os.path.join(tmp, name + '.html'); open(h, 'w', encoding='utf-8').write(html); jobs.append([h, os.path.join(HERE, name + '.png')])
    js = os.path.join(tmp, 'shot.js')
    open(js, 'w').write("""const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1000,height:1500}});
for(const [h,o] of JSON.parse(process.argv[2])){await p.goto('file://'+h);await p.screenshot({path:o});console.log('wrote',o)}
await b.close()})();""")
    subprocess.run(['node', js, json.dumps(jobs)], check=True); shutil.rmtree(tmp)

if __name__ == '__main__':
    main()
