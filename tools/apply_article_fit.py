import re
p='/home/ubuntu/chinese-worksheet/index.html'
s=open(p).read()

# 1) fit-to-width for screen
anchor="""    content.innerHTML = articlePagesHtml(o);
    content.classList.toggle('quiz-mode', !!o.quizMode);
    setWsFooter(o);
    installGlyphLayer(content);
    return;"""
assert anchor in s, 'render anchor'
new="""    content.innerHTML = articlePagesHtml(o);
    content.classList.toggle('quiz-mode', !!o.quizMode);
    setWsFooter(o);
    installGlyphLayer(content);
    fitArticlePages();
    return;"""
s=s.replace(anchor,new)

# 2) the fit function, before renderWorksheet
anchor2='function renderWorksheet() {'
assert anchor2 in s
fit='''// 文章頁在螢幕上等比縮到容器闊（列印時 zoom 還原為 1，尺寸不受影響）
function fitArticlePages() {
  const content = document.getElementById('wsContent');
  if (!content) return;
  const pages = [...content.querySelectorAll('.ws-page')];
  if (!pages.length) return;
  const avail = Math.max(280, content.clientWidth || document.documentElement.clientWidth);
  const pw = parseFloat(pages[0].style.getPropertyValue('--pw')) || pages[0].offsetWidth || 794;
  const scale = Math.max(0.22, Math.min(1, (avail - 4) / pw));
  pages.forEach(p => { p.style.zoom = scale; });
}
window.addEventListener('resize', () => {
  if (currentOptions && currentOptions.layout === 'article') fitArticlePages();
});

'''
s=s.replace(anchor2, fit+anchor2)

# 3) print: reset zoom
old='@media print{\n  #worksheet.article-mode{padding:0;margin:0;max-width:none}'
assert old in s
s=s.replace(old,'@media print{\n  .ws-page{zoom:1!important}\n  #worksheet.article-mode{padding:0;margin:0;max-width:none}')

open(p,'w').write(s)
b=re.findall(r'<script(?![^>]*src=)(?![^>]*type="application)[^>]*>(.*?)</script>',s,re.S)
open('/tmp/main.js','w').write(max(b,key=len))
print('patched', len(s))
