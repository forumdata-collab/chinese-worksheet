#!/usr/bin/env python3
"""Full data-layer audit: CHAR_DB ↔ glyphs ↔ hk_order ↔ stroke_seq ↔ variants.

Checks (each prints a count and up to N offenders):
  1. glyph file whose char has no CHAR_DB entry (card would show no reading)
  2. CHAR_DB char with no glyph (falls back to HanziWriter/font)
  3. duplicate glyph content (identical JSON hash → same source animation, e.g. 正字/異體 pair)
  4. CHAR_DB stroke count vs glyph stroke count
  5. HK_ORDER keys without glyph / unknown chars
  6. STROKE_SEQ entries that already have a glyph (stale grey buttons)
  7. variants/ files whose base glyph or CHAR_DB entry is missing
  8. JSON structural integrity of every glyph (s/m lengths, closed paths)
"""
import glob
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT = 20


def load_char_db():
    src = open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    m = re.search(r'window\.CHAR_DB\s*=\s*(\{.*\});?\s*$', src, re.S)
    if not m:
        sys.exit('cannot locate CHAR_DB in data.js')
    return json.loads(m.group(1))


def load_js_map(name, var):
    path = os.path.join(ROOT, name)
    if not os.path.exists(path):
        return {}
    src = open(path, encoding='utf-8').read()
    m = re.search(var + r'\s*=\s*(\{.*\});?\s*$', src, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


def glyph_files(sub=''):
    return sorted(glob.glob(os.path.join(ROOT, 'glyphs', sub, '*.json')))


def main():
    db = load_char_db()
    order = load_js_map('hk_order.js', r'window\.HK_ORDER')
    seq = load_js_map('stroke_seq.js', r'window\.STROKE_SEQ')
    files = glyph_files()
    variants = glyph_files('variants')
    print('CHAR_DB %d | glyphs %d | variants %d | HK_ORDER %d | STROKE_SEQ %d'
          % (len(db), len(files), len(variants), len(order), len(seq)))

    by_char = {}
    bad_json = []
    for f in files + variants:
        hexs = os.path.basename(f)[:-5]
        try:
            rec = json.load(open(f, encoding='utf-8'))
        except Exception as e:
            bad_json.append((os.path.basename(f), str(e)[:60]))
            continue
        ch = chr(int(hexs, 16))
        by_char.setdefault(ch, f)
        s, m = rec.get('s') or [], rec.get('m') or []
        problems = []
        if not s:
            problems.append('no strokes')
        if len(m) != len(s):
            problems.append('m=%d s=%d' % (len(m), len(s)))
        for i, d in enumerate(s):
            if not d.lstrip().startswith('M'):
                problems.append('stroke %d not M-start' % (i + 1))
                break
            if 'Z' not in d.upper():
                problems.append('stroke %d not closed' % (i + 1))
                break
        if problems:
            bad_json.append(('%s (%s)' % (os.path.basename(f), ch), ', '.join(problems)))

    def report(title, items):
        print('\n%s: %d' % (title, len(items)))
        for x in items[:LIMIT]:
            print('   ', x)
        if len(items) > LIMIT:
            print('    … %d more' % (len(items) - LIMIT))

    report('1. glyph 但 CHAR_DB 冇呢個字', sorted(set(by_char) - set(db)))
    miss = sorted(set(db) - set(by_char))
    print('\n2. CHAR_DB 有字但冇 glyph（HanziWriter／字體後備）: %d' % len(miss))
    print('   ', ' '.join(miss[:LIMIT]), '…' if len(miss) > LIMIT else '')

    # 3. duplicate content
    hashes = {}
    for f in files:
        h = hashlib.sha256(open(f, 'rb').read()).hexdigest()[:16]
        hashes.setdefault(h, []).append(chr(int(os.path.basename(f)[:-5], 16)))
    dups = ['%s ← %s' % (''.join(v), h) for h, v in hashes.items() if len(v) > 1]
    report('3. 字形內容完全相同（同一動畫，多為正字／異體）', dups)

    # 4. stroke count mismatch
    mism = []
    for ch, f in by_char.items():
        if ch not in db:
            continue
        try:
            n = len(json.load(open(f, encoding='utf-8'))['s'])
        except Exception:
            continue
        if db[ch].get('s') != n:
            mism.append('%s DB=%s glyph=%d' % (ch, db[ch].get('s'), n))
    report('4. CHAR_DB 筆畫數 ≠ glyph 筆畫數', mism)

    # 5. HK_ORDER keys without glyph
    report('5. HK_ORDER 有字但冇 glyph', sorted(c for c in order if c not in by_char))

    # 6. STROKE_SEQ 已有 glyph（按鈕會繼續灰）
    report('6. STROKE_SEQ 已有 glyph（過時條目，會錯誤灰掉按鈕）',
           sorted(c for c in seq if c in by_char))

    # 7. variants integrity
    vbad = []
    for f in variants:
        ch = chr(int(os.path.basename(f)[:-5], 16))
        if ch not in by_char:
            vbad.append('%s：冇標準 glyph' % ch)
        if ch not in db:
            vbad.append('%s：CHAR_DB 冇讀音' % ch)
        try:
            n = len(json.load(open(f, encoding='utf-8'))['s'])
            if ch in db and db[ch].get('s') != n:
                vbad.append('%s：variants %d 筆 ≠ DB %s' % (ch, n, db[ch].get('s')))
        except Exception as e:
            vbad.append('%s：%s' % (ch, e))
    report('7. variants 字形問題', vbad)

    report('8. glyph JSON 結構問題', bad_json)

    total = sum(len(x) for x in [set(by_char) - set(db), dups, mism, bad_json, vbad])
    print('\nSUMMARY: hard issues = %d (正字/異體共用字形 = %d 組)'
          % (total, sum(1 for v in hashes.values() if len(v) > 1)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
