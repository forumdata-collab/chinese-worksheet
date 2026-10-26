"""Audit: CHAR_DB chars without a local glyph — do they have HanziWriter data?
Chars with neither source have no stroke animation at all (button should be grey).
"""
import concurrent.futures as cf
import json
import os
import re
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = 'https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0/%s.json'

src = open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
db = json.loads(re.search(r'window\.CHAR_DB\s*=\s*(\{.*\});?\s*$', src, re.S).group(1))
have = {chr(int(os.path.basename(f)[:-5], 16)) for f in os.listdir(os.path.join(ROOT, 'glyphs'))
        if f.endswith('.json')}
missing = sorted(set(db) - have)
print('CHAR_DB %d | glyph %d | no-glyph %d' % (len(db), len(have), len(missing)))


def probe(ch):
    url = HW % urllib.parse.quote(ch)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode('utf-8', 'replace'))
            return ch, len(d.get('strokes') or []), len(d.get('medians') or [])
    except Exception as e:
        return ch, 0, str(e)[:40]


rows = []
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    for ch, n, m in ex.map(probe, missing):
        rows.append((ch, n if isinstance(n, int) else 0, m))

no_hw = [(c, n, m) for c, n, m in rows if not n]
mismatch = [(c, db[c].get('s'), n) for c, n, m in rows if n and db[c].get('s') != n]
print('有 HanziWriter 資料: %d | 完全冇筆順來源: %d' % (len(rows) - len(no_hw), len(no_hw)))
if no_hw:
    print('NO SOURCE (%d):' % len(no_hw), ' '.join(c for c, n, m in no_hw))
if mismatch:
    print('筆畫數唔一致 (%d):' % len(mismatch),
          ', '.join('%s DB=%s HW=%s' % (c, d, n) for c, d, n in mismatch[:30]))
json.dump({'no_hw': [c for c, n, m in no_hw],
           'stroke_mismatch': [{'ch': c, 'db': d, 'hw': n} for c, d, n in mismatch],
           'checked': len(rows)},
          open('/tmp/cw_hw_audit.json', 'w'), ensure_ascii=False)
print('→ /tmp/cw_hw_audit.json')
