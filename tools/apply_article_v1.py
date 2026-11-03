import re
p='/home/ubuntu/chinese-worksheet/index.html'
s=open(p).read()

old="""  if (o.layout === 'article') {
    content.innerHTML = articlePagesHtml(o);
    setWsFooter(o);
    installGlyphLayer(content);
    return;
  }"""
assert old in s, 'anchor A'
new="""  if (o.layout === 'article') {
    content.innerHTML = articlePagesHtml(o);
    content.classList.toggle('quiz-mode', !!o.quizMode);
    setWsFooter(o);
    installGlyphLayer(content);
    return;
  }"""
s=s.replace(old,new)

old2="#worksheet.article-mode{padding:0;max-width:none;background:transparent;box-shadow:none}"
assert old2 in s, 'anchor B'
s=s.replace(old2, old2+"\n#worksheet.article-mode .ws-header{display:none}")

old3="""  const clone = ws.cloneNode(true);"""
assert s.count(old3)==1, 'anchor C'
new3="""  let clone = ws.cloneNode(true);
  if (o.layout === 'article') {
    const pages = clone.querySelectorAll('.ws-page');
    const n = pages.length;
    for (let i = 1; i < n; i++) pages[i].remove();
    if (info) info.textContent += ` · 文章共 ${n} 頁（預覽只顯示第 1 頁）`;
  }"""
s=s.replace(old3,new3)

old4="""  info.textContent = `排版：${o.layout === 'sentence' ? '整句' : o.layout === 'word+sentence' ? '每字+整句' : '每字'}"""
assert old4 in s, 'anchor D'
new4="""  info.textContent = `排版：${o.layout === 'article' ? '文章抄寫紙' : o.layout === 'sentence' ? '整句' : o.layout === 'word+sentence' ? '每字+整句' : '每字'}"""
s=s.replace(old4,new4)

open(p,'w').write(s)
b=re.findall(r'<script(?![^>]*src=)(?![^>]*type="application)[^>]*>(.*?)</script>',s,re.S)
open('/tmp/main.js','w').write(max(b,key=len))
print('patched', len(s), 'scripts', len(b))
