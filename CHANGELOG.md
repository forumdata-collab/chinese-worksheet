# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.4] - 2026-09-15

### Fixed
- **25 個字被誤剪筆畫（用戶報「基本字顯示錯誤」）**：EDB 動畫的筆畫數標籤有兩種寫法，其一是 `to({x:76.2,y:22.1,text:"3"},0)`（屬性在前）— 舊 regex 只認 `to({text:"N"},0)`，數字就會少一；再加上「同 delay 合併」讓**數字標籤 tween**（name 數目較多，例如 `['text'×5,'shape']`）贏過真筆畫 chain，兩者夾擊就剪走真筆畫。實例：**山 得 2 畫（應 3）、先 5（應 6）、京 7（應 8）、兌 5（應 7）、鑰 22（應 25）、鑼 22（應 27）** — 而 導 16→15、巍 21→20 則係修掉過度計數。
  - 修正：① 先剔除含 `text*` 的 chain（數字標籤唔係筆畫）再合併；② 標籤解析接受屬性在前的寫法，並以「1 + 設定數字的次數」計；③ **修剪只在中位數標籤與 CHAR_DB 筆畫數（Unihan）兩個獨立來源都一致時才執行** — 單靠標籤唔安全（先/京/兌/鑰 等的標籤會落後於實際筆畫）。
  - 驗證：25 個字重建後筆畫數全部與 CHAR_DB 一致；線上抽查 先=6、生=5、京=8、鑰=25、鑿=28、導=15、巍=20。
- **誤灰「筆順／試寫」按鈕（用戶報「有筆順卻灰了」）**：舊判斷每次靠 fetch（EDB 字形 + HanziWriter），任何一次網絡失敗都會當成「無資料」而灰掉。現在以離線建好的 `STROKE_SEQ`（已知全無筆順字形嘅 197 字）為第一準則，網絡錯誤一律不灰；另外彈窗動畫若真的載入失敗，會自動降級為說明畫面，唔會再留低空白動畫。
  - 驗證：51 字抽查，灰掉狀態與 STROKE_SEQ 完全一致（0 誤差）。

### Changed
- 字形 cache-busting `?v=8 → ?v=9`（25 個字重建）。

## [1.2.3] - 2026-09-15

### Added
- **未收錄字的筆順「次序」顯示**：197 個既無 EDB 字形、亦無 HanziWriter 資料的字（搵/磡/柺/祂/蟶/蜆/囍 + 粵語字 咗/喺/佢/冇/咁/哋/攞/冧…），現於卡片顯示逐筆次序，例如 咗 → 「筆順次序：豎折橫橫撇橫豎橫（共 8 筆）」，並標明來源。彈窗同樣顯示，方便對照。
  - 資料：`stroke_seq.js`（`window.STROKE_SEQ`，197 字）＝ 漢典 zdic.net「笔顺编号」（1橫 2豎 3撇 4點 5折）。
  - 驗證：197 個編號長度與 CHAR_DB 筆畫數 **0 不符**。
- `docs/stroke-data-notes.md`：筆順資料來源調查、各來源覆蓋率，以及暫緩嘅「部件推導字形」實驗結果（見下）。

### Notes
- **部件推導字形實驗唔達標，唔出街**：用同部首／同聲符 EDB 字轉移部件形，盲測 70 個有官方真值嘅字 → 筆畫數正確僅 36%、墨跡 IoU 平均 0.41、筆順 identity 2/17。根因：部件在合體字內會變形（手→扌 4→3 畫、水→氵、心→忄），而把模板字切回部件本身就需要該份未知分解。詳見 `docs/stroke-data-notes.md`。

## [1.2.2] - 2026-09-15

### Added
- **未收錄字的明確處理**：少數字（粵語字 咗/喺/佢/冇/咁/哋/攞/冧 …）既不在《香港小學學習字詞表》，HanziWriter 亦無資料 → 以前撳「筆順」會開出**空白動畫**（播放鍵無作用）。現在卡片上的「筆順／試寫」變灰並附說明（`title`），撳入彈窗會顯示「此字未收錄於《香港小學學習字詞表》，暫無官方筆順資料」，播放鍵同時停用（關閉鍵維持可用）。

### Notes（筆順資料來源調查，2026-09-15）
- 4,493 / 5,509 字有教育局官方字形＋筆順；餘 1,016 字中 **839 字**有 HanziWriter 資料（通用筆順，數字層已修正），**177 字完全無筆順資料**（例：搵/磡/柺/祂/蟶/蜆/囍/叄 及上述粵語字）。
- 已核查嘅替代來源：**EDB 字詞表**（0 命中 — 逐字查 result.jsp 確認"找不到"，非 mapping 漏）、**makemeahanzi/HanziWriter 上游 9,574 字**（0 命中）、**KanjiVG**（51/198 命中，但屬**日本字形標準**，字形與香港教育局標準有別，混用會造成練習格與筆順動畫字形不一致）、**Wikimedia 筆順專案**（0 命中）。
- 結論：呢批字**沒有權威香港筆順來源**，故採明確告知而非拼湊字形。

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