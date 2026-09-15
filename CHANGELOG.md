# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.1] - 2026-09-15

### Fixed
- **字形取錯（311 字的「最終字形」問題，例：個）**：EDB 每個字的動畫檔有兩組 shapes — 逐格顯示的漸進 sub-shape（`shape`…`shape_34`）同動畫結尾「整字」的官方最終 shapes（`shape_35`…）。舊 parser 用漸進版，而漸進版的中間 state 不等於最終字形：**個** 第 10 筆取到 x 260-791（由「人」跨到「固」底下，看上去像一條連住兩邊的底線），官方最終為 x 458-877（只在固內）。現改用 show-all 區塊的官方幾何 — 該區塊順序**不可直接信**（147/296 字的順序列唔符筆順，例：什），故保留動畫 chain 的筆順、只用全域最優 bbox 配對換上最終形狀。
- **漏一筆（例：三 只有 2 畫）**：筆畫數標籤有兩種格式，除 `to({text:"N"},0)` 外另有 state-based `p:{text:"N"}`（三 用後者）→ 舊碼讀到 "2" 便 trim 走第 3 筆。同時修正「同 delay 合併」會把數字標籤 tween（name 較多）當成筆畫 chain 而吞掉真筆畫。
- **非教育局字的筆順數字上下鏡像**：HanziWriter 的 stroke／median 為 y-up，描紅數字層卻直接畫入 SVG 的 y-down 空間（少了一次翻轉）。以墨跡行剖面相關量度：**對齊 0.357 vs 翻轉 0.622**（噠）→ 數字全部落在錯誤筆畫上。影響所有非教育局字形字（粵語字 嘅/咁/呢/睇 等）。
- **筆順數字互相重疊**：新增沿筆畫中心線的避撞放置（`placeNumberLabels`）— 每個數字先在自己筆畫的中線上試 15 個位置，全撞才垂直筆畫方向側移。修正前：噠 11/12 重疊 33×33px、4/5、10/11、10/12、6/8；進 6/7。實測 38 字（個/三/進/噠/嘅/十/土/香/鄭/雅/說…）墨跡框重疊 = 0。

### Changed
- 全部 4,493 個字形重建（build → flip → reframe），`glyphs/` cache-busting `?v=7 → ?v=8`。

## [1.2.0] - 2026-09-15

### Added
- **練習模式（3 種）**：`每字練習`（預設）· `每字 + 整句` · `整句練習`。整句模式產生描紅範句一行 + N 行空格（`整句練習次數` 1–8 可調），每格一字，附引導線與筆順數字。
- **標點全形直出**：標點符號佔一格，同中文字一樣有練習格。半形 `, . ! ? : ; ( )` 自動轉全形 `，。！？：；（）`；標點不做光學放大（保持字體原本大小位置），亦不顯示筆順／試寫按鈕（無筆順資料）。

### Changed
- **字形覆蓋 3,776 → 4,491 字**：修正 EDB 字詞表 ID 對照（`4001-ZC` 資料夾帶字母，舊 regex 漏掉 ID > 4000 的全部字）。
- **香港筆順次序 523 → 671 字**（IoU 筆畫配對重建）。

### Fixed
- **筆畫數錯誤（37 字）**：EDB 動畫解析器修正三類問題 — ①同一 delay 的並行 chain 重複計為多筆（例：一 誤判 2 畫）②部分檔案墨色非 `#000000`（例：瘟 全部 14 畫遺失）③初始 state 非空 / `_off:false` 格式漏接（例：鋸 少 1 畫）。現與官方筆順動畫逐字核對，0 不符。
- **筆順彈窗字體過大／出界**：字形數據 re-frame 到 HanziWriter 假設的 1024 座標空間（此前重 build 後漏做 re-frame，字被切邊）。
- 標點不再被 `normalizeGlyphs` 光學放大。

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