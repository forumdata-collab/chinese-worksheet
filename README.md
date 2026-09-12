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
| 🔤 HK standard glyphs | Characters render using the 教育局 (HK EDB) standard glyph outlines (3,776 chars) instead of a generic font |
| 🔢 Stroke-order digits | Numbered strokes (1…n) overlaid on the first tracing cell — the strokeorder.com.tw look |
| 🔊 Pronunciation | Jyutping (Cantonese) + Pinyin (Mandarin), with TTS audio for both |
| 🗣️ Multiple readings | 又讀 (alternative readings) shown when a character is polyphonic |
| 📄 Print-focused | Dedicated A4 CSS output with **82% character-to-cell ratio** (copybook look); 默書版 (dictation) hides answers |
| 🔲 6 grid styles | 米字格 · 田字格 · 九宮格 · 井字格 · 虛線格 · 空白格 |
| 📏 Flexible layout | 4 grid sizes (56–128 px), 4–8 cells per row, per-row count |
| 🔤 Smart input | Simplified Chinese → Traditional conversion, dedup option |
| 👤 Worksheet meta | Title / student name / date fields; header toggle |
| 📱 Responsive | Works on phone, tablet and desktop; settings persist in localStorage |

### Data coverage

- **5,509 common Traditional Chinese characters**, each with Jyutping, Pinyin, stroke count, simplified form
- **518 polyphonic groups** with alternate readings
- Sources: [開放粵語字典](https://kaifangcidian.com) (CC-BY 3.0), pypinyin, Unicode Unihan (kTotalStrokes), OpenCC

### Hong Kong standard (香港標準)

- **Stroke order** follows 香港教育局《香港小學學習字詞表》— derived from the official EDB stroke-order animations (`edbchinese.hk`), covering 3,776 characters (523 of which differ from the generic 通用筆順 order)
- **Glyph forms** use the official 教育局 standard outlines (e.g. 「舟」's open top-right corner, which differs from the Taiwan-style font form)
- Characters outside the lexicon fall back to the bundled font + generic stroke order

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
├── hk_order.js         # HK stroke-order permutation table (window.HK_ORDER, 523 chars)
├── glyphs/             # HK standard glyph outlines + centrelines (3,776 chars, on-demand)
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

## 📜 License

MIT © 2026 [forumdata-collab](https://github.com/forumdata-collab). Chinese pronunciation data from [開放粵語字典](https://kaifangcidian.com) is CC-BY 3.0.

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
