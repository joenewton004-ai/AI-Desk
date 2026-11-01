"""Backtest Bench EP01 - draft video build.

Re-run after any audio change:  python venture/studio/video/ep01/build.py
Options: --no-render (reuse PNGs), --only long|short1|short2|short3|stills

Pipeline: data (research/output/ict_long.md) -> HTML slides -> PNG (node render.js, Playwright,
2x pixel density) -> per-piece clips (ffmpeg, slow push-in 1.00->1.04 per scene) -> concat -> mux
with the joined narration mp3. Slide timing comes from ffprobe on each paragraph mp3 plus the
probed gap (_gap.mp3), so a slide starts exactly when its paragraph starts in the joined file.
"""
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
STUDIO = os.path.join(REPO, 'venture', 'studio')
VOICE = os.path.join(STUDIO, 'voice', 'ep01')
DATA_MD = os.path.join(REPO, 'research', 'output', 'ict_long.md')
BRAND = os.path.join(STUDIO, 'brand', 'brand.html')
HTML_DIR = os.path.join(HERE, 'slides', 'html')
PNG_DIR = os.path.join(HERE, 'slides', 'png')
CLIP_DIR = os.path.join(HERE, 'build')
FPS = 30
ZOOM = 0.04  # push-in 1.00 -> 1.04 per scene

BG, TEXT, ACC, BLUE, MUTED, RED, GREEN = '#1b2330', '#f3f1ec', '#ff8a3d', '#8fb3d9', '#9fb0c6', '#e5675c', '#6cc58c'
SRC = 'Source: Backtest Bench research, Alpaca 5-min bars 2016-2026'
DISC = 'Educational research, not financial advice'
M = '−'  # minus sign for display


def neg(s):
    """Display a number string from the data file with a real minus sign."""
    return s.replace('-', M)


# ---------------------------------------------------------------- data (never typed by hand)
def load_data():
    md = open(DATA_MD, encoding='utf-8').read()
    secs = re.split(r'^## ', md, flags=re.M)
    m1 = next(s for s in secs if s.startswith('Model 1'))
    m2 = next(s for s in secs if s.startswith('Model 2'))

    def table(sec):
        rows = {}
        for line in sec.splitlines():
            if line.startswith('|') and not line.startswith('|---') and not line.startswith('| rules'):
                c = [x.strip() for x in line.strip('|').split('|')]
                rows[c[0]] = dict(trades=c[1], win=c[2], r=c[3], after=c[4], t=c[5], stress=c[6], port=c[7], sharpe=c[8])
        return rows

    def quarters(sec):
        q = re.search(r'By quarter, per trade after costs: (.*?)\.\n', sec).group(1)
        return [(a, b) for a, b in re.findall(r'(\d{4}Q\d) ([+-]\d+\.\d+)%', q)]

    def years(sec):
        y = re.search(r'By year: (.*?)\.\s*$', sec, flags=re.M).group(1)
        return re.findall(r'(\d{4}) ([+-]\d+\.\d+)%', y)

    def halves(sec):
        return re.findall(r'(2016-20|2021-26) ([+-]\d+\.\d+%) \(([\d,]+)(?: trades)?\)', sec)

    head = secs[0]
    d = dict(
        sb=table(m1), js=table(m2), sbq=quarters(m1), jsq=quarters(m2), sby=years(m1), jsy=years(m2),
        sbh=halves(m1), jsh=halves(m2),
        period=re.search(r'(\d{4}-\d\d-\d\d) to (\d{4}-\d\d-\d\d)', head).groups(),
        cover=re.search(r'(\d+) of (\d+) companies', head).groups(),
        days_setup=re.search(r'([\d,]+) trading days with a setup', m1).group(1),
    )
    assert len(d['sbq']) == 44 and len(d['jsq']) == 44 and len(d['sby']) == 11
    return d


D = load_data()
PURE, COIN = 'Pure ICT (both sides, all stocks)', 'Control: same trades, coin-flip direction'
FIN, FINL, TREND = ('+ financial bias (long top third, short bottom third)', '+ financials, long only (top third)',
                    '+ trend bias (long above 50-day, short below)')
SB_TRADES = f"{int(D['sb'][PURE]['trades']):,}"   # 129,658
JS_TRADES = f"{int(D['js'][PURE]['trades']):,}"   # 80,366
SB_RED = sum(1 for _, v in D['sbq'] if float(v) < 0)
JS_RED = sum(1 for _, v in D['jsq'] if float(v) < 0)
SB_GREEN_Q = [q for q, v in D['sbq'] if float(v) > 0]
assert (SB_RED, JS_RED) == (42, 39), (SB_RED, JS_RED)  # the script's claims


def pct(s):
    return float(s.rstrip('%'))


def rv(s):
    return float(s)


# ---------------------------------------------------------------- HTML scaffolding
MARK = re.search(r'<template id="mark">\s*(<svg.*?</svg>)\s*</template>', open(BRAND).read(), flags=re.S).group(1)


def mark_svg(size):
    return MARK.replace('<svg ', f'<svg width="{size}" height="{size}" ', 1)


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:%(W)dpx;height:%(H)dpx;overflow:hidden}
body{background:#1b2330;color:#f3f1ec;font-family:'Lato','Carlito','DejaVu Sans',sans-serif;position:relative}
.bg{position:absolute;inset:0;background-image:linear-gradient(#ffffff08 2px,transparent 2px),linear-gradient(90deg,#ffffff08 2px,transparent 2px);background-size:80px 80px}
.mark{position:absolute}
.main{position:absolute;display:flex;flex-direction:column}
.kicker{color:#ff8a3d;font-weight:700;letter-spacing:4px;text-transform:uppercase}
h1{font-weight:900;line-height:1.08;letter-spacing:-1px}
h2{font-weight:700;color:#9fb0c6;line-height:1.22}
.src{position:absolute;color:#9fb0c6}
.disc{position:absolute;left:0;right:0;bottom:0;background:#11171f;border-top:4px solid #ff8a3d;display:flex;align-items:center;justify-content:center;color:#f3f1ec;text-align:center}
.o{color:#ff8a3d}.b{color:#8fb3d9}.r{color:#e5675c}.g{color:#6cc58c}.m{color:#9fb0c6}
.fill{flex:1;display:flex;align-items:center;justify-content:center;position:relative}
.big{font-weight:900;letter-spacing:-3px;line-height:1}
.card{background:#232d3d;border:3px solid #33415a;border-radius:22px}
.row{display:flex}
svg text{font-family:'Lato','Carlito','DejaVu Sans',sans-serif}
/* landscape */
body.L .mark{top:58px;right:80px}
body.L .main{left:120px;right:120px;top:84px;bottom:120px}
body.L .kicker{font-size:36px}
body.L h1{font-size:74px;margin-top:10px;padding-right:130px}
body.L h2{font-size:44px;margin-top:14px}
body.L .src{left:120px;bottom:46px;font-size:30px}
body.L .disc{height:86px;font-size:38px}
/* vertical */
body.V .mark{top:90px;right:70px}
body.V .main{left:80px;right:80px;top:110px;bottom:210px}
body.V .kicker{font-size:42px}
body.V h1{font-size:92px;margin-top:14px;padding-right:120px}
body.V h2{font-size:54px;margin-top:20px}
body.V .src{left:80px;right:80px;bottom:130px;font-size:30px;text-align:center}
body.V .disc{height:110px;font-size:40px}
"""


def page(orient, body, disc=False, src=False, mark=True, extra=''):
    W, H = (1920, 1080) if orient == 'L' else (1080, 1920)
    msize = 96 if orient == 'L' else 110
    parts = [f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS % dict(W=W, H=H)}{extra}</style></head>',
             f'<body class="{orient}"><div class="bg"></div>']
    if mark:
        parts.append(f'<div class="mark">{mark_svg(msize)}</div>')
    parts.append(body)
    if src:
        parts.append(f'<div class="src">{src if isinstance(src, str) else SRC}</div>')
    if disc:
        parts.append(f'<div class="disc">{disc if isinstance(disc, str) else DISC}</div>')
    parts.append('</body></html>')
    return ''.join(parts)


def head(kicker, title, sub=None):
    s = f'<div class="kicker">{kicker}</div><h1>{title}</h1>' if kicker else f'<h1>{title}</h1>'
    if sub:
        s += f'<h2>{sub}</h2>'
    return s


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ---------------------------------------------------------------- SVG pieces
def coin(size, sx=1.0, face='H'):
    """A coin; sx = horizontal squash for a spin frame (cos of the angle)."""
    a = abs(sx)
    f = face if sx >= 0 else ('T' if face == 'H' else 'H')
    txt = '' if a < 0.25 else (f'<text x="0" y="34" text-anchor="middle" font-size="104" font-weight="900" '
                               f'fill="#1b2330">{f}</text>')
    return (f'<svg width="{size}" height="{size}" viewBox="-115 -115 230 230">'
            f'<g transform="scale({max(a, 0.04):.3f},1)">'
            f'<circle r="108" fill="#b35a22"/><circle r="100" fill="#ff8a3d"/>'
            f'<circle r="80" fill="none" stroke="#ffc796" stroke-width="5" opacity=".75"/>{txt}</g></svg>')


def tspans(text, x, fs, lh=1.18):
    lines = text.split('\n')
    out = []
    for i, ln in enumerate(lines):
        out.append(f'<tspan x="{x}" dy="{0 if i == 0 else fs * lh:.0f}">{esc(ln)}</tspan>')
    return ''.join(out), len(lines)


def vbars(items, W, H, vmin, vmax, ticks, tickfmt, fs=36, lm=170, bar_w=240):
    """Vertical bars from a zero line. items: dict(label, v, text, color, dim)."""
    maxl = max(len(it['label'].split('\n')) for it in items)
    allneg = vmax <= 0
    top = (fs * 1.2 * maxl + 30) if allneg else fs * 2
    bottom = fs * 2.2 if allneg else fs * 1.2 * maxl + 40
    ph = H - top - bottom
    y = lambda v: top + (vmax - v) / (vmax - vmin) * ph
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for t in ticks:
        s.append(f'<line x1="{lm}" x2="{W}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="#ffffff22" stroke-width="2"/>')
        s.append(f'<text x="{lm - 18}" y="{y(t) + fs * 0.35:.1f}" text-anchor="end" font-size="{fs * 0.85:.0f}" '
                 f'fill="{MUTED}">{tickfmt(t)}</text>')
    n = len(items)
    slot = (W - lm) / n
    bw = min(bar_w, slot * 0.62)
    for i, it in enumerate(items):
        cx = lm + slot * (i + 0.5)
        v = it['v']
        y0, y1 = y(0), y(v)
        op = 0.35 if it.get('dim') else 1
        s.append(f'<g opacity="{op}">')
        s.append(f'<rect x="{cx - bw / 2:.1f}" y="{min(y0, y1):.1f}" width="{bw:.1f}" height="{max(abs(y1 - y0), 3):.1f}" '
                 f'rx="6" fill="{it["color"]}"/>')
        vy = (max(y0, y1) + fs * 1.15) if v < 0 else (min(y0, y1) - 16)
        s.append(f'<text x="{cx:.1f}" y="{vy:.1f}" text-anchor="middle" font-size="{fs * 1.15:.0f}" font-weight="900" '
                 f'fill="{it.get("tcolor", it["color"])}">{esc(it["text"])}</text>')
        if allneg:
            nl = len(it['label'].split('\n'))
            ly = y0 - 18 - fs * 1.2 * (nl - 1)
        else:
            ly = top + ph + fs + 20
        sp, _ = tspans(it['label'], f'{cx:.1f}', fs)
        s.append(f'<text y="{ly:.1f}" text-anchor="middle" font-size="{fs}" font-weight="700" fill="{TEXT}">{sp}</text>')
        s.append('</g>')
    s.append(f'<line x1="{lm}" x2="{W}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{TEXT}" stroke-width="3"/>')
    s.append('</svg>')
    return ''.join(s)


def hbars(items, W, H, vmin, vmax, ticks, tickfmt, fs=36, label_w=520, rm=40, extra_col=None):
    """Horizontal bars from a zero line. extra_col = (header, [texts]) drawn right of the plot."""
    ecw = 260 if extra_col else 0
    x0, x1 = label_w, W - rm - ecw
    x = lambda v: x0 + (v - vmin) / (vmax - vmin) * (x1 - x0)
    n = len(items)
    top, bottom = (fs * 1.6 if extra_col else 20), fs * 2.2
    rh = (H - top - bottom) / n
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    for t in ticks:
        s.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top}" y2="{H - bottom}" stroke="#ffffff22" stroke-width="2"/>')
        s.append(f'<text x="{x(t):.1f}" y="{H - bottom + fs * 1.2:.1f}" text-anchor="middle" font-size="{fs * 0.85:.0f}" '
                 f'fill="{MUTED}">{tickfmt(t)}</text>')
    if extra_col:
        s.append(f'<text x="{W - rm - ecw / 2:.0f}" y="{fs:.0f}" text-anchor="middle" font-size="{fs * 0.8:.0f}" '
                 f'fill="{MUTED}">{extra_col[0]}</text>')
    for i, it in enumerate(items):
        cy = top + rh * (i + 0.5)
        v = it['v']
        bh = min(rh * 0.56, 110)
        op = 0.35 if it.get('dim') else 1
        s.append(f'<g opacity="{op}">')
        xa, xb = sorted([x(0), x(v)])
        s.append(f'<rect x="{xa:.1f}" y="{cy - bh / 2:.1f}" width="{max(xb - xa, 4):.1f}" height="{bh:.1f}" rx="6" '
                 f'fill="{it["color"]}"/>')
        left = v < 0 or it['text'].startswith(M)
        tx = (x(v) - 16) if left else (x(v) + 16)
        if left and v == 0:
            tx = x(0) - 16
        s.append(f'<text x="{tx:.1f}" y="{cy + fs * 0.4:.1f}" text-anchor="{"end" if left else "start"}" '
                 f'font-size="{fs * 1.15:.0f}" font-weight="900" fill="{it.get("tcolor", it["color"])}">{esc(it["text"])}</text>')
        sp, nl = tspans(it['label'], label_w - 30, fs)
        s.append(f'<text y="{cy + fs * 0.35 - (nl - 1) * fs * 0.6:.1f}" text-anchor="end" font-size="{fs}" '
                 f'font-weight="700" fill="{TEXT}">{sp}</text>')
        if extra_col:
            s.append(f'<text x="{W - rm - ecw / 2:.0f}" y="{cy + fs * 0.35:.1f}" text-anchor="middle" font-size="{fs}" '
                     f'font-weight="700" fill="{MUTED}">{extra_col[1][i]}</text>')
        s.append('</g>')
    s.append(f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{top - 10}" y2="{H - bottom + 6}" stroke="{TEXT}" stroke-width="3"/>')
    s.append('</svg>')
    return ''.join(s)


def qgrid(qs, W, H, orient, reveal=44, fs=34, values=True):
    """44 quarter squares, red = loss after costs, green = gain."""
    years = sorted({q[:4] for q, _ in qs})
    vals = dict(qs)
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    if orient == 'L':
        lw, th = 90, fs * 1.6
        cw, ch = (W - lw) / len(years), (H - th) / 4
        for j, yv in enumerate(years):
            s.append(f'<text x="{lw + cw * (j + .5):.1f}" y="{fs * 1.05:.1f}" text-anchor="middle" font-size="{fs}" '
                     f'font-weight="700" fill="{TEXT}">{yv}</text>')
        for i in range(4):
            s.append(f'<text x="{lw - 20}" y="{th + ch * (i + .5) + fs * .35:.1f}" text-anchor="end" font-size="{fs}" '
                     f'font-weight="700" fill="{MUTED}">Q{i + 1}</text>')
        cell = lambda yi, qi: (lw + cw * yi, th + ch * qi)
    else:
        lw, th = 140, fs * 1.6
        cw, ch = (W - lw) / 4, (H - th) / len(years)
        for i in range(4):
            s.append(f'<text x="{lw + cw * (i + .5):.1f}" y="{fs * 1.05:.1f}" text-anchor="middle" font-size="{fs}" '
                     f'font-weight="700" fill="{MUTED}">Q{i + 1}</text>')
        for j, yv in enumerate(years):
            s.append(f'<text x="{lw - 20}" y="{th + ch * (j + .5) + fs * .35:.1f}" text-anchor="end" font-size="{fs}" '
                     f'font-weight="700" fill="{TEXT}">{yv}</text>')
        cell = lambda yi, qi: (lw + cw * qi, th + ch * yi)
    k = 0
    for yi, yv in enumerate(years):
        for qi in range(4):
            q = f'{yv}Q{qi + 1}'
            x, y = cell(yi, qi)
            pad = 7
            if q in vals and k < reveal:
                v = float(vals[q])
                col = GREEN if v > 0 else RED
                s.append(f'<rect x="{x + pad:.1f}" y="{y + pad:.1f}" width="{cw - 2 * pad:.1f}" height="{ch - 2 * pad:.1f}" '
                         f'rx="10" fill="{col}"/>')
                if values:
                    s.append(f'<text x="{x + cw / 2:.1f}" y="{y + ch / 2 + fs * .36:.1f}" text-anchor="middle" '
                             f'font-size="{fs}" font-weight="900" fill="#1b2330">{neg(vals[q])}</text>')
            else:
                s.append(f'<rect x="{x + pad:.1f}" y="{y + pad:.1f}" width="{cw - 2 * pad:.1f}" height="{ch - 2 * pad:.1f}" '
                         f'rx="10" fill="none" stroke="#3a4860" stroke-width="3"/>')
            k += 1
    s.append('</svg>')
    return ''.join(s)


class CandlePlot:
    """Map illustrative candles (o, h, l, c) into an SVG box."""

    def __init__(self, x0, y0, w, h, n, pmin, pmax, cw=0.56):
        self.x0, self.y0, self.w, self.h, self.n, self.pmin, self.pmax, self.cwr = x0, y0, w, h, n, pmin, pmax, cw

    def px(self, i):
        return self.x0 + self.w / self.n * (i + 0.5)

    def py(self, p):
        return self.y0 + (self.pmax - p) / (self.pmax - self.pmin) * self.h

    def candle(self, i, o, h, l, c, hl=False, op=1.0):
        col = GREEN if c >= o else RED
        cw = self.w / self.n * self.cwr
        x = self.px(i)
        sw = max(3, cw * 0.08)
        out = (f'<g opacity="{op}"><line x1="{x:.1f}" x2="{x:.1f}" y1="{self.py(h):.1f}" y2="{self.py(l):.1f}" '
               f'stroke="{col}" stroke-width="{sw:.1f}" stroke-linecap="round"/>'
               f'<rect x="{x - cw / 2:.1f}" y="{self.py(max(o, c)):.1f}" width="{cw:.1f}" '
               f'height="{max(abs(self.py(o) - self.py(c)), 3):.1f}" rx="4" fill="{col}"/>')
        if hl:
            out += (f'<rect x="{x - cw / 2 - 12:.1f}" y="{self.py(h) - 12:.1f}" width="{cw + 24:.1f}" '
                    f'height="{self.py(l) - self.py(h) + 24:.1f}" rx="10" fill="none" stroke="{ACC}" stroke-width="5"/>')
        return out + '</g>'


ARROW_DEFS = (f'<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
              f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{ACC}"/></marker>'
              f'<marker id="aw" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
              f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{TEXT}"/></marker></defs>')

# Illustrative ICT day: run up, sweep above the line, displacement down with a fair value gap,
# retrace into the gap (entry), run to a 2R target. Not real data - labelled "Illustration".
SETUP = [(94, 96, 93, 95.5), (95.5, 97.5, 95, 97), (97, 98.5, 96, 96.5), (96.5, 99, 96, 98.5),
         (98.5, 101.6, 98, 98.8), (98.8, 99.2, 97.5, 97.8), (97.8, 98, 92.5, 93), (93, 94.5, 92, 94.2),
         (94.2, 96, 93.8, 95.6), (95.6, 95.8, 90, 90.5), (90.5, 91.2, 86, 86.5), (86.5, 87.2, 82, 82.3)]
LINE, ENTRY, STOP = 100, 95.6, 102.4
TARGET = ENTRY - 2 * (STOP - ENTRY)  # 2R


def sweep_svg(W, H, fs=36):
    cp = CandlePlot(60, 150, W - 120, H - 190, 9, 90.5, 102.6)
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{ARROW_DEFS}']
    ly = cp.py(LINE)
    s.append(f'<line x1="40" x2="{W - 30}" y1="{ly:.1f}" y2="{ly:.1f}" stroke="{BLUE}" stroke-width="4" stroke-dasharray="18 12"/>')
    s.append(f'<text x="50" y="{ly - 70:.1f}" font-size="{fs}" font-weight="700" fill="{BLUE}">Yesterday\'s high</text>')
    s.append(f'<text x="50" y="{ly - 22:.1f}" font-size="{fs}" fill="{TEXT}">stops rest here</text>')
    for k, i in enumerate([1.4, 2.5, 6.4, 7.5]):
        x = cp.px(i)
        s.append(f'<rect x="{x - 48:.1f}" y="{ly - 64:.1f}" width="96" height="44" rx="8" fill="#2a3446" stroke="{ACC}" stroke-width="3"/>'
                 f'<text x="{x:.1f}" y="{ly - 32:.1f}" text-anchor="middle" font-size="26" font-weight="700" fill="{ACC}">stop</text>')
    for i, c in enumerate(SETUP[:9]):
        s.append(cp.candle(i, *c, hl=(i == 4)))
    sx, sy = cp.px(4), cp.py(SETUP[4][1])
    s.append(f'<text x="{sx:.1f}" y="{sy - 40:.1f}" text-anchor="middle" font-size="{fs * 1.3:.0f}" font-weight="900" fill="{ACC}">SWEEP</text>')
    ax = cp.px(6) + 110
    s.append(f'<path d="M{cp.px(5) + 40:.1f},{cp.py(99.5):.1f} Q{ax:.1f},{cp.py(98):.1f} {ax:.1f},{cp.py(93.5):.1f}" fill="none" '
             f'stroke="{ACC}" stroke-width="6" marker-end="url(#ah)"/>')
    s.append(f'<text x="{ax + 40:.1f}" y="{cp.py(97.4):.1f}" font-size="{fs}" font-weight="700" fill="{TEXT}">reverses sharply</text>')
    s.append('</svg>')
    return ''.join(s)


def fvg_svg(W, H, fs=36, vertical=False):
    c3 = SETUP[5:8]
    cp = CandlePlot(W * 0.06, 70, W * (0.62 if not vertical else 0.80), H - 110, 4, 91.5, 99.6, cw=0.5)
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{ARROW_DEFS}']
    gy0, gy1 = cp.py(c3[0][2]), cp.py(c3[2][1])  # candle 1 low, candle 3 high
    s.append(f'<rect x="{cp.px(0) - 60:.1f}" y="{gy0:.1f}" width="{cp.px(3) - cp.px(0) + 60:.1f}" height="{gy1 - gy0:.1f}" '
             f'fill="{ACC}" opacity=".28"/>')
    s.append(f'<line x1="{cp.px(0) - 60:.1f}" x2="{cp.px(3):.1f}" y1="{gy0:.1f}" y2="{gy0:.1f}" stroke="{ACC}" stroke-width="3" stroke-dasharray="10 8"/>')
    s.append(f'<line x1="{cp.px(2) - 60:.1f}" x2="{cp.px(3):.1f}" y1="{gy1:.1f}" y2="{gy1:.1f}" stroke="{ACC}" stroke-width="3" stroke-dasharray="10 8"/>')
    for i, c in enumerate(c3):
        s.append(cp.candle(i, *c))
        s.append(f'<text x="{cp.px(i):.1f}" y="{cp.py(c[1]) - 24:.1f}" text-anchor="middle" font-size="{fs * 1.2:.0f}" '
                 f'font-weight="900" fill="{MUTED}">{i + 1}</text>')
    # price returns into the gap
    ex, ey = cp.px(3), (gy0 + gy1) / 2
    s.append(f'<path d="M{cp.px(2) + 30:.1f},{cp.py(92.6):.1f} Q{ex - 20:.1f},{cp.py(92.4):.1f} {ex:.1f},{ey + 10:.1f}" fill="none" '
             f'stroke="{TEXT}" stroke-width="5" stroke-dasharray="12 10" marker-end="url(#aw)"/>')
    s.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="16" fill="{ACC}"/>')
    tx = cp.px(3) + 70 if not vertical else W * 0.06
    ty = ey - 30 if not vertical else H - 10
    if not vertical:
        s.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="{fs * 1.3:.0f}" font-weight="900" fill="{ACC}">FAIR VALUE GAP</text>')
        s.append(f'<text x="{tx:.1f}" y="{ty + fs * 1.5:.1f}" font-size="{fs}" fill="{TEXT}">candle 3 doesn\'t overlap candle 1</text>')
        s.append(f'<text x="{tx:.1f}" y="{ty + fs * 2.8:.1f}" font-size="{fs}" font-weight="700" fill="{TEXT}">price comes back in = entry</text>')
    s.append('</svg>')
    return ''.join(s)


def setup_svg(W, H, fs=36, show_labels=True):
    """The 'perfect' social-media chart: sweep, FVG, entry, stop, 2R target hit."""
    cp = CandlePlot(40, 60, W - 330, H - 100, len(SETUP), 81, 103.4)
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{ARROW_DEFS}']
    xr = W - 290

    def hline(p, col, label, dash='14 10'):
        y = cp.py(p)
        return (f'<line x1="40" x2="{xr:.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="4" stroke-dasharray="{dash}"/>'
                f'<text x="{xr + 16:.1f}" y="{y + fs * .35:.1f}" font-size="{fs}" font-weight="900" fill="{col}">{label}</text>')
    gy0, gy1 = cp.py(SETUP[5][2]), cp.py(SETUP[7][1])
    s.append(f'<rect x="{cp.px(5) - 20:.1f}" y="{gy0:.1f}" width="{cp.px(9) - cp.px(5) + 40:.1f}" height="{gy1 - gy0:.1f}" fill="{ACC}" opacity=".25"/>')
    s.append(hline(LINE, BLUE, 'liquidity'))
    s.append(hline(STOP, RED, 'stop'))
    s.append(hline(ENTRY, ACC, 'entry', '4 8'))
    s.append(hline(TARGET, GREEN, 'target 2R'))
    for i, c in enumerate(SETUP):
        s.append(cp.candle(i, *c, hl=(i == 4)))
    if show_labels:
        s.append(f'<text x="{cp.px(4):.1f}" y="{cp.py(STOP) - 22:.1f}" text-anchor="middle" font-size="{fs}" font-weight="900" fill="{ACC}">sweep</text>')
        s.append(f'<text x="{cp.px(6) + 26:.1f}" y="{cp.py(SETUP[5][2]) - 14:.1f}" font-size="{fs * .8:.0f}" font-weight="700" fill="{ACC}">FVG</text>')
    s.append(f'<path d="M{cp.px(8):.1f},{cp.py(ENTRY) + 30:.1f} L{cp.px(11) - 10:.1f},{cp.py(TARGET) - 26:.1f}" stroke="{ACC}" '
             f'stroke-width="7" marker-end="url(#ah)"/>')
    s.append(f'<circle cx="{cp.px(11):.1f}" cy="{cp.py(TARGET):.1f}" r="22" fill="none" stroke="{GREEN}" stroke-width="6"/>')
    s.append('</svg>')
    return ''.join(s)


def messy_svg(W, H, cols, rows, fs=34, seed=7):
    """Many rule-taken days: random-walk illustrations (not data), one highlighted 'perfect' tile."""
    rnd = random.Random(seed)
    s = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    tw, th = W / cols, H / rows
    hi = (rows // 2) * cols + cols // 2
    for k in range(cols * rows):
        x0, y0 = (k % cols) * tw, (k // cols) * th
        s.append(f'<rect x="{x0 + 6:.1f}" y="{y0 + 6:.1f}" width="{tw - 12:.1f}" height="{th - 12:.1f}" rx="10" '
                 f'fill="#202a39" stroke="{ACC if k == hi else "#33415a"}" stroke-width="{6 if k == hi else 2}"/>')
        if k == hi:
            cs = SETUP
        else:
            p, cs = 100.0, []
            for _ in range(12):
                o = p
                c = o + rnd.gauss(0, 1.6)
                h = max(o, c) + abs(rnd.gauss(0, .9))
                l = min(o, c) - abs(rnd.gauss(0, .9))
                cs.append((o, h, l, c))
                p = c
        lo = min(c[2] for c in cs)
        hh = max(c[1] for c in cs)
        cp = CandlePlot(x0 + 16, y0 + 18, tw - 32, th - 36, len(cs), lo, hh, cw=.6)
        for i, c in enumerate(cs):
            s.append(cp.candle(i, *c))
        if k != hi:  # each messy day gets a dashed 'level' that it may or may not respect
            lv = cs[0][1] + (hh - cs[0][1]) * rnd.random()
            s.append(f'<line x1="{x0 + 14:.1f}" x2="{x0 + tw - 14:.1f}" y1="{cp.py(lv):.1f}" y2="{cp.py(lv):.1f}" '
                     f'stroke="{BLUE}" stroke-width="2" stroke-dasharray="8 6" opacity=".7"/>')
    s.append('</svg>')
    return ''.join(s)


def clock_svg(size):
    r = size / 2 - 20
    c = size / 2
    s = [f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">']
    s.append(f'<circle cx="{c}" cy="{c}" r="{r}" fill="#232d3d" stroke="{TEXT}" stroke-width="8"/>')
    a0, a1 = math.radians(300 - 90), math.radians(330 - 90)
    rr = r - 14
    s.append(f'<path d="M{c},{c} L{c + rr * math.cos(a0):.1f},{c + rr * math.sin(a0):.1f} A{rr},{rr} 0 0 1 '
             f'{c + rr * math.cos(a1):.1f},{c + rr * math.sin(a1):.1f} Z" fill="{ACC}" opacity=".9"/>')
    for h in range(12):
        a = math.radians(h * 30 - 90)
        r0 = r - (34 if h % 3 == 0 else 22)
        s.append(f'<line x1="{c + r0 * math.cos(a):.1f}" y1="{c + r0 * math.sin(a):.1f}" x2="{c + (r - 8) * math.cos(a):.1f}" '
                 f'y2="{c + (r - 8) * math.sin(a):.1f}" stroke="{TEXT}" stroke-width="{7 if h % 3 == 0 else 4}"/>')
    for h, lab in [(10, '10'), (11, '11'), (12, '12'), (3, '3'), (6, '6'), (9, '9')]:
        a = math.radians((h % 12) * 30 - 90)
        rl = r - 78
        s.append(f'<text x="{c + rl * math.cos(a):.1f}" y="{c + rl * math.sin(a) + 18:.1f}" text-anchor="middle" '
                 f'font-size="48" font-weight="900" fill="{ACC if h in (10, 11) else TEXT}">{lab}</text>')
    a = math.radians(300 - 90)  # hour hand at 10
    s.append(f'<line x1="{c}" y1="{c}" x2="{c + r * .5 * math.cos(a):.1f}" y2="{c + r * .5 * math.sin(a):.1f}" stroke="{TEXT}" stroke-width="16" stroke-linecap="round"/>')
    s.append(f'<line x1="{c}" y1="{c}" x2="{c}" y2="{c - r * .75:.1f}" stroke="{TEXT}" stroke-width="10" stroke-linecap="round"/>')
    s.append(f'<circle cx="{c}" cy="{c}" r="14" fill="{ACC}"/></svg>')
    return ''.join(s)


# ---------------------------------------------------------------- slides
SLIDES = {}  # id -> (orient, html)


def add(sid, orient, html):
    SLIDES[sid] = (orient, html)


def center(inner, extra_style=''):
    return f'<div class="main" style="justify-content:center;align-items:center;text-align:center;{extra_style}">{inner}</div>'


sb, js = D['sb'], D['js']


def counter_frames(prefix, orient, n_count=28, n_spin=14):
    """p1: counter ticks up to 129,658, then a coin spins. Returns list of (slide_id, seconds)."""
    total = int(sb[PURE]['trades'])
    fs = 230 if orient == 'L' else 190
    seq = []
    for k in range(n_count + 1):
        t = k / n_count
        val = round(total * (1 - (1 - t) ** 3))
        sid = f'{prefix}_count{k:02d}'
        body = center(f'<div class="big o" style="font-size:{fs}px">{val:,}</div>'
                      f'<h2 style="font-size:{60 if orient == "L" else 64}px">trades</h2>')
        add(sid, orient, page(orient, body, disc=True))
        seq.append((sid, 2.6 / n_count if k < n_count else 0.25))
    for k in range(n_spin):
        ang = k / n_spin * 4 * math.pi + math.pi / 2  # two full turns
        sid = f'{prefix}_spin{k:02d}'
        body = center(f'<div class="big o" style="font-size:{fs}px">{SB_TRADES}</div>'
                      f'<h2 style="font-size:{60 if orient == "L" else 64}px">trades</h2>'
                      f'<div style="margin-top:40px">{coin(300 if orient == "L" else 360, math.cos(ang))}</div>')
        add(sid, orient, page(orient, body, disc=True))
        seq.append((sid, 1.4 / n_spin))
    return seq


def build_long_slides():
    O = 'L'
    # p1 hold
    add('L01_hook', O, page(O, center(
        f'<div class="big o" style="font-size:230px">{SB_TRADES}</div><h2 style="font-size:60px">trades</h2>'
        f'<div style="margin-top:40px">{coin(300)}</div>'
        f'<h2 style="font-size:58px;color:#f3f1ec;margin-top:30px">Before costs: about a coin flip</h2>'), disc=True))
    add('L02_title', O, page(O, center(
        f'<div style="margin-bottom:30px">{mark_svg(170)}</div>'
        f'<div class="kicker" style="font-size:44px">ICT Silver Bullet</div>'
        f'<h1 style="font-size:120px;padding:0;margin-top:18px">10 years, <span class="o">{SB_TRADES}</span> trades</h1>'
        f'<h2 style="font-size:52px;margin-top:30px">Fixed rules. Real data. Honest costs.</h2>'), disc=True, mark=False))
    add('L03_question', O, page(O, f'<div class="main">{head("One narrow question", "Do the setups themselves have an edge?")}'
        '<div class="fill" style="justify-content:flex-start"><div style="font-size:50px;line-height:1.55">'
        '<div><span class="o">&#10003;</span> Best-known ICT setups, written as <b>fixed rules</b></div>'
        '<div><span class="o">&#10003;</span> Run on <b>years of real market data</b></div>'
        '<div><span class="o">&#10003;</span> With <b>honest costs</b></div>'
        '<div class="m" style="margin-top:26px">Not about personalities.</div></div></div></div>', disc=True))
    add('L04_disclaimer', O, page(O, center(
        '<div class="kicker" style="font-size:44px">Quick note</div>'
        '<h1 style="font-size:100px;padding:0;margin-top:20px">Educational research,<br>not financial advice</h1>'
        '<h2 style="font-size:50px;margin-top:36px">I\'m not a financial adviser. Nothing here is a<br>recommendation to buy or sell anything.</h2>')))
    add('L05_sweep', O, page(O, f'<div class="main">{head("ICT in plain English", "Liquidity: stops sit beyond obvious highs")}'
        f'<div class="fill">{sweep_svg(1640, 700)}</div></div>', src='Illustration, not real data'))
    add('L06_fvg', O, page(O, f'<div class="main">{head("ICT in plain English", "The sharp move leaves a fair value gap")}'
        f'<div class="fill">{fvg_svg(1680, 700)}</div></div>', src='Illustration, not real data'))
    add('L07_killzone', O, page(O, f'<div class="main">{head("Timing", "Only taken in set windows: kill zones")}'
        f'<div class="fill" style="gap:110px">{clock_svg(600)}<div style="text-align:left">'
        f'<div class="big o" style="font-size:130px">10:00&ndash;11:00</div>'
        f'<div style="font-size:60px;font-weight:700;margin-top:18px">New York time</div>'
        f'<div class="m" style="font-size:46px;margin-top:22px">The Silver Bullet\'s kill zone</div></div></div></div>'))

    def rule_card(kicker, title, rows):
        rs = ''.join(f'<div class="row" style="padding:16px 0;border-bottom:2px solid #33415a">'
                     f'<div class="o" style="width:330px;font-weight:900;flex:none">{a}</div><div>{b}</div></div>' for a, b in rows)
        return page(O, f'<div class="main">{head(kicker, title)}<div class="fill" style="align-items:flex-start;'
                    f'justify-content:flex-start;margin-top:30px"><div style="font-size:46px;width:100%">{rs}</div></div></div>')
    add('L08_silver', O, rule_card('Model 1', 'SILVER BULLET', [
        ('When', '10:00&ndash;11:00 New York, 5-minute bars'),
        ('Trigger', 'Sweep of the prior day\'s high/low or the opening range'),
        ('Entry', 'Limit order in the fair value gap'),
        ('Stop', 'Beyond the sweep'),
        ('Target', '2&times; the risk (2R) &middot; out by the end of the day')]))
    add('L09_judas', O, rule_card('Model 2', 'JUDAS SWING', [
        ('Bars', 'Hourly'),
        ('Fake-out', 'First hour goes beyond the prior day\'s high or low&hellip;'),
        ('', '&hellip;then closes back inside'),
        ('Entry', 'Against the fake-out at 10:30'),
        ('Target', '2&times; the risk (2R)')]))
    # R scale
    r_svg = ['<svg width="1600" height="300" viewBox="0 0 1600 300">']
    xr = lambda v: 160 + (v + 1) / 3 * 1280
    r_svg.append(f'<line x1="{xr(-1)}" x2="{xr(2)}" y1="150" y2="150" stroke="{TEXT}" stroke-width="5"/>')
    for v, lab, col, note in [(-1, f'{M}1R', RED, 'stop hit'), (0, '0R', TEXT, 'break-even'), (1, '+1R', GREEN, 'made what you risked'),
                              (2, '+2R', GREEN, 'target hit')]:
        r_svg.append(f'<circle cx="{xr(v)}" cy="150" r="20" fill="{col}"/>'
                     f'<text x="{xr(v)}" y="100" text-anchor="middle" font-size="56" font-weight="900" fill="{col}">{lab}</text>'
                     f'<text x="{xr(v)}" y="230" text-anchor="middle" font-size="38" fill="{MUTED}">{note}</text>')
    r_svg.append('</svg>')
    add('L10_R', O, page(O, f'<div class="main">{head("One bit of jargon", "R = the amount you risk on a trade")}'
        f'<div class="fill" style="flex-direction:column">{"".join(r_svg)}</div></div>'))

    items = [('Data', '10 years of 5-minute bars, Jan 2016 &ndash; Oct 2026 (Alpaca consolidated feed)'),
             ('Stocks', f'The 100 largest US companies at each point in time: {D["cover"][1]} companies, bars for {D["cover"][0]}'),
             ('Rules', 'Fixed in code before running; community descriptions of ICT, not his course'),
             ('Costs', '0.03% each way (cheap: a tight spread on a big, liquid stock)'),
             ('Control', 'The same trades, with a coin flip for the direction')]
    for k in range(6):
        rows = ''
        for i, (a, b) in enumerate(items):
            on = i < k
            rows += (f'<div class="row" style="align-items:flex-start;padding:14px 0;opacity:{1 if on else .22}">'
                     f'<div style="width:70px;flex:none;color:{ACC}">{"&#10003;" if on else "&#9675;"}</div>'
                     f'<div style="width:230px;flex:none;font-weight:900">{a}</div><div>{b}</div></div>')
        add(f'L11_check{k}', O, page(O, f'<div class="main">{head("How we tested it", "Every choice, upfront")}'
            f'<div class="fill" style="justify-content:flex-start"><div style="font-size:42px;line-height:1.3">{rows}</div></div></div>'))
    add('L12_twist', O, page(O, f'<div class="main">{head("The twist", "Mixing in company financials, and trend")}'
        '<div class="fill" style="gap:50px;align-items:stretch;margin:40px 0 10px">'
        '<div class="card" style="flex:1;padding:44px;font-size:44px;line-height:1.4"><div class="o" style="font-weight:900;font-size:50px;margin-bottom:20px">Financial bias</div>'
        '<div><b class="g">Longs</b> only in the top third by a quality score built from SEC filings</div>'
        '<div style="margin-top:16px"><b class="r">Shorts</b> only in the bottom third</div></div>'
        '<div class="card" style="flex:1;padding:44px;font-size:44px;line-height:1.4"><div class="b" style="font-weight:900;font-size:50px;margin-bottom:20px">Trend bias</div>'
        '<div><b class="g">Longs</b> only above the 50-day average</div>'
        '<div style="margin-top:16px"><b class="r">Shorts</b> only below it</div></div></div></div>'))
    add('L13_second', O, page(O, f'<div class="main">{head("This is our second test", "Same rules, far more data")}'
        '<div class="fill" style="gap:40px">'
        f'<div class="card" style="flex:1;padding:44px;font-size:44px;line-height:1.4;opacity:.75"><div class="m" style="font-weight:900">TEST 1</div>'
        f'<div style="font-size:64px;font-weight:900;margin:10px 0">60 days</div><div>Yahoo 5-minute data<br>(all Yahoo keeps)</div></div>'
        f'<div style="font-size:90px" class="o">&#10140;</div>'
        f'<div class="card" style="flex:1;padding:44px;font-size:44px;line-height:1.4;border-color:{ACC}"><div class="o" style="font-weight:900">TEST 2 &middot; THIS VIDEO</div>'
        f'<div style="font-size:64px;font-weight:900;margin:10px 0">10 years</div><div>Alpaca 5-minute bars,<br>{D["period"][0]} to {D["period"][1]}</div></div>'
        '</div></div>'))
    add('L14_big', O, page(O, center(
        '<div class="kicker" style="font-size:46px">Silver Bullet</div>'
        f'<div class="big o" style="font-size:280px;margin-top:20px">{SB_TRADES}</div>'
        f'<h2 style="font-size:64px;color:#f3f1ec">trades in ten years</h2>'
        f'<h2 style="font-size:44px">{D["days_setup"]} trading days with a setup</h2>'), src=True))

    def rchart(W, H, fs, note=False):
        items = [dict(label='Silver Bullet', v=rv(sb[PURE]['r']), text=neg(sb[PURE]['r']) + 'R', color=GREEN),
                 dict(label='Coin-flip\ndirection', v=rv(sb[COIN]['r']), text=neg(sb[COIN]['r']) + 'R', color=MUTED, tcolor=TEXT)]
        return hbars(items, W, H, -1, 1, [-1, -.5, 0, .5, 1], lambda t: {-1: f'{M}1R', -.5: f'{M}0.5R', 0: '0R', .5: '+0.5R', 1: '+1R'}[t], fs=fs,
                     label_w=360 if W > 1200 else 300)
    add('L15_R', O, page(O, f'<div class="main">{head("Silver Bullet, before costs", "Average result per trade")}'
        f'<div class="fill">{rchart(1680, 520, 40)}</div></div>', src=True))
    add('L15_Rnote', O, page(O, f'<div class="main">{head("Silver Bullet, before costs", "Average result per trade")}'
        f'<div class="fill" style="flex-direction:column">{rchart(1680, 420, 40)}'
        f'<div class="card" style="padding:22px 40px;font-size:44px;margin-top:10px;border-color:{ACC}">Direction call worth about <b class="o">0.01%</b> a trade'
        f' &middot; round trip costs <b class="r">0.06%</b> (0.03% each way)</div></div></div>', src=True))

    def after_items(highlight):
        it = [dict(label='Silver Bullet', v=pct(sb[PURE]['after']), text=neg(sb[PURE]['after']), color=RED),
              dict(label='SB coin flip', v=pct(sb[COIN]['after']), text=neg(sb[COIN]['after']), color='#a5524c'),
              dict(label='Judas swing', v=pct(js[PURE]['after']), text=neg(js[PURE]['after']), color=RED),
              dict(label='Judas coin flip', v=pct(js[COIN]['after']), text=neg(js[COIN]['after']), color='#a5524c')]
        if highlight == 'sb':
            return it[:2]
        for i in (0, 1):
            it[i]['dim'] = True
        return it
    tf = lambda t: '0%' if t == 0 else f'{M}{abs(t):.2f}%'
    add('L16_after_sb', O, page(O, f'<div class="main">{head("After costs (0.03% each way)", "Per trade: both lose money")}'
        f'<div class="fill">{vbars(after_items("sb"), 1500, 640, -0.08, 0, [0, -.02, -.04, -.06, -.08], tf, fs=40)}</div></div>', src=True))
    add('L17_grid_sb', O, page(O, f'<div class="main">{head("Silver Bullet, after costs, % per trade", f"Lost money in <span class=r>{SB_RED}</span> of 44 quarters")}'
        f'<div class="fill">{qgrid(D["sbq"], 1680, 620, "L", fs=34)}</div></div>',
        src=f'{SRC} &middot; 2026 Q4 = Oct 1&ndash;26'))
    yitems = [dict(label=y, v=float(v), text=neg(v), color=RED) for y, v in D['sby']]
    h1, h2 = D['sbh']
    add('L18_years', O, page(O, f'<div class="main">{head("Silver Bullet, after costs, % per trade", "Lost money in every year, 2016&ndash;2026")}'
        f'<div class="fill" style="flex-direction:column">{vbars(yitems, 1680, 560, -0.08, 0, [0, -.02, -.04, -.06, -.08], tf, fs=34, lm=150, bar_w=110)}'
        f'<div style="font-size:42px;margin-top:6px">{h1[0].replace("-", "&ndash;")}: <b class="r">{neg(h1[1])}</b> &nbsp;&middot;&nbsp; '
        f'{h2[0].replace("-", "&ndash;")}: <b class="r">{neg(h2[1])}</b></div></div></div>',
        src=f'{SRC} &middot; 2026 = Jan&ndash;Oct'))
    add('L19_judas', O, page(O, f'<div class="main">{head("Model 2", "Judas swing")}'
        '<div class="fill" style="gap:40px">'
        f'<div class="card" style="flex:1;padding:40px;text-align:center"><div class="big o" style="font-size:130px">{JS_TRADES}</div>'
        f'<div style="font-size:46px;margin-top:16px">trades</div></div>'
        f'<div class="card" style="flex:1;padding:40px;text-align:center"><div class="big" style="font-size:130px">{neg(js[PURE]["r"])}R</div>'
        f'<div style="font-size:46px;margin-top:16px">before costs</div><div class="m" style="font-size:40px;margin-top:8px">'
        f'coin flip: {neg(js[COIN]["r"])}R</div></div></div></div>', src=True))
    add('L20_after_all', O, page(O, f'<div class="main">{head("After costs (0.03% each way)", "Per trade, both models and their coin flips")}'
        f'<div class="fill">{vbars(after_items("all"), 1680, 620, -0.08, 0, [0, -.02, -.04, -.06, -.08], tf, fs=38)}</div></div>', src=True))
    add('L21_grid_js', O, page(O, f'<div class="main">{head("Judas swing, after costs, % per trade", f"Lost money in <span class=r>{JS_RED}</span> of 44 quarters")}'
        f'<div class="fill">{qgrid(D["jsq"], 1680, 620, "L", fs=34)}</div></div>',
        src=f'{SRC} &middot; 2026 Q4 = Oct 1&ndash;26'))
    pitems = [dict(label='Silver Bullet', v=pct(sb[PURE]['port']), text=neg(sb[PURE]['port']) + ' a year', color=RED),
              dict(label='Judas swing', v=pct(js[PURE]['port']), text=neg(js[PURE]['port']) + ' a year', color=RED)]
    add('L22_portfolio', O, page(O, f'<div class="main">{head("As a portfolio", "10% per trade, up to 10 trades a day")}'
        f'<div class="fill">{vbars(pitems, 1300, 640, -20, 0, [0, -5, -10, -15, -20], lambda t: "0%" if t == 0 else f"{M}{abs(t):.0f}%", fs=42)}</div></div>',
        src=f'{SRC} &middot; return per year, cash in T-bills otherwise'))

    def ladder(hl):
        rows = [('Pure ICT', PURE), ('+ trend bias', TREND), ('+ financial bias', FIN), ('+ financials,\nlong only', FINL)]
        its = [dict(label=a, v=pct(sb[k]['after']), text=neg(sb[k]['after']), color=RED if k != hl else ACC,
                    dim=(hl is not None and k not in (hl, PURE))) for a, k in rows]
        return hbars(its, 1680, 640, -0.08, 0, [-.08, -.06, -.04, -.02, 0], tf, fs=40, label_w=420,
                     extra_col=('before costs', [neg(sb[k]['r']) + 'R' for _, k in rows]))
    add('L23_ladder_long', O, page(O, f'<div class="main">{head("Silver Bullet versions, after costs", "Long-only in quality companies: least bad")}'
        f'<div class="fill">{ladder(FINL)}</div></div>', src=True))
    add('L24_ladder_trend', O, page(O, f'<div class="main">{head("Silver Bullet versions, after costs", "The trend filter made it slightly worse")}'
        f'<div class="fill">{ladder(TREND)}</div></div>', src=True))
    add('L25_why', O, page(O, center(
        '<div class="kicker" style="font-size:46px">Why is day trading this hard?</div>'
        '<div style="display:flex;gap:60px;margin-top:60px">'
        '<div class="card" style="padding:50px 60px;font-size:60px;font-weight:900"><span class="o">1</span> &nbsp;Costs</div>'
        '<div class="card" style="padding:50px 60px;font-size:60px;font-weight:900"><span class="o">2</span> &nbsp;Efficient stocks</div></div>')))
    # costs bar: typical move 0.5%-1%, round trip 0.06%
    bw = 1400 / 1.0
    cost_svg = (f'<svg width="1640" height="420" viewBox="0 0 1640 420">'
                f'<rect x="120" y="120" width="{bw * .5:.0f}" height="130" rx="8" fill="{BLUE}"/>'
                f'<rect x="{120 + bw * .5:.0f}" y="120" width="{bw * .5:.0f}" height="130" rx="8" fill="none" stroke="{BLUE}" stroke-width="4" stroke-dasharray="14 10"/>'
                f'<rect x="{120 + bw * .5 - bw * .06:.0f}" y="100" width="{bw * .06:.0f}" height="170" fill="{RED}"/>'
                f'<text x="120" y="80" font-size="42" font-weight="700" fill="{TEXT}">A typical intraday move: 0.5% to 1%</text>'
                f'<text x="{120 + bw * .5 - bw * .03:.0f}" y="330" text-anchor="middle" font-size="44" font-weight="900" fill="{RED}">costs: 0.06%</text>'
                f'<text x="{120 + bw * .5 - bw * .03:.0f}" y="385" text-anchor="middle" font-size="36" fill="{MUTED}">round trip</text>'
                f'<text x="140" y="200" font-size="44" font-weight="900" fill="#1b2330">0.5%</text>'
                f'<text x="{120 + bw - 20:.0f}" y="200" text-anchor="end" font-size="44" font-weight="900" fill="{BLUE}">1%</text></svg>')
    add('L26_costs', O, page(O, f'<div class="main">{head("Reason 1", "Costs are a big share of every trade")}'
        f'<div class="fill" style="flex-direction:column">{cost_svg}<div style="font-size:46px;margin-top:20px">'
        f'Fighting over hundredths of a percent, <b class="r">0.06%</b> swallows a small edge whole.</div></div></div>'))
    add('L27_efficient', O, page(O, f'<div class="main">{head("Reason 2", "The most efficient stocks in the world")}'
        '<div class="fill" style="flex-direction:column;align-items:flex-start;font-size:52px;line-height:1.6">'
        f'<div>Yesterday\'s high &middot; the opening range</div>'
        f'<div class="m">Everyone can see those levels, including high-frequency trading firms.</div>'
        f'<div class="o" style="font-weight:900;font-size:64px;margin-top:20px">Obvious levels don\'t leave a free lunch.</div></div></div>'))
    add('L28_perfect', O, page(O, f'<div class="main">{head("On social media", "The perfect-looking ICT chart")}'
        f'<div class="fill">{setup_svg(1680, 660, fs=38)}</div></div>', src='Illustration, not real data'))
    add('L29_messy', O, page(O, f'<div class="main">{head("Chosen after the fact", "One perfect chart, many messy days")}'
        f'<div class="fill">{messy_svg(1680, 650, 7, 3)}</div></div>',
        src='Illustration, not real data &middot; hindsight picks the winners'))
    labels = [('Discretion', 'Which gap "looks right", skipping news days: a fixed rule can\'t measure that skill'),
              ('Futures &amp; forex', 'Where ICT is mostly taught. We tested large US stocks'),
              ('Small caps', 'Not tested')]
    for k in range(4):
        cards = ''.join(f'<div class="card" style="flex:1;padding:40px;opacity:{1 if (k == 0 or k == i + 1) else .35};'
                        f'border-color:{ACC if k == i + 1 else "#33415a"}"><div style="font-size:58px;font-weight:900" class="o">{a}</div>'
                        f'<div style="font-size:40px;margin-top:22px;line-height:1.35">{b}</div></div>' for i, (a, b) in enumerate(labels))
        add(f'L30_limits{k}', O, page(O, f'<div class="main">{head("What this test can\'t tell you", "Real limits")}'
            f'<div class="fill" style="gap:40px;align-items:stretch;margin:40px 0 20px">{cards}</div></div>'))
    add('L31_tjr', O, page(O, center(
        '<div class="kicker" style="font-size:44px">A close relative</div>'
        '<h1 style="font-size:110px;padding:0;margin-top:20px">TJR\'s model</h1>'
        '<h2 style="font-size:56px;margin-top:26px;color:#f3f1ec">Ten years of QQQ and SPY: <b class="o">the same answer</b></h2>'
        '<h2 style="font-size:46px;margin-top:30px">Its own video, coming up</h2>')))
    add('L32_takeaway', O, page(O, f'<div class="main" style="flex-direction:row;align-items:center;gap:90px">'
        f'<div style="flex:none">{coin(440, 1.0)}</div><div style="font-size:66px;font-weight:900;line-height:1.5">'
        f'<div>Before costs: <span class="m">a coin flip.</span></div><div>After costs: <span class="r">a loss.</span></div>'
        f'<div><span class="r">{SB_RED} of 44</span> quarters.</div></div></div>', src=True))
    arrows = (f'<svg width="1600" height="440" viewBox="0 0 1600 440"><defs>'
              f'<marker id="r1" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker>'
              f'<marker id="g1" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{GREEN}"/></marker></defs>'
              f'<path d="M80,330 L240,300 L300,350 L380,290 L460,340 L560,320" fill="none" stroke="{RED}" stroke-width="14" stroke-linejoin="round" marker-end="url(#r1)"/>'
              f'<text x="320" y="200" text-anchor="middle" font-size="70" font-weight="900" fill="{RED}">minutes</text>'
              f'<text x="320" y="420" text-anchor="middle" font-size="38" fill="{MUTED}">costs eat the move</text>'
              f'<path d="M900,360 C1100,340 1250,230 1480,90" fill="none" stroke="{GREEN}" stroke-width="14" marker-end="url(#g1)"/>'
              f'<text x="1050" y="170" text-anchor="middle" font-size="70" font-weight="900" fill="{GREEN}">months</text>'
              f'<text x="1180" y="420" text-anchor="middle" font-size="38" fill="{MUTED}">costs tiny next to the move</text></svg>')
    add('L33_months', O, page(O, f'<div class="main">{head("What held up in our research", "Strong financials and price strength")}'
        f'<div class="fill">{arrows}</div></div>'))
    add('L34_comments', O, page(O, center(
        '<div class="kicker" style="font-size:44px">Your turn</div>'
        '<h1 style="font-size:84px;padding:0;margin-top:24px;line-height:1.2">Trade ICT and profitable?<br><span class="o">What does a rule miss?</span></h1>'
        '<h2 style="font-size:50px;margin-top:40px">Tell us in the comments.<br>Starting out? Test the rules on your own data, with costs, first.</h2>')))
    add('L35_end', O, page(O, center(
        f'<div>{mark_svg(260)}</div><h1 style="font-size:130px;padding:0;margin-top:20px">Backtest <span class="o">Bench</span></h1>'
        f'<h2 style="font-size:48px;margin-top:16px">Famous trading strategies, tested honestly</h2>'
        f'<div style="margin-top:50px;background:{ACC};color:#1b2330;font-size:64px;font-weight:900;padding:22px 70px;border-radius:60px">SUBSCRIBE</div>'),
        disc="Educational research, not financial advice. I'm not a financial adviser; past results don't predict future ones.",
        mark=False, extra='body.L .disc{font-size:34px}'))


def build_short_slides():
    O = 'V'
    sdisc = 'Educational, not financial advice'
    add('V01_hook', O, page(O, center(
        f'<div class="kicker" style="font-size:52px">ICT Silver Bullet</div>'
        f'<div class="big o" style="font-size:190px;margin-top:30px">{SB_TRADES}</div><h2 style="font-size:64px">trades &middot; 10 years</h2>'
        f'<div style="margin-top:50px">{coin(360)}</div>'
        f'<h2 style="font-size:58px;color:#f3f1ec;margin-top:40px">The 100 biggest<br>US stocks</h2>'), disc=sdisc))
    items = [dict(label='Silver\nBullet', v=rv(sb[PURE]['r']), text=neg(sb[PURE]['r']) + 'R', color=GREEN),
             dict(label='Coin\nflip', v=rv(sb[COIN]['r']), text=neg(sb[COIN]['r']) + 'R', color=MUTED, tcolor=TEXT)]
    rsvg = vbars(items, 920, 1000, -1, 1, [-1, -.5, 0, .5, 1],
                 lambda t: {-1: f'{M}1R', -.5: f'{M}0.5R', 0: '0R', .5: '+0.5R', 1: '+1R'}[t], fs=52, lm=170)
    add('V02_R', O, page(O, f'<div class="main">{head("Before costs", "Average result per trade")}'
        f'<div class="fill">{rsvg}</div><h2 style="text-align:center;font-size:50px">1R = the amount risked</h2></div>', disc=sdisc, src=True))
    tf = lambda t: '0%' if t == 0 else f'{M}{abs(t):.2f}%'
    aitems = [dict(label='Silver\nBullet', v=pct(sb[PURE]['after']), text=neg(sb[PURE]['after']), color=RED),
              dict(label='Coin\nflip', v=pct(sb[COIN]['after']), text=neg(sb[COIN]['after']), color='#a5524c')]
    add('V03_after', O, page(O, f'<div class="main">{head("After 0.03% costs each way", "Per trade: both lose")}'
        f'<div class="fill">{vbars(aitems, 920, 1050, -0.08, 0, [0, -.02, -.04, -.06, -.08], tf, fs=52, lm=190)}</div></div>',
        disc=sdisc, src=True))
    add('V04_caption', O, page(O, center(
        '<h1 style="font-size:96px;padding:0;line-height:1.15">Fixed-rule version.<br><span class="o">Discretion not tested.</span></h1>'
        '<h2 style="font-size:56px;margin-top:50px">Community rules made precise,<br>not a trader\'s judgement.</h2>'
        f'<div style="margin-top:80px">{mark_svg(200)}</div>'
        '<div style="font-size:60px;font-weight:900;margin-top:20px">Full test on <span class="o">Backtest Bench</span></div>'), disc=sdisc, mark=False))
    # short 2 grid fill frames
    for k in range(45):
        add(f'V05_fill{k:02d}', O, page(O, f'<div class="main">{head("ICT Silver Bullet", "Every quarter, after costs")}'
            f'<div class="fill">{qgrid(D["sbq"], 920, 1250, "V", reveal=k, fs=40)}</div></div>', disc=sdisc, src=True))
    add('V06_grid_sb', O, page(O, f'<div class="main">{head("ICT Silver Bullet", f"<span class=r>{SB_RED}</span> losing, <span class=g>{44 - SB_RED}</span> winning quarters")}'
        f'<div class="fill">{qgrid(D["sbq"], 920, 1200, "V", fs=40)}</div></div>', disc=sdisc, src=True))
    add('V07_grid_js', O, page(O, f'<div class="main">{head("Judas swing", f"<span class=r>{JS_RED}</span> of 44 quarters lost")}'
        f'<div class="fill">{qgrid(D["jsq"], 920, 1200, "V", fs=40)}</div></div>', disc=sdisc, src=True))
    add('V08_close2', O, page(O, center(
        '<h1 style="font-size:88px;padding:0;line-height:1.2">Liquid stocks\' intraday charts:<br><span class="o">close to random</span><br>once you count costs</h1>'
        f'<div style="margin-top:90px">{mark_svg(200)}</div>'
        '<div style="font-size:60px;font-weight:900;margin-top:20px">Full breakdown on<br><span class="o">Backtest Bench</span></div>'), disc=sdisc, mark=False))
    add('V09_perfect', O, page(O, f'<div class="main">{head("On social media", "A flawless ICT setup")}'
        f'<div class="fill">{setup_svg(940, 1150, fs=44)}</div></div>', disc=sdisc, src='Illustration, not real data'))
    add('V10_messy', O, page(O, f'<div class="main">{head("Taken by the rules", f"<span class=o>{SB_TRADES}</span> of them")}'
        f'<div class="fill">{messy_svg(920, 1180, 3, 5, seed=11)}</div></div>', disc=sdisc, src='Illustration, not real data'))
    add('V11_stats', O, page(O, center(
        '<div style="font-size:64px;line-height:1.5;font-weight:900">'
        f'<div class="kicker" style="font-size:48px">Before costs</div><div style="font-size:90px">roughly <span class="m">a coin flip</span></div>'
        f'<div class="kicker" style="font-size:48px;margin-top:80px">After costs</div><div style="font-size:90px">a loss in<br><span class="r">{SB_RED} of 44</span> quarters</div></div>'),
        disc=sdisc, src=True))
    add('V12_close3', O, page(O, center(
        '<h1 style="font-size:92px;padding:0;line-height:1.2">Charts picked after the fact always look good.</h1>'
        '<h2 style="font-size:64px;margin-top:40px;color:#ff8a3d;font-weight:900">That\'s hindsight,<br>not a strategy.</h2>'
        '<h2 style="font-size:50px;margin-top:50px">Discretion: not measured.<br>The setups: measured.</h2>'
        f'<div style="margin-top:60px">{mark_svg(180)}</div>'
        '<div style="font-size:56px;font-weight:900;margin-top:16px">Full video on <span class="o">Backtest Bench</span></div>'), disc=sdisc, mark=False))


def build_thumb():
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1280px;height:720px;overflow:hidden}}
body{{background:#1b2330;color:#f3f1ec;font-family:'Lato','Carlito','DejaVu Sans',sans-serif;position:relative}}
.bg{{position:absolute;inset:0;background-image:linear-gradient(#ffffff0a 2px,transparent 2px),linear-gradient(90deg,#ffffff0a 2px,transparent 2px);background-size:64px 64px}}
.t{{position:absolute;left:56px;top:70px;font-weight:900;line-height:.92;letter-spacing:-3px}}
.n{{font-size:196px;color:#ff8a3d;text-shadow:0 8px 0 #0d1218}}
.w{{font-size:150px;color:#f3f1ec;text-shadow:0 8px 0 #0d1218}}
.tag{{position:absolute;left:56px;bottom:56px;background:#e5675c;color:#fff;font-weight:900;font-size:60px;padding:10px 26px;border-radius:12px;letter-spacing:1px}}
.coin{{position:absolute;right:50px;top:40px}}
.mk{{position:absolute;right:75px;bottom:20px}}
</style></head><body><div class="bg"></div>
<div class="t"><div class="n">129,658</div><div class="w">TRADES</div></div>
<div class="tag">ICT SILVER BULLET TESTED</div>
<div class="coin">{coin(330)}<div style="text-align:center;font-weight:900;font-size:56px;margin-top:6px">COIN FLIP?</div></div><div class="mk">{mark_svg(190)}</div>
</body></html>"""
    assert '129,658' == SB_TRADES
    SLIDES['thumbnail'] = ('T', html)


# ---------------------------------------------------------------- timelines
def probe(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]))


NARR = json.load(open(os.path.join(VOICE, 'narration.json'), encoding='utf-8'))


def para_times(key):
    gap = probe(os.path.join(VOICE, 'audio', '_gap.mp3'))
    t, out = 0.0, []
    for i, txt in enumerate(NARR[key], 1):
        d = probe(os.path.join(VOICE, 'audio', f'{key}-{i:02d}.mp3'))
        out.append(dict(i=i, start=t, speech=d, end=t + d + gap, text=txt))
        t += d + gap
    return out, t


def at(p, marker):
    """Time inside a paragraph where `marker` is spoken (estimated by character position)."""
    idx = p['text'].index(marker)
    return p['start'] + p['speech'] * idx / len(p['text'])


def timeline_long():
    P, total = para_times('long')
    p = {x['i']: x for x in P}
    T = []  # (start_sec, slide_id, group, zoom)

    def seq(t0, frames, group):
        t = t0
        for sid, dur in frames:
            T.append((t, sid, group, False))
            t += dur
        return t
    t = seq(0.0, counter_frames('L01', 'L'), 'p1seq')
    T.append((t, 'L01_hook', 'p1', True))
    T.append((p[2]['start'], 'L02_title', 'p2', True))
    T.append((at(p[2], "Today we're"), 'L03_question', 'p2b', True))
    T.append((p[3]['start'], 'L04_disclaimer', 'p3', True))
    T.append((p[4]['start'], 'L05_sweep', 'p4', True))
    T.append((p[5]['start'], 'L06_fvg', 'p5', True))
    T.append((p[6]['start'], 'L07_killzone', 'p6', True))
    T.append((p[7]['start'], 'L08_silver', 'p7', True))
    T.append((p[8]['start'], 'L09_judas', 'p8', True))
    T.append((p[9]['start'], 'L10_R', 'p9', True))
    T.append((p[10]['start'], 'L11_check0', 'check', True))
    for k, mk in enumerate(['- The data', '- The stocks', '- The rules', '- Costs', '- And a control'], 1):
        T.append((at(p[11], mk) if k > 1 else p[11]['start'], f'L11_check{k}', 'check', True))
    T.append((p[12]['start'], 'L12_twist', 'p12', True))
    T.append((p[13]['start'], 'L13_second', 'p13', True))
    T.append((p[14]['start'], 'L14_big', 'p14', True))
    T.append((p[15]['start'], 'L15_R', 'p15', True))
    T.append((at(p[15], "But it's worth"), 'L15_Rnote', 'p15', True))
    T.append((p[16]['start'], 'L16_after_sb', 'p16', True))
    T.append((p[17]['start'], 'L17_grid_sb', 'p17', True))
    T.append((at(p[17], 'And it lost in every'), 'L18_years', 'p17b', True))
    T.append((p[18]['start'], 'L19_judas', 'p18', True))
    T.append((at(p[18], 'After costs:'), 'L20_after_all', 'p18b', True))
    T.append((at(p[18], 'It lost in 39'), 'L21_grid_js', 'p18c', True))
    T.append((p[19]['start'], 'L22_portfolio', 'p19', True))
    T.append((p[20]['start'], 'L23_ladder_long', 'ladder', True))
    T.append((p[21]['start'], 'L24_ladder_trend', 'ladder', True))
    T.append((p[22]['start'], 'L25_why', 'p22', True))
    T.append((p[23]['start'], 'L26_costs', 'p23', True))
    T.append((p[24]['start'], 'L27_efficient', 'p24', True))
    T.append((p[25]['start'], 'L28_perfect', 'p25', True))
    T.append((at(p[25], "It's usually taught"), 'L29_messy', 'p25b', True))
    T.append((p[26]['start'], 'L30_limits0', 'limits', True))
    T.append((p[27]['start'], 'L30_limits1', 'limits', True))
    T.append((at(p[27], '- ICT is mostly'), 'L30_limits2', 'limits', True))
    T.append((at(p[27], "- And we didn't"), 'L30_limits3', 'limits', True))
    T.append((p[28]['start'], 'L31_tjr', 'p28', True))
    T.append((p[29]['start'], 'L32_takeaway', 'p29', True))
    T.append((p[30]['start'], 'L33_months', 'p30', True))
    T.append((p[31]['start'], 'L34_comments', 'p31', True))
    T.append((p[32]['start'], 'L35_end', 'p32', True))
    return T, total, P


def timeline_short(key):
    P, total = para_times(key)
    p = {x['i']: x for x in P}
    T = []
    if key == 'short1':
        t = 0.0
        for sid, dur in counter_frames('V01', 'V'):
            T.append((t, sid, 's1seq', False))
            t += dur
        T.append((t, 'V01_hook', 's1p1', True))
        T.append((p[2]['start'], 'V02_R', 's1p2', True))
        T.append((p[3]['start'], 'V03_after', 's1p3', True))
        T.append((p[4]['start'], 'V04_caption', 's1p4', True))
    elif key == 'short2':
        T.append((0.0, 'V05_fill00', 'fill', False))
        t0, t1 = 0.8, p[1]['end'] - 0.8
        for k in range(1, 45):
            T.append((t0 + (t1 - t0) * (k - 1) / 44, f'V05_fill{k:02d}', 'fill', False))
        T.append((p[2]['start'], 'V06_grid_sb', 's2p2', True))
        T.append((at(p[2], 'The Judas swing?'), 'V07_grid_js', 's2p2b', True))
        T.append((at(p[2], "Liquid stocks'"), 'V08_close2', 's2p2c', True))
    else:
        T.append((0.0, 'V09_perfect', 's3p1', True))
        T.append((p[2]['start'], 'V10_messy', 's3p2', True))
        T.append((at(p[2], 'Before costs:'), 'V11_stats', 's3p2b', True))
        T.append((at(p[2], 'Charts picked'), 'V12_close3', 's3p2c', True))
    return T, total, P


# ---------------------------------------------------------------- render + encode
def render(ids):
    os.makedirs(HTML_DIR, exist_ok=True)
    os.makedirs(PNG_DIR, exist_ok=True)
    jobs = []
    for sid in ids:
        orient, html = SLIDES[sid]
        hp = os.path.join(HTML_DIR, sid + '.html')
        with open(hp, 'w', encoding='utf-8') as f:
            f.write(html)
        if orient == 'T':
            jobs.append(dict(html=hp, png=os.path.join(HERE, 'thumbnail.png'), w=1280, h=720, scale=1))
        else:
            w, h = (1920, 1080) if orient == 'L' else (1080, 1920)
            jobs.append(dict(html=hp, png=os.path.join(PNG_DIR, sid + '.png'), w=w, h=h, scale=2))
    jp = os.path.join(HERE, 'slides', 'jobs.json')
    json.dump(jobs, open(jp, 'w'))
    subprocess.run(['node', os.path.join(HERE, 'render.js'), jp], check=True, cwd=HERE)


def encode_piece(args):
    png, out, n, zoom, off, tot, W, H = args
    if zoom:
        z = f"1+{ZOOM}*({off}+on)/{max(tot - 1, 1)}"
        vf = (f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},format=yuv420p")
    else:
        vf = f'scale={W}:{H}:flags=lanczos,format=yuv420p'
    cmd = ['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-framerate', str(FPS), '-i', png, '-vf', vf,
           '-frames:v', str(n), '-r', str(FPS), '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
           '-pix_fmt', 'yuv420p', '-video_track_timescale', '15360', out]
    subprocess.run(cmd, check=True)
    return out


def make_video(name, T, total, audio, W, H):
    d = os.path.join(CLIP_DIR, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    T = sorted(T, key=lambda x: x[0])
    total_frames = round(total * FPS)
    bounds = [round(t * FPS) for t, *_ in T] + [total_frames]
    pieces = []
    # zoom groups: frame span per group
    gspan = {}
    for k, (t, sid, g, z) in enumerate(T):
        a, b = bounds[k], bounds[k + 1]
        s = gspan.setdefault(g, [a, b])
        s[0], s[1] = min(s[0], a), max(s[1], b)
    jobs = []
    for k, (t, sid, g, z) in enumerate(T):
        n = bounds[k + 1] - bounds[k]
        if n <= 0:
            continue
        ga, gb = gspan[g]
        out = os.path.join(d, f'{k:03d}_{sid}.mp4')
        jobs.append((os.path.join(PNG_DIR, sid + '.png'), out, n, z, bounds[k] - ga, gb - ga, W, H))
        pieces.append(out)
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(encode_piece, jobs))
    lst = os.path.join(d, 'list.txt')
    with open(lst, 'w') as f:
        f.writelines(f"file '{p}'\n" for p in pieces)
    silent = os.path.join(d, 'video.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', silent], check=True)
    out = os.path.join(HERE, name + '.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', silent, '-i', audio, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
    return out


def contact_sheet(ids):
    cells = []
    for sid in ids:
        orient = SLIDES[sid][0]
        w = 300 if orient == 'L' else 120
        cells.append(f'<figure><img src="file://{os.path.join(PNG_DIR, sid + ".png")}" style="width:{w}px;height:{w * (9 / 16) if orient == "L" else w * 16 / 9:.0f}px">'
                     f'<figcaption>{sid}</figcaption></figure>')
    html = ('<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;padding:20px;background:#11171f;'
            'font-family:DejaVu Sans,sans-serif;color:#f3f1ec;width:1880px}.g{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end}'
            'figure{margin:0}figcaption{font-size:13px;color:#9fb0c6;margin-top:4px}h1{font-size:24px;margin:0 0 14px}</style></head>'
            f'<body><h1>Backtest Bench EP01 draft - distinct slides ({len(ids)})</h1><div class="g">{"".join(cells)}</div></body></html>')
    hp = os.path.join(HERE, 'slides', 'contact_sheet.html')
    open(hp, 'w').write(html)
    jp = os.path.join(HERE, 'slides', 'jobs_cs.json')
    json.dump([dict(html=hp, png=os.path.join(HERE, 'contact_sheet.png'), w=1920, h=400, scale=1, full=True)], open(jp, 'w'))
    subprocess.run(['node', os.path.join(HERE, 'render.js'), jp], check=True, cwd=HERE)


def fmt_t(s):
    return f'{int(s // 60)}:{s % 60:05.2f}'


def notes(timelines):
    L = ['# EP01 draft - edit notes', '',
         'Generated by `build.py` (re-run it after any audio change; timings come from ffprobe). '
         'Draft only: not committed, not uploaded.', '',
         'Timing: each paragraph slot = its mp3 duration + the probed gap (`_gap.mp3` = '
         f'{probe(os.path.join(VOICE, "audio", "_gap.mp3")):.4f} s; the brief said 0.45 s, but MP3 padding makes the real gap '
         'longer, and the joined files equal sum(paragraphs) + N x that gap exactly). Splits *inside* a paragraph '
         '(marked ~) are estimated from the character position of the cue words, so they can be off by ~0.5 s.', '']
    for name, (T, total, P) in timelines.items():
        L += [f'## {name}.mp4 ({fmt_t(total)}, {total:.2f} s)', '', '| start | slide | paragraph | cue |', '|---|---|---|---|']
        T = sorted(T, key=lambda x: x[0])
        shown = []
        for t, sid, g, z in T:
            if not z and shown and shown[-1][1].split('_')[0] == sid.split('_')[0] and ('count' in sid or 'spin' in sid or 'fill' in sid):
                continue  # collapse animation frames
            shown.append((t, sid))
        for t, sid in shown:
            para = next(x for x in P if x['start'] - 1e-6 <= t < x['end'])
            exact = abs(t - para['start']) < 1e-6
            label = sid
            if 'count' in sid:
                label = sid.split('_')[0] + '_count* / spin* (animated counter + coin spin, 4 s)'
            if 'fill' in sid:
                label = 'V05_fill* (grid fills square by square)'
            L.append(f'| {fmt_t(t)} | {label} | {para["i"]} | {"start" if exact else "~ mid-paragraph"} |')
        L.append('')
    L += ['## What each chart shows (all numbers parsed from research/output/ict_long.md by build.py)', '',
          f'- L15_R / V02_R: avg R before costs, Silver Bullet {sb[PURE]["r"]}R vs coin-flip {sb[COIN]["r"]}R, on a -1R..+1R axis (so the bars look as tiny as they are).',
          f'- L16 / V03: after costs per trade, SB {sb[PURE]["after"]} vs coin {sb[COIN]["after"]}; L20 adds Judas {js[PURE]["after"]} vs coin {js[COIN]["after"]}.',
          f'- L17 / V06: 44-quarter grid, Silver Bullet: {SB_RED} red, {44 - SB_RED} green ({", ".join(SB_GREEN_Q)}). L21 / V07: Judas, {JS_RED} red.',
          '- L18: by-year bars 2016-2026 (Silver Bullet, after costs) + both halves.',
          f'- L22: portfolio return per year, SB {sb[PURE]["port"]}, Judas {js[PURE]["port"]}.',
          f'- L23/L24: version ladder after costs (pure {sb[PURE]["after"]}, trend {sb[TREND]["after"]}, financial {sb[FIN]["after"]}, '
          f'long-only {sb[FINL]["after"]}) with before-costs R alongside.',
          '- Diagrams (sweep, fair value gap, perfect setup, messy days) are labelled "Illustration, not real data".', '',
          '## Not done / to check', '',
          '- No real coin-spin footage: the coin is an SVG drawn in brand orange, spun with 14 squashed frames.',
          '- "Black screen" for the hook counter is the brand slate background instead (channel look).',
          '- Lato is not installed; text renders in Carlito (fallback in the brand font stack).',
          '- Mid-paragraph cut points are estimates (see above); nudge in `timeline_long()` if a cut lands early/late.',
          '- 2026 Q4 / 2026 in the grids and year bars are partial (data ends 2026-10-26); noted in the source line.',
          '- No music, no captions/subtitles burned in, no transitions beyond hard cuts + slow push-in.',
          '- Thumbnail title text: "129,658 TRADES" + "ICT SILVER BULLET TESTED" (video title per YOUTUBE METADATA: '
          '"I Tested ICT\'s Silver Bullet on 129,658 Trades (10 Years of Data)").', '']
    open(os.path.join(HERE, 'EDIT_NOTES.md'), 'w').write('\n'.join(L))


def main():
    args = sys.argv[1:]
    only = args[args.index('--only') + 1] if '--only' in args else None
    build_long_slides()
    build_short_slides()
    build_thumb()
    tl = {'long': timeline_long()}
    for k in ('short1', 'short2', 'short3'):
        tl[k] = timeline_short(k)
    if '--no-render' not in args:
        render(list(SLIDES))
    distinct = [s for s in SLIDES if s != 'thumbnail' and not re.search(r'_(count|spin|fill)\d', s)]
    contact_sheet(distinct)
    for name, (T, total, _) in tl.items():
        if only and only != name:
            continue
        if only == 'stills':
            break
        W, H = (1920, 1080) if name == 'long' else (1080, 1920)
        out = make_video(name, T, total, os.path.join(VOICE, name + '.mp3'), W, H)
        print(f'{out}: video {probe(out):.3f}s, audio {total:.3f}s')
    notes(tl)


if __name__ == '__main__':
    main()
