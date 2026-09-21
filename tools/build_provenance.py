#!/usr/bin/env python3
"""Build per-character glyph provenance: glyphs/<hex>.json → source + verified.

Output: data/glyph_sources.json
  {
    "version": "...", "generated": "...",
    "sources": { "EDB": {...}, "twpen": {...} },
    "glyphs": { "<hex>": "EDB" | "twpen", ... }
  }

Source logic:
  * char in EDB lexicon (edb_id_map) → glyph extracted from EDB animation  → "EDB"
  * new HK-正字 added manually (copy/build from EDB, see HK_NEW_CHARS)     → "EDB"
  * otherwise (glyph reverse-engineered from twpen.com breakdown PNG)      → "twpen"

Verified: sanity suite (sanity_data/parser/geom/numbers) passes → both sources
are marked verified:true at the source level (no per-char flag needed yet).
"""
import json
import os
import re
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLYPHS = os.path.join(ROOT, 'glyphs')
OUT = os.path.join(ROOT, 'data', 'glyph_sources.json')

# 2026-09-21 手動補嘅 26 個香港正字（glyph 由 EDB 動畫 copy/build，唔喺 edb_id_map）
HK_NEW_CHARS = '兑卧囱媪悦户敍温税脱葱藴衞説醖鈎鋭閲着絃愠枴氲蜕裏牀'


def load_edb_chars():
    """EDB lexicon chars = edb_id_map keys + manually added HK 正字."""
    m = json.load(open(os.path.join(ROOT, 'tools', 'edb_id_map.json')))
    chars = set(m['mapping'].keys())
    chars.update(HK_NEW_CHARS)
    return chars


def main():
    edb_chars = load_edb_chars()
    glyphs = {}
    n_edb = n_twpen = 0
    for fn in sorted(os.listdir(GLYPHS)):
        if not fn.endswith('.json'):
            continue
        hexv = fn[:-5]
        ch = chr(int(hexv, 16))
        if ch in edb_chars:
            glyphs[hexv] = 'EDB'
            n_edb += 1
        else:
            glyphs[hexv] = 'twpen'
            n_twpen += 1

    rec = {
        'version': '1',
        'generated': date.today().isoformat(),
        'note': 'Per-character glyph source (shape + stroke order).',
        'sources': {
            'EDB': {
                'name': '香港教育局《香港小學學習字詞表》',
                'url': 'https://www.edbchinese.hk/lexlist_ch/',
                'verified': True,
                'note': '官方筆順動畫逆向提取',
            },
            'twpen': {
                'name': '台灣教育部筆順字典',
                'url': 'https://www.twpen.com/',
                'verified': True,
                'note': 'breakdown PNG 逆向（台灣標準，非香港）',
            },
        },
        'glyphs': glyphs,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rec, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'glyph_sources.json: {len(glyphs)} glyphs (EDB {n_edb} / twpen {n_twpen})')


if __name__ == '__main__':
    main()
