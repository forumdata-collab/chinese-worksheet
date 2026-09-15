# tools/ — data pipeline + sanity suite

Everything that turns the EDB (香港教育局《香港小學學習字詞表》) stroke animations into
the `glyphs/*.json` the site ships, plus the checks that stop today's bugs from coming back.

Before this directory existed the whole pipeline lived in `/tmp`: a parser fix could be
lost with the scratch directory, and nothing could verify the shipped glyphs. Every file
here is versioned; `tools/edb_id_map.json` is the only generated artefact kept in git
because everything downstream is keyed by it.

## Sanity suite

Three independent checks. Run them all before any deploy that touches data or the number
layer — each one encodes a bug that actually shipped.

```bash
python3 tools/sanity_data.py       # glyph JSON, medians, orientation, stroke counts, tables
python3 tools/sanity_parser.py     # re-parses the raw EDB animations and compares
node    tools/sanity_numbers.js    # stroke-number layer: collisions + digits off their stroke
```

| check | catches |
| --- | --- |
| `sanity_data.py` | double-flipped glyphs (stored y-down → upside-down 先), a glyph losing a stroke (山 2 of 3), `m` drifting out of step with `s` (numbers on the wrong strokes), stale `hk_order.js` / `stroke_seq.js` tables |
| `sanity_parser.py` | the number-label tween winning the same-delay merge (山 2/3, 先 5/6), an unread label encoding, and **shipped glyphs that no longer reproduce from the parser** — it found 導/巍 this way |
| `sanity_numbers.js` | digit collisions (噠 11/12) and digits whose anchor falls outside their own stroke, floating in blank space (兒 #1) |

Exit code 0 = pass. `--verbose` on the Python checks lists every offending character.

Both Python checks skip gracefully when the raw animations are absent (`CW_WORK` unset
and `/tmp/edb_strokes` missing), so the repo still checks out on a clean machine.

## Pipeline

```bash
export CW_WORK=/tmp                 # scratch dir for downloaded data (default /tmp)

python3 tools/edb_fetch.py          # 1. EDB lexicon ids  -> edb_id_map.json
                                    #    + animations     -> $CW_WORK/edb_strokes/*.js
python3 tools/edb_convert.py        # 2. animations -> edb_svg_strokes.json (the parser)
python3 tools/build_glyphs.py       # 3. -> glyphs/<hex>.json   (stored space: y-UP)
python3 tools/flip_glyphs.py        # 4. y-flip for the HanziWriter coordinate space
python3 tools/reframe_glyphs.py     # 5. rescale into the HanziWriter 1024 framing
```

`get_codes.py` + `build_seq.py` produce `stroke_seq.js` — the 筆順次序 text for the 197
characters that have no outlines anywhere (sourced from 漢典 zdic.net 笔顺编号).

### Gotchas that cost real debugging time

* **Progress files.** `build_glyphs.py`, `flip_glyphs.py` and `reframe_glyphs.py` skip
  work already recorded in `$CW_WORK/*_done.json`, and **the key formats differ**: the
  build file is keyed by character, the flip/reframe files by filename (`5152.json`).
  Removing a character with the wrong key silently reports `removed 0` and the step is
  skipped — which is exactly how 先 once ended up y-flipped twice. After a rebuild,
  compare the "to flip: N" line against the number of characters you rebuilt.
* **Re-run the parser before rebuilding.** `build_glyphs.py` renders from
  `edb_svg_strokes.json`, so a parser fix only reaches the glyphs after
  `edb_convert.py` runs again. `sanity_parser.py` fails when the two disagree.
* **Deleted data.** `glyphs/` (~21 MB, 4,493 files) is regenerated, never edited by hand.
  Never delete it without a rebuild plan — it is the only copy of the final geometry.
