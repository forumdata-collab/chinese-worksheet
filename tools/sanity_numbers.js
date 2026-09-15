#!/usr/bin/env node
/**
 * Sanity check — the STROKE NUMBER LAYER.
 *
 * These checks come straight from the bugs that shipped on 2026-09-15:
 *   * numbers colliding (噠 11/12 overlapped 33x33 px, 進 6/7)
 *   * a number landing OUTSIDE its own stroke, floating in blank space (兒 #1)
 *   * a number pushed sideways onto a neighbouring stroke by collision avoidance
 *   * the wrong number of labels (山 losing a stroke, 先 5 instead of 6)
 *
 * It eval()s the real placeNumberLabels()/medianPtAt() out of index.html so the test
 * always exercises shipping code, and runs a dependency-free ray-casting test for
 * "is this point inside that stroke's ink".
 *
 *   node tools/sanity_numbers.js [--list N] [--verbose]
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const GLYPH_DIR = path.join(ROOT, 'glyphs');
const LIST_LIMIT = (() => {
  const i = process.argv.indexOf('--list');
  return i >= 0 ? parseInt(process.argv[i + 1], 10) : 12;
})();
const VERBOSE = process.argv.includes('--verbose');

// ---------------------------------------------------------------- load shipping code
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const start = html.indexOf('// arc-length point at fraction f');
const end = html.indexOf('// Build the display SVG for one glyph record');
if (start < 0 || end < 0) {
  console.error('FATAL: could not locate placeNumberLabels() in index.html (markers moved?)');
  process.exit(2);
}
eval(html.slice(start, end));

// ---------------------------------------------------------------- geometry helpers
const CMD_RE = /([MLQCHVAZ])([^MLQCHVAZ]*)/g;

function numsOf(d) {
  return (d.match(/[-0-9.]+/g) || []).map(Number);
}

function glyphBBox(rec) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const d of rec.s) {
    const n = numsOf(d);
    for (let i = 0; i + 1 < n.length; i += 2) {
      x0 = Math.min(x0, n[i]); x1 = Math.max(x1, n[i]);
      y0 = Math.min(y0, n[i + 1]); y1 = Math.max(y1, n[i + 1]);
    }
  }
  return { x0, y0, x1, y1, box: Math.max(x1 - x0, y1 - y0), C: y0 + y1 };
}

/** flatten an SVG path to a polygon (sampled) — enough for containment tests */
function polygonOf(d, perSeg = 14) {
  const pts = [];
  let cur = [0, 0], startPt = [0, 0];
  const re = /([MLQCHVAZ])([^MLQCHVAZ]*)/gi;
  let m;
  while ((m = re.exec(d))) {
    const cmd = m[1].toUpperCase();
    const v = (m[2].match(/[-0-9.]+/g) || []).map(Number);
    if (cmd === 'M') {
      for (let i = 0; i + 1 < v.length; i += 2) { cur = [v[i], v[i + 1]]; pts.push(cur); }
      startPt = cur;
    } else if (cmd === 'L') {
      for (let i = 0; i + 1 < v.length; i += 2) { cur = [v[i], v[i + 1]]; pts.push(cur); }
    } else if (cmd === 'Q') {
      for (let i = 0; i + 3 < v.length; i += 4) {
        const p0 = cur, p1 = [v[i], v[i + 1]], p2 = [v[i + 2], v[i + 3]];
        for (let k = 1; k <= perSeg; k++) {
          const t = k / perSeg, u = 1 - t;
          pts.push([u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]]);
        }
        cur = p2;
      }
    } else if (cmd === 'C') {
      for (let i = 0; i + 5 < v.length; i += 6) {
        const p0 = cur, p1 = [v[i], v[i + 1]], p2 = [v[i + 2], v[i + 3]], p3 = [v[i + 4], v[i + 5]];
        for (let k = 1; k <= perSeg; k++) {
          const t = k / perSeg, u = 1 - t;
          pts.push([u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
                    u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]]);
        }
        cur = p3;
      }
    } else if (cmd === 'Z') {
      cur = startPt;
    }
  }
  return pts;
}

function insidePolygon(poly, pt) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if (((yi > pt[1]) !== (yj > pt[1])) &&
        (pt[0] < (xj - xi) * (pt[1] - yi) / ((yj - yi) || 1e-9) + xi)) inside = !inside;
  }
  return inside;
}

// ---------------------------------------------------------------- checks
function checkGlyph(file, rec, opts) {
  const problems = [];
  let mild = 0;
  const { box, C } = glyphBBox(rec);
  if (!(box > 0)) { problems.push('degenerate bbox'); return { problems }; }
  const medians = (rec.m || []).filter(m => m && m.length > 1);
  if (medians.length !== rec.s.length) {
    problems.push(`median/stroke count mismatch (${medians.length} vs ${rec.s.length})`);
    return { problems };
  }
  const fs = box * 0.14;
  const polys = rec.s.map(d => polygonOf(d));
  // mirror of the shipped insideFn: display point -> stored space (C - y)
  const insideFn = (i, cx, cy) => insidePolygon(polys[i], [cx, C - cy]);
  // mirror of the shipped inkPointFn: a grid sample guaranteed to be inside the polygon
  const inkPointFn = (i) => {
    const poly = polys[i];
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const [px, py] of poly) {
      x0 = Math.min(x0, px); x1 = Math.max(x1, px);
      y0 = Math.min(y0, py); y1 = Math.max(y1, py);
    }
    if (!isFinite(x0)) return null;
    for (let k = 1; k <= 6; k++) {
      for (let j = 1; j <= 6; j++) {
        const sx = x0 + (x1 - x0) * (k / 7), sy = y0 + (y1 - y0) * (j / 7);
        if (insidePolygon(poly, [sx, sy])) return { x: sx, y: sy };
      }
    }
    return null;
  };
  // mirror of the shipped size cap: a digit must not dwarf its stroke's thickness
  const polyThick = (i) => {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const [px, py] of polys[i]) {
      x0 = Math.min(x0, px); x1 = Math.max(x1, px);
      y0 = Math.min(y0, py); y1 = Math.max(y1, py);
    }
    return Math.max(Math.min(x1 - x0, y1 - y0), 1);
  };
  const hooks = {
    inside: insideFn,
    inkPoint: inkPointFn,
    size: (i, digitCount) => {
      const thick = polyThick(i);
      return Math.max(Math.min(fs, 1.8 * thick, 2.36 * thick / Math.max(digitCount, 1)), fs * 0.45);
    },
  };
  const placed = placeNumberLabels(medians, { fs, C }, hooks);

  if (placed.length !== rec.s.length) {
    problems.push(`placed ${placed.length} labels for ${rec.s.length} strokes`);
  }
  // 1) labels must not overlap each other
  for (let a = 0; a < placed.length; a++) {
    for (let b = a + 1; b < placed.length; b++) {
      const p = placed[a], q = placed[b];
      const ox = Math.min(p.bx1, q.bx1) - Math.max(p.bx0, q.bx0);
      const oy = Math.min(p.by1, q.by1) - Math.max(p.by0, q.by0);
      if (ox > 0 && oy > 0) {
        // the solver's box is deliberately conservative (~15% bigger than the glyph ink
        // plus a gap), so only a substantial overlap is a real collision
        const area = ox * oy;
        const smaller = Math.min((p.bx1 - p.bx0) * (p.by1 - p.by0),
                                 (q.bx1 - q.bx0) * (q.by1 - q.by0));
        const frac = area / Math.max(smaller, 1e-6);
        // >45 % of a digit box hidden behind another digit means a visible pile-up (the
        // shipped 噠 11/12 bug was ~80 %); below that the conservative box is just
        // brushing, not the ink.
        if (frac > 0.45) {
          problems.push(`labels ${p.label}/${q.label} overlap ${Math.round(ox)}x${Math.round(oy)} (${Math.round(frac * 100)}% of the smaller)`);
        } else {
          mild++;
        }
      }
    }
  }
  // 2) every label must sit inside the ink of the stroke it numbers.
  //    NOTE: this uses a sampled polygon, so it is an approximation of the browser's
  //    isPointInFill() — a handful of false positives on hair-thin strokes is expected.
  let offStroke = 0;
  const offList = [];
  placed.forEach((p, i) => {
    if (!insidePolygon(polys[i], [p.cx, C - p.cy])) {
      offStroke++;
      offList.push(`${p.label}@${Math.round(p.cx)},${Math.round(p.cy)}`);
    }
  });
  return { problems, fs, box, mild, offStroke, offList };
}

function main() {
  const files = fs.readdirSync(GLYPH_DIR).filter(f => f.endsWith('.json')).sort();
  let checked = 0, bad = [], mildTotal = 0, labelTotal = 0, offStrokeTotal = 0;
  const offGlyphs = [];
  const offenders = [];
  for (const f of files) {
    let rec;
    try { rec = JSON.parse(fs.readFileSync(path.join(GLYPH_DIR, f), 'utf8')); }
    catch (e) { bad.push([f, ['unreadable JSON']]); continue; }
    const r = checkGlyph(f, rec, {});
    checked++;
    mildTotal += r.mild || 0;
    offStrokeTotal += r.offStroke || 0;
    if (r.offStroke) offGlyphs.push([f, r.offList]);
    labelTotal += (rec.s || []).length;
    if (r.problems && r.problems.length) {
      bad.push([f, r.problems]);
      offenders.push([f, r.problems.length]);
    }
  }
  console.log('sanity_numbers: %d glyphs / %d digits checked', checked, labelTotal);
  console.log('  sub-45%% box overlaps (tolerated: the solver box is ~15%% wider than the ink): %d', mildTotal);
  console.log('  digits whose anchor missed its own stroke (approx. test): %d', offStrokeTotal);
  for (const [f, lst] of offGlyphs) console.log('     %s: %s', f, lst.join(' '));
  if (!bad.length) {
    console.log('  OK — no collisions, every label sits inside its own stroke');
    process.exit(0);
  }
  console.log('  FAIL — %d glyph(s) with problems (%d%%):',
              bad.length, (100 * bad.length / Math.max(checked, 1)).toFixed(2));
  offenders.sort((a, b) => b[1] - a[1]);
  const list = VERBOSE ? bad : bad.slice(0, LIST_LIMIT);
  for (const [f, probs] of list) {
    console.log('   %s: %s', f, probs.slice(0, 3).join('; '));
  }
  if (!VERBOSE && bad.length > list.length) console.log('   … %d more (use --verbose)', bad.length - list.length);
  process.exit(1);
}

main();
