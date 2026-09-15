# Code review — 2026-09-15

Triggered by a day of shipped bugs: 個's bottom stroke drawn wrong, 噠's numbers overlapping,
`三` losing a stroke, 25 characters quietly losing strokes (`山` 2 of 3, `先` 5 of 6), digits
floating in blank space (`兒`), and `先` rendering upside down. Every one of them lived in the
same three places: the EDB parser, the glyph pipeline, and the stroke-number layer inside
`index.html`.

Measured with `/tmp/recon_smells.py` and `/tmp/smell_scan2.py` (function spans, argument counts,
dead-code resolution against HTML `onclick=` handlers, pairwise function-body similarity).

## Result summary

| smell | verdict | evidence → action |
| --- | --- | --- |
| **Shotgun Surgery** | **fixed** | The entire pipeline (parser, builder, flip, reframe) lived in `/tmp`; today's parser fixes were unversioned and unreproducible. → all of it now lives in `tools/` with a README and a parameterised work dir (`CW_WORK`). |
| **Large Class** | not applicable | No classes; the app is a single module of free functions. |
| **Long Method** | **fixed** | `renderWorksheet` was 170 lines (194 before this week's edits) doing setup, header, cards, sentences, footer and the async glyph install. → split into `charCardHtml` (72), `sentenceSectionHtml` (23), `setWsFooter` (8), `installGlyphLayer` (15); `renderWorksheet` is now **57**. |
| **Duplicated Code** | **fixed** | Two 11-line blocks built the tracing cell (word practice cells vs sentence cells) with a divergent punctuation rule — one of them marked `。` as a stroke-number cell. → single `traceCellHtml(ch, cellClass, opts)`. Pairwise body similarity now finds no pair above 20 %. |
| **Long Parameter List** | **fixed** | `placeNumberLabels(medians, fontSize, flipC, insideFn)` and `hkGlyphSvg(rec, opts)`. → `placeNumberLabels(medians, frame, insideFn)` and `hkGlyphSvg(rec)` (the `opts.numbers` flag was dead). No function has more than 3 parameters now. |
| **Data Clumps** | **fixed** | The glyph geometry `(box, C, fs)` was recomputed in three places and travelled as separate arguments. → one `glyphFrame(rec)` returning `{x0,y0,x1,y1,box,cx,cy,C,fs,viewBox}`, reused by the SVG builder, the number layer and (via `_glyphMeta`) the label placement. |
| **Dead Code** | **fixed** | `zhVoiceSummary` defined, never called; `hkGlyphSvg`'s `opts.numbers`; three copies of `const NS = 'http://www.w3.org/2000/svg'`. → all removed, `NS` hoisted to module scope (this one was an actual latent crash: the extracted helpers reference it). Scanner note: the other seven "unreferenced" functions (`setInput`, `toggleQuizMode`, `printWorksheet`, `readAllText`, `strokeReplay`, `strokeStep`) **are** live — they are called from `onclick=` attributes. |
| **Primitive Obsession** | **accepted** | Stroke data is a raw SVG path string plus an `[[x,y]…]` polyline, characters are single-character strings, and options are dotted primitives. This is the EDB/HanziWriter interchange format — wrapping it in the browser would add mapping code without removing any bug class. Enforced instead by the sanity suite. |
| **Feature Envy** | **partial** | `overlayStrokeNum` (HanziWriter fallback) re-measures geometry, re-derives the font size and re-implements label emission that `addGlyphNumbers` already does for EDB glyphs. Both now share `placeNumberLabels`, but the surrounding setup is still duplicated. Left as-is: rewriting the fallback path risks the 1,000-char no-EDB class for no user-visible gain. |
| **Divergent Change** | **reduced** | A single bug ("a character shows the wrong stroke count") used to require touching the parser, the builder, `index.html` **and** the skill. The pipeline is now versioned and one command (`tools/sanity_parser.py`) proves parser and shipped glyphs agree. |
| **Message Chains** | not present | Longest chain is `document.getElementById(...).innerHTML = …` (2 links). No `a().b().c().d()`. |
| **Speculative Generality** | **checked, clean** | Every option checkbox in the UI is read: `o.dedup` (as `opts.dedup`), `opts.s2t`, `optSentenceGroup` (display toggle) all have real consumers. Nothing was added "for later". |
| **Shotgun Surgery (UI layer)** | **reduced** | Cell markup decisions are now in one function, so a change to "what a tracing cell contains" is a one-line edit instead of three. |

## Safety net

Three independent checks in `tools/`, each encoding a bug that actually shipped:

```bash
python3 tools/sanity_data.py       # 4,493 glyphs: JSON, medians, orientation, counts, tables
python3 tools/sanity_parser.py     # re-parse EDB animations; shipped glyphs must reproduce
node    tools/sanity_numbers.js    # 54,474 digits: collisions + anchors off their own stroke
```

Current state: `sanity_data` OK, `sanity_parser` OK, `sanity_numbers` reports 3 of 54,474
digits marginally outside their stroke under an **approximate** sampled-polygon test (the
browser's `isPointInFill()` is authoritative and reports 0 for the sampled characters).

Value already demonstrated: `sanity_parser` found `導` (15→16) and `巍` (20→21) where an earlier
label-count bug had silently trimmed a real stroke, and the whole 4,491 remaining glyphs proved
byte-identical to a fresh parse.

## Refactor verification

Refactors were checked against a **DOM fingerprint** taken before and after (4 configurations ×
worksheet HTML + every digit's coordinates + cell/class counts, sha256). `renderWorksheet`'s
split and the parameter/frame changes reproduced the fingerprint exactly; the only intended
difference is the punctuation fix in sentence cells (2 cells in the sampled case).

## Deliberately not done

* **Splitting `index.html`** into modules. The project deliberately ships as one file plus data;
  the number layer is now the only part that would benefit, and it is fully covered by tests.
* **Rewriting the HanziWriter fallback** (see Feature Envy).
* **A real browser-driven number test in CI.** The Node test is a population-wide screen; exact
  verification needs `isPointInFill()`. The probe snippet is documented in the `chineseword-site`
  skill.
