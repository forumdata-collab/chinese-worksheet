"""Extract per-stroke stage centroids from EDB JS (stage 1 = pen start region)."""
import re, json, os, sys
sys.path.insert(0, '/tmp')
from createjs_decode import decode_createjs_path
from PIL import Image, ImageDraw
import numpy as np
# --- work directory (all scratch data lives here; CW_WORK overrides) ---------
import os as _os
WORK = _os.environ.get('CW_WORK', '/tmp')
def wpath(*parts):
    return _os.path.join(WORK, *parts)



STROKE_DIR = wpath('edb_strokes', '')
IDMAP = json.load(open(wpath('edb_id_map.json')))['mapping']

SHAPE_RE = re.compile(r'this\.(\w+)\.graphics\.f\("#([0-9A-Fa-f]{6})"\)\.s\(\)\.p\("([^"]*)"\);')
XFORM_RE = re.compile(r'this\.(\w+)\.setTransform\(([^)]+)\)')


def parse(path):
    js = open(path, encoding='utf-8', errors='replace').read()
    shapes = {}
    for m in SHAPE_RE.finditer(js):
        shapes.setdefault(m.group(1), {'color': m.group(2), 'path': m.group(3)})
    for m in XFORM_RE.finditer(js):
        vals = [float(x) for x in m.group(2).split(',')]
        if m.group(1) in shapes:
            shapes[m.group(1)]['x'] = vals[0]
            shapes[m.group(1)]['y'] = vals[1]

    groups = []   # list of {delay, names}
    pat_a = re.compile(r'addTween\(cjs\.Tween\.get\(\{\}\)\.to\(\{state:\[\]\}\)'
                       r'((?:\.to\(\{state:\[\{t:this\.(\w+)\}\]\},\d+\))+)(?:\.wait\(\d+\))?')
    for m in pat_a.finditer(js):
        steps = re.findall(r'\.to\(\{state:\[\{t:this\.(\w+)\}\]\},(\d+)\)', m.group(1))
        if steps:
            groups.append({'delay': int(steps[0][1]), 'names': [s[0] for s in steps]})
    pat_b = re.compile(r'addTween\(cjs\.Tween\.get\(this\.(\w+)\)\.wait\((\d+)\)\.to\(\{_off:false\}')
    for m in pat_b.finditer(js):
        groups.append({'delay': int(m.group(2)), 'names': [m.group(1)]})
    groups.sort(key=lambda g: g['delay'])

    out = []
    for g in groups:
        names = [n for n in g['names'] if shapes.get(n, {}).get('color') == '000000']
        if not names:
            continue
        stages = []
        for n in names:
            s = shapes[n]
            stages.append({'path': s['path'], 'x': s.get('x', 0), 'y': s.get('y', 0)})
        out.append(stages)
    return out


def centroid(path, x, y, n=64):
    """Ink centroid + bbox of one CreateJS shape, mapped to a unit square (0..1)."""
    cmds = decode_createjs_path(path)
    pts = []
    for cmd in cmds:
        if cmd[0] == 'Z':
            continue
        for i in range(0, len(cmd) - 1, 2):
            pts.append((x + cmd[i + 1], y + cmd[i + 2]))
    if len(pts) < 3:
        return None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, x1 = min(xs), max(xs); y0, y1 = min(ys), max(ys)
    sc = (n - 1) / max(x1 - x0, y1 - y0, 1e-6)
    img = Image.new('1', (n, n), 0)
    dr = ImageDraw.Draw(img)
    dr.polygon([((px - x0) * sc, (py - y0) * sc) for px, py in pts], fill=1)
    arr = np.array(img, dtype=bool)
    if arr.sum() == 0:
        return None
    rows, cols = np.nonzero(arr)
    cx = cols.mean() / sc + x0
    cy = rows.mean() / sc + y0
    return {'cx': cx, 'cy': cy, 'x0': x0, 'x1': x1, 'y0': y0, 'y1': y1}


if __name__ == '__main__':
    ch = '\u8239'
    jid = IDMAP[ch]
    stages = parse(STROKE_DIR + f'{jid:04d}.js')
    print(f'{ch}: {len(stages)} strokes')
    for i, st in enumerate(stages):
        cs = [centroid(s['path'], s['x'], s['y']) for s in st]
        first = cs[0] if cs else None
        print(f'  #{i+1}: {len(st)} stages; stage1 centroid=({first["cx"]:.0f},{first["cy"]:.0f})' if first else f'  #{i+1}: no centroid')
