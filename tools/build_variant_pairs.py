#!/usr/bin/env python3
"""Build data/variant_pairs.json — the semantic layer behind the 字形雙軌呈現.

For every pair of chars whose glyph files are byte-identical (one EDB animation,
i.e. 同一個字的不同寫法), record:
    alts        the other member(s) the user might type
    standard    the member whose form the EDB animation draws (香港教育標準寫法)
    relation    '部件位置變體' | '同字異寫'
    own_glyph   whether glyphs/variants/<hex>.json exists (can we draw the typed form?)

The UI uses this to print 「字形：峯（標準）｜峰（另一寫法）」 instead of silently
showing a different shape, and to know when 「顯示我輸入的寫法」 cannot be honoured.
"""
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# EDB／《常用字字形表》代表字形（與 tools/build_variants.py 的白名單一致）
HK_PRIMARY = set('兑卧囱媪悦户敍温税脱葱藴衞説醖鈎鋭閲裏牀峯')
# 位置不同（部件左右↔上下）的組別，其餘一律「同字異寫」
POSITION_VARIANTS = {'峰', '峯', '群', '羣'}

groups = {}
for fn in os.listdir(os.path.join(ROOT, 'glyphs')):
    if not fn.endswith('.json'):
        continue
    raw = open(os.path.join(ROOT, 'glyphs', fn), 'rb').read()
    groups.setdefault(hashlib.sha256(raw).hexdigest(), []).append(
        chr(int(fn[:-5], 16)))

has_variant = {f[:-5] for f in os.listdir(os.path.join(ROOT, 'glyphs', 'variants'))
               if f.endswith('.json')}

pairs = {}
for members in groups.values():
    if len(members) < 2:
        continue
    primary = [c for c in members if c in HK_PRIMARY]
    standard = primary[0] if len(primary) == 1 else None
    relation = '部件位置變體' if any(c in POSITION_VARIANTS for c in members) else '同字異寫'
    for ch in members:
        pairs['%x' % ord(ch)] = {
            'char': ch,
            'alts': [c for c in members if c != ch],
            'standard': standard or members[0],
            'relation': relation,
            'own_glyph': ('%x' % ord(ch)) in has_variant,
        }

out = {
    'version': 1,
    'generated': '2026-10-26',
    'note': '同一字的另一寫法（字形檔案相同＝同一個 EDB 筆順動畫）。'
            'standard = EDB 動畫所畫的香港教育標準字形；own_glyph = 有冇該字自己的字形。',
    'pairs': pairs,
}
path = os.path.join(ROOT, 'data', 'variant_pairs.json')
json.dump(out, open(path, 'w'), ensure_ascii=False, indent=1)

print('pairs: %d chars in %d groups | own glyph: %d | missing: %s'
      % (len(pairs), len(groups), sum(1 for p in pairs.values() if p['own_glyph']),
         ''.join(p['char'] for p in pairs.values() if not p['own_glyph'])))
