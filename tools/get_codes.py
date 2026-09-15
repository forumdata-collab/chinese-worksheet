"""Extract zdic's 笔顺编号 for every char that has no stroke data, validating that its
length equals the character's official stroke count (CHAR_DB where available)."""
import json, re, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

UA = {'User-Agent': 'Mozilla/5.0 (research)'}
gap = json.load(open('/tmp/gap.json'))
colloquial = list('咗喺佢冇咁哋攞冧嘅乜睇嘢咩呢噉嗰嚟嘥嘜嘞嘢')
targets = list(dict.fromkeys(gap['no_data'] + colloquial))

# expected stroke counts: CHAR_DB has them for the in-lexicon chars
db = json.loads(re.search(r'window\.CHAR_DB\s*=\s*(\{.*\});?\s*$',
                          open('/home/ubuntu/chinese-worksheet/data.js', encoding='utf-8').read(),
                          re.DOTALL).group(1))


def code_for(ch):
    url = 'https://www.zdic.net/hans/' + urllib.parse.quote(ch)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            html = r.read().decode('utf-8', errors='replace')
    except Exception as e:
        return ch, None, 'fetch-fail'
    # two page layouts observed: mono meta row, and the generic meta-value row
    for pat in (r'meta-value--mono">(\d{2,40})</span>',
                r'笔顺编号[^<]*</span>\s*<span[^>]*>(\d{2,40})<',
                r'笔顺编号.{0,120}?(\d{2,40})'):
        m = re.search(pat, html, re.DOTALL)
        if m:
            break
    if not m:
        return ch, None, 'no-code'
    code = m.group(1)
    if not set(code) <= set('12345'):
        return ch, None, 'bad-charset:' + code[:12]
    return ch, code, 'ok'


with ThreadPoolExecutor(max_workers=6) as ex:
    res = list(ex.map(code_for, targets))

ok = {c: code for c, code, note in res if code}
bad = [(c, note) for c, code, note in res if not code]
print('targets      :', len(targets))
print('extracted    :', len(ok))
print('failed       :', len(bad), bad[:8])

mismatch = []
for ch, code in ok.items():
    exp = (db.get(ch) or {}).get('s')
    if exp and len(code) != exp:
        mismatch.append((ch, len(code), exp))
print('count vs CHAR_DB mismatches:', len(mismatch), mismatch[:10])

json.dump(ok, open('/tmp/zdic_codes.json', 'w'), ensure_ascii=False)
print()
for ch in '咗喺佢冇咁哋攞冧嘅乜睇嘢咩呢搵磡祂蜆蟶囍叄':
    print('   %s %s' % (ch, ok.get(ch, 'MISSING')))
