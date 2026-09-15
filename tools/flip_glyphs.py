"""Convert glyph JSON from EDB-native y-DOWN to y-UP (font space).

hanzi-writer-data convention is y-UP (HanziWriter renders with scale(s,-s));
the display SVG applies `translate(0,C) scale(1,-1)` to bring it back. Storing
the raw EDB (y-down) paths made everything render upside down.

Flip:  y_up = C - y_down,  C = y0 + y1 (ink bbox in y-down space, so the flipped
data occupies the same numeric range and the browser's C = y0 + y1 still holds).
"""
import json, os, re, sys
# --- work directory (all scratch data lives here; CW_WORK overrides) ---------
import os as _os
WORK = _os.environ.get('CW_WORK', '/tmp')
def wpath(*parts):
    return _os.path.join(WORK, *parts)



DIR = '/home/ubuntu/chinese-worksheet/glyphs'
PROG = wpath('glyph_flip_done.json')

CMD_RE = re.compile(r'([MLQCHVAZ])([^MLQCHVAZ]*)')


def flip_path(d, C):
    out = []
    for m in CMD_RE.finditer(d):
        cmd, args = m.group(1), m.group(2)
        out.append(cmd)
        if cmd == 'Z' or not args.strip():
            continue
        nums = [float(x) for x in args.replace(',', ' ').split()]
        for k in range(0, len(nums) - 1, 2):
            nums[k + 1] = C - nums[k + 1]
        out.append(','.join(f'{v:g}' for v in nums))
    return ''.join(out)


def bbox_of(paths):
    x0 = y0 = 1e18
    x1 = y1 = -1e18
    for d in paths:
        for m in CMD_RE.finditer(d):
            cmd, args = m.group(1), m.group(2)
            if cmd == 'Z' or not args.strip():
                continue
            nums = [float(x) for x in args.replace(',', ' ').split()]
            for k in range(0, len(nums) - 1, 2):
                x0 = min(x0, nums[k]); x1 = max(x1, nums[k])
                y0 = min(y0, nums[k + 1]); y1 = max(y1, nums[k + 1])
    return x0, y0, x1, y1


done = set()
if os.path.exists(PROG):
    done = set(json.load(open(PROG)))

files = [f for f in os.listdir(DIR) if f.endswith('.json') and f not in done]
print('to flip:', len(files), 'of', len(os.listdir(DIR)), flush=True)

for i, fn in enumerate(files):
    if i % 400 == 0:
        print(f'  {i}/{len(files)}', flush=True)
        json.dump(sorted(done), open(PROG, 'w'))
    p = os.path.join(DIR, fn)
    try:
        rec = json.load(open(p))
        _, y0, _, y1 = bbox_of(rec['s'])
        C = y0 + y1
        rec['s'] = [flip_path(d, C) for d in rec['s']]
        rec['m'] = [[[round(x, 1), round(C - y, 1)] for x, y in m] for m in rec['m']]
        json.dump(rec, open(p, 'w'), ensure_ascii=False, separators=(',', ':'))
        done.add(fn)
    except Exception as e:
        print('FAIL', fn, str(e)[:60], flush=True)

json.dump(sorted(done), open(PROG, 'w'))
print('flipped:', len(done), flush=True)
