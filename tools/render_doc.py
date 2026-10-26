"""Render docs/linguistic-review.md into a printable single-file HTML (CJK-friendly)."""
import io
import os

import markdown

ROOT = '/home/ubuntu/chinese-worksheet'
md_path = os.path.join(ROOT, 'docs', 'linguistic-review.md')
out_path = os.path.join(ROOT, 'docs', 'linguistic-review.html')

body = markdown.markdown(
    io.open(md_path, encoding='utf-8').read(),
    extensions=['tables', 'sane_lists', 'attr_list'],
)

HTML = """<!DOCTYPE html>
<html lang="zh-Hant-HK">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>中文筆順練習簿平台：字形與筆順判斷框架說明</title>
<style>
  :root { --ink:#1c1c1c; --muted:#5b6470; --line:#d9dee5; --accent:#1f4e79; --soft:#f4f6f8; }
  * { box-sizing: border-box; }
  body { margin:0; background:#eef1f4; color:var(--ink);
         font-family:"LXGW WenKai TC","Noto Serif CJK TC","Songti TC","PingFang HK","Microsoft JhengHei",serif;
         line-height:1.85; font-size:16.5px; }
  .page { max-width: 860px; margin: 28px auto 60px; background:#fff; padding: 52px 64px 64px;
          box-shadow: 0 2px 18px rgba(20,30,50,.08); border-radius: 2px; }
  h1 { font-size: 1.75em; line-height:1.4; margin:0 0 .2em; letter-spacing:.02em; }
  h1 + p { color:var(--muted); font-size:.95em; }
  h2 { font-size: 1.28em; margin: 2.1em 0 .7em; padding-bottom:.32em; border-bottom:2px solid var(--accent); color:var(--accent); }
  h3 { font-size: 1.08em; margin: 1.6em 0 .5em; color:#22303d; }
  p { margin: .8em 0; text-align: justify; }
  ul, ol { padding-left: 1.5em; margin: .6em 0; }
  li { margin: .3em 0; }
  strong { color:#0f2d4a; }
  hr { border:0; border-top:1px solid var(--line); margin:2.2em 0; }
  table { border-collapse: collapse; width:100%; margin: 1em 0; font-size:.93em; }
  th, td { border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }
  th { background: var(--soft); font-weight:600; }
  code { background:var(--soft); padding:.1em .35em; border-radius:3px; font-size:.88em;
         font-family:"SFMono-Regular",Consolas,monospace; }
  blockquote { margin:1em 0; padding:.6em 1em; border-left:3px solid var(--accent); background:var(--soft); color:#33414f; }
  em { color:var(--muted); }
  @media print {
    body { background:#fff; font-size:11.5pt; }
    .page { box-shadow:none; margin:0; padding:0 8mm; max-width:none; }
    h2 { page-break-after: avoid; }
    table, li { page-break-inside: avoid; }
  }
</style>
</head>
<body>
<div class="page">
__BODY__
</div>
</body>
</html>
"""

io.open(out_path, 'w', encoding='utf-8').write(HTML.replace('__BODY__', body))
print('wrote', out_path, os.path.getsize(out_path), 'bytes')
