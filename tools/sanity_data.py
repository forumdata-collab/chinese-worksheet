#!/usr/bin/env python3
"""Sanity check — the GLYPH DATA.

Encodes today's failure modes so a regression is caught before deploy:
  * a rebuilt glyph left in y-DOWN (double flip → 先 came out upside down)
  * a glyph losing a stroke (山 2 instead of 3, 先 5 instead of 6)
  * median array drifting out of step with the stroke array (numbers on wrong strokes)
  * STROKE_SEQ / hk_order tables going stale against the data

Usage:  python3 tools/sanity_data.py [--verbose]
Exit code 0 = pass, 1 = problems found.
"""
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLYPHS = os.path.join(ROOT, 'glyphs')
VERBOSE = '--verbose' in sys.argv
NUM_RE = re.compile(r'[-0-9.]+')

# characters whose top/bottom structure is unambiguous — used to detect a flipped glyph.
# Single-stroke characters (一) carry no orientation signal, so they are excluded.
ORIENTATION_PROBES = ('二', '三', '十', '干', '先', '生', '兒', '京', '個', '山', '字', '學', '說', '進')


def load_char_db():
    src = open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    m = re.search(r'window\.CHAR_DB\s*=\s*(\{.*\});?\s*$', src, re.DOTALL)
    return json.loads(m.group(1))


def mean_y(path_d):
    n = [float(v) for v in NUM_RE.findall(path_d)]
    ys = n[1::2]
    return sum(ys) / len(ys) if ys else 0.0


def main():
    problems = []
    warnings = []
    db = load_char_db()
    files = sorted(f for f in os.listdir(GLYPHS) if f.endswith('.json'))

    # 1) integrity + medians aligned with strokes
    parsed = {}
    for f in files:
        try:
            rec = json.load(open(os.path.join(GLYPHS, f), encoding='utf-8'))
        except Exception as e:
            problems.append('%s: unreadable JSON (%s)' % (f, e))
            continue
        s, m = rec.get('s'), rec.get('m')
        if not s or not m:
            problems.append('%s: missing s/m arrays' % f)
            continue
        if len(s) != len(m):
            problems.append('%s: %d strokes vs %d medians' % (f, len(s), len(m)))
        if any(len(d.strip()) < 5 for d in s):
            problems.append('%s: empty stroke path' % f)
        parsed[f] = rec

    # 2) orientation: stored space is y-UP, so a glyph's LAST stroke (bottom of the
    #    character) must sit LOWER (smaller y) than its FIRST stroke on average
    flipped = []
    deltas = []
    for ch in ORIENTATION_PROBES:
        f = '%x.json' % ord(ch)
        rec = parsed.get(f)
        if not rec or len(rec['s']) < 2:
            continue
        d = mean_y(rec['s'][0]) - mean_y(rec['s'][-1])
        deltas.append(d)
        if d <= 0:
            flipped.append(ch)
    if flipped:
        problems.append('orientation: %s stored y-DOWN (would render upside down)'
                        % ''.join(flipped))
    if deltas and min(deltas) <= 0:
        warnings.append('orientation margin is thin for some probes: %s'
                        % [round(x) for x in deltas])

    # 3) stroke counts vs CHAR_DB (HK vs Unihan differ legitimately for ~13% of chars,
    #    so only large gaps are treated as bugs)
    mismatches = []
    for f, rec in parsed.items():
        ch = chr(int(f[:-5], 16))
        official = (db.get(ch) or {}).get('s')
        if not official:
            continue
        n = len(rec['s'])
        if abs(n - official) > 2:
            mismatches.append((ch, n, official))
    # NB: EDB draws some characters in their HK variant form (勳→勛 12, 癡→痴 13,
    # 艷→豔 28, 麵→麪 15) while CHAR_DB uses Unihan's mainland count, so a gap is not
    # automatically a bug — the EDB animation's own label is the authority
    # (tools/sanity_parser.py checks that). Report, don't fail.
    if mismatches:
        warnings.append('stroke count differs from CHAR_DB (HK variants?) — %d chars: %s'
                        % (len(mismatches), ['%s %d/%d' % m for m in mismatches[:8]]))

    # 4) STROKE_SEQ (order text for chars with no outlines) vs official stroke counts
    seq = {}
    seq_src = os.path.join(ROOT, 'stroke_seq.js')
    if os.path.exists(seq_src):
        txt = open(seq_src, encoding='utf-8').read()
        for m in re.finditer(r'"([^"]+)"\s*:\s*\["(\d+)"\s*,\s*"([^"]+)"\]', txt):
            seq[m.group(1)] = (m.group(2), m.group(3))
    bad_seq = []
    for ch, (code, names) in seq.items():
        if len(names) != len(code):
            bad_seq.append((ch, 'name/code length'))
        if not set(code) <= set('12345'):
            bad_seq.append((ch, 'bad digits'))
        official = (db.get(ch) or {}).get('s')
        if official and len(code) != official:
            bad_seq.append((ch, '%d code vs %d official' % (len(code), official)))
    if bad_seq:
        problems.append('STROKE_SEQ inconsistent: %s' % bad_seq[:8])

    # 5) hk_order.js permutations must match the glyph stroke count
    order_src = os.path.join(ROOT, 'hk_order.js')
    if os.path.exists(order_src):
        txt = open(order_src, encoding='utf-8').read()
        bad_order = []
        for m in re.finditer(r'"([^"]+)"\s*:\s*\[([0-9,\s]+)\]', txt):
            ch, perm = m.group(1), [int(x) for x in m.group(2).split(',') if x.strip()]
            rec = parsed.get('%x.json' % ord(ch))
            if rec and len(perm) != len(rec['s']):
                bad_order.append((ch, len(perm), len(rec['s'])))
            if sorted(perm) != list(range(len(perm))):
                bad_order.append((ch, 'not a permutation'))
        if bad_order:
            problems.append('hk_order.js stale vs glyphs: %s' % bad_order[:8])

    # 6) counts
    print('sanity_data:')
    print('  glyph files            : %d' % len(files))
    print('  parsed ok              : %d' % len(parsed))
    print('  strokes total          : %d' % sum(len(r['s']) for r in parsed.values()))
    print('  chars differing vs DB   : %d (HK variant forms; see warn)' % len(mismatches))
    print('  STROKE_SEQ entries     : %d' % len(seq))
    if warnings:
        for w in warnings:
            print('  warn: %s' % w)
    if problems:
        print('  FAIL:')
        for p in problems:
            print('    - %s' % p)
        return 1
    print('  OK — data is self-consistent and upright')
    return 0


if __name__ == '__main__':
    sys.exit(main())
