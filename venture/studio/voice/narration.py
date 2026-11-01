"""Pull the spoken words out of a script (drops headings, [VISUAL] cues, notes) into numbered paragraphs.
Usage: python narration.py ../EP01_SCRIPT.md ep01   -> ep01/narration.json (+ .txt to read)"""
import json, os, re, sys
src, out = sys.argv[1], sys.argv[2]
text = open(src, encoding='utf-8').read()
def section(start, end=None):
    s = text.split(start, 1)[1]
    return s.split(end, 1)[0] if end else s
parts = {'long': section('## FULL SCRIPT', '## CHART LIST')}
shorts = section('## SHORTS', '## YOUTUBE METADATA')
for i, chunk in enumerate(re.split(r'\n### ', shorts)[1:], 1):
    parts[f'short{i}'] = chunk.split('\n', 1)[1]

def clean(block):
    block = re.sub(r'\[VISUAL.*?\]', '', block, flags=re.S)
    paras = []
    for p in re.split(r'\n\s*\n', block):
        p = '\n'.join(l for l in p.splitlines() if not re.match(r'\s*(#|\[VISUAL|\*\*?\[|---|\|)', l))
        p = re.sub(r'\[VISUAL[^\]]*\]', '', p)
        p = re.sub(r'\*|__|`', '', p).replace('−', '-').strip()
        p = re.sub(r'\s+', ' ', p)
        if p and not p.lower().startswith(('on-screen', 'disclaimer strip', 'note:')):
            paras.append(p)
    return paras
os.makedirs(out, exist_ok=True)
data = {k: clean(v) for k, v in parts.items()}
json.dump(data, open(f'{out}/narration.json', 'w'), indent=1, ensure_ascii=False)
with open(f'{out}/narration.txt', 'w') as f:
    for k, ps in data.items():
        f.write(f'== {k} ==\n')
        for i, p in enumerate(ps, 1): f.write(f'[{k}-{i:02d}] {p}\n\n')
for k, ps in data.items(): print(k, len(ps), 'paragraphs', sum(len(p) for p in ps), 'chars')
