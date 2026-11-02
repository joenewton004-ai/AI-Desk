"""Backtest Bench EP01 Shorts, v2: avatar ("Up") + top card + burned-in captions.

Re-run after any audio / mood / narration change:
    python venture/studio/video/ep01_shorts_v2/build.py [--only short3] [--keep-build]

Pipeline
  1. Timing: ffprobe of each paragraph mp3 + the probed _gap.mp3 (the joined voice/ep01/<key>.mp3 is
     paragraphs each followed by that gap). Sentences split with (?<=[.?!])\\s+; a sentence's start is
     estimated by its character share of the paragraph's audio. Long sentences are split into caption
     chunks (<= 3 lines), timed the same way inside the sentence.
  2. Moods from voice/ep01/moods.json (string = whole paragraph, list = one per sentence).
  3. Every frame gets a state = (card, caption chunk, mood, mouth open/closed, bounce). Each distinct
     state is rendered once to PNG (node render.js, Playwright; one page, setState() per still).
  4. ffmpeg concat demuxer holds each still for its frame count -> H.264 crf 20 + AAC 192k of the joined mp3.
  5. contact sheet (one frame per mood change), EDIT_NOTES.md, build/ deleted unless --keep-build.

Every number on a card is parsed from research/output/ict_long.md (via the episode 1 build's loader)
or research/ICT.md; captions are the narration text verbatim.
"""
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
STUDIO = os.path.join(REPO, 'venture', 'studio')
VOICE = os.path.join(STUDIO, 'voice', 'ep01')
BUILD = os.path.join(HERE, 'build')
FPS = 30
W, H = 1080, 1920
SHORTS = ['short1', 'short2', 'short3', 'short4', 'short5', 'short6']

# ---------------------------------------------------------------- reuse episode 1's data reader + drawings
_spec = importlib.util.spec_from_file_location('ep01_build', os.path.join(STUDIO, 'video', 'ep01', 'build.py'))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)
D, PURE, COIN, TREND, FINL = B.D, B.PURE, B.COIN, B.TREND, B.FINL
sb, js = D['sb'], D['js']
neg, pct, M = B.neg, B.pct, B.M
BG, TEXT, ACC, BLUE, MUTED, RED, GREEN = B.BG, B.TEXT, B.ACC, B.BLUE, B.MUTED, B.RED, B.GREEN

HEAD_MD = open(B.DATA_MD, encoding='utf-8').read()
COST_EACH = float(re.search(r'Costs (\d+\.\d+)% each way', HEAD_MD).group(1))          # 0.03
ROUND_TRIP = round(2 * COST_EACH, 4)                                                    # 0.06
EDGE = round(pct(sb[PURE]['after']) - pct(sb[COIN]['after']), 3)                       # 0.010: ICT vs coin, per trade
ICT_MD = open(os.path.join(REPO, 'research', 'ICT.md'), encoding='utf-8').read()
MOVE = re.search(r'typical intraday move is (\d+\.\d+)[–-](\d+)%', ICT_MD).groups()  # ('0.5', '1')
SB_RED, JS_RED = B.SB_RED, B.JS_RED
assert (SB_RED, JS_RED) == (42, 39) and B.SB_TRADES == '129,658' and B.JS_TRADES == '80,366'
assert COST_EACH == 0.03 and abs(EDGE - 0.01) < 1e-9 and MOVE == ('0.5', '1')
SRC = 'Source: Backtest Bench research &middot; Alpaca 5-min bars 2016&ndash;2026'


# ---------------------------------------------------------------- avatar "Candle" (owner's pick 2026-11-02)
# One STILL image per mood: arms (bars either side) and wicks change with the mood; no talking mouth, no bounce.
POSES = {
    #            left arm, right arm, wick top, wick bottom, eye, mouth, fill, brows
    'neutral':   (0, 0, 16, 192, 7, 'M86 120 Q100 127 114 120', 'none', None),
    'shocked':   (55, -55, 2, 204, 10, 'M90 122 a10 12 0 1 0 20 0 a10 12 0 1 0 -20 0', '#1b2330', 'M66 64 L90 58 M110 58 L134 64'),
    'sceptical': (-60, 0, 30, 186, 4, 'M86 124 L114 118', 'none', 'M66 76 L90 74 M110 64 L134 70'),
    'pleased':   (35, -35, 8, 196, 3, 'M80 114 Q100 138 120 114', 'none', None),
    'thinking':  (-40, -70, 22, 190, 7, 'M90 122 Q104 118 114 122', 'none', None),
}


def avatar_svg(mood, talk_open=False, size=600):
    la, ra, wt, wb, eye, mouth, fill, brow = POSES[mood]
    s = [f'<svg viewBox="0 0 200 210" width="{size}" height="{round(size * 1.05)}">',
         f'<line x1="100" y1="{wt}" x2="100" y2="52" stroke="#ff8a3d" stroke-width="8" stroke-linecap="round"/>',
         f'<line x1="100" y1="168" x2="100" y2="{wb}" stroke="#ff8a3d" stroke-width="8" stroke-linecap="round"/>',
         f'<rect x="26" y="100" width="34" height="11" rx="5.5" fill="#ff8a3d" transform="rotate({la} 58 105)"/>',
         f'<rect x="140" y="100" width="34" height="11" rx="5.5" fill="#ff8a3d" transform="rotate({ra} 142 105)"/>',
         '<rect x="56" y="50" width="88" height="120" rx="14" fill="#ff8a3d"/>',
         '<rect x="56" y="50" width="88" height="20" rx="10" fill="#ffb07a"/>']
    if brow:
        s.append(f'<path d="{brow}" stroke="#1b2330" stroke-width="6" stroke-linecap="round" fill="none"/>')
    s.append(f'<ellipse cx="80" cy="92" rx="7" ry="{eye}" fill="#1b2330"/><ellipse cx="120" cy="92" rx="7" ry="{eye}" fill="#1b2330"/>')
    s.append(f'<path d="{mouth}" stroke="#1b2330" stroke-width="5" stroke-linecap="round" fill="{fill}"/>')
    s.append('</svg>')
    return ''.join(s)


# ---------------------------------------------------------------- card drawings (card body = 800 x ~440)
CW = 800


def card(kicker, body, note=None):
    s = f'<div class="ck">{kicker}</div><div class="cb">{body}</div>'
    if note:
        s += f'<div class="cn">{note}</div>'
    return s


def big(num, sub, color=ACC, fs=170):
    return (f'<div class="big" style="font-size:{fs}px;color:{color}">{num}</div>'
            f'<div class="sub">{sub}</div>')


def mbars(rows, vmax, Wd=CW, Hd=330, fs=34):
    """Magnitude bars from a left zero line. rows: (label, value_text, magnitude, color, label_color)."""
    n = len(rows)
    rh = Hd / n
    x0, x1 = 6, Wd - 190
    s = [f'<svg width="{Wd}" height="{Hd}" viewBox="0 0 {Wd} {Hd}">']
    for i, (lab, txt, mag, col, lcol) in enumerate(rows):
        y = rh * i
        s.append(f'<text x="{x0}" y="{y + fs:.0f}" font-size="{fs}" font-weight="700" fill="{lcol}">{lab}</text>')
        bw = max(abs(mag) / vmax * (x1 - x0), 6)
        by = y + fs + 14
        bh = min(rh - fs - 34, 64)
        s.append(f'<rect x="{x0}" y="{by:.0f}" width="{bw:.1f}" height="{bh:.0f}" rx="8" fill="{col}"/>')
        s.append(f'<text x="{x0 + bw + 18:.1f}" y="{by + bh / 2 + fs * 0.42:.0f}" font-size="{fs * 1.3:.0f}" '
                 f'font-weight="900" fill="{col}">{txt}</text>')
    s.append('</svg>')
    return ''.join(s)


def rbars(rows, Wd=CW, Hd=330, fs=34):
    """Average R before costs on a -1R..+1R axis (so tiny bars look as tiny as they are)."""
    x = lambda v: 40 + (v + 1) / 2 * (Wd - 80)
    n = len(rows)
    top, bot = 10, 60
    rh = (Hd - top - bot) / n
    s = [f'<svg width="{Wd}" height="{Hd}" viewBox="0 0 {Wd} {Hd}">']
    for t, lab in [(-1, f'{M}1R'), (-.5, f'{M}0.5R'), (0, '0R'), (.5, '+0.5R'), (1, '+1R')]:
        s.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top}" y2="{Hd - bot}" stroke="#ffffff22" stroke-width="2"/>')
        s.append(f'<text x="{x(t):.1f}" y="{Hd - bot + 40}" text-anchor="middle" font-size="28" fill="{MUTED}">{lab}</text>')
    for i, (lab, v, txt, col) in enumerate(rows):
        cy = top + rh * (i + .5)
        xa, xb = sorted([x(0), x(v)])
        s.append(f'<rect x="{xa:.1f}" y="{cy - 30:.1f}" width="{max(xb - xa, 6):.1f}" height="60" rx="6" fill="{col}"/>')
        s.append(f'<text x="{x(0) - 24:.1f}" y="{cy + fs * .38:.1f}" text-anchor="end" font-size="{fs}" font-weight="700" fill="{TEXT}">{lab}</text>')
        s.append(f'<text x="{x(0) + 28:.1f}" y="{cy + fs * .45:.1f}" font-size="{fs * 1.3:.0f}" font-weight="900" fill="{col}">{txt}</text>')
    s.append(f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{top - 6}" y2="{Hd - bot + 6}" stroke="{TEXT}" stroke-width="3"/></svg>')
    return ''.join(s)


def grid(qs, reveal=44):
    return B.qgrid(qs, CW, 330, 'L', reveal=reveal, fs=26, values=False)


def years_svg(ys, Wd=CW, Hd=340):
    lm, top, bot = 110, 50, 10
    vmin = -0.08
    y = lambda v: top + v / vmin * (Hd - top - bot)
    slot = (Wd - lm) / len(ys)
    s = [f'<svg width="{Wd}" height="{Hd}" viewBox="0 0 {Wd} {Hd}">']
    for t in (-0.02, -0.04, -0.06, -0.08):
        s.append(f'<line x1="{lm}" x2="{Wd}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="#ffffff1c" stroke-width="2"/>')
        s.append(f'<text x="{lm - 14}" y="{y(t) + 9:.1f}" text-anchor="end" font-size="26" fill="{MUTED}">{M}{abs(t):.2f}%</text>')
    for i, (yr, v) in enumerate(ys):
        cx = lm + slot * (i + .5)
        s.append(f'<rect x="{cx - slot * .32:.1f}" y="{y(0):.1f}" width="{slot * .64:.1f}" height="{y(float(v)) - y(0):.1f}" rx="5" fill="{RED}"/>')
        s.append(f'<text x="{cx:.1f}" y="{top - 14}" text-anchor="middle" font-size="25" font-weight="700" fill="{TEXT}">&#8217;{yr[2:]}</text>')
    s.append(f'<line x1="{lm}" x2="{Wd}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{TEXT}" stroke-width="3"/></svg>')
    return ''.join(s)


def judas_svg(Wd=CW, Hd=400):
    """Illustration: yesterday's high, first hour pokes above it and closes back inside -> trade against it."""
    yday = [(94, 96, 93.5, 95.6), (95.6, 98.2, 95, 97.6), (97.6, 100, 97, 98.6), (98.6, 99.2, 96.8, 97.4)]
    today = [(97.6, 101.9, 97.2, 98.8), (98.8, 99.1, 96.2, 96.5), (96.5, 97, 94.2, 94.6), (94.6, 95.1, 92.4, 92.8)]
    cp = B.CandlePlot(20, 70, Wd - 40, Hd - 90, 9, 92, 102.6, cw=0.55)
    s = [f'<svg width="{Wd}" height="{Hd}" viewBox="0 0 {Wd} {Hd}">{B.ARROW_DEFS}']
    ly = cp.py(100)
    s.append(f'<line x1="10" x2="{Wd - 10}" y1="{ly:.1f}" y2="{ly:.1f}" stroke="{BLUE}" stroke-width="4" stroke-dasharray="16 10"/>')
    s.append(f'<text x="14" y="{ly - 16:.1f}" font-size="28" font-weight="700" fill="{BLUE}">yesterday&#8217;s high</text>')
    dx = cp.px(4)
    s.append(f'<line x1="{dx:.1f}" x2="{dx:.1f}" y1="60" y2="{Hd - 10}" stroke="#ffffff30" stroke-width="2" stroke-dasharray="6 8"/>')
    s.append(f'<text x="{cp.px(1.5):.1f}" y="{Hd - 4}" text-anchor="middle" font-size="26" fill="{MUTED}">yesterday</text>')
    s.append(f'<text x="{cp.px(6.5):.1f}" y="{Hd - 4}" text-anchor="middle" font-size="26" fill="{MUTED}">today (hourly)</text>')
    for i, c in enumerate(yday):
        s.append(cp.candle(i, *c, op=0.55))
    for i, c in enumerate(today):
        s.append(cp.candle(i + 5, *c, hl=(i == 0)))
    fx = cp.px(5)
    s.append(f'<text x="{fx:.1f}" y="{cp.py(101.9) - 26:.1f}" text-anchor="middle" font-size="32" font-weight="900" fill="{ACC}">fake-out</text>')
    s.append(f'<path d="M{cp.px(6) - 10:.1f},{cp.py(100.6):.1f} Q{cp.px(7.6):.1f},{cp.py(100.2):.1f} {cp.px(8) + 10:.1f},{cp.py(95.4):.1f}" '
             f'fill="none" stroke="{ACC}" stroke-width="6" marker-end="url(#ah)"/>')
    s.append(f'<text x="{cp.px(7.2):.1f}" y="{cp.py(101.6):.1f}" text-anchor="middle" font-size="28" font-weight="700" fill="{TEXT}">trade against it</text>')
    s.append('</svg>')
    return ''.join(s)


def cost_svg(with_cost, Wd=CW, Hd=370):
    lo, hi = float(MOVE[0]), float(MOVE[1])
    sc = (Wd - 40) / hi  # px per 1%
    x0, y0, bh = 10, 100, 110
    s = [f'<svg width="{Wd}" height="{Hd}" viewBox="0 0 {Wd} {Hd}">']
    s.append(f'<text x="{x0}" y="60" font-size="34" font-weight="700" fill="{TEXT}">A typical intraday move: '
             f'<tspan fill="{BLUE}" font-weight="900">{MOVE[0]}% to {MOVE[1]}%</tspan></text>')
    s.append(f'<rect x="{x0}" y="{y0}" width="{lo * sc:.0f}" height="{bh}" rx="8" fill="{BLUE}"/>')
    s.append(f'<rect x="{x0 + lo * sc:.0f}" y="{y0}" width="{(hi - lo) * sc:.0f}" height="{bh}" rx="8" fill="none" stroke="{BLUE}" stroke-width="4" stroke-dasharray="14 10"/>')
    s.append(f'<text x="{x0 + 20}" y="{y0 + bh / 2 + 14:.0f}" font-size="40" font-weight="900" fill="#1b2330">{MOVE[0]}%</text>')
    s.append(f'<text x="{x0 + hi * sc - 20:.0f}" y="{y0 + bh / 2 + 14:.0f}" text-anchor="end" font-size="40" font-weight="900" fill="{BLUE}">{MOVE[1]}%</text>')
    if with_cost:
        cx = x0 + lo * sc - ROUND_TRIP * sc
        s.append(f'<rect x="{cx:.1f}" y="{y0 - 18}" width="{ROUND_TRIP * sc:.1f}" height="{bh + 36}" fill="{RED}"/>')
        s.append(f'<text x="{cx + ROUND_TRIP * sc / 2:.1f}" y="{y0 + bh + 70}" text-anchor="middle" font-size="36" font-weight="900" '
                 f'fill="{RED}">costs: {ROUND_TRIP:.2f}% round trip</text>')
        s.append(f'<text x="{cx + ROUND_TRIP * sc / 2:.1f}" y="{y0 + bh + 112}" text-anchor="middle" font-size="28" '
                 f'fill="{MUTED}">{COST_EACH:.2f}% in + {COST_EACH:.2f}% out</text>')
    s.append('</svg>')
    return ''.join(s)


def tick_rows(rows):
    out = ''
    for mark, col, a, b in rows:
        out += (f'<div style="display:flex;align-items:center;gap:28px;margin:18px 0;width:780px">'
                f'<div style="font-size:84px;font-weight:900;color:{col};width:80px;text-align:center">{mark}</div>'
                f'<div style="text-align:left"><div style="font-size:46px;font-weight:900">{a}</div><div style="font-size:32px;color:{MUTED}">{b}</div></div></div>')
    return out


def build_cards():
    C = {}
    R = lambda lab, key, model: (lab, float(model[key]['r']), neg(model[key]['r']) + 'R', GREEN if float(model[key]['r']) > 0 else MUTED)
    C['trades'] = card('ICT Silver Bullet &middot; tested by the rules',
                       big(B.SB_TRADES, 'trades &middot; 10 years &middot; the 100 biggest US stocks'), SRC)
    C['sb_R'] = card('Before costs &middot; average result per trade',
                     rbars([R('Silver Bullet', PURE, sb), R('Coin flip', COIN, sb)]) +
                     '<div class="sub" style="margin-top:6px">1R = the amount risked on a trade</div>', SRC)
    C['sb_after'] = card(f'After {COST_EACH:.2f}% costs each way &middot; per trade',
                         mbars([('Silver Bullet', neg(sb[PURE]['after']), pct(sb[PURE]['after']), RED, TEXT),
                                ('Coin flip for the direction', neg(sb[COIN]['after']), pct(sb[COIN]['after']), '#a5524c', TEXT)], 0.08) +
                         f'<div class="sub" style="margin-top:4px">Both lose. ICT beat the coin by <b class="o">{EDGE:.3f}%</b> a trade.</div>', SRC)
    C['rules'] = card('What we tested',
                      '<div style="font-size:66px;font-weight:900;line-height:1.15;text-align:center">Fixed-rule version.<br>'
                      '<span class="o">Discretion not tested.</span></div>'
                      '<div class="sub" style="margin-top:26px">Community rules made precise, not a trader&#8217;s judgement</div>')
    C['rules_js'] = card('What we tested',
                         '<div style="font-size:70px;font-weight:900;line-height:1.15;text-align:center">Fixed rules.<br>'
                         '<span class="o">Not a trader&#8217;s judgement.</span></div>')
    for k, word in [('end_test', 'Full test on'), ('end_break', 'Full breakdown on'), ('end_video', 'Full video on')]:
        C[k] = card('Backtest Bench',
                    f'<div>{B.mark_svg(170)}</div><div style="font-size:48px;font-weight:700;margin-top:10px">{word}</div>'
                    '<div style="font-size:84px;font-weight:900;line-height:1.05">Backtest <span class="o">Bench</span></div>')
    gnote = f'{SRC} &middot; 2026 Q4 = Oct 1&ndash;26'
    C['grid_empty'] = card('ICT Silver Bullet &middot; every quarter, after costs', grid(D['sbq'], 0) +
                           '<div class="sub" style="margin-top:10px"><b class="o">44</b> quarters &middot; 2016&ndash;2026</div>', gnote)
    C['grid_sb'] = card('ICT Silver Bullet &middot; every quarter, after costs', grid(D['sbq']) +
                        f'<div class="sub" style="margin-top:10px;font-size:40px;font-weight:900;color:{TEXT}"><span class="r">{SB_RED}</span> losing &middot; '
                        f'<span class="g">{44 - SB_RED}</span> winning</div>', gnote)
    C['grid_js'] = card('Judas swing &middot; every quarter, after costs', grid(D['jsq']) +
                        f'<div class="sub" style="margin-top:10px;font-size:40px;font-weight:900;color:{TEXT}"><span class="r">{JS_RED}</span> of 44 quarters lost</div>', gnote)
    C['years'] = card('ICT Silver Bullet &middot; per trade after costs, by year', years_svg(D['sby']) +
                      f'<div class="sub" style="margin-top:6px;font-size:38px;font-weight:900;color:{TEXT}">Every year <span class="r">negative</span></div>',
                      f'{SRC} &middot; 2026 = Jan&ndash;Oct')
    C['random'] = card('Liquid stocks, intraday',
                       f'<div style="display:flex;align-items:center;gap:40px"><div>{B.coin(230)}</div>'
                       '<div style="font-size:72px;font-weight:900;line-height:1.1"><span class="o">Close to<br>random</span>'
                       '<div style="font-size:40px;color:#9fb0c6;margin-top:14px">once you count costs</div></div></div>')
    C['perfect'] = card('On social media', B.setup_svg(CW, 420, fs=32), 'Illustration, not real data')
    C['messy'] = card(f'Taken by the rules: <span style="color:{TEXT}">{B.SB_TRADES}</span> of them', B.messy_svg(CW, 420, 5, 3, seed=11),
                      'Illustration, not real data')
    C['hindsight'] = card('Picked after the fact',
                          '<div style="font-size:66px;font-weight:900;line-height:1.15;text-align:center">Always looks good.<br>'
                          '<span class="o">That&#8217;s hindsight,<br>not a strategy.</span></div>')
    C['measure'] = card('What a test like this can measure',
                        tick_rows([('&#10007;', MUTED, 'A trader&#8217;s discretion', 'Which setups they skip: not measured'),
                                   ('&#10003;', GREEN, 'The setups themselves', f'{B.SB_TRADES} of them, every one by the rules')]))
    C['judas_title'] = card('ICT&#8217;s other famous setup',
                            '<div style="font-size:120px;font-weight:900;line-height:1">Judas <span class="o">swing</span></div>'
                            '<div class="sub" style="margin-top:20px">hourly bars &middot; the first hour of the day</div>')
    C['judas_rule'] = card('Judas swing &middot; the rule', judas_svg(), 'Illustration, not real data')
    C['js_trades'] = card('Judas swing &middot; tested by the rules', big(B.JS_TRADES, 'trades &middot; 10 years'), SRC)
    C['js_R'] = card('Before costs &middot; average result per trade',
                     rbars([R('Judas swing', PURE, js), R('Coin flip', COIN, js)]) +
                     '<div class="sub" style="margin-top:6px">Zero edge before costs</div>', SRC)
    tf = lambda k: (neg(sb[k]['after']), pct(sb[k]['after']))
    C['rescue'] = card('Can it be rescued?',
                       f'<div class="sub" style="color:{TEXT}">ICT Silver Bullet, pure rules</div>' +
                       big(neg(sb[PURE]['after']), 'a trade, after costs', RED, 150), SRC)
    C['fix_trend'] = card('Fix 1 &middot; trend filter (higher-timeframe bias)',
                          tick_rows([('&#8593;', GREEN, 'Longs only above', 'the 50-day average'),
                                     ('&#8595;', RED, 'Shorts only below', 'the 50-day average')]))
    C['trend_res'] = card('Per trade, after costs',
                          mbars([('Pure ICT', *tf(PURE), RED, TEXT), ('+ trend filter', *tf(TREND), ACC, TEXT)], 0.07) +
                          f'<div class="sub" style="margin-top:4px">The filter made it <b class="r">worse</b></div>', SRC)
    C['fix_fin'] = card('Fix 2 &middot; quality filter',
                        tick_rows([('&#8593;', GREEN, 'Longs only', 'no shorts'),
                                   ('&#9733;', ACC, 'Top third by financials', 'high-quality companies')]))
    C['ladder'] = card('Per trade, after costs',
                       mbars([('Pure ICT', *tf(PURE), RED, MUTED), ('+ trend filter', *tf(TREND), RED, MUTED),
                              ('Long only, quality companies (best)', *tf(FINL), ACC, TEXT)], 0.07, Hd=380), SRC)
    C['least_bad'] = card('Best version we found',
                          big(neg(sb[FINL]['after']), 'a trade after costs &middot; <b class="o">least bad isn&#8217;t good</b>', RED, 150), SRC)
    C['why'] = card('Day trading the biggest stocks',
                    '<div style="font-size:100px;font-weight:900;line-height:1.05;text-align:center">Why is it<br>so <span class="o">hard?</span></div>')
    C['costs'] = card('Day trading the biggest stocks',
                      '<div style="font-size:150px;font-weight:900;color:#e5675c;letter-spacing:4px">COSTS</div>')
    C['move'] = card('Reason: costs', cost_svg(False), 'Source: Backtest Bench research (research/ICT.md)')
    C['move_cost'] = card('Reason: costs', cost_svg(True), 'Source: Backtest Bench research (research/ICT.md)')
    C['edge_cost'] = card('Per trade',
                          mbars([('ICT&#8217;s direction call (vs a coin flip)', f'{EDGE:.2f}%', EDGE, GREEN, TEXT),
                                 ('Round-trip cost', f'{ROUND_TRIP:.2f}%', ROUND_TRIP, RED, TEXT)], 0.07) +
                          f'<div class="sub" style="margin-top:4px">The edge is about <b class="o">a sixth</b> of the cost</div>', SRC)
    assert abs(EDGE / ROUND_TRIP - 1 / 6) < 0.01
    C['costs_win'] = card('Hundredths of a percent',
                          '<div style="font-size:120px;font-weight:900;line-height:1">Costs <span class="r">win.</span></div>')
    return C


# Which card shows from (paragraph, sentence) on - 1-based paragraph, 0-based sentence.
CARD_PLAN = {
    'short1': [((1, 0), 'trades'), ((2, 0), 'sb_R'), ((3, 0), 'sb_after'), ((4, 0), 'rules'), ((4, 1), 'end_test')],
    'short2': [((1, 0), 'grid_empty'), ((2, 0), 'grid_sb'), ((2, 2), 'years'), ((2, 3), 'grid_js'), ((2, 5), 'random'),
               ((2, 6), 'end_break')],
    'short3': [((1, 0), 'perfect'), ((2, 0), 'messy'), ((2, 1), 'sb_R'), ((2, 2), 'grid_sb'), ((2, 3), 'hindsight'),
               ((2, 4), 'measure'), ((2, 6), 'end_video')],
    'short4': [((1, 0), 'judas_title'), ((1, 1), 'judas_rule'), ((2, 0), 'js_trades'), ((3, 0), 'js_R'), ((3, 2), 'grid_js'),
               ((4, 0), 'rules_js'), ((4, 1), 'end_test')],
    'short5': [((1, 0), 'rescue'), ((1, 1), 'fix_trend'), ((2, 0), 'trend_res'), ((3, 0), 'fix_fin'), ((3, 1), 'ladder'),
               ((4, 1), 'least_bad')],
    'short6': [((1, 0), 'why'), ((1, 1), 'costs'), ((2, 0), 'move'), ((2, 1), 'move_cost'), ((3, 0), 'edge_cost'),
               ((4, 0), 'costs_win'), ((4, 1), 'end_test')],
}

# ---------------------------------------------------------------- timing
NARR = json.load(open(os.path.join(VOICE, 'narration.json'), encoding='utf-8'))
MOODS = json.load(open(os.path.join(VOICE, 'moods.json'), encoding='utf-8'))
SPLIT = re.compile(r'(?<=[.?!])\s+')
TALK = 0.15        # mouth open/closed every 0.15 s while a sentence is spoken
BOUNCE = 0.10      # 3 px up for 0.1 s on each mood change
MAX_CHARS = 58     # caption chunk budget (then the page shrinks 72 -> 56 px to fit 3 lines)


def probe(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]))


def split_chunk(s):
    if len(s) <= MAX_CHARS:
        return [s]
    mid = len(s) / 2
    best = None
    for m in re.finditer(r'(, | - |: |\? )', s):  # natural breaks first
        cut = m.end()
        if min(cut, len(s) - cut) >= 14 and (best is None or abs(cut - mid) < abs(best - mid)):
            best = cut
    if best is None or abs(best - mid) > len(s) * 0.3:
        spaces = [m.end() for m in re.finditer(' ', s)]
        best = min(spaces, key=lambda c: abs(c - mid))
    a, b = s[:best].rstrip(), s[best:].lstrip()
    if a.endswith(' -'):  # don't leave a dangling dash at a caption break
        a = a[:-2].rstrip()
    return split_chunk(a) + split_chunk(b)


def timeline(key):
    gap = probe(os.path.join(VOICE, 'audio', '_gap.mp3'))
    t, sents = 0.0, []
    for pi, text in enumerate(NARR[key], 1):
        dur = probe(os.path.join(VOICE, 'audio', f'{key}-{pi:02d}.mp3'))
        parts = SPLIT.split(text)
        mood = MOODS[key][pi - 1]
        moods = mood if isinstance(mood, list) else [mood] * len(parts)
        assert len(moods) == len(parts), (key, pi, len(moods), len(parts))
        pos = 0
        for si, sx in enumerate(parts):
            off = text.index(sx, pos)
            pos = off + len(sx)
            sents.append(dict(p=pi, s=si, text=sx, mood=moods[si], start=t + dur * off / len(text), pstart=t,
                              speech_end=t + dur, para_end=t + dur + gap))
        t += dur + gap
    total = t
    for i, s in enumerate(sents):
        nxt = sents[i + 1] if i + 1 < len(sents) else None
        same_para = nxt is not None and nxt['p'] == s['p']
        s['talk_end'] = nxt['start'] if same_para else s['speech_end']
        s['end'] = nxt['start'] if nxt else total
        plan = [c for (ps, c) in CARD_PLAN[key] if ps <= (s['p'], s['s'])]
        s['card'] = plan[-1]
        chunks, cpos, s['chunks'] = split_chunk(s['text']), 0, []
        for c in chunks:
            off = s['text'].index(c, cpos)
            cpos = off + len(c)
            s['chunks'].append(dict(text=c, start=s['start'] + (s['talk_end'] - s['start']) * off / len(s['text'])))
    return sents, total


HL = re.compile(r"(?:minus )?\d[\d,]*(?:\.\d+)?%?|\b(?:[Tt]en|[Ff]orty-four|[Ff]orty-two|[Tt]wo|[Tt]hirty-nine|zero|"
                r"one hundredth|half a percent|one percent|[Aa] sixth|hundredths)\b")


def caption_html(text):
    text = text.replace(' - ', ' – ').replace("'", '’')
    out, last = [], 0
    for m in HL.finditer(text):
        out.append(nowrap(text[last:m.start()]))
        out.append(f'<span class="o" style="white-space:nowrap">{html.escape(m.group(0))}</span>')
        last = m.end()
    out.append(nowrap(text[last:]))
    return ''.join(out)


def nowrap(t):
    """Keep hyphenated words (break-even, fake-out) on one line."""
    return re.sub(r'(\w+(?:-\w+)+)', r'<span style="white-space:nowrap">\1</span>', html.escape(t))


# Reaction timing (owner 2026-11-02): react more often, and never on the same frame as a slide change.
HOLD_MAX = 4.2      # a pose held longer than this gets ONE follow-up reaction (middle ground, owner 2026-11-02)
REACT_LAG = 0.6     # a mood change near a slide change waits this long after the slide
NEAR = 0.4          # "near" = within this many seconds
# follow-up reactions, tried in order; never the pose already showing or the next tagged one
FOLLOW = {'shocked': ['sceptical'], 'sceptical': ['thinking'], 'pleased': ['neutral'],
          'neutral': ['thinking'], 'thinking': ['neutral']}   # a follow-up settles the mood; 'pleased' only where tagged


def mood_events(sents, total):
    """Mood change times: the tagged moods (nudged off slide changes), plus follow-up reactions so no pose is held
    longer than about HOLD_MAX. Every event is a visible change."""
    cards = [s['start'] for i, s in enumerate(sents) if i == 0 or s['card'] != sents[i - 1]['card']]
    near_card = lambda t: next((c for c in cards if abs(t - c) < NEAR), None)
    tagged = []
    for s in sents:
        if tagged and tagged[-1][1] == s['mood']:
            continue
        t = s['start']
        c = near_card(t)
        if c is not None and t > 0.05:
            t = c + REACT_LAG
        tagged.append((t, s['mood']))
    tagged.append((total, None))
    out, used = [tagged[0]], {}
    for (t, m) in tagged[1:]:
        n_follow = 0
        while t - out[-1][0] > HOLD_MAX + 1.2 and n_follow < 2:   # at most two follow-ups per tagged mood
            n_follow += 1
            tt = out[-1][0] + HOLD_MAX
            c = near_card(tt)
            if c is not None:
                tt = c + REACT_LAG
            cur = out[-1][1]
            opts = [o for o in FOLLOW[cur] if o != m] or FOLLOW[cur]
            k = used.get(cur, 0) % len(opts)
            used[cur] = used.get(cur, 0) + 1
            if t - tt >= 1.2:
                out.append((tt, opts[k]))
        if m is not None and m != out[-1][1]:
            out.append((t, m))
    return out


def frame_states(sents, total):
    n = round(total * FPS)
    ev = mood_events(sents, total)
    states = []
    for f in range(n):
        t = f / FPS
        si = max(i for i, s in enumerate(sents) if s['start'] <= t + 1e-9)
        s = sents[si]
        ch = [c for c in s['chunks'] if c['start'] <= t + 1e-9][-1]
        mood = [m for (tm, m) in ev if tm <= t + 1e-9][-1]
        states.append((s['card'], ch['text'], mood, False, False))   # still image: no mouth, no bounce
    return states


# ---------------------------------------------------------------- page template
def template(cards):
    mark = B.mark_svg(120)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden}}
body{{background:{BG};color:{TEXT};font-family:'Lato','Carlito','DejaVu Sans',sans-serif;position:relative}}
.bg{{position:absolute;inset:0;background-image:linear-gradient(#ffffff08 2px,transparent 2px),linear-gradient(90deg,#ffffff08 2px,transparent 2px);background-size:80px 80px}}
#card{{position:absolute;left:60px;top:250px;width:880px;height:580px;background:#222c3b;border-radius:28px;padding:30px 40px 22px;display:flex;flex-direction:column}}
.ck{{font-size:28px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:{ACC};white-space:nowrap;overflow:hidden}}
.cb{{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}}
.cn{{font-size:22px;color:{MUTED};text-align:center}}
.big{{font-weight:900;line-height:1;letter-spacing:-3px}}
.sub{{font-size:34px;color:{MUTED};margin-top:14px;line-height:1.25}}
.o{{color:{ACC}}}.r{{color:{RED}}}.g{{color:{GREEN}}}.m{{color:{MUTED}}}
svg text{{font-family:'Lato','Carlito','DejaVu Sans',sans-serif}}
#capbox{{position:absolute;left:60px;top:850px;width:840px;height:250px;display:flex;align-items:center;justify-content:center}}
#cap{{font-weight:900;line-height:1.1;text-align:center;letter-spacing:-0.5px;color:{TEXT}}}
#av{{position:absolute;left:30px;top:1032px;width:600px;height:600px}}
#mark{{position:absolute;left:700px;top:1300px}}
#disc{{position:absolute;left:600px;top:1440px;width:320px;text-align:center;font-size:28px;line-height:1.25;color:{MUTED}}}
</style></head><body><div class="bg"></div>
<div id="card"></div><div id="capbox"><div id="cap"></div></div><div id="av"></div>
<div id="mark">{mark}</div><div id="disc">Educational,<br>not financial advice</div>
<script>
window.setState = function(s) {{
  document.getElementById('card').innerHTML = s.card;
  document.getElementById('av').innerHTML = s.avatar;
  document.getElementById('av').style.transform = s.bounce ? 'translateY(-3px)' : 'none';
  const cap = document.getElementById('cap');
  cap.innerHTML = s.caption;
  let fs = 72, lines = 0;
  for (; fs >= 56; fs -= 2) {{
    cap.style.fontSize = fs + 'px';
    lines = Math.round(cap.getBoundingClientRect().height / (fs * 1.1));
    if (lines <= 3 && cap.scrollWidth <= 840) break;
  }}
  const r = cap.getBoundingClientRect();
  const card = document.getElementById('card');
  const cardOver = card.scrollHeight > card.clientHeight + 1 || card.scrollWidth > card.clientWidth + 1;
  return {{fs: Math.max(fs, 56), lines: lines, overflow: lines > 3 || r.left < 60 || r.right > 900 || r.top < 250,
          cardOverflow: cardOver, box: [r.left, r.top, r.right, r.bottom]}};
}};
</script></body></html>"""


# ---------------------------------------------------------------- build one Short
def build_short(key, cards, notes):
    sents, total = timeline(key)
    states = frame_states(sents, total)
    d = os.path.join(BUILD, key)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    uniq = {}
    for st in states:
        if st not in uniq:
            uniq[st] = len(uniq)
    tpl = os.path.join(BUILD, 'frame.html')
    if not os.path.exists(tpl):
        open(tpl, 'w', encoding='utf-8').write(template(cards))
    job = dict(template=tpl, report=os.path.join(d, 'report.json'), states=[
        dict(png=os.path.join(d, f's{i:03d}.png'), card=cards[st[0]], caption=caption_html(st[1]),
             avatar=avatar_svg(st[2], st[3]), bounce=1 if st[4] else 0) for st, i in uniq.items()])
    jp = os.path.join(d, 'job.json')
    json.dump(job, open(jp, 'w'))
    subprocess.run(['node', os.path.join(HERE, 'render.js'), jp], check=True, cwd=HERE)
    report = json.load(open(job['report']))
    bad = [r for r in report if r['overflow'] or r['cardOverflow']]
    for r in bad:
        print('FIT PROBLEM', key, r)
    # run-length encode frames -> concat list (exact frame counts)
    runs = []
    for st in states:
        if runs and runs[-1][0] == st:
            runs[-1][1] += 1
        else:
            runs.append([st, 1])
    lst = os.path.join(d, 'concat.txt')
    with open(lst, 'w') as f:
        f.write('ffconcat version 1.0\n')
        for st, k in runs:
            f.write(f"file '{os.path.join(d, f's{uniq[st]:03d}.png')}'\nduration {k / FPS:.6f}\n")
        f.write(f"file '{os.path.join(d, f's{uniq[runs[-1][0]]:03d}.png')}'\n")
    out = os.path.join(HERE, key + '.mp4')
    nframes = len(states)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-i', os.path.join(VOICE, key + '.mp3'), '-map', '0:v', '-map', '1:a',
                    '-vf', f'fps={FPS},format=yuv420p', '-frames:v', str(nframes),
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-t', f'{total:.3f}', '-movflags', '+faststart', out], check=True)
    vdur = probe(out)
    audio = probe(os.path.join(VOICE, key + '.mp3'))
    print(f'{key}: {len(uniq)} stills, {nframes} frames, video {vdur:.3f}s, joined mp3 {audio:.3f}s, timeline {total:.3f}s')
    assert abs(vdur - audio) <= 0.1, (vdur, audio)
    # mood-change frames for the contact sheet (first non-bounce frame of each new mood)
    picks = []
    for i, s in enumerate(sents):
        if i == 0 or sents[i - 1]['mood'] != s['mood']:
            f = min(round((s['start'] + BOUNCE + 0.02) * FPS), nframes - 1)
            st = states[f]
            picks.append(dict(t=f / FPS, mood=s['mood'], png=os.path.join(d, f's{uniq[st]:03d}.png'), card=st[0]))
    notes[key] = dict(sents=sents, total=total, vdur=vdur, audio=audio, stills=len(uniq), picks=picks, fit=report)
    return picks


def contact_sheet(all_picks):
    rows = ''
    for key, picks in all_picks.items():
        cells = ''.join(f'<div class="c"><img src="file://{p["png"]}"><div class="l"><b>{p["mood"]}</b> {fmt_t(p["t"])}</div></div>'
                        for p in picks)
        rows += f'<div class="row"><div class="k">{key}</div>{cells}</div>'
    maxn = max(len(p) for p in all_picks.values())
    width = 140 + maxn * 196 + 40
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:#11161f;color:#f3f1ec;font-family:'Lato','Carlito',sans-serif;padding:20px;width:{width}px}}
.row{{display:flex;gap:12px;align-items:flex-start;margin-bottom:18px}}
.k{{width:120px;font-weight:900;font-size:26px;color:#ff8a3d;padding-top:20px}}
.c img{{width:184px;height:327px;display:block;border-radius:8px}}
.l{{font-size:18px;margin-top:4px;color:#9fb0c6}}.l b{{color:#f3f1ec}}
</style></head><body>{rows}</body></html>"""
    hp = os.path.join(BUILD, 'contact.html')
    open(hp, 'w', encoding='utf-8').write(page)
    js_ = os.path.join(BUILD, 'contact.js')
    open(js_, 'w').write(
        "const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();"
        f"const p=await b.newPage({{viewport:{{width:{width + 40},height:400}}}});await p.goto('file://{hp}');"
        f"await p.waitForLoadState('load');await p.screenshot({{path:'{os.path.join(HERE, 'contact_sheet.png')}',fullPage:true}});"
        "await b.close();})();")
    subprocess.run(['node', js_], check=True, cwd=HERE)


def fmt_t(s):
    return f'{int(s // 60)}:{s % 60:05.2f}'


CARD_DESC = {
    'trades': f'big number {B.SB_TRADES} trades, 10 years, 100 biggest US stocks',
    'sb_R': f'before costs, avg R: Silver Bullet {sb[PURE]["r"]}R vs coin flip {sb[COIN]["r"]}R on a -1R..+1R axis',
    'sb_after': f'after costs per trade: SB {sb[PURE]["after"]} vs coin {sb[COIN]["after"]}; ICT beat the coin by {EDGE:.3f}%',
    'rules': '"Fixed-rule version. Discretion not tested."', 'rules_js': '"Fixed rules. Not a trader\'s judgement."',
    'end_test': 'logo + "Full test on Backtest Bench"', 'end_break': 'logo + "Full breakdown on Backtest Bench"',
    'end_video': 'logo + "Full video on Backtest Bench"',
    'grid_empty': '44-quarter grid, outlines only (2016-2026)', 'grid_sb': f'Silver Bullet quarter grid: {SB_RED} red, {44 - SB_RED} green',
    'grid_js': f'Judas quarter grid: {JS_RED} of 44 red', 'years': 'Silver Bullet by year 2016-2026, all bars negative',
    'random': 'coin + "Close to random once you count costs"', 'perfect': 'flawless ICT setup chart (illustration)',
    'messy': f'15 rule-taken days, one perfect (illustration), "{B.SB_TRADES} of them"',
    'hindsight': '"Always looks good. That\'s hindsight, not a strategy."',
    'measure': 'x discretion not measured / check the setups measured',
    'judas_title': '"Judas swing" title, hourly bars', 'judas_rule': 'Judas rule diagram: first hour fakes past yesterday\'s high, closes back inside, trade against it (illustration)',
    'js_trades': f'big number {B.JS_TRADES} trades', 'js_R': f'before costs avg R: Judas {js[PURE]["r"]}R vs coin {js[COIN]["r"]}R',
    'rescue': f'"Can it be rescued?" pure SB {sb[PURE]["after"]} a trade after costs',
    'fix_trend': 'Fix 1: longs above / shorts below the 50-day average',
    'trend_res': f'bars: pure {sb[PURE]["after"]} vs + trend filter {sb[TREND]["after"]}',
    'fix_fin': 'Fix 2: longs only, top third by financials',
    'ladder': f'bars: pure {sb[PURE]["after"]}, trend {sb[TREND]["after"]}, long-only quality {sb[FINL]["after"]} (orange)',
    'least_bad': f'big {sb[FINL]["after"]} "least bad isn\'t good"', 'why': '"Why is it so hard?"', 'costs': 'big red COSTS',
    'move': f'typical intraday move bar {MOVE[0]}% to {MOVE[1]}%', 'move_cost': f'same + red {ROUND_TRIP:.2f}% round-trip slice ({COST_EACH:.2f}% each way)',
    'edge_cost': f'bars: direction call {EDGE:.2f}% vs round-trip cost {ROUND_TRIP:.2f}% ("a sixth")', 'costs_win': '"Costs win."',
}


def write_notes(notes):
    gap = probe(os.path.join(VOICE, 'audio', '_gap.mp3'))
    L = ['# EP01 Shorts v2 - edit notes', '',
         'Built by `build.py` in this folder (re-run after any audio, mood or narration change; nothing is typed by hand: timings from',
         f'ffprobe, numbers from research/output/ict_long.md and research/ICT.md). Draft only: not committed, not uploaded.', '',
         'Layout (1080x1920, 30 fps): card #222c3b at x 60-940 / y 250-830 (visual for the current part), caption at x 60-900 / '
         'y 850-1100 (72 px, shrinks to 56 px if needed, max 3 lines, key numbers orange), avatar "Up" (triangle 420 px tall, '
         'apex y 1110, bottom y 1530, centre x 330), logo mark + "Educational, not financial advice" right of it (y 1300-1510). '
         'Nothing below y 1530 (YouTube Shorts title/UI area).', '',
         f'Timing: paragraph slot = its mp3 duration + the probed gap ({gap:.4f} s). Sentence starts (split on `(?<=[.?!])\\s+`) and '
         'caption-chunk starts are estimated from character share, so they can be ~0.3-0.5 s off. Mouth alternates closed/open every '
         '0.15 s while a sentence is spoken (closed in the paragraph gap; shocked keeps its O-mouth); the avatar rises 3 px for 0.1 s on '
         'each mood change. No zoom anywhere.', '']
    for key in SHORTS:
        if key not in notes:
            continue
        n = notes[key]
        L += [f'## {key}.mp4 ({fmt_t(n["vdur"])}, video {n["vdur"]:.3f} s vs joined mp3 {n["audio"]:.3f} s; {n["stills"]} distinct stills)', '',
              '| start | mood | card | caption (sentence) |', '|---|---|---|---|']
        for s in n['sents']:
            mk = '' if s['s'] else f'**P{s["p"]}** '
            L.append(f'| {fmt_t(s["start"])} | {s["mood"]} | {s["card"]} | {mk}{s["text"].replace("|", "/")} |')
            for c in s['chunks'][1:]:
                L.append(f'| {fmt_t(c["start"])} | | | ~ caption continues: "{c["text"]}" |')
        used = []
        for s in n['sents']:
            if s['card'] not in used:
                used.append(s['card'])
        L += ['', 'Cards used: ' + '; '.join(f'`{c}` = {CARD_DESC[c]}' for c in used), '']
        fs = sorted({r['fs'] for r in n['fit']})
        L += [f'Caption font sizes used: {", ".join(map(str, fs))} px; fit problems: '
              f'{sum(1 for r in n["fit"] if r["overflow"] or r["cardOverflow"])}.', '']
    L += ['## Not done / to check', '',
          '- Lato is not installed here; text renders in Carlito (metric-compatible fallback in the brand font stack).',
          '- Sentence/caption cut points are character-share estimates, not forced alignment; nudge `CARD_PLAN` or `MAX_CHARS` if a cut lands early/late.',
          '- 2026 Q4 / 2026 in the grids and year bars are partial (data ends 2026-10-26); said in the card source line.',
          '- Charts of setups (perfect, messy, Judas rule) are illustrations, labelled on the card.',
          '- No music; hard cuts only.', '']
    open(os.path.join(HERE, 'EDIT_NOTES.md'), 'w', encoding='utf-8').write('\n'.join(L))


def main():
    args = sys.argv[1:]
    only = args[args.index('--only') + 1] if '--only' in args else None
    shutil.rmtree(BUILD, ignore_errors=True)
    os.makedirs(BUILD)
    cards = build_cards()
    notes, picks = {}, {}
    for key in SHORTS:
        if only and only != key:
            continue
        picks[key] = build_short(key, cards, notes)
    contact_sheet(picks)
    if not only:
        write_notes(notes)
    if '--keep-build' not in args:
        shutil.rmtree(BUILD, ignore_errors=True)


if __name__ == '__main__':
    main()
