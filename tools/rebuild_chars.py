#!/usr/bin/env python3
"""Targeted EDB glyph rebuild for a specific char list (flip + reframe only).

WHY THIS EXISTS
===============
`flip_glyphs.py` / `reframe_glyphs.py` decide their work from a progress file
(`/tmp/glyph_flip_done.json`, `/tmp/reframe_done.json`). If those files are
missing or incomplete (e.g. /tmp was cleared, or the glyph came from a different
pipeline such as twpen), running them wholesale **re-flips and re-frames already
finished glyphs** → double scaling, broken geometry.

This script applies exactly the same two transforms as those tools, but only to
the characters you name:

    python3 tools/rebuild_chars.py 咩 効 嚐 揹 睇

Pipeline position: run AFTER `tools/build_glyphs.py` has produced fresh
EDB-native (y-DOWN) glyph files for those chars, and BEFORE deploying.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys

from svgpathtools import parse_path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLYPHS = os.path.join(ROOT, 'glyphs')
WORK = os.environ.get('CW_WORK', '/tmp')
HW_CACHE = os.path.join(WORK, 'hw_cache') + os.sep
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


def hw_reference():
    """Same fallback framing rule as reframe_glyphs.py: median HW ink pose."""
    poses = []
    if os.path.isdir(HW_CACHE):
        for fn in sorted(os.listdir(HW_CACHE))[:600]:
            if not fn.endswith('.json'):
                continue
            try:
                bb = hw_bbox(chr(int(fn.split('.')[0])))
                if bb:
                    poses.append(bb)
            except Exception:
                pass
    if not poses:
        return 512, 400, 830
    return (statistics.median([(b[0] + b[2]) / 2 for b in poses]),
            statistics.median([(b[1] + b[3]) / 2 for b in poses]),
            statistics.median([max(b[2] - b[0], b[3] - b[1]) for b in poses]))


def flip(rec):
    """y-DOWN (EDB native) → y-UP (font space), same as flip_glyphs.py."""
    x0, y0, x1, y1 = bbox_nums(rec['s'])
    C = y0 + y1
    out = []
    for d in rec['s']:
        parts = []
        for m in CMD_RE.finditer(d):
            cmd, args = m.group(1), m.group(2)
            parts.append(cmd)
            if cmd == 'Z' or not args.strip():
                continue
            nums = [float(v) for v in args.replace(',', ' ').split()]
            for k in range(0, len(nums) - 1, 2):
                nums[k + 1] = C - nums[k + 1]
            parts.append(','.join(f'{v:g}' for v in nums))
        out.append(''.join(parts))
    rec['s'] = out
    rec['m'] = [[[round(x, 1), round(C - y, 1)] for x, y in m] for m in rec['m']]
    return rec


def reframe(rec, ch, ref):
    """Map our ink bbox onto the HW framing, same as reframe_glyphs.py."""
    med_cx, med_cy, med_max = ref
    ox0, oy0, ox1, oy1 = bbox_nums(rec['s'])
    ow = max(ox1 - ox0, 1e-6); oh = max(oy1 - oy0, 1e-6)
    bb = hw_bbox(ch)
    if bb:
        hx0, hy0, hx1, hy1 = bb
        s = min((hx1 - hx0) / ow, (hy1 - hy0) / oh)
        tcx, tcy = (hx0 + hx1) / 2, (hy0 + hy1) / 2
    else:
        s = med_max / max(ow, oh)
        tcx, tcy = med_cx, med_cy
    ocx, ocy = (ox0 + ox1) / 2, (oy0 + oy1) / 2
    tx = tcx - ocx * s
    ty = tcy - ocy * s
    rec['s'] = [transform_path(d, s, tx, ty) for d in rec['s']]
    rec['m'] = [[[round(x * s + tx, 1), round(y * s + ty, 1)] for x, y in m] for m in rec['m']]
    return rec, ('HW' if bb else 'median')


def main():
    chars = [c for c in sys.argv[1:] if c]
    if not chars:
        print('usage: rebuild_chars.py 字 [字 ...]'); return 1
    ref = hw_reference()
    print(f'HW framing reference: centre=({ref[0]:.0f},{ref[1]:.0f}) maxdim={ref[2]:.0f}')
    for ch in chars:
        p = os.path.join(GLYPHS, f'{ord(ch):x}.json')
        if not os.path.exists(p):
            print(f'  ⚠️ {ch}: no glyph file, skip'); continue
        rec = json.load(open(p, encoding='utf-8'))
        before = len(rec['m'])
        rec = flip(rec)
        rec, how = reframe(rec, ch, ref)
        json.dump(rec, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        xs = [pt[0] for m in rec['m'] for pt in m]
        ys = [pt[1] for m in rec['m'] for pt in m]
        print(f'  ✅ {ch}: {before} strokes | framing={how} | median bbox x {min(xs):.0f}-{max(xs):.0f} y {min(ys):.0f}-{max(ys):.0f}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
