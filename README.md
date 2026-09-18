# 中文筆順練習簿 (Chinese Character Worksheet Generator)

An interactive, print-ready Chinese character practice worksheet generator. Input any Traditional Chinese text and get:

- **粵拼 (Jyutping) + 普通話拼音 (Pinyin)** pronunciations for every character
- **Cantonese & Mandarin audio** via Web Speech API
- **Animated stroke order + guided writing practice** — following 香港小學學習字詞表 (HK EDB standard)
- **A4 printable worksheets** with multiple grid styles

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🖊️ Stroke order | Animated per-stroke playback + interactive 試寫 (draw-along quiz), **following the 香港小學學習字詞表 stroke-order standard** |
| 🔤 HK standard glyphs | Characters render using the 教育局 (HK EDB) standard glyph outlines (4,493 chars) instead of a generic font |
| 🔢 Stroke-order digits | Numbered strokes (1…n) overlaid on the first tracing cell — the strokeorder.com.tw look |
| ➡️ Stroke direction arrows | Optional (off by default): dotted centreline + arrowhead per stroke, at the stroke's end, showing the writing direction |
| 📝 練習模式 (3 modes) | 每字練習 (default) · 每字 + 整句 · 整句練習 — sentence copybook adds a 描紅 model row plus N blank rows (次數 adjustable) |
| ❕ 標點全形直出 | Punctuation occupies its own grid cell like a character; half-width `, . ! ?` auto-convert to full-width `，。！？` |
| 🔊 Pronunciation | Jyutping (Cantonese) + Pinyin (Mandarin), with TTS audio for both |
| 🗣️ Multiple readings | 又讀 (alternative readings) shown when a character is polyphonic |
| 📄 Print-focused | Dedicated A4 CSS output with **82% character-to-cell ratio** (copybook look); 默書版 (dictation) hides answers |
| 🔲 5 grid styles | 米字格 · 田字格 · 新九宮格（22:56:22 中宮放大）· 井字格 · 空白格 — all guide lines light + dashed |
| 📏 Flexible layout | 4 grid sizes (56–128 px), 4–8 cells per row, per-row count |
| 🎲 常用範例 | **32 組** presets |
| 🔤 Smart input | Simplified Chinese → Traditional conversion, dedup option |
| 🎨 淺色描紅 | Tracing 描紅字 `#F9E8E5`（淺粉，打印同步調淡） |
| 👤 Worksheet meta | Title / student name / date fields; header toggle |
| 📱 Responsive | Works on phone, tablet and desktop; settings persist in localStorage |

### Data coverage

- **5,509 common Traditional Chinese characters**, each with Jyutping, Pinyin, stroke count, simplified form
- **518 polyphonic groups** with alternate readings
- Sources: [開放粵語字典](https://kaifangcidian.com) (CC-BY 3.0), pypinyin, Unicode Unihan (kTotalStrokes), OpenCC

### Hong Kong standard (香港標準)

- **Stroke order** follows 香港教育局《香港小學學習字詞表》— derived from the official EDB stroke-order animations (`edbchinese.hk`), covering 4,493 characters (671 of which differ from the generic 通用筆順 order)
- **Glyph forms** use the official 教育局 standard outlines (e.g. 「舟」's open top-right corner, which differs from the Taiwan-style font form)
- Characters outside the lexicon fall back to the bundled font + generic stroke order
  (their stroke-order digits are placed with the same collision-aware solver, so they stay on the right stroke)
- **197 characters are in neither source** (搵/磡/祂/蜆/蟶/囍 and Cantonese 咗/喺/佢/冇/咁/哋/攞/冧 …). For those the
  per-stroke ORDER is shown as text from zdic.net's 笔顺编号 (e.g. 咗 → 豎折橫橫撇橫豎橫, 共 8 筆) while
  筆順/試寫 stay disabled — there are no outlines to animate. See `docs/stroke-data-notes.md`.

## 🚀 Quick start

The app is static — no build step, no server dependency:

```bash
git clone https://github.com/forumdata-collab/chinese-worksheet.git
cd chinese-worksheet

# any static file server works
python3 -m http.server 8080
# → http://localhost:8080
```

Or open `index.html` directly in a browser.

## 📁 Project structure

```
chinese-worksheet/
├── index.html          # Single-page app (UI + logic + styles)
├── data.js             # Character database (window.CHAR_DB, ~287 KB)
├── hk_order.js         # HK stroke-order permutation table (window.HK_ORDER, 671 chars)
├── glyphs/             # HK standard glyph outlines + centrelines (4,493 chars, on-demand)
├── fonts/              # Self-hosted LXGW WenKai TC CJK subsets
└── LICENSE             # MIT
```

## 🧠 How it works

- **`data.js`** is a precomputed dictionary: `window.CHAR_DB = { 字: {jy, py, s, jy2?, py2?, si?}, ... }`
  - `jy` / `py` — primary Jyutping / Pinyin readings
  - `jy2` / `py2` — alternative readings
  - `s` — stroke count (from Unihan kTotalStrokes)
  - `si` — simplified form (via OpenCC)
- **HK stroke order** (`hk_order.js`) is a per-character permutation applied over [HanziWriter](https://hanziwriter.org) stroke data; the animation and quiz both use it
- **HK glyphs** (`glyphs/`) are vector outlines extracted from the official EDB stroke animations, rendered as inline SVG in every cell (and used by the animation modal); fetched per-character on demand
- **Stroke numbers** are placed at each stroke's centreline midpoint (from the glyph data), so they stay on the ink in every media and size
- **Audio** uses the browser's Web Speech API (`zh-HK` / `zh-CN` voices) with graceful fallback and a soft warning when the exact dialect voice is unavailable
- **Print** is `@media print` CSS — the on-screen editor is hidden, only the worksheet (A4) is printed

## 🗣️ Audio support notes

- Requires a browser/OS with Chinese TTS voices installed (zh-HK for Cantonese, zh-CN for Mandarin)
- Falls back to the best available Chinese voice and warns when dialect mismatches
- Audio speed adjustable in the toolbar (🐢–🐇)

## 🔧 Regenerating the data

`data.js` was generated from upstream sources. To rebuild it (requires Python + `jyutping`, `pypinyin`, `OpenCC`, `cjkradlib` and a Unihan download), see the generation pipeline documented in the repo history.

## 🐛 Debugging the glyph / stroke-order / number layers

The glyph pipeline (EDB animation → outline → centreline → stroke numbers) has a history of
subtle data bugs — missing strokes, misplaced numbers, stale glyph geometry. When a character
renders wrong, work through [DEBUG.md](DEBUG.md):

- **Symptom → root-cause table** — which layer to suspect first (missing stroke, shifted stroke, floating digit…)
- **Diagnosis flow** — 4 steps, each with a script:
  1. `python3 tools/sanity_parser.py` — parser vs deployed stroke-count consistency
  2. `python3 tools/sanity_geom.py` — full-chain geometry comparison (catches *stale* glyphs the count check misses)
  3. `node tools/sanity_numbers.js` — digit collision + anchor-on-own-stroke check
  4. Browser visual check with headless Chromium (⚠️ don't trust vision on glyph shapes)
- **Known parser pitfalls** — 9-arg `setTransform` regX/regY, multi-shape stroke finals, label-counting traps
- **Rebuild-only-changed flow** — regenerate just the affected glyphs, not all 4,493

## 📜 License

MIT © 2026 [forumdata-collab](https://github.com/forumdata-collab). Chinese pronunciation data from [開放粵語字典](https://kaifangcidian.com) is CC-BY 3.0.

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
