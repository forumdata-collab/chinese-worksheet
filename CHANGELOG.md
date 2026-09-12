# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] - 2026-09-12

### Added
- **香港標準筆順**：筆順次序改跟香港教育局《香港小學學習字詞表》（3,776 字；523 字與通用筆順不同）。資料源自教育局官方筆順動畫（edbchinese.hk）。
- **教育局標準字形**：示範格／描紅格／筆順動畫改用官方字形輪廓（3,776 字），逐字 on-demand 載入（`glyphs/<hex>.json`，含筆畫中心線）。
- **筆順數字 overlay**：首個練習格顯示 1…n 筆順數字，位置取自字形中心線中點（螢幕／列印對齊）。
- **字與框比例統一 82%**（顯示及列印，`GLYPH_RATIO`），兩者所見即所得。
- 修正：筆順數字原先因 y 軸方向（y-up vs y-down）錯置而上下鏡像。
- 修正：筆順動畫彈窗內字偏移/被切頂（字形 re-frame 到 HanziWriter 假設的座標空間）。

## [1.0.0] - 2026-09-09

### Added
- Interactive Chinese character practice worksheet generator
- Input parsing for Traditional Chinese text (CJK + extension A)
- Per-character **Jyutping (Cantonese)** and **Pinyin (Mandarin)** readings with alternate-reading support
- **Audio playback** via Web Speech API (zh-HK / zh-CN) with dialect-aware voice matching, fallback and warnings
- **Stroke order animation** and **guided writing (quiz)** via HanziWriter
- **6 printable grid styles**: 米字格 (cross+diagonals), 田字格 (cross), 九宮格 (3×3 with center emphasis), 井字格 (3×3), 虛線格, 空白格
- **4 practice grid sizes** (56 / 72 / 96 / 128 px) and **per-row count** (auto / 4 / 6 / 8)
- **默書版 (dictation mode)**: hides character, shows pronunciation as cue
- **Simplified → Traditional** input conversion (client-side, no external library)
- Worksheet header (title / name / date) with show/hide toggle
- Settings persistence via localStorage
- Responsive design (mobile / tablet / desktop)

### Data
- `data.js`: 5,509 characters with jyutping, pinyin, stroke counts (Unihan kTotalStrokes), simplified forms
- Sources: 開放粵語字典 (kaifangcidian.com, CC-BY 3.0), pypinyin, Unicode Unihan, OpenCC

### Fixed
- Audio now plays on devices without a matching dialect voice (soft warning instead of silent block)