"""Build per-char HK glyph data: EDB official stroke outlines + skeleton medians.

Output: /home/ubuntu/chinese-worksheet/glyphs/<hex>.json
        {"s": [stroke path...], "m": [[[x,y],...] ...]}   (EDB 1080-space, y-down)
"""
import json, os, sys, time
sys.path.insert(0, '/tmp')
from edb_median import medians_for
from edb_stages import parse as parse_stages, centroid
# --- work directory (all scratch data lives here; CW_WORK overrides) ---------
import os as _os
WORK = _os.environ.get('CW_WORK', '/tmp')
def wpath(*parts):
    return _os.path.join(WORK, *parts)



EDB = json.load(open(wpath('edb_svg_strokes.json')))
IDMAP = json.load(open(wpath('edb_id_map.json')))['mapping']
STROKE_DIR = wpath('edb_strokes', '')
OUTDIR = '/home/ubuntu/chinese-worksheet/glyphs'
PROG = wpath('glyph_build_done.json')

os.makedirs(OUTDIR, exist_ok=True)

done = set()
if os.path.exists(PROG):
    done = set(json.load(open(PROG)))

chars = [c for c in EDB if c not in done]
print(f'to build: {len(chars)} of {len(EDB)}', flush=True)

t0 = time.time()
fails = []
for i, ch in enumerate(chars):
    if i % 100 == 0:
        print(f'  {i}/{len(chars)} ({time.time()-t0:.0f}s)', flush=True)
        json.dump(sorted(done), open(PROG, 'w'))
    try:
        strokes = EDB[ch]
        med = medians_for(strokes)
        # orient: first point nearest stage-1 centroid
        jid = IDMAP.get(ch)
        if jid is not None:
            try:
                stages = parse_stages(STROKE_DIR + f'{jid:04d}.js')
            except Exception:
                stages = []
            for si, st in enumerate(stages):
                if si >= len(med) or not med[si]:
                    continue
                c = centroid(st[0]['path'], st[0]['x'], st[0]['y'])
                if not c:
                    continue
                mx, my = c['cx'], c['cy']
                d0 = (med[si][0][0]-mx)**2 + (med[si][0][1]-my)**2
                d1 = (med[si][-1][0]-mx)**2 + (med[si][-1][1]-my)**2
                if d1 < d0:
                    med[si] = med[si][::-1]
        rec = {'s': [p.replace(' ', '') for p in strokes],
               'm': [[[round(x, 1), round(y, 1)] for x, y in m] for m in med]}
        with open(f'{OUTDIR}/{ord(ch):x}.json', 'w') as f:
            json.dump(rec, f, ensure_ascii=False, separators=(',', ':'))
        done.add(ch)
    except Exception as e:
        fails.append((ch, str(e)[:60]))

json.dump(sorted(done), open(PROG, 'w'))
print(f'DONE built {len(done)} | fails {len(fails)}', flush=True)
if fails:
    print('fails sample:', fails[:5], flush=True)
sz = sum(os.path.getsize(os.path.join(OUTDIR, f)) for f in os.listdir(OUTDIR))
print(f'total glyph dir size: {sz/1024/1024:.1f} MB, files {len(os.listdir(OUTDIR))}', flush=True)
