#!/usr/bin/env python3
"""Sanity check — the EDB ANIMATION PARSER.

The 2026-09-15 bugs all came from mis-reading the EDB CreateJS timeline:
  * a number-label tween winning the same-delay merge and deleting a real stroke (山 2/3)
  * a label encoding the old regex missed (to({x:..,y:..,text:"3"},0))  (先 5/6)
  * trimming strokes because the label lagged behind the drawing
  * the "show-all" block being taken for a stroke, or an animation sub-shape being used
    instead of the final glyph geometry (個's bottom stroke)

This re-runs the parser against the raw animations (if /tmp/edb_strokes is present) and
checks three independent counts per character:
    chains : distinct ink shapes picked from the timeline
    label  : the number the animation itself displays
    db     : CHAR_DB (Unihan kTotalStrokes)
plus that the shipped glyph has exactly `chains` strokes.

Usage: python3 tools/sanity_parser.py [--verbose]
"""
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/tmp')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STROKES = '/tmp/edb_strokes'
VERBOSE = '--verbose' in sys.argv

try:
    import edb_convert_v12 as parser          # the shipped parser (tools/edb_convert.py)
except ImportError:
    try:
        import edb_convert as parser
    except ImportError:
        print('sanity_parser: SKIP — parser module not importable (tools/edb_convert.py)')
        sys.exit(0)


def main():
    if not os.path.isdir(STROKES):
        print('sanity_parser: SKIP — raw EDB animations not present at %s' % STROKES)
        print('  (fetch them with tools/edb_fetch.py before running this check)')
        return 0

    idmap = json.load(open(os.path.join(ROOT, 'tools', 'edb_id_map.json')))['mapping'] \
        if os.path.exists(os.path.join(ROOT, 'tools', 'edb_id_map.json')) \
        else json.load(open('/tmp/edb_id_map.json'))['mapping']

    db = parser.db_counts  # EDB id -> CHAR_DB 筆畫數
    label_diff, glyph_diff, missing = [], [], []
    checked = 0
    for ch, jid in idmap.items():
        fn = os.path.join(STROKES, '%04d.js' % jid)
        if not os.path.exists(fn):
            missing.append(ch)
            continue
        strokes, label_n, n_fin = parser.parse_edb_js(fn)
        checked += 1
        n = len(strokes)
        official = db.get(jid, 0)
        # the animation label may LAG the drawing (先 shows 1..5 for 6 strokes), so only
        # a label GREATER than the chain count is a hard error
        if label_n and label_n > n:
            label_diff.append((ch, n, label_n))
        if official and abs(n - official) > 2:
            glyph_diff.append((ch, n, official))
        gf = os.path.join(ROOT, 'glyphs', '%x.json' % ord(ch))
        if os.path.exists(gf):
            shipped = len(json.load(open(gf, encoding='utf-8'))['s'])
            if shipped != n:
                glyph_diff.append((ch, 'shipped %d vs parsed %d' % (shipped, n)))
    print('sanity_parser:')
    print('  animations checked      : %d of %d' % (checked, len(idmap)))
    print('  chain count < label     : %d  %s' % (len(label_diff), label_diff[:6] if VERBOSE else ''))
    print('  glyph/parse/db mismatch : %d  %s' % (len(glyph_diff), glyph_diff[:8]))
    print('  raw animation missing   : %d' % len(missing))
    problems = []
    if label_diff:
        problems.append('parser produced fewer strokes than the animation label: %s' % label_diff[:6])
    # shipped glyph must always equal the parser's own output
    hard = [g for g in glyph_diff if isinstance(g[1], str)]
    if hard:
        problems.append('shipped glyphs differ from a fresh parse: %s' % hard[:6])
    if missing:
        print('  (info) no raw animation for: %s' % ''.join(missing[:40]))
    if problems:
        print('  FAIL:')
        for p in problems:
            print('    - %s' % p)
        return 1
    print('  OK — parser and shipped glyphs agree with the animations')
    return 0


if __name__ == '__main__':
    sys.exit(main())
