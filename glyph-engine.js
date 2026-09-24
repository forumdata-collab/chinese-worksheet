// ===== SHARED GLYPH ENGINE =====
// Extracted from index.html (2026-09-24) so the picture-worksheet feature can reuse the
// exact same HK glyph / stroke-order / stroke-number code instead of duplicating it.
// Classic script (not a module): every function stays a global, so index.html and
// picture/ call them unchanged. Source of truth = this file.
//
//   hkGlyph(ch)        → glyphs/<hex>.json  {s:[path…], m:[median…]}  (stored y-UP)
//   hkGlyphSvg(rec,ch) → display SVG (y-down via translate(0,C) scale(1,-1))
//   addGlyphNumbers(svg) → stroke numbers  — MUST run after the SVG is in the document
//                          (isPointInFill() is false for detached nodes)
//   appendStrokeArrows()  → dotted centrelines + direction arrows
//   measureInkFrame / partialGlyphSvg / addStepNumber → progressive stroke sheets
//   strokeCountOf(ch)     → authoritative count (EDB/twpen glyph, not Unihan)
//   applyHKOrder / hkCharDataLoader → HK stroke order for HanziWriter
//
// Deps: window.HK_ORDER (hk_order.js), window.STROKE_SEQ (stroke_seq.js),
//       window.CHAR_DB (data.js), HanziWriter (for non-EDB fallback + animations),
//       const NS = 'http://www.w3.org/2000/svg' — declare NS before loading if absent.

function applyHKOrder(ch, data) {
  const perm = (window.HK_ORDER || {})[ch];
  if (!perm || !data || !data.strokes || perm.length !== data.strokes.length) return data;
  return {
    strokes: perm.map(i => data.strokes[i]),
    medians: perm.map(i => data.medians[i]),
  };
}

// Custom loader so HanziWriter's own animation/quiz也跟香港次序
function hkCharDataLoader(ch, onComplete, onError) {
  hkGlyph(ch).then(rec => {
    if (rec && rec.s && rec.s.length && rec.m && rec.m.length === rec.s.length) {
      // 教育局標準字形（香港寫法）+ 香港筆順次序
      onComplete({ strokes: rec.s, medians: rec.m });
      return null;
    }
    return HanziWriter.loadCharacterData(ch).then(d => onComplete(applyHKOrder(ch, d)));
  }).catch(e => onError && onError(e));
}

// ===== 教育局標準字形 (香港小學學習字詞表 字形) =====
// glyphs/<hex>.json = {s:[stroke path…], m:[[[x,y]…]…]} — official EDB animation
// outlines (1080-space) plus skeleton centrelines, IN STORED Y-UP SPACE.
// Displayed via a flipped <g> so SVG (y-down) shows the character the right way up.
const _hkGlyphCache = new Map();
function glyphDir() { return window.GLYPH_DIR || 'glyphs/'; }
function hkGlyph(ch) {
  if (!ch) return Promise.resolve(null);
  if (_hkGlyphCache.has(ch)) return _hkGlyphCache.get(ch);
  const hex = ch.codePointAt(0).toString(16);
  const p = fetch(`${glyphDir()}${hex}.json?v=20`)
    .then(r => (r.ok ? r.json() : null))
    .catch(() => null);
  _hkGlyphCache.set(ch, p);
  return p;
}

// 字形來源（provenance）—— 顯式標記每字 glyph 從邊度嚟。
// 回 'EDB'（香港教育局字詞表）｜'twpen'（台灣筆順字典逆向）｜null（無字形，fallback 字體）。
let _glyphSources = null;
async function glyphSource(ch) {
  if (!ch) return null;
  if (!_glyphSources) {
    try {
      const r = await fetch(`${glyphDir()}../data/glyph_sources.json`);
      _glyphSources = r.ok ? (await r.json()).glyphs : {};
    } catch (e) { _glyphSources = {}; }
  }
  const hex = ch.codePointAt(0).toString(16);
  return _glyphSources[hex] || null;
}

// arc-length point at fraction f (0..1) along a polyline [[x,y]…]
function medianPtAt(m, f) {
  if (!m || !m.length) return null;
  if (m.length === 1) return { x: m[0][0], y: m[0][1] };
  let total = 0;
  const segs = [];
  for (let k = 1; k < m.length; k++) {
    const L = Math.hypot(m[k][0] - m[k - 1][0], m[k][1] - m[k - 1][1]);
    segs.push(L); total += L;
  }
  if (!total) return { x: m[0][0], y: m[0][1] };
  const want = total * f;
  let acc = 0;
  for (let k = 0; k < segs.length; k++) {
    if (acc + segs[k] >= want) {
      const t = (want - acc) / (segs[k] || 1);
      return { x: m[k][0] + (m[k + 1][0] - m[k][0]) * t, y: m[k][1] + (m[k + 1][1] - m[k][1]) * t };
    }
    acc += segs[k];
  }
  return { x: m[m.length - 1][0], y: m[m.length - 1][1] };
}

// Stroke numbers, placed ON their own stroke but kept apart from each other.
// Each number tries several arc-length positions of its own median — so it can never
// drift off the stroke it labels — and takes the first slot that does not overlap an
// already-placed number; if every slot collides, the least-overlapping one wins.
// Without this, characters whose strokes cross at their midpoints (十-shaped parts,
// 噠 strokes 4/5 and 11/12 …) print two numbers on top of each other.
// flipC mirrors stored y-up data into the SVG's y-down space: y_display = flipC - y.
// inkPointFn(i) is the optional last resort: it returns a median-space point known to be
// inside stroke i's ink, used when no centreline candidate qualifies (see below).
// insideFn(i, cx, cy) is optional: it must report whether the display-space point
// actually lies in stroke i's ink.  A plain arc-length midpoint can fall OUTSIDE a
// short/thin stroke (兒's first stroke is only ~25 units wide, so its number floated
// in blank space), and candidates that miss their own stroke are penalised hard.
// 統一數字字級（2026-09-18）：筆畫多嘅字全部數字用同一個基準級數，唔會一大一小。
// DIGIT_SCALE = 用戶要求「所有數字再縮一個單位」（= SIZE_SCALES 一級 0.85）。
const DIGIT_SCALE = 0.85;
// 密字數字位置 override（0-based stroke index → 弧長 fraction）。
// 呢啲字嘅相鄰/共線筆畫，避撞算法（側移+縮字）搵唔到 clean spot，人手指定更遠弧長位置。
// （由 tools 搜尋腳本搵出最優 fraction；籌/鬱 嘅 49% 重疊係密字極限，fraction 都救唔到）
const NUMBER_OVERRIDES = {
  '繭': {8: 0.6},    // 第 9 筆（9/10 重疊 24%→0%）
  '輛': {8: 0.32},   // 第 9 筆（9/13 重疊 52%→0%）
  '騷': {11: 0.14},  // 第 12 筆（12/13 重疊 60%→0%）
  '髒': {16: 0.8},   // 第 17 筆（17/18 重疊 65%→0%）
  '齷': {6: 0.05},   // 第 7 筆（7/8 重疊 31%→11%）
};
function numberBaseScale(n) {
  return DIGIT_SCALE * (n > 8 ? Math.max(0.45, 1 - 0.028 * (n - 8)) : 1);
}

function placeNumberLabels(medians, frame, hooks) {
  const { fs: globalFs, C: flipC } = frame;  // glyph geometry travels as one frame
  const nStrokes = medians.length || 1;
  const fontSize = globalFs * numberBaseScale(nStrokes);  // 全字統一基準
  const wideLen = String(nStrokes).length;                // 10 筆以上：全部當兩位寬
  hooks = hooks || {};
  const insideFn = hooks.inside;              // is this point in MY stroke's ink?
  const inkPointFn = hooks.inkPoint;          // a point certainly in MY stroke's ink
  const otherFn = hooks.others;               // is this point in ANOTHER stroke's ink?
  const placed = [];
  // Dense characters (鬱, 鸚, 鹽 … 15+ crossing strokes) can leave no clean spot at full
  // size, so the search walks 23 positions along the stroke at decreasing sizes and stops
  // at the first size that fits without a pile-up. Shrinking beats both overlapping and
  // leaving the labelled stroke.
  // 2026-09-18 用戶要求：數字放喺**起筆後 1/5 弧長**位置（由 1/2 中點改；1/4、1/5、1/6 三版
  // 對比後用戶揀 1/5）。由 0.2 開始向兩邊展開搵位，後面位置保留做避撞 fallback。
  const FRACTIONS = [0.2, 0.17, 0.23, 0.14, 0.26, 0.11, 0.29, 0.08, 0.32, 0.05, 0.36, 0.4,
                     0.46, 0.52, 0.6, 0.7, 0.8, 0.9];
  const SIZE_SCALES = [1, 0.85, 0.72, 0.6, 0.5, 0.42, 0.36, 0.3];
  // 側移距離（× 字級）：0 = 中線本身，之後左右交替
  const LATERAL = [0, 0.45, -0.45, 0.8, -0.8, 1.2, -1.2];
  // Box ≈ the DIGIT INK, not the em box: a digit is ~0.55em wide and rises ~0.72em
  // above its baseline, plus a small breathing gap. Using the full em box made the
  // solver think two labels 90 units apart still collided and settle for a needless
  // overlap (個 strokes 5/6).
  const gap = fontSize * 0.05;
  // Penalties are FRACTIONS OF ONE DIGIT'S AREA, matching how a collision actually shows
  // (two small digits stacked are as unreadable as two big ones, but an absolute-area
  // objective rated them as an improvement and shrank its way into the problem).
  const OFF_STROKE_PENALTY = 4;      // leaving the labelled stroke loses to any overlap
  // Where strokes cross, a digit can sit exactly on the crossing point — on its own
  // stroke, but also on a neighbour's ink (喻 8/10, 勤 9/10). Prefer elsewhere on the
  // stroke: this penalty is far below OFF_STROKE_PENALTY, so leaving the stroke still
  // loses, but a quieter spot on it wins.
  const CROSS_PENALTY = 0.5;
  // NOTE: relaxing the penalty for sidestepping off the stroke was tried and reverted —
  // it clears the pile-ups but leaves digits floating beside their stroke (暗/靜/髏/璽),
  // which is the defect the numbers layer exists to avoid. Dense characters instead shrink
  // further (SIZE_SCALES) so a clean on-stroke spot is more likely to exist.
  medians.forEach((m, i) => {
    const label = String(i + 1);
    // Per-char per-stroke fraction override（密字共線筆畫嘅數字，指定一個更遠嘅弧長位置）
    const ovFrac = (hooks && hooks.override) ? hooks.override(i) : null;
    const fracs = ovFrac != null ? [ovFrac, ...FRACTIONS.filter(f => f !== ovFrac)] : FRACTIONS;
    // A digit must not dwarf the stroke it labels: on a thin/short stroke the global size
    // looks like a misplaced number (兒 #1 sits on a 25x40 stroke, 離 #8 on 55x40) rather
    // than a label. hooks.size(i) caps it to the stroke's own thickness; the floor keeps
    // it legible.
    let size = fontSize;
    if (hooks.size) {
      try {
        const s = hooks.size(i, wideLen);
        if (s && s > 0) size = s;
      } catch (e) { /* keep the global size */ }
    }
    // A stroke can have a degenerate centreline — 孿's stroke 17 is a single point — and
    // then no candidate exists and the stroke ends up with NO number at all. Anchor such
    // strokes on a point taken from their own ink instead.
    if (!m || m.length < 2) {
      let p = null;
      try { p = inkPointFn ? inkPointFn(i) : (m && m[0] ? { x: m[0][0], y: m[0][1] } : null); } catch (e) { p = null; }
      if (p) {
        const cx = p.x, cy = flipC - p.y;
        const bw = size * 0.55 * wideLen;
        placed.push({ label, cx, cy,
                      bx0: cx - bw / 2 - gap, bx1: cx + bw / 2 + gap,
                      by0: cy - size * 0.90 - gap, by1: cy - size * 0.18 + gap,
                      fs: size });
      }
      return;
    }
    let best = null, bestOv = Infinity, bestOff = false;
    // 候選點 = 中線上嘅位置 ＋ 沿中線法線嘅側移（側移只准留喺自己筆畫嘅墨跡內）。
    // 側移排喺縮字之前：同一字嘅數字級數先保持一致，唔使靠越縮越細去避撞。
    const aN = medianPtAt(m, 0.42), bN = medianPtAt(m, 0.58);
    let nX = 0, nY = 0;
    if (aN && bN) {
      const dxN = bN.x - aN.x, dyN = -(bN.y - aN.y);
      const LN = Math.hypot(dxN, dyN);
      if (LN) { nX = -dyN / LN; nY = dxN / LN; }
    }
    scales: for (const scale of SIZE_SCALES) {
    const sizeS = Math.max(size * scale, fontSize * 0.3);
    for (const f of fracs) {
      const pt = medianPtAt(m, f);
      if (!pt) continue;
      const bx = pt.x, by = flipC - pt.y;
      for (let li = 0; li < LATERAL.length; li++) {
      const off = sizeS * LATERAL[li];
      const cx = bx + nX * off, cy = by + nY * off;
      const bw = sizeS * 0.55 * wideLen;
      const bx0 = cx - bw / 2 - gap, bx1 = cx + bw / 2 + gap;
      // Digits sit ON the text baseline, which the renderer lifts 0.18em above cy,
      // and their ink reaches ~0.72em above that baseline — so the box is NOT centred
      // on cy. Modelling it as centred left 進's 6/7 overlapping by 68x16 units.
      const by0 = cy - sizeS * 0.90 - gap, by1 = cy - sizeS * 0.18 + gap;
      const area = Math.max((bx1 - bx0) * (by1 - by0), 1e-6);
      let ov = 0;
      for (const p of placed) {
        const ox = Math.min(bx1, p.bx1) - Math.max(bx0, p.bx0);
        const oy = Math.min(by1, p.by1) - Math.max(by0, p.by0);
        if (ox > 0 && oy > 0) ov += (ox * oy) / area;
      }
      if (insideFn) {
        let onStroke = true;
        try { onStroke = insideFn(i, cx, cy); } catch (e) { onStroke = true; }
        if (!onStroke) ov += OFF_STROKE_PENALTY;
      }
      if (otherFn) {
        let onOther = false;
        try { onOther = otherFn(i, cx, cy); } catch (e) { onOther = false; }
        if (onOther) ov += CROSS_PENALTY;
      }
      if (ov < bestOv) {
        bestOv = ov;
        bestOff = !!(insideFn && ov >= OFF_STROKE_PENALTY);
        best = { label, cx, cy, bx0, bx1, by0, by1, fs: sizeS };
      }
      if (ov === 0) break scales;      // clean spot at this size — keep the largest
      }
    }
    if (bestOv === 0) break;           // nothing smaller will beat a clean fit
    }
    // Last resort: a stroke can be too short to hold all its own labels apart (進's
    // stroke 7 shares one vertical line with 5 and 6). Step SIDEWAYS off the stroke —
    // perpendicular to its local direction — keeping the number beside its own stroke.
    if (best && bestOv > 0) {
      const a = medianPtAt(m, 0.46), b = medianPtAt(m, 0.54);
      let nx = 1, ny = 0;
      if (a && b) {
        const dx = b.x - a.x, dy = -(b.y - a.y);      // display space (y flipped)
        const L = Math.hypot(dx, dy);
        if (L) { nx = -dy / L; ny = dx / L; }
      }
      for (const k of [0.6, 0.9, 1.2, 1.5, 1.8, -0.6, -0.9, -1.2, -1.5, -1.8]) {
        const cx2 = best.cx + nx * size * k, cy2 = best.cy + ny * size * k;
        const bw2 = size * 0.55 * wideLen;
        const bx2 = [cx2 - bw2 / 2 - gap, cx2 + bw2 / 2 + gap];
        const by2 = [cy2 - size * 0.90 - gap, cy2 - size * 0.18 + gap];
        const area2 = Math.max((bx2[1] - bx2[0]) * (by2[1] - by2[0]), 1e-6);
        let ov2 = 0;
        for (const p of placed) {
          const ox = Math.min(bx2[1], p.bx1) - Math.max(bx2[0], p.bx0);
          const oy = Math.min(by2[1], p.by1) - Math.max(by2[0], p.by0);
          if (ox > 0 && oy > 0) ov2 += (ox * oy) / area2;
        }
        if (insideFn) {
          let onStroke = true;
          try { onStroke = insideFn(i, cx2, cy2); } catch (e) { onStroke = true; }
          if (!onStroke) ov2 += OFF_STROKE_PENALTY;  // staying on the stroke wins
        }
        if (ov2 < bestOv) {
          bestOv = ov2;
          bestOff = !!(insideFn && ov2 >= OFF_STROKE_PENALTY);
          best = { label, cx: cx2, cy: cy2, bx0: bx2[0], bx1: bx2[1], by0: by2[0], by1: by2[1], fs: size };
        }
        if (ov2 === 0) break;
      }
    }
    // Final resort: some strokes have a centreline that never enters their own ink (thin
    // or sharply curved). Then EVERY candidate is penalised, so the solver settles for the
    // least-bad one and the digit ends up on a neighbouring stroke or in blank space
    // (靜 #14 landed on stroke 13, 暗 #13 on no stroke at all). inkPointFn(i) supplies a
    // point that is definitely inside stroke i's own fill — put the digit there.
    if (best && bestOff && inkPointFn) {
      let p = null;
      try { p = inkPointFn(i); } catch (e) { p = null; }
      if (p) {
        const cx3 = p.x, cy3 = flipC - p.y;
        const bw3 = size * 0.55 * wideLen;
        const bx3 = [cx3 - bw3 / 2 - gap, cx3 + bw3 / 2 + gap];
        const by3 = [cy3 - size * 0.90 - gap, cy3 - size * 0.18 + gap];
        const area3 = Math.max((bx3[1] - bx3[0]) * (by3[1] - by3[0]), 1e-6);
        let ov3 = 0;
        for (const q of placed) {
          const ox = Math.min(bx3[1], q.bx1) - Math.max(bx3[0], q.bx0);
          const oy = Math.min(by3[1], q.by1) - Math.max(by3[0], q.by0);
          if (ox > 0 && oy > 0) ov3 += (ox * oy) / area3;
        }
        // staying on the labelled stroke always beats floating off it
        best = { label, cx: cx3, cy: cy3, bx0: bx3[0], bx1: bx3[1], by0: by3[0], by1: by3[1], fs: size };
      }
    }
    if (best) placed.push(best);
  });
  return placed;
}

/**
 * Ink bounding box of a glyph's stroke paths. getBBox() only works on rendered
 * geometry, so the paths are measured inside an off-screen probe SVG that is removed
 * again straight away. Returns null for a degenerate (empty) record.
 */
function glyphInkBBox(paths) {
  const probe = document.createElementNS(NS, 'svg');
  probe.setAttribute('width', '0'); probe.setAttribute('height', '0');
  probe.style.cssText = 'position:absolute;left:-9999px;overflow:hidden';
  document.body.appendChild(probe);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const d of paths) {
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', d); probe.appendChild(p);
    const b = p.getBBox();
    x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y);
    x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height);
  }
  probe.remove();
  if (!isFinite(x0) || x1 <= x0 || y1 <= y0) return null;
  return { x0, y0, x1, y1 };
}

/**
 * Display frame of one glyph record — everything downstream needs, in one object.
 * Stored space is y-UP, so `C` is the flip axis that turns the display y-down again.
 * The stroke-number font size is 14% of the ink box (unchanged ratio).
 */
function glyphFrame(rec) {
  const b = glyphInkBBox(rec.s);
  if (!b) return null;
  const box = Math.max(b.x1 - b.x0, b.y1 - b.y0);
  const cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2;
  return {
    ...b, box, cx, cy,
    C: b.y0 + b.y1,
    fs: box * 0.14,
    viewBox: `${(cx - box / 2).toFixed(1)} ${(cy - box / 2).toFixed(1)} `
           + `${box.toFixed(1)} ${box.toFixed(1)}`,
  };
}

// Build the display SVG for one glyph record. Ink is ~62% of the box (matches the old
// font glyph look). Stroke numbers are added afterwards by addGlyphNumbers().
function hkGlyphSvg(rec, ch) {
  const frame = glyphFrame(rec);
  if (!frame) return null;

  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('class', 'hk-glyph-svg');
  svg.setAttribute('viewBox', frame.viewBox);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  svg.setAttribute('aria-hidden', 'true');

  const g = document.createElementNS(NS, 'g');
  g.setAttribute('transform', `translate(0,${frame.C.toFixed(1)}) scale(1,-1)`);
  const strokeEls = [];
  for (const d of rec.s) {
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', d);
    g.appendChild(p);
    strokeEls.push(p);
  }
  svg.appendChild(g);

  // numbers are placed later, once this SVG is in the document — see addGlyphNumbers
  svg._glyphMeta = { ...frame, strokeEls, medians: rec.m, ch };
  return svg;
}


// Place the stroke numbers. MUST run after the SVG is attached to the document:
// isPointInFill() returns false for detached nodes (verified), which would silently
// disable the "stay inside your own stroke" test and let labels float in blank space.
function addGlyphNumbers(svg) {
  const meta = svg && svg._glyphMeta;
  if (!meta || !meta.medians || !meta.medians.length) return;
  const { fs, C, strokeEls, medians } = meta;
  const insideFn = (i, cx, cy) => {
    const el = strokeEls[i];
    if (!el) return true;
    try { return el.isPointInFill(new DOMPoint(cx, C - cy)); } catch (e) { return true; }
  };
  // A point guaranteed to be inside stroke i's own fill: sample a grid over the stroke's
  // box until isPointInFill() agrees. Used when the centreline misses the ink entirely.
  const inkPointFn = (i) => {
    const el = strokeEls[i];
    if (!el) return null;
    let b;
    try { b = el.getBBox(); } catch (e) { return null; }
    for (let k = 1; k <= 6; k++) {
      for (let j = 1; j <= 6; j++) {
        const sx = b.x + b.width * (k / 7), sy = b.y + b.height * (j / 7);
        try {
          if (el.isPointInFill(new DOMPoint(sx, sy))) return { x: sx, y: sy };
        } catch (e) { /* ignore, try the next sample */ }
      }
    }
    return null;
  };
  const hooks = {
    inside: insideFn,
    inkPoint: inkPointFn,
    // Cap a digit to its stroke's own thickness — a number wider than the stroke it
    // labels reads as misplaced rather than as a label (兒's first stroke is 25x40 units
    // against a 114-unit digit). Floor at 45 % of the global size to stay legible.
    size: (i, digitCount) => {
      const el = strokeEls[i];
      if (!el) return fs;
      let b;
      try { b = el.getBBox(); } catch (e) { return fs; }
      const thick = Math.min(b.width, b.height);
      if (!(thick > 0)) return fs;
      const fsEff = fs * numberBaseScale(medians.length);
      const byHeight = 1.8 * thick;                    // digit ink ~0.72 em tall
      const byWidth = 2.36 * thick / Math.max(digitCount, 1);   // ~0.55 em per digit
      return Math.max(Math.min(fsEff, byHeight, byWidth), fsEff * 0.8);
    },
    // digits must not sit on a crossing neighbour's ink either
    others: (i, cx, cy) => {
      for (let k = 0; k < strokeEls.length; k++) {
        if (k === i) continue;
        try { if (strokeEls[k].isPointInFill(new DOMPoint(cx, C - cy))) return true; } catch (e) { /* skip */ }
      }
      return false;
    },
    // 密字數字位置 override（NUMBER_OVERRIDES）：指定某筆嘅優先弧長位置
    override: (i) => {
      const ov = meta.ch && NUMBER_OVERRIDES[meta.ch];
      return ov && ov[i] != null ? ov[i] : null;
    },
  };
  placeNumberLabels(medians, { fs, C }, hooks).forEach(p => {
    const sz = p.fs || fs;
    const t = document.createElementNS(NS, 'text');
    t.setAttribute('x', p.cx.toFixed(1));
    t.setAttribute('y', (p.cy - sz * 0.18).toFixed(1));
    t.setAttribute('font-size', sz.toFixed(1));
    t.textContent = p.label;
    svg.appendChild(t);
  });
}

// Install HK glyphs into .char-glyph / .guide-glyph spans (font glyph = fallback).
// Numbers go on the first tracing cell only.
async function installHKGlyphs(root) {
  const els = [...root.querySelectorAll('.char-glyph[data-ch], .guide-glyph[data-ch]')];
  if (!els.length) return new Set();
  const chars = [...new Set(els.map(e => e.dataset.ch))];
  const recs = new Map();
  await Promise.all(chars.map(async ch => {
    const rec = await hkGlyph(ch);
    if (rec && rec.s && rec.s.length) recs.set(ch, rec);
  }));
  const handled = new Set();
  els.forEach(el => {
    const rec = recs.get(el.dataset.ch);
    if (!rec) return;
    const withNum = el.classList.contains('guide-glyph') && !!el.closest('.stroke-num-cell');
    const svg = hkGlyphSvg(rec, el.dataset.ch);
    if (!svg) return;
    el.textContent = '';
    el.style.transform = '';           // font-based optical normalisation not needed
    el.appendChild(svg);
    if (withNum) {
      // per-cell flags：第一示範格跟示範格格式，其餘格跟練習格格式（唔可以讀全局 currentOptions）
      const cellEl = el.closest('.stroke-num-cell');
      const wantArrow = cellEl && cellEl.dataset.arrow != null ? cellEl.dataset.arrow === '1' : !!currentOptions.arrow;
      const wantNum = cellEl && cellEl.dataset.num != null ? cellEl.dataset.num === '1' : currentOptions.strokeNum !== false;
      if (wantArrow) {
        appendStrokeArrows(svg, rec.m, svg._glyphMeta.C, svg._glyphMeta.box);
      }
      if (wantNum) addGlyphNumbers(svg);   // 數字最上層
    }
    handled.add(el.dataset.ch);
  });
  return handled;
}

function _hwCharData(ch) {
  if (_hwCharCache.has(ch)) return _hwCharCache.get(ch);
  const p = HanziWriter.loadCharacterData(ch)
    .then(d => applyHKOrder(ch, d))
    .catch(() => null);
  _hwCharCache.set(ch, p);
  return p;
}

// Inject numbered SVG strokes into a .stroke-num-cell.
// The SVG lives INSIDE the .guide-glyph span, so it tracks the glyph's own box
// (font-size driven) in EVERY media — screen px map, print cm, any size — with
// no pixel measurement. Numbers are placed in HanziWriter's 1024-space via the
// viewBox; preserveAspectRatio=meet fits them to the (square, CJK) glyph box.
async function overlayStrokeNum(cell) {
  const ch = cell.dataset.ch;
  if (!ch) return;
  const data = await _hwCharData(ch);
  if (!data || !data.strokes || !data.strokes.length) return;

  const glyph = cell.querySelector('.guide-glyph');
  if (!glyph) return;

  // --- 1. measure HanziWriter stroke bbox + number anchors (in HW 1024-space) ---
  const probe = document.createElementNS(NS, 'svg');
  probe.setAttribute('width', '0');
  probe.setAttribute('height', '0');
  probe.style.cssText = 'position:absolute;left:-9999px;overflow:hidden';
  document.body.appendChild(probe);
  let hwX0 = Infinity, hwY0 = Infinity, hwX1 = -Infinity, hwY1 = -Infinity;
  const medPolys = [];
  // Number anchor = a point on the stroke's MEDIAN (true centreline). HW `strokes` are
  // closed ink contours — their geometric midpoint can land on a stroke tip, so the
  // centreline (medians, already reordered to HK order) is used instead.
  for (let si = 0; si < data.strokes.length; si++) {
    const d = data.strokes[si];
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', d); probe.appendChild(p);
    const b = p.getBBox();
    hwX0 = Math.min(hwX0, b.x); hwY0 = Math.min(hwY0, b.y);
    hwX1 = Math.max(hwX1, b.x + b.width); hwY1 = Math.max(hwY1, b.y + b.height);
    const med = data.medians && data.medians[si];
    if (med && med.length > 1) {
      medPolys.push(med);
    } else {
      let pt;
      try {
        const len = p.getTotalLength();
        pt = p.getPointAtLength(len * 0.5);
      } catch (e) {
        pt = { x: b.x + b.width / 2, y: b.y + b.height / 2 };
      }
      medPolys.push([[pt.x, pt.y], [pt.x, pt.y]]);
    }
  }
  probe.remove();

  // --- 2. build overlay SVG (viewBox = HW bbox + padding) ---
  const hwW = hwX1 - hwX0, hwH = hwY1 - hwY0;
  if (!hwW || !hwH) return;  // degenerate stroke data
  const pad = 0.06 * Math.max(hwW, hwH);

  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('class', 'stroke-num-svg');
  svg.setAttribute('viewBox', `${hwX0 - pad} ${hwY0 - pad} ${hwW + 2 * pad} ${hwH + 2 * pad}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  svg.setAttribute('aria-hidden', 'true');

  const numFontSize = Math.max(40, Math.min(80, hwH * 0.13));
  // HanziWriter ships y-UP data while this overlay draws into the SVG's y-down space,
  // so the whole number layer used to come out vertically MIRRORED against the font
  // glyph (measured: row-profile correlation 0.357 aligned vs 0.622 flipped, 噠) —
  // numbers landed on the wrong strokes. Mirror about the ink bbox, exactly like the
  // HK-glyph path does with C = y0 + y1.
  const flipC = hwY0 + hwY1;
  // per-cell flags（同 installHKGlyphs 一致）：唔可以讀全局 currentOptions
  const wantArrow = cell.dataset.arrow != null ? cell.dataset.arrow === '1' : !!currentOptions.arrow;
  const wantNum = cell.dataset.num != null ? cell.dataset.num === '1' : currentOptions.strokeNum !== false;
  // 方向箭咀（同一 flip 修正）先畫，數字後畫 = 數字喺最上層
  if (wantArrow) {
    appendStrokeArrows(svg, medPolys, flipC, Math.max(hwW, hwH));
  }
  if (!wantNum) { glyph.appendChild(svg); return; }
  placeNumberLabels(medPolys, { fs: numFontSize, C: flipC }).forEach(p => {
    const t = document.createElementNS(NS, 'text');
    t.setAttribute('x', p.cx.toFixed(1));
    t.setAttribute('y', (p.cy - numFontSize * 0.18).toFixed(1));
    t.setAttribute('font-size', numFontSize.toFixed(1));
    t.textContent = p.label;
    svg.appendChild(t);
  });

  glyph.appendChild(svg);
}
// 每筆中線 + 筆尾箭咀（顯示書寫方向），同筆順數字共用一個 SVG / 座標系。
// medians 係 stored y-UP 空間（EDB rec.m ／ HanziWriter medians），display y = C - y。
// 尺寸全部按墨跡 box 比例計 → 螢幕/列印/任何字級自動跟住縮放。
function appendStrokeArrows(svg, medians, C, box) {
  if (!svg || !medians || !medians.length || !(box > 0)) return;
  const w = box * 0.02;                                   // 線粗（亦係圓點直徑）
  const dots = `0 ${(box * 0.028).toFixed(1)}`;            // 密點線：0 長度 dash + round cap = 圓點
  const headL = box * 0.075, headW = box * 0.036;          // 箭頭長 / 半闊
  medians.forEach(med => {
    if (!med || med.length < 2) return;
    const pts = med.map(p => [p[0], C - p[1]]);
    const pl = document.createElementNS(NS, 'polyline');
    pl.setAttribute('class', 'stroke-arrow');
    pl.setAttribute('points', pts.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' '));
    pl.setAttribute('stroke-width', w.toFixed(1));
    pl.setAttribute('stroke-dasharray', dots);
    svg.appendChild(pl);
    const [ax, ay] = pts[pts.length - 1];
    const [bx, by] = pts[pts.length - 2];
    let dx = ax - bx, dy = ay - by;
    const len = Math.hypot(dx, dy);
    if (!len || !isFinite(len)) return;
    dx /= len; dy /= len;
    const nx = -dy, ny = dx;
    const d = `M${(ax - dx * headL + nx * headW).toFixed(1)},${(ay - dy * headL + ny * headW).toFixed(1)}`
            + ` L${ax.toFixed(1)},${ay.toFixed(1)}`
            + ` L${(ax - dx * headL - nx * headW).toFixed(1)},${(ay - dy * headL - ny * headW).toFixed(1)} Z`;
    const head = document.createElementNS(NS, 'path');
    head.setAttribute('class', 'stroke-arrow-head');
    head.setAttribute('d', d);
    svg.appendChild(head);
  });
}

function strokeCountOf(ch) {
  const seq = strokeSeqInfo(ch);
  const db = (window.CHAR_DB || {})[ch];
  const n = db && db.s ? db.s : (seq ? seq.count : 0);
  if (!n) return null;
  return { count: n, seq };
}

function strokePageHtml(o) {
  if (!o.strokePage || o.layout === 'sentence' || !currentChars.length) return '';
  let rows = '';
  let total = 0;
  currentChars.forEach(ch => {
    if (isPunct(ch)) return;
    const info = strokeCountOf(ch);
    if (!info) return;
    total++;
    const db = (window.CHAR_DB || {})[ch] || {};
    const meta = [];
    if (o.canto && db.jy) meta.push(db.jy);
    if (o.pinyin && db.py) meta.push(db.py);
    let cells = '';
    for (let k = 1; k <= info.count; k++) {
      cells += `<div class="practice-cell stroke-step-cell" data-step-ch="${esc(ch)}" data-step-k="${k}">`
        + guideSvg((k - 1) % 3)
        + `<span class="guide-char"><span class="step-glyph">${esc(ch)}</span></span>`
        + `</div>`;
    }
    rows += `<div class="stroke-page-block">`
      + `<div class="stroke-caption">✍️ ${esc(ch)}`
      + `<span class="stroke-meta">（共 ${info.count} 筆${meta.length ? ' · ' + esc(meta.join(' / ')) : ''}）</span>`
      + (info.seq ? `<span class="seq-names-inline">${esc(info.seq.names)}</span><span class="seq-src">次序來源：漢典 zdic.net</span>` : '')
      + `</div><div class="practice-row stroke-page-row">${cells}</div></div>`;
  });
  if (!total) return '';
  return `<div class="stroke-page"><div class="stroke-page-title">🖊️ 筆順工作紙</div>${rows}</div>`;
}

/** 墨跡框（用離屏 probe 量 paths 嘅 union bbox）+ 翻轉軸 C + 方形 viewBox。 */
function measureInkFrame(paths) {
  const probe = document.createElementNS(NS, 'svg');
  probe.setAttribute('width', '0');
  probe.setAttribute('height', '0');
  probe.style.cssText = 'position:absolute;left:-9999px;overflow:hidden';
  document.body.appendChild(probe);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  try {
    for (const d of paths) {
      const p = document.createElementNS(NS, 'path');
      p.setAttribute('d', d); probe.appendChild(p);
      const b = p.getBBox();
      x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y);
      x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height);
    }
  } catch (e) { /* fall through */ }
  probe.remove();
  if (!(x1 > x0) || !(y1 > y0)) return null;
  const box = Math.max(x1 - x0, y1 - y0);
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  return {
    box, C: y0 + y1,
    viewBox: `${(cx - box / 2).toFixed(1)} ${(cy - box / 2).toFixed(1)} ${box.toFixed(1)} ${box.toFixed(1)}`,
  };
}

/** 只畫前 k 筆嘅 SVG（geometry 同 hkGlyphSvg 一致：g 內 translate(0,C) scale(1,-1)）。 */
function partialGlyphSvg(paths, frame, k) {
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('class', 'hk-glyph-svg step-svg');
  svg.setAttribute('viewBox', frame.viewBox);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  svg.setAttribute('aria-hidden', 'true');
  const g = document.createElementNS(NS, 'g');
  g.setAttribute('transform', `translate(0,${frame.C.toFixed(1)}) scale(1,-1)`);
  const els = [];
  for (let i = 0; i < Math.min(k, paths.length); i++) {
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', paths[i]);
    g.appendChild(p);
    els.push(p);
  }
  svg.appendChild(g);
  return { svg, lastEl: els[els.length - 1] || null };
}

// 新增嗰筆嘅編號。⚠️ 一定要喺 SVG append 落 DOM 之後才做 —— isPointInFill() 對
// detached 節點永遠回 false（skill 有記錄），會令「貼住自己筆畫」嘅判斷静默失效。
// 參數由 6 個收成一個物件（原 svg/lastEl/frame/k/med/totalStrokes = Long Parameter List）
function addStepNumber(svg, { lastEl, frame, k, med, totalStrokes }) {
  if (!lastEl || !med) return;
  const fs = frame.box * 0.14 * numberBaseScale(totalStrokes || k);
  let chosen = null, onInkFound = false;
  for (const f of [0.2, 0.35, 0.5, 0.65, 0.8]) {
    const pt = medianPtAt(med, f);
    if (!pt) continue;
    const cx = pt.x, cy = frame.C - pt.y;
    if (!chosen) chosen = { cx, cy };
    let onInk = false;
    try { onInk = lastEl.isPointInFill(new DOMPoint(cx, frame.C - cy)); } catch (e) { onInk = true; }
    if (onInk) { chosen = { cx, cy }; onInkFound = true; break; }
  }
  if (!onInkFound) {
    // 中線全部落唔到墨跡（幼點/短筆）→ 喺最後一筆嘅 bbox 掃一個保證喺墨跡內嘅點
    try {
      const b = lastEl.getBBox();
      for (let i = 1; i <= 6 && !onInkFound; i++) {
        for (let j = 1; j <= 6; j++) {
          const sx = b.x + b.width * (i / 7), sy = b.y + b.height * (j / 7);
          let ok = false;
          try { ok = lastEl.isPointInFill(new DOMPoint(sx, sy)); } catch (e) { ok = true; }
          if (ok) { chosen = { cx: sx, cy: frame.C - sy }; onInkFound = true; break; }
        }
      }
    } catch (e) { /* 用中線嘅第一個候選 */ }
  }
  if (!chosen) return;
  const t = document.createElementNS(NS, 'text');
  t.setAttribute('x', chosen.cx.toFixed(1));
  t.setAttribute('y', (chosen.cy - fs * 0.18).toFixed(1));
  t.setAttribute('font-size', fs.toFixed(1));
  t.textContent = String(k);
  svg.appendChild(t);
}
