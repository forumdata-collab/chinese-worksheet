#!/usr/bin/env python3
"""Build glyphs/variants/*.json — the shapes used by the 直出異體字 option.

Many 正字/異體 pairs share one EDB animation, so the shipped glyphs are byte-identical
and typing either member draws the same (official) shape. For those chars the option
falls back to the character's own HanziWriter shape, so 峰 → 山在左, 稅 → 兌, …

Rules:
  * only chars whose glyph file is byte-identical to another char's (same EDB animation)
  * only when HanziWriter has data AND its stroke count == CHAR_DB.s (keeps the card's
    「N畫」, the stroke-number count and the stroke-order worksheet in sync)
  * the EDB glyph always stays as the default (option off)

Usage: python3 tools/build_variants.py [--dry-run]
"""
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = 'https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0/%s.json'
HDRS = {'User-Agent': 'Mozilla/5.0'}
DRY = '--dry-run' in sys.argv

src = open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
DB = json.loads(re.search(r'window\.CHAR_DB\s*=\s*(\{.*\});?\s*$', src, re.S).group(1))

groups = {}
for fn in os.listdir(os.path.join(ROOT, 'glyphs')):
    if not fn.endswith('.json'):
        continue
    raw = open(os.path.join(ROOT, 'glyphs', fn), 'rb').read()
    groups.setdefault(hashlib.sha256(raw).hexdigest(), []).append(chr(int(fn[:-5], 16)))
pairs = [g for g in groups.values() if len(g) > 1]
print('identical-glyph groups: %d → %s' % (len(pairs), ''.join(''.join(g) for g in pairs)))

# EDB／《常用字字形表》嘅香港正字：呢批字保留官方字形，唔應該被 HanziWriter 版本取代
HK_PRIMARY = set('兑卧囱媪悦户敍温税脱葱藴衞説醖鈎鋭閲裏牀峯')


def hw_data(ch):
    try:
        d = json.loads(urllib.request.urlopen(
            urllib.request.Request(HW % urllib.parse.quote(ch), headers=HDRS),
            timeout=30).read().decode('utf-8', 'replace'))
        return d.get('strokes') or [], d.get('medians') or []
    except Exception:
        return [], []


built, skipped = [], []
for group in pairs:
    for ch in group:
        hexs = '%x' % ord(ch)
        if ch not in DB:
            skipped.append((ch, 'CHAR_DB 冇呢個字'))
            continue
        if ch in HK_PRIMARY:
            vf = os.path.join(ROOT, 'glyphs', 'variants', '%s.json' % hexs)
            if os.path.exists(vf) and not DRY:
                os.remove(vf)
            skipped.append((ch, '香港正字，保留 EDB 字形'))
            continue
        strokes, medians = hw_data(ch)
        if not strokes or len(strokes) != len(medians):
            skipped.append((ch, 'HanziWriter 冇資料'))
            continue
        if len(strokes) != DB[ch]['s']:
            skipped.append((ch, 'HW %d 筆 ≠ DB %s 筆' % (len(strokes), DB[ch]['s'])))
            continue
        out = os.path.join(ROOT, 'glyphs', 'variants', '%s.json' % hexs)
        if not DRY:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            json.dump({'s': strokes, 'm': medians}, open(out, 'w'),
                      ensure_ascii=False, separators=(',', ':'))
        built.append(ch)

# --- keep the engine whitelist in sync ---------------------------------------
vdir = os.path.join(ROOT, 'glyphs', 'variants')
hexes = sorted(f[:-5] for f in os.listdir(vdir) if f.endswith('.json'))
engine_path = os.path.join(ROOT, 'glyph-engine.js')
engine = open(engine_path, encoding='utf-8').read()
new_const = 'const VARIANT_GLYPHS = { %s };' % ', '.join("'%s': 1" % h for h in hexes)
engine2 = re.sub(r'const VARIANT_GLYPHS = \{[^}]*\};', new_const, engine)
if engine2 != engine and not DRY:
    open(engine_path, 'w', encoding='utf-8').write(engine2)

print('\nbuilt  %d: %s' % (len(built), ''.join(built)))
print('skipped %d:' % len(skipped))
for ch, why in skipped:
    print('   %s — %s' % (ch, why))
print('\nvariants now: %d (%s)' % (len(hexes), ' '.join(hexes)))
print('engine whitelist:', new_const)
