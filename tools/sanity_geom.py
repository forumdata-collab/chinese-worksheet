#!/usr/bin/env python3
"""Sanity check — GEOMETRY staleness of deployed glyphs vs a fresh parse.

sanity_parser.py only compares stroke COUNTS; a glyph built from an older parser
run can carry the right count but wrong geometry and pass silently (兒 st1 was a
25x40 stale fragment vs the correct 257x211 撇; 兔/兗/兜/兢 likewise).

This re-runs parse_edb_js() on every raw EDB animation, pushes each stroke through
the full shipped transform chain (strip spaces -> y-flip -> HW reframe) and
compares the result path-for-path against glyphs/<hex>.json.

    python3 tools/sanity_geom.py [--threshold N]

Threshold: max coordinate delta (any axis, any point) above which a char is
"stale".  Default 0.3 — below that is sub-pixel rounding noise (756 chars sit
in 0..0.3 and are fine).

Needs: /tmp/edb_strokes/*.js (raw animations), /tmp/hw_cache/*.json,
/tmp/edb_id_map.json, svgpathtools.
"""
import json, os, re, sys, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/tmp')
from edb_convert import parse_edb_js, group_to_svg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'glyphs')
STROKES = '/tmp/edb_strokes'
HW_CACHE = '/tmp/hw_cache'
IDMAP = '/tmp/edb_id_map.json'
THRESHOLD = float(sys.argv[sys.argv.index('--threshold') + 1]) if '--threshold' in sys.argv else 0.3

CMD_RE = re.compile(r'([MLQCHVAZ])([^MLQCHVAZ]*)')


def bbox_nums(paths):
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


def hw_bbox(ch):
    p = os.path.join(HW_CACHE, str(ord(ch)) + '.json')
    if not os.path.exists(p):
        return None
    import svgpathtools
    hw = json.load(open(p))
    x0 = y0 = 1e18
    x1 = y1 = -1e18
    for d in hw['strokes']:
        b = svgpathtools.parse_path(d).bbox()
        x0 = min(x0, b[0]); x1 = max(x1, b[1])
        y0 = min(y0, b[2]); y1 = max(y1, b[3])
    return x0, y0, x1, y1


def max_delta(a, b):
    na = re.findall(r'-?[\d.]+', a)
    nb = re.findall(r'-?[\d.]+', b)
    return max((abs(float(x) - float(y)) for x, y in zip(na, nb)), default=0.0)


def main():
    if not os.path.isdir(STROKES):
        print('sanity_geom: SKIP — raw EDB animations missing at %s' % STROKES)
        return 0
    idmap = json.load(open(IDMAP))['mapping']

    # global fallback framing from HW data (mirror of reframe_glyphs.py)
    poses = []
    for fn in os.listdir(HW_CACHE)[:600]:
        try:
            bb = hw_bbox(chr(int(fn.split('.')[0])))
            if bb:
                poses.append(bb)
        except Exception:
            pass
    med_cx = statistics.median([(b[0] + b[2]) / 2 for b in poses])
    med_cy = statistics.median([(b[1] + b[3]) / 2 for b in poses])
    med_max = statistics.median([max(b[2] - b[0], b[3] - b[1]) for b in poses])

    stale, subpixel, checked = [], 0, 0
    for ch, fid in idmap.items():
        fn = os.path.join(STROKES, '%04d.js' % fid)
        gf = os.path.join(DIR, '%x.json' % ord(ch))
        if not os.path.exists(fn) or not os.path.exists(gf):
            continue
        strokes, _ln, _nf = parse_edb_js(fn)
        shipped = json.load(open(gf))
        stripped = [p.replace(' ', '') for p in (group_to_svg(g) for g in strokes)]
        if len(stripped) != len(shipped['s']):
            stale.append((ch, 'count %d vs %d' % (len(stripped), len(shipped['s']))))
            continue
        _, y0, _, y1 = bbox_nums(stripped)
        C = y0 + y1
        flipped = [flip_path(d, C) for d in stripped]
        ox0, oy0, ox1, oy1 = bbox_nums(flipped)
        ow = max(ox1 - ox0, 1e-6); oh = max(oy1 - oy0, 1e-6)
        bb = hw_bbox(ch)
        if bb:
            s = min((bb[2] - bb[0]) / ow, (bb[3] - bb[1]) / oh)
            tcx, tcy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        else:
            s = med_max / max(ow, oh); tcx, tcy = med_cx, med_cy
        ocx, ocy = (ox0 + ox1) / 2, (oy0 + oy1) / 2
        tx = tcx - ocx * s; ty = tcy - ocy * s
        expected = [transform_path(d, s, tx, ty) for d in flipped]
        checked += 1
        if expected == shipped['s']:
            continue
        d = max(max_delta(a, b) for a, b in zip(expected, shipped['s']))
        if d > THRESHOLD:
            stale.append((ch, 'geom %.1f' % d))
        else:
            subpixel += 1

    print('sanity_geom:')
    print('  checked        : %d' % checked)
    print('  sub-pixel drift: %d (<=%s, fine)' % (subpixel, THRESHOLD))
    print('  STALE          : %d' % len(stale))
    for ch, why in stale:
        print('    %s: %s' % (ch, why))
    if stale:
        print('  FAIL — rebuild the stale chars (rebuild-only-changed flow, DEBUG.md §6)')
        return 1
    print('  OK — every deployed glyph matches a fresh parse through the full pipeline')
    return 0


if __name__ == '__main__':
    sys.exit(main())