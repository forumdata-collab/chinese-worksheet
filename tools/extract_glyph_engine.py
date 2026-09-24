# -*- coding: utf-8 -*-
"""Extract the shared glyph engine out of index.html into glyph-engine.js.

Pure move, no logic edits: the same function bodies become top-level declarations in a
classic (non-module) script, so both index.html and picture/ keep calling them exactly
as before. index.html then loads the engine with a <script src> instead of inlining it.
"""
import re

SRC = "/home/ubuntu/chinese-worksheet/index.html"
OUT = "/home/ubuntu/chinese-worksheet/glyph-engine.js"
lines = open(SRC, encoding="utf-8").read().split("\n")   # 0-indexed; file line N == lines[N-1]


def grab(a, b):
    """1-indexed inclusive line range."""
    return "\n".join(lines[a - 1:b])


# ── Blocks, in file order ──────────────────────────────────────────────────────
# applyHKOrder .. glyphSource                 (HK order + EDB glyph loader)
b1 = grab(1599, 1649)
# medianPtAt .. placeNumberLabels (stroke-number placement solver) + constants
b2 = grab(1651, 1890)
# glyphInkBBox .. appendStrokeArrows (ink bbox, frame, SVG builder, number layer, arrows)
b3 = grab(1892, 2197)
# strokeCountOf / measureInkFrame / partialGlyphSvg / addStepNumber (used by picture/)
b4 = grab(2392, 2514)

header = """// ===== SHARED GLYPH ENGINE =====
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
"""

body = "\n\n".join([b1, b2, b3, b4])
open(OUT, "w", encoding="utf-8").write(header + "\n" + body + "\n")
print("wrote", OUT, len(body), "chars of engine code")

# Sanity: every engine function the picture feature needs must be present exactly once.
names = ["applyHKOrder", "hkCharDataLoader", "hkGlyph", "glyphSource", "medianPtAt",
         "numberBaseScale", "placeNumberLabels", "glyphInkBBox", "glyphFrame",
         "hkGlyphSvg", "addGlyphNumbers", "installHKGlyphs", "_hwCharData",
         "overlayStrokeNum", "appendStrokeArrows", "strokeCountOf",
         "measureInkFrame", "partialGlyphSvg", "addStepNumber"]
src_txt = open(OUT, encoding="utf-8").read()
missing = [n for n in names if f"function {n}(" not in src_txt]
print("missing:", missing or "none")
