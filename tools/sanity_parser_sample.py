#!/usr/bin/env python3
"""Sample-based parser sanity: re-fetch N EDB animations and confirm the shipped
glyph stroke counts still reproduce from the raw CreateJS timeline.

The full check (tools/sanity_parser.py) needs /tmp/edb_strokes which is not in git;
this samples the id map so the parser can still be validated after a fresh clone.
"""
import json
import os
import random
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edb_convert as parser  # noqa: E402
import edb_fetch as ef  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://www.edbchinese.hk/EmbziciwebRes/stkdemo_js/%s/%s'
SAMPLE = int(os.environ.get('CW_SAMPLE', '80'))
HDRS = {'User-Agent': 'Mozilla/5.0'}

idmap = json.load(open(os.path.join(ROOT, 'tools', 'edb_id_map.json')))['mapping']
chars = sorted(c for c in idmap if os.path.exists(
    os.path.join(ROOT, 'glyphs', '%x.json' % ord(c))))
random.seed(42)
sample = random.sample(chars, min(SAMPLE, len(chars)))

ok = bad = err = 0
fails = []
tmp = tempfile.mkdtemp(prefix='edb_sample_')
for ch in sample:
    url = BASE % (ef.folder_for(idmap[ch]), ef.idfile(idmap[ch]))
    path = os.path.join(tmp, ef.idfile(idmap[ch]))
    try:
        data = urllib.request.urlopen(urllib.request.Request(url, headers=HDRS),
                                      timeout=30).read()
        open(path, 'wb').write(data)
        strokes, label_n, _ = parser.parse_edb_js(path)
    except Exception as e:
        err += 1
        fails.append((ch, url, 'download/parse: %s' % str(e)[:50]))
        continue
    shipped = len(json.load(open(os.path.join(ROOT, 'glyphs', '%x.json' % ord(ch))))['s'])
    if len(strokes) == shipped and not (label_n and label_n > len(strokes)):
        ok += 1
    else:
        bad += 1
        fails.append((ch, url, 'parsed=%d shipped=%d label=%s'
                      % (len(strokes), shipped, label_n)))

print('sampled %d | match %d | mismatch %d | errors %d' % (len(sample), ok, bad, err))
for ch, url, why in fails[:12]:
    print('  ', ch, why)
sys.exit(1 if bad else 0)
