"""Retry the few chars whose page fetch failed, then write the site data file."""
import json, re, urllib.request, urllib.parse, time

UA = {'User-Agent': 'Mozilla/5.0 (research)'}
codes = json.load(open('/tmp/zdic_codes.json'))
gap = json.load(open('/tmp/gap.json'))
targets = list(dict.fromkeys(gap['no_data'] + list('咗喺佢冇咁哋攞冧嘅乜睇嘢咩呢噉嗰嚟嘥嘜嘞嘢')))
missing = [c for c in targets if c not in codes]
print('missing:', ''.join(missing))


def fetch_code(ch):
    url = 'https://www.zdic.net/hans/' + urllib.parse.quote(ch)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                html = r.read().decode('utf-8', errors='replace')
            for pat in (r'meta-value--mono">(\d{2,40})</span>',
                        r'笔顺编号[^<]*</span>\s*<span[^>]*>(\d{2,40})<',
                        r'笔顺编号.{0,120}?(\d{2,40})'):
                m = re.search(pat, html, re.DOTALL)
                if m and set(m.group(1)) <= set('12345'):
                    return ch, m.group(1)
        except Exception:
            time.sleep(2)
    return ch, None


for ch in missing:
    c, code = fetch_code(ch)
    if code:
        codes[c] = code
        print('  recovered %s = %s' % (c, code))
    else:
        print('  STILL MISSING', ch)

json.dump(codes, open('/tmp/zdic_codes.json', 'w'), ensure_ascii=False)
print('total codes:', len(codes))

NAMES = {'1': '橫', '2': '豎', '3': '撇', '4': '點', '5': '折'}
lines = ['// 通用筆順次序（逐筆類型）for characters with no EDB glyph and no HanziWriter data.',
         '// 1=橫 2=豎 3=撇 4=點 5=折 — source: 漢典 zdic.net 「笔顺编号」, length == official',
         '// stroke count (cross-checked against CHAR_DB 筆畫數 for all in-lexicon chars).',
         '// Used only to SHOW the writing order for chars that have no stroke outlines at all.',
         'window.STROKE_SEQ = {']
for ch in sorted(codes):
    code = codes[ch]
    seq = ''.join(NAMES[d] for d in code)
    lines.append('  %s: ["%s", "%s"],' % (json.dumps(ch, ensure_ascii=False), code, seq))
lines.append('};')
out = '/home/ubuntu/chinese-worksheet/stroke_seq.js'
open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('wrote', out)
print()
for ch in ['咗', '佢', '搵', '囍']:
    if ch in codes:
        print('  %s -> %s = %s' % (ch, codes[ch], ''.join(NAMES[d] for d in codes[ch])))
