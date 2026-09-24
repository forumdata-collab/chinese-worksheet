// ===== 詞語圖解工作紙 — worksheet-renderer.js =====
// A4 直向 210×297mm 版面:標題 → 大楷(輪廓+筆順數字)→ 3×2 插圖格。
// 字形渲染完全重用 ../glyph-engine.js(HK EDB 字形 + 筆順數字 + 避撞)。
'use strict';

// ── 版面常量 ──
const A4_W = 210, A4_H = 297;      // mm
const MARGIN = 14;                 // mm
const GLYPH_W = 44;                // 每字大楷格 mm(2 字並排 → 44×2+gap=92 < 182 可用)
const GLYPH_H = 44;
const GRID_GAP = 6;                // 圖格間距 mm

// 由 semantic + glyph 資料構建 worksheet 模型(spec §29)
async function buildWorksheetModel(word, semantic, glyphRecs) {
  const glyphs = word.split('').map(ch => {
    const rec = glyphRecs.get(ch);
    const seq = (window.STROKE_SEQ || {})[ch];
    return {
      character: ch,
      supported: !!rec,
      strokeCount: rec ? rec.s.length : (seq ? seq[0].length : null),
      glyph: rec || null,
    };
  });
  return {
    id: 'ws-' + Date.now().toString(36),
    word,
    grade: document.getElementById('optGrade') ? document.getElementById('optGrade').value : 'P1',
    glyphs,
    semantic: { meaning: semantic.meaning, version: semantic.version || 'v1' },
    examples: semantic.examples,   // [{id, caption, scene} …]
  };
}

// 大楷字形區 HTML:每個字一格,輪廓 + 筆順數字(數字由 installGlyphNumbers 異歩填)
function bigCharsHtml(glyphs) {
  return `<div class="pw-bigchars" role="img" aria-label="大字 ${glyphs.map(g => g.character).join('')}">
${glyphs.map(g => `
    <div class="pw-bigchar">
      <span class="pw-big-glyph" data-ch="${g.character}"></span>
      <span class="pw-strokecount" aria-hidden="true">${g.strokeCount ? g.strokeCount + ' 畫' : ''}</span>
    </div>`).join('')}
  </div>`;
}

// 3×2 插圖格 HTML(Phase 1 placeholder 圖片由 image-generator 出)
function imageGridHtml(examples, styleKey) {
  const cells = examples.map(ex => `
    <figure class="pw-imgcell">
      <div class="pw-imgwrap" data-caption="${ex.caption}" data-scene="${ex.scene}" data-idx="${ex.id}">
        <img alt="${ex.caption}" data-scene="${ex.scene}" data-caption="${ex.caption}" data-idx="${ex.id}" />
      </div>
      <figcaption>${ex.caption}</figcaption>
    </figure>`).join('');
  return `<div class="pw-imggrid" data-style="${styleKey}">${cells}</div>`;
}

// 整張 A4 工作紙 HTML(純結構;字形 + 圖片喺 append 後異歩填入)
function worksheetHtml(model, styleKey) {
  const w = model.word;
  return `
  <article class="pw-sheet" data-word="${w}" data-grade="${model.grade}">
    <header class="pw-head">
      <div class="pw-title">中文認字．詞語圖解</div>
      <div class="pw-level">${model.grade}${model.grade ? ' 級' : ''}</div>
    </header>

    <p class="pw-question">認字－「${w}」這裡是代表什麼意思？</p>
    <p class="pw-instr">請看圖認字、填色、並寫字。</p>

    ${bigCharsHtml(model.glyphs)}

    <p class="pw-meaning">「${w}」的意思是：${model.semantic.meaning}</p>

    ${imageGridHtml(model.examples, styleKey)}

    <footer class="pw-foot">請沿虛線剪下，貼在詞語卡或練習簿上 ✂</footer>
  </article>`;
}

// 落 image:每格 1 張(由 image-generator.js 出)。好處:單張失敗唔影響其他格 
async function installImages(sheetEl, examples, styleKey) {
  const imgs = [...sheetEl.querySelectorAll('.pw-imgwrap img')];
  await Promise.all(imgs.map(async img => {
    try {
      const scene = img.dataset.scene;
      const url = await imageFor({
        word: sheetEl.dataset.word,
        scene,
        caption: img.dataset.caption,
        style: styleKey,
        grade: sheetEl.dataset.grade,
        version: (window.SEMANTIC_VERSION || 'v1'),
      });
      img.src = url;
      img.removeAttribute('data-scene');
    } catch (e) {
      img.src = placeholderSvgFor('', styleKey);   // 兜底:唔整死張紙
    }
  }));
}

// 大楷字形:用中線畫「可描紅」嘅空心筆畫(非填充輪廓),學生可以沿線填色。
// rec.m 係 stored y-UP 空間的中線折線 → display y = C - y。
function traceGlyphSvg(rec, ch) {
  if (!rec || !rec.m || !rec.m.length) return null;
  const b = glyphInkBBox(rec.s) || glyphInkBBox(rec.m);
  if (!b) return null;
  const box = Math.max(b.x1 - b.x0, b.y1 - b.y0);
  const cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2;
  const C = b.y0 + b.y1;
  const svg = document.createElementNS(window.NS || NS, 'svg');
  svg.setAttribute('viewBox', `${(cx - box / 2).toFixed(1)} ${(cy - box / 2).toFixed(1)} ${box.toFixed(1)} ${box.toFixed(1)}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  svg.setAttribute('class', 'pw-big-svg');
  svg.setAttribute('aria-hidden', 'true');
  // 中線(可描紅)。⚠️ stroke-width 用 viewBox user unit = box 比例,唔可以用 CSS px
  const sw = (box * 0.030).toFixed(1);
  rec.m.forEach(m => {
    if (!m || m.length < 2) return;
    const pl = document.createElementNS(window.NS || NS, 'polyline');
    pl.setAttribute('points', m.map(p => `${p[0].toFixed(1)},${(C - p[1]).toFixed(1)}`).join(' '));
    pl.setAttribute('class', 'pw-trace-line');
    pl.setAttribute('stroke-width', sw);
    pl.setAttribute('stroke-linecap', 'round');
    pl.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(pl);
  });
  // 筆順數字 metadata(畀 addGlyphNumbers 用)
  svg._glyphMeta = {
    fs: box * 0.14,
    C,
    ch,
    medians: rec.m,
    // 數字層用中線放位(唔靠 fill 檢測)
    strokeEls: rec.m.map(m => {
      const el = document.createElementNS(window.NS || NS, 'polyline');
      el.setAttribute('points', (m || []).map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' '));
      el.isPointInFill = () => true;   // 中線點一定喺自己筆畫上
      el.getBBox = () => ({ x: 0, y: 0, width: box, height: box });
      return el;
    }),
  };
  return svg;
}

// 落大楷字形 + 筆順數字。⚠️ 必須 append 後先裝數字(isPointInFill 對 detached = false)
async function installBigGlyphs(sheetEl) {
  const els = [...sheetEl.querySelectorAll('.pw-big-glyph[data-ch]')];
  const chars = [...new Set(els.map(e => e.dataset.ch))];
  const recs = new Map();
  await Promise.all(chars.map(async ch => {
    const rec = await hkGlyph(ch);
    if (rec && rec.s && rec.s.length) recs.set(ch, rec);
  }));
  els.forEach(el => {
    const rec = recs.get(el.dataset.ch);
    if (!rec) return;
    const svg = traceGlyphSvg(rec, el.dataset.ch);
    if (!svg) return;
    el.textContent = '';
    el.appendChild(svg);
    try { addGlyphNumbers(svg); } catch (e) { /* 數字失敗唔影響字形 */ }
  });
}

// 主渲染:填入 #pwWorksheet 容器 → 異歩填字形 + 圖片
async function renderWorksheet(model, styleKey) {
  const box = document.getElementById('pwWorksheet');
  box.innerHTML = worksheetHtml(model, styleKey);
  installBigGlyphs(box);              // async,冇 await 都唔阻(字形逐個 pop)
  await installImages(box, model.examples, styleKey);
  return box;
}

// 列印觸發(瀏覽器 Print → Save as PDF)
function printSheet() {
  window.print();
}