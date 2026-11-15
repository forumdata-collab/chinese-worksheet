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
# 2026-11-13 獒：EDB 敖(U+6556) + EDB 犬(U+72AC) 拼合，來源仍係 EDB
# 2026-11-15 v2.35：菇/窿/蜒 為 EDB 新字形（用戶提供），一併加入；氳 屬 EDB 修訂（Edb.R）
HK_NEW_CHARS = '兑卧囱媪悦户敍温税脱葱藴衞説醖鈎鋭閲着絃愠枴氲蜕裏牀峯麪羣獒祕秘菇窿蜒'

# 字形由 EDB 動畫修訂（edb refined）而成：筆順按異體字原則核對，來源標 Edb.R 而非 EDB。
EDB_REVISED = {f'{ord(c):x}': c for c in '氳'}

# 2026-11-14 v232c：23 個 HanziWriter 通用字形（筆順／筆數已按 EDB 拆字核實修正）。
# 字形本身唔係 EDB／twpen，來源維持 HW——唔可以被下面嘅預設邏輯翻做 twpen。
HW_GLYPHS = frozenset(
    '5577 74e4 7934 7a70 7cbc 7ccd 89b7 9011 9036 9052 905b 9062 '
    '9083 9088 908b 9312 93a9 991a 9957 9a4a 9ab6 9b2e 9f10'.split()
)


def load_edb_chars():
    """EDB lexicon chars = edb_id_map keys + manually added HK 正字."""
    m = json.load(open(os.path.join(ROOT, 'tools', 'edb_id_map.json')))
    chars = set(m['mapping'].keys())
    chars.update(HK_NEW_CHARS)
    return chars


def main():
    edb_chars = load_edb_chars()
    glyphs = {}
    n_edb = n_twpen = n_hw = n_rev = 0
    for fn in sorted(os.listdir(GLYPHS)):
        if not fn.endswith('.json'):
            continue
        hexv = fn[:-5]
        ch = chr(int(hexv, 16))
        if hexv in HW_GLYPHS:
            glyphs[hexv] = 'HW'
            n_hw += 1
        elif hexv in EDB_REVISED:
            glyphs[hexv] = 'Edb.R'
            n_rev += 1
        elif ch in edb_chars:
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
            'Edb.R': {
                'name': 'EDB 字形修訂',
                'url': 'https://www.edbchinese.hk/lexlist_ch/',
                'verified': True,
                'note': 'EDB 字形修補（edb refined），筆順按異體字原則核對',
            },
            'HW': {
                'name': 'HanziWriter 通用字形（已按香港次序修正）',
                'url': 'https://github.com/chanind/hanzi-writer-data',
                'verified': True,
                'note': '字形來自 HanziWriter 通用數據，筆順／筆數已按香港教育局《香港小學學習字詞表》拆字核實修正；非 EDB 官方字形',
            },
        },
        'glyphs': glyphs,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rec, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'glyph_sources.json: {len(glyphs)} glyphs (EDB {n_edb} / twpen {n_twpen} / HW {n_hw} / Edb.R {n_rev})')


if __name__ == '__main__':
    main()
