import re
p='/home/ubuntu/chinese-worksheet/glyph-engine.js'
s=open(p).read()
old="""  const box = Math.max(b.x1 - b.x0, b.y1 - b.y0);
  const cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2;
  return {
    ...b, box, cx, cy,
    C: b.y0 + b.y1,
    fs: box * 0.14,"""
new="""  // 字身框（em）固定：以前用「自身墨跡框」做 box，等於每個字都放大到填滿格子，
  // 結果少筆劃而方正的字（白、西、口、日）視覺上撐爆格，同筆劃多的字唔協調。
  // 900 ≈ 全字庫墨跡中位數（856）同 1024 字身之間，令密字大小不變、疏字自然收細。
  const EM = 900;
  const box = EM;
  const cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2;
  return {
    ...b, box, cx, cy,
    C: b.y0 + b.y1,
    fs: box * 0.12,"""
assert old in s, 'anchor'
s=s.replace(old,new)
open(p,'w').write(s)

# bump cache-bust in both pages
for f in ['/home/ubuntu/chinese-worksheet/index.html']:
    t=open(f).read()
    t=t.replace('glyph-engine.js?v=7','glyph-engine.js?v=8')
    open(f,'w').write(t)
print('patched engine + bump v8')
