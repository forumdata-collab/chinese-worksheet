# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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