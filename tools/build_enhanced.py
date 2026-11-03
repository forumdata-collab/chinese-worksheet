#!/usr/bin/env python3
"""Build /enhanced/ preview page from the main index.html.

The enhanced page lives one directory down but reuses the shared assets
(data.js, glyphs/, fonts/, bgm/, caoni-bg.jpg) from the site root, so every
asset URL gets a ../ prefix and the glyph engine is pointed at ../glyphs/.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()

rep = [
    ('<link href="fonts/lxgw.css"', '<link href="../fonts/lxgw.css"'),
    ('<script src="data.js?', '<script src="../data.js?'),
    ('<script src="hk_order.js?', '<script src="../hk_order.js?'),
    ('<script src="stroke_seq.js?', '<script src="../stroke_seq.js?'),
    ('<script src="glyph-engine.js?', '<script src="../glyph-engine.js?'),
    ('src="bgm/bishun-song-v2.mp3"', 'src="../bgm/bishun-song-v2.mp3"'),
    ('<image href="caoni-bg.jpg"', '<image href="../caoni-bg.jpg"'),
]
for a, b in rep:
    if a not in src:
        sys.exit('missing anchor: ' + a)
    src = src.replace(a, b)

# glyph engine needs GLYPH_DIR + NS before it runs in a subdirectory
anchor = '<script src="../glyph-engine.js?'
assert src.count(anchor) == 1
src = src.replace(anchor,
    "<script>window.GLYPH_DIR='../glyphs/';window.NS='http://www.w3.org/2000/svg';</script>\n" + anchor)

# preview badge + title
src = src.replace('<title>中文筆順練習簿',
                  '<title>（enhanced 預覽）中文筆順練習簿', 1)
badge = '''<div id="enhBadge" class="no-print" style="position:fixed;left:12px;bottom:12px;z-index:9999;background:#1f2937;color:#fff;font-size:12px;padding:6px 10px;border-radius:999px;opacity:.85">
enhanced 預覽 · 文章抄寫紙 · <a href="../" style="color:#93c5fd">返回原版</a></div>
<style>@media print{#enhBadge{display:none!important}}</style>
'''
src = src.replace('</body>', badge + '</body>', 1)

out = os.path.join(ROOT, 'enhanced', 'index.html')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf-8').write(src)
print('built', out, len(src))
