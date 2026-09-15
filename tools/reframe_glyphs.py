"""Re-frame glyph JSON into the Make Me a Hanzi 1024-space framing.

HanziWriter applies a FIXED transform (it assumes mmh data framing:
x 0..1024, character ink sitting where a font draws it), so EDB-native
coordinates render shifted/clipped (top cut off). Fix: per char, map our ink
bbox onto that char's hanzi-writer-data ink bbox (uniform scale + centre align).
Display is unaffected (the display SVG normalises by its own ink bbox).
"""
import json, os, re, sys, statistics
sys.path.insert(0, '/tmp')
from svgpathtools import parse_path
# --- work directory (all scratch data lives here; CW_WORK overrides) ---------
import os as _os
WORK = _os.environ.get('CW_WORK', '/tmp')
def wpath(*parts):
    return _os.path.join(WORK, *parts)



DIR = '/home/ubuntu/chinese-worksheet/glyphs'
HW_CACHE = wpath('hw_cache/')
PROG = wpath('reframe_done.json')
CMD_RE = re.compile(r'([MLQCHVAZ])([^MLQCHVAZ]*)')


def bbox_nums(paths):
    """Bbox from raw numbers (fast; control points included — fine for framing)."""
    x0 = y0 = 1e18
    x1 = y1 = -1e18
    for d in paths:
        for m in CMD_RE.finditer(d):
            cmd, args = m.group(1), m.group(2)
            if cmd == 'Z' or not args.strip():
                continue
            nums = [float(v) for v in args.replace(',', ' ').split()]
            for k in range(0, len(nums) - 1, 2):
                x0 = min(x0, nums[k]); x1 = max(x1, nums[k])
                y0 = min(y0, nums[k + 1]); y1 = max(y1, nums[k + 1])
    return x0, y0, x1, y1


def hw_bbox(ch):
    """True-geometry ink bbox of hanzi-writer-data for ch (y-up 1024 space)."""
    p = HW_CACHE + str(ord(ch)) + '.json'
    if not os.path.exists(p):
        return None
    hw = json.load(open(p))
    x0 = y0 = 1e18
    x1 = y1 = -1e18
    for d in hw['strokes']:
        b = parse_path(d).bbox()
        x0 = min(x0, b[0]); x1 = max(x1, b[1])
        y0 = min(y0, b[2]); y1 = max(y1, b[3])
    return x0, y0, x1, y1


def transform_path(d, s, tx, ty):
    out = []
    for m in CMD_RE.finditer(d):
        cmd, args = m.group(1), m.group(2)
        out.append(cmd)
        if cmd == 'Z' or not args.strip():
            continue
        nums = [float(v) for v in args.replace(',', ' ').split()]
        vals = []
        for k in range(0, len(nums) - 1, 2):
            vals.append(nums[k] * s + tx)
            vals.append(nums[k + 1] * s + ty)
        out.append(','.join(f'{v:.1f}' for v in vals))
    return ''.join(out)


# ---- global fallback framing from HW data (median of ink bboxes) ----
poses = []
for fn in os.listdir(HW_CACHE)[:600]:
    try:
        ch = chr(int(fn.split('.')[0]))
        bb = hw_bbox(ch)
        if bb:
            poses.append(bb)
    except Exception:
        pass
if poses:
    med_cx = statistics.median([(b[0] + b[2]) / 2 for b in poses])
    med_cy = statistics.median([(b[1] + b[3]) / 2 for b in poses])
    med_max = statistics.median([max(b[2] - b[0], b[3] - b[1]) for b in poses])
    print(f'HW framing reference: centre=({med_cx:.0f},{med_cy:.0f}) maxdim={med_max:.0f}', flush=True)
else:
    med_cx, med_cy, med_max = 512, 400, 830

done = set(json.load(open(PROG))) if os.path.exists(PROG) else set()
files = [f for f in os.listdir(DIR) if f.endswith('.json') and f not in done]
print('to reframe:', len(files), flush=True)

noHW = 0
for i, fn in enumerate(files):
    if i % 400 == 0:
        print(f'  {i}/{len(files)}', flush=True)
        json.dump(sorted(done), open(PROG, 'w'))
    p = os.path.join(DIR, fn)
    try:
        rec = json.load(open(p))
        ox0, oy0, ox1, oy1 = bbox_nums(rec['s'])
        ow = max(ox1 - ox0, 1e-6); oh = max(oy1 - oy0, 1e-6)
        ch = chr(int(fn.split('.')[0], 16))
        bb = hw_bbox(ch)
        if bb:
            hx0, hy0, hx1, hy1 = bb
            tw = hx1 - hx0; th = hy1 - hy0
            s = min(tw / ow, th / oh)
            tcx, tcy = (hx0 + hx1) / 2, (hy0 + hy1) / 2
        else:
            noHW += 1
            s = med_max / max(ow, oh)
            tcx, tcy = med_cx, med_cy
        ocx, ocy = (ox0 + ox1) / 2, (oy0 + oy1) / 2
        tx = tcx - ocx * s
        ty = tcy - ocy * s
        rec['s'] = [transform_path(d, s, tx, ty) for d in rec['s']]
        rec['m'] = [[[round(x * s + tx, 1), round(y * s + ty, 1)] for x, y in m] for m in rec['m']]
        json.dump(rec, open(p, 'w'), ensure_ascii=False, separators=(',', ':'))
        done.add(fn)
    except Exception as e:
        print('FAIL', fn, str(e)[:60], flush=True)

json.dump(sorted(done), open(PROG, 'w'))
print('reframed:', len(done), '| no-HW (used median framing):', noHW, flush=True)
