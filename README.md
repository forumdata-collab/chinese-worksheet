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
| 🔢 Stroke-order digits | Numbered strokes (1…n) overlaid on the first tracing cell, placed **a fifth of the way along each stroke from its start**, with **one uniform digit size per character** (dense characters scale down as a whole instead of mixing big and small digits) — the strokeorder.com.tw look |
| ➡️ Stroke direction arrows | Optional (off by default): dotted centreline + arrowhead per stroke, at the stroke's end, showing the writing direction |
| 📝 練習模式 (3 modes) | 每字練習 (default) · 每字 + 整句 · 整句練習 — sentence copybook adds a 描紅 model row plus N blank rows (次數 adjustable) |
| ✍️ 描紅格數 | How many of a character's cells carry the light 描紅 tracing model: none / 1 / 2 / all |
| 🖍️ 描紅格式 | 示範格（第一格）同其餘練習格**各自**揀 純描紅 / 描紅＋筆順數字 / 描紅＋數字＋方向箭咀。每個 cell 帶自己嘅 flags（`data-num` / `data-arrow`），overlay 層逐格跟隨 —— 唔會再出現「練習格揀咗只有數字但仍然出箭咀」 |
| 🖊️ 筆順工作紙 | Optional printable stroke-order sheet: one row per character, cell *k* = the first *k* strokes, with the new stroke numbered |
| ❕ 標點全形直出 | Punctuation occupies its own grid cell like a character; half-width `, . ! ?` auto-convert to full-width `，。！？` |
| 🔊 Pronunciation | Jyutping (Cantonese) + Pinyin (Mandarin), with TTS audio for both |
| 🗣️ Multiple readings | 又讀 (alternative readings) shown when a character is polyphonic |
| 📄 Print-focused | Dedicated A4 CSS output with **82% character-to-cell ratio** (copybook look); 默書版 (dictation) hides answers |
| 🔲 7 grid styles | 米字格 · 田字格 · 新九宮格（22:56:22 中宮放大）· 井字格 · **彩色天草泥井字（3×3）** · **天草泥三色（只有顏色）** · 空白格 — all guide lines light + dashed |
| 🌤️ 彩色天草泥井字 | 上中下三色帶（天 淺藍 / 草 淺綠 / 泥 淺棕）＋圖案，用**原圖**切片渲染（`caoni-bg.jpg`：`<image>` × 3 倍闊 + 負 x 偏移，SVG viewport 自動裁走 = 一行三格重組原圖），格線仍叠喺色帶上；另一款「只有顏色」唔用圖 |
| 📏 Flexible layout | 4 grid sizes (56–128 px), 4–8 cells per row, per-row count |
| 🎲 常用範例 | **32 組** presets |
| 🔤 Smart input | Simplified Chinese → Traditional conversion, dedup option |
| 🎨 淺色描紅 | Tracing 描紅字 `#F9E8E5`（淺粉，打印同步調淡） |
| 👤 Worksheet meta | Title / student name / date fields; header toggle |
| 📱 Responsive | Works on phone, tablet and desktop; settings persist in localStorage |

### Data coverage

- **5,534 common Traditional Chinese characters**, each with Jyutping, Pinyin, stroke count, simplified form
- **518 polyphonic groups** with alternate readings
- Sources: [開放粵語字典](https://kaifangcidian.com) (CC-BY 3.0), pypinyin, Unicode Unihan (kTotalStrokes), OpenCC

### Hong Kong standard (香港標準)

- **Stroke order** follows 香港教育局《香港小學學習字詞表》— derived from the official EDB stroke-order animations (`edbchinese.hk`), covering 4,518 characters (671 of which differ from the generic 通用筆順 order)
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

## 🔤 異體字正字缺 glyph 修復（2026-09-21）

「裏」嘅 bug 係系統性嘅：站內字典收咗台灣／大陸慣用異體字（兌/臥/戶/說/衛/鉤…），而 EDB 香港正字係另一批（兑/卧/户/説/衞/鈎…）。pipeline 用異體字查 EDB 時被 redirect 去正字（共用同一個 demo id），所以 build 出嚟嘅 glyph 內容係**正字字形**、但掛咗喺**異體字檔名**——正字反而冇 glyph，輸入正字就 fallback HanziWriter（筆順／字形唔啱）。

### 分辨方法（決定性，唔靠 vision）

EDB 查詢頁面有兩個欄位直接標示邊個係正字：

- **「異體字」欄**（`YiTiZi_gif/{id}a.gif`）→ 顯示**異體**字
- **「簡化字」欄**（文字）→ 顯示**簡化**字
- EDB 動畫（`{id}.js`）畫嘅係**正字**

例：查「脣」→ 簡化字欄顯示「唇」＝脣係正字（站內收脣啱，無 bug）；查「兌」→ 異體 gif 顯示「兌」＝兌係異體、正字係「兑」（站內收咗異體 = bug）。

⚠️ OpenCC t2hk 方向唔可靠（t2hk 話「脣→唇」，但 EDB 正字係「脣」），只能做候選清單；判定一定要用 EDB 頁面欄位。

### 修法

- **共用 EDB id**（異體 glyph 內容實為正字字形）：`cp glyphs/<異體hex>.json glyphs/<正字hex>.json`
- **獨立 EDB id**（着/絃/愠/枴/氲/蜕）：download 動畫 → parse → flip → reframe（冇 HW cache 用 median fallback framing）

2026-09-21 補齊 25 字（18 共用 + 6 獨立 + 裏），連同讀音（`jy`/`py`/`s` 由異體字 copy、`si` 欄位唔設以免搞亂 SIM2T）一併補入 `data.js`（5,509 → 5,534 字）。

## 🧪 品質與代碼健康（2026-09-19 審計）

- **回歸測試套件 37 項**（headless chromium 注入 + `dispatchEvent('change')` 模擬真實操作，`--dump-dom` 讀結果）：輸入解析（半形標點／去重／簡轉繁）· 描紅格數 × 示範/練習格格式矩陣 · 7 款格線樣式 · 整句練習 · 筆順工作紙 · 默書版 · perRow 字級 · localStorage · 橫向溢出 · JS error。列印版面另測（`@media print` 規則強制生效 + A4 闊度）：無溢出、格 2.2cm 正確。
- **已修氣味**：Shotgun Surgery + Primitive Obsession（`GUIDE_STYLES` 單一真相表 + `<select>` 由 JS 生成）· Data Clumps（`cellFlags()`）· Long Parameter List（`addStepNumber` 物件參數）· Dead Code（死 CSS）。
- **刻意保留**：`index.html` 單檔、無 build step（部署 = copy 檔案）—— Large Class 係設計取捨；`placeNumberLabels()`（184 行）係避碰演算法本體，硬拆反而令狀態更難追；`traceCellHtml()` 4 個參數（其中 `opts` 係 flags 物件）唔算 Long Parameter List。

## 📜 License

MIT © 2026 [forumdata-collab](https://github.com/forumdata-collab). Chinese pronunciation data from [開放粵語字典](https://kaifangcidian.com) is CC-BY 3.0.

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
