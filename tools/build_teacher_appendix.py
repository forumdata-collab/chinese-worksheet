#!/usr/bin/env python3
"""Build the teacher appendix (docs/teacher-appendix.html + .csv).

載荷爭議資訊，令工作紙本身保持乾淨（語言學顧問建議 10）：
  * 同一字的另一寫法：香港教育標準／另一常見寫法／關係／本站示範／有沒有替代字形
  * 筆數：香港教育標準 vs 其他地區計法（只列有差異風險的字）
  * 字形來源（EDB／TW／HW）與筆順來源
  * 粵拼主讀／又讀、拼音、簡體
"""
import csv
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_char_db():
    src = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    return json.loads(re.search(r'window\.CHAR_DB\s*=\s*(\{.*\});?\s*$', src, re.S).group(1))


def load_js_map(name, var):
    path = os.path.join(ROOT, name)
    src = io.open(path, encoding='utf-8').read()
    m = re.search(var + r'\s*=\s*(\{.*\});?\s*$', src, re.S)
    return json.loads(m.group(1)) if m else {}


db = load_char_db()
sources = json.load(open(os.path.join(ROOT, 'data', 'glyph_sources.json')))['glyphs']
pairs = json.load(open(os.path.join(ROOT, 'data', 'variant_pairs.json')))['pairs']
hk_order = load_js_map('hk_order.js', r'window\.HK_ORDER')
try:
    stroke_seq = load_js_map('stroke_seq.js', r'window\.STROKE_SEQ')
except Exception:
    stroke_seq = {}
hw_audit = {}
if os.path.exists('/tmp/cw_hw_audit.json'):
    for row in json.load(open('/tmp/cw_hw_audit.json')).get('stroke_mismatch', []):
        hw_audit[row['ch']] = (row['db'], row['hw'])

# 香港筆數與其他計法不同的已知個案（字形筆數 vs Unihan／漢典）
REGION_NOTES = {}
try:
    for ch, (db_s, hw_s) in hw_audit.items():
        REGION_NOTES[ch] = '香港字形 %d 畫；部分字典依另一字形作 %d 畫' % (hw_s, db_s)
except Exception:
    pass
REGION_NOTES.setdefault('為', '香港字形 9 畫（火部）；部分字典依「爲」作 12 畫')
REGION_NOTES.setdefault('撝', '香港字形 12 畫（扌3＋為9）；部分字典依「爲」作 15 畫')
REGION_NOTES.setdefault('臺', '香港教育標準寫法為「台」（5 畫）；印刷常見「臺」（14 畫）')


def src_of(ch):
    hexs = '%x' % ord(ch)
    if hexs in sources:
        return sources[hexs]
    return 'HW' if ch in db else '—'


def label_src(s):
    return {'EDB': '香港教育局', 'twpen': '台灣教育部', 'HW': 'HanziWriter', '—': '—'}[s]


def order_src(ch):
    s = src_of(ch)
    if s == 'EDB':
        return 'EDB（教育局次序）'
    if s == 'twpen':
        return '台灣教育部（逆向）'
    if ch in stroke_seq:
        return '漢典筆順編號'
    return 'HanziWriter' + ('（已套香港次序）' if ch in hk_order else '')


rows = []
seen = set()

# 1) 同一字的另一寫法（42 字）
for hexs, info in sorted(pairs.items(), key=lambda kv: kv[1]['char']):
    ch = info['char']
    if ch in seen:
        continue
    seen.add(ch)
    d = db.get(ch, {})
    own = '有' if info['own_glyph'] else '暫無'
    rows.append({
        '輸入字': ch,
        '香港教育標準寫法': info['standard'],
        '對應寫法': ('／'.join(info['alts']) if ch == info['standard']
                      else info['standard']),
        '是否標準寫法': '是' if ch == info['standard'] else '否',
        '關係': info['relation'],
        '本站預設示範': info['standard'],
        '可切換成你的寫法': own,
        '筆數': d.get('s', ''),
        '筆數備註': REGION_NOTES.get(ch, ''),
        '字形來源': label_src(src_of(ch)),
        '筆順來源': order_src(ch),
        '粵拼（主讀）': d.get('jy', ''),
        '粵拼（又讀）': d.get('jy2', ''),
        '拼音': d.get('py', ''),
        '簡體': d.get('si', ''),
    })

# 2) 筆數需要說明的字（不重複）
for ch, note in sorted(REGION_NOTES.items()):
    if ch in seen:
        continue
    seen.add(ch)
    d = db.get(ch, {})
    rows.append({
        '輸入字': ch,
        '香港教育標準寫法': ch,
        '對應寫法': '',
        '是否標準寫法': '是',
        '關係': '筆數說明',
        '本站預設示範': ch,
        '可切換成你的寫法': '—',
        '筆數': d.get('s', ''),
        '筆數備註': note,
        '字形來源': label_src(src_of(ch)),
        '筆順來源': order_src(ch),
        '粵拼（主讀）': d.get('jy', ''),
        '粵拼（又讀）': d.get('jy2', ''),
        '拼音': d.get('py', ''),
        '簡體': d.get('si', ''),
    })

# 3) 台灣字形後備字（td=twpen）
tw = [ch for hexs, s in sources.items() if s == 'twpen' for ch in [chr(int(hexs, 16))]]
for ch in sorted(tw):
    if ch in seen:
        continue
    seen.add(ch)
    d = db.get(ch, {})
    rows.append({
        '輸入字': ch,
        '香港教育標準寫法': '（字詞表未收錄）',
        '對應寫法': '',
        '是否標準寫法': '是',
        '關係': '口語用字／字詞表未收',
        '本站預設示範': ch,
        '可切換成你的寫法': '—',
        '筆數': d.get('s', ''),
        '筆數備註': '字形依台灣教育部標準，非香港官方字形',
        '字形來源': label_src('twpen'),
        '筆順來源': '台灣教育部（逆向）',
        '粵拼（主讀）': d.get('jy', ''),
        '粵拼（又讀）': d.get('jy2', ''),
        '拼音': d.get('py', ''),
        '簡體': d.get('si', ''),
    })

cols = list(rows[0].keys())

csv_path = os.path.join(ROOT, 'docs', 'teacher-appendix.csv')
with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

trs = '\n'.join('<tr>' + ''.join('<td>%s</td>' % (r[c] or '') for c in cols) + '</tr>' for r in rows)
ths = ''.join('<th>%s</th>' % c for c in cols)

html = """<!DOCTYPE html>
<html lang="zh-Hant-HK"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>教師附錄：字形與筆數對照表</title>
<style>
 body{margin:0;background:#fff;color:#1c1c1c;line-height:1.7;
      font-family:"LXGW WenKai TC","Noto Serif CJK TC","Songti TC","PingFang HK",serif;}
 .wrap{max-width:1180px;margin:0 auto;padding:36px 28px 80px;}
 h1{font-size:1.6em;margin:0 0 .2em;}
 .sub{color:#5b6470;font-size:.92em;margin-bottom:1.4em;}
 h2{font-size:1.1em;margin:1.8em 0 .5em;color:#1f4e79;border-bottom:2px solid #1f4e79;padding-bottom:.25em;}
 table{border-collapse:collapse;width:100%;font-size:.78em;margin:.8em 0 1.6em;}
 th,td{border:1px solid #d9dee5;padding:5px 6px;text-align:left;vertical-align:top;}
 th{background:#f4f6f8;position:sticky;top:0;}
 tr:nth-child(even) td{background:#fbfcfd;}
 .note{background:#f4f6f8;border-left:3px solid #1f4e79;padding:.7em 1em;margin:1em 0;font-size:.92em;}
 a.dl{display:inline-block;margin-right:14px;padding:6px 12px;border:1px solid #1f4e79;
      color:#1f4e79;border-radius:4px;text-decoration:none;font-size:.9em;}
 @media print{ .wrap{padding:0 8mm;} table{font-size:8.4pt;} th{position:static;}
   a.dl{display:none;} h2{page-break-after:avoid;} tr{page-break-inside:avoid;} }
</style></head><body><div class="wrap">
<h1>教師附錄：字形與筆數對照表</h1>
<div class="sub">供教師與家長查核用；工作紙本體不含這些爭議資訊。資料更新：2026-10-26。</div>
<a class="dl" href="teacher-appendix.csv">下載 CSV（__N__ 列）</a>
<a class="dl" href="linguistic-review.html">語言學審閱文件</a>
<div class="note">
  <b>用法</b>：左起「輸入字」是學生／家長可能輸入的寫法；「香港教育標準寫法」是本站在工作紙上示範的字形；
  「另一常見寫法」不代表錯字，只是另一種通行寫法。「字形來源」中 EDB 為香港教育局《香港小學學習字詞表》，
  TW 為台灣教育部《筆順字典》，HW 為 HanziWriter 通用字形（後兩者非香港官方字形）。
  「筆數備註」列只說明與其他地區計法不同之處，並非指本站數字有誤。
</div>
<h2>對照表（__N__ 列）</h2>
<table><thead><tr>__THS__</tr></thead><tbody>
__TRS__
</tbody></table>
</div></body></html>
"""
html = (html.replace("__N__", str(len(rows)))
            .replace("__THS__", ths)
            .replace("__TRS__", trs))

out = os.path.join(ROOT, 'docs', 'teacher-appendix.html')
io.open(out, 'w', encoding='utf-8').write(html)
print('rows %d | wrote %s and %s' % (len(rows), out, csv_path))
print('pairs %d | region notes %d | twpen %d' % (len(pairs), len(REGION_NOTES), len(tw)))
