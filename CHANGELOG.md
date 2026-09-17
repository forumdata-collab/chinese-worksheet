# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.11] - 2026-09-17

### Added
- **未收錄字 twpen.com 筆順註解**（沚 案）：香港字詞表／HanziWriter／漢典都無嘅字（例：沚、芷），卡片同「未收錄」彈窗加小字註解連結「筆順字典 twpen.com」（台灣教育部標準），用戶可跳去睇台灣標準筆順動畫。href=`https://www.twpen.com/<hex>.html`。

### Fixed
- **`strokeUnavailable()` 分辨唔到「真 404」同「網絡錯誤」**：舊用 `HanziWriter.loadCharacterData()`，404 時拋 `Failed to load char data` 被 catch 當「網絡問題→有資料」→ 沚等字筆順按鈕唔灰、彈窗空白。改為直接 fetch `hanzi-writer-data@2.0/<hex>.json`，`!r.ok` = 真冇資料（灰按鈕），網絡錯誤先 catch 返回 false。

## [1.2.10] - 2026-09-16

### Added
- **頁首筆順口訣選項**（`optRhyme`，內容區）：勾選後列印頁首顯示 8 種基本筆畫（橫豎撇點捺挑鈎折）+ 7 條筆順歌（先橫後直/先撇後捺/從上到下/從外到內/從左到右/進屋關門/先寫中央），每條附例字。筆順歌 7 條首加數字 1–7 排序。
- **新九宮格導線樣式**（`jiugong` 重設計）：由均等 3×3 改為 **22%/78% 非等分結字輔助格** — 中宮放大至 56%（寬大長方形，定位字心）、上下邊格扁平（規範捺撇提豎縱向伸展）、左右邊格狹長（規範偏旁開合）、四角最小（留白控制）。紅色雙線 `--red-grid`、`stroke-width:1.6`。與井字格（33.3/66.7 均等）清晰區分。

### Changed
- `index.html`：`guideSvg()` 新增 `g-hn3a/b`、`g-vn3a/b`（22%/78% 分割線）；`.guide-jiugong` 改用新線並設紅色粗度；`.cell-guides .g-center` 預設 `display:none`（井字格唔會漏出中宮框）。
- 導線選項 label：`九宮格（中宮）` → `新九宮格（3×3）`。

## [1.2.9] - 2026-09-16

Reported as「凹/凸 缺右下角 + 凹 上下倒轉 + 凸 筆順動畫由下而上」。三個獨立 root cause：

### Fixed
- **chain 數 > label 數時 blind trim 砍錯筆**（凹/凸 缺右下）：凹(EDB 320) 7 個動畫 chain 但官方 5 筆，舊 `picked[:5]` 直接砍走 delay 105+120（底橫 + 右下大塊）→ 右下角成筆消失。修法：`tools/edb_convert.py` 用 **label timing window 分組** — chain delay 落入邊個 label 區間（24/48/72/96/120ms）就併入邊一筆，同一筆嘅第二段 reveal（chain 36/105）合併而唔係當獨立 chain 砍走。全庫 diff：只有 凹/凸 兩字幾何改變，其餘 4,491 字不變。
- **flip 進度檔 hex 寫錯 → 凹 上下倒轉**：rebuild 凹(51f9) 時移除 progress 誤用 `533d.json` → `flip_glyphs.py` 跳過 → y-down 未反轉就 deploy。修法：補跑 flip+reframe，並喺 DEBUG.md 記低「`glyph_build_done.json` 用字元、`glyph_flip_done/reframe_done` 用檔名」嘅陷阱。
- **median 方向錯 → 凸 筆順動畫由下而上**：`build_glyphs.py` orient 邏輯對多段 chain 判斷錯起筆點。修法：直接反轉 `glyphs/51f8.json` 同 `glyphs/51f9.json` 相關筆畫嘅 `rec.m[i]`（HanziWriter 沿 median[0]→[-1] 起筆）。驗證：stored y-up 空間 start_y > end_y = 由上而下。

### Changed
- `tools/edb_convert.py`：label timing window 分組取代 blind trim（v14）。
- `glyphs/51f8.json`（凸）、`glyphs/51f9.json`（凹）：flip 修正 + median 方向反轉。
- `index.html`：`glyphs/*.json?v=12 → ?v=13`。
- 常用範例由 12 組增至 **32 組**（新增 家人/日子/衣物/水果/用具/叫聲/反義/百千/樹木/彩色，全部組間零重複；五行 → 金銀銅鐵錫、時間 → 早午晚夜 避重複）。
- 描紅字色 `#F5D5D0 → #F9E8E5`（更淺）。

## [1.2.8] - 2026-09-16

Reported as「兒 第一筆遺失；又/離 殘缺；你 第2筆直線過長」。全量重跑 parser + 重建 glyph，根因係兩個 parser 缺陷 + 一批 stale glyph：

### Fixed
- **9-arg `setTransform` 忽略 `regX/regY`**（你 等 27 字）：EDB 動畫偶用 `setTransform(x, y, sx, sy, rot, skx, sky, regX, regY)`，舊 parser 只讀頭兩個數 → shape 位置錯 273+ 單位。你 第2筆（亻豎）因此向下移 273 單位，睇落「直線過長」。修法：`_shape_origin()` 計 `x − regX·sx, y − regY·sy`。
- **多 shape final state 只取一個**（又/離/曙）：chain 最後一個 state 可能含**兩個 shape 合組一筆**（又 st1 = `[shape_10, shape_9]`，離 st8 = `[shape_33, shape_32]`），舊 parser 每 chain 只揀一個 → 又/離 殘缺。修法：`find_chains()` 記錄 final state 全部 name，`picked` 變 list-of-lists，`group_to_svg()` 合併。
- **Stale glyphs**（兒/兔/兗/兜/兢）：deployed glyph 係舊 parse 產物（兒 st1 得 25×40 碎片，正確 257×211）。全量重跑後 32 字重建（27 parser-fixed + 5 stale），全庫 4,493 字 fresh-parse 與 deployed 逐 path 比對 **0 stale**。

### Changed
- `tools/edb_convert.py`：`_shape_origin()`、`find_chains()` 新增 `final` 欄位、`stroke_bbox()`/`group_to_svg()`。
- `hk_order.js` 重生成（仍 671 overrides；你/兒/又/離 恢復 identity）。
- `glyphs/*.json?v=11 → ?v=12`。

## [1.2.7] - 2026-09-15

Reported as「你，離，兒 仍然有顯示問題」。經量度後，計數／筆順次序／數字所屬筆畫全部正確，但發現兩個真缺陷：

### Fixed
- **數字大過筆畫本身**（兒、離、你）：用 canvas `measureText` 量數字**真實墨跡**（`getBBox()` 係 em box，會遮蓋此問題）—— 數字墨跡 ÷ 筆畫厚度：兒 **2.15**、離 **1.51**（基準 先 = 0.77）。數字比佢標示嘅筆畫大成兩倍 → 睇落似「擺錯位」。現在每個數字按筆畫厚度設上限（1.8× 厚度；雙位數 2.36×/位），下限 45% 保可讀性。修後：兒 1.46、離 1.31、你 1.11、先 **0.77 不變**。
- **`孿` 22 筆只顯示 21 個數字**：第 17 筆中線退化成單點 `[[698.9, 460.6]]` → 所有候選回 null → 該筆冇任何數字。現在退化中線改用「保証喺自己墨跡內」嘅點做錨（全庫 7 筆屬此類，全部已補上數字）。
- **交叉筆畫上嘅數字碰撞**：數字若同時落在**鄰筆墨跡**上會被輕懲（低於 off-stroke 懲罰），並加寬側移範圍（±1.8em）。清除了 進 6/7（19%）、離 3/4、10/11、17/18 等碰撞。

### Changed
- `placeNumberLabels(medians, frame, hooks)`：原本嘅 `insideFn`/`inkPointFn` 加上 `size(i, digitCount)` 收成一個 `hooks` 物件（參數維持 3 個）。
- **測試用真墨跡量度**：`tools/sanity_numbers.js` 嘅碰撞判準改用實測數字墨跡尺寸（0.48em/位 寬、0.70em 高，來自 live 頁面 canvas 量度），取代原本偏大約 15% 嘅保守盒 —— 呢個偏差就係之前 ~2,000 個假警報嘅來源。同時輸出違規清單到 `/tmp/cw_offenders.json` 以便瀏覽器複核。

### Fixed（密集字數字疊住）
- 檢查器對全部 4,493 字報 196 個警報，瀏覽器逐字複核後 **169 個係真碰撞**（鬱/鸚 100%、霍 81%、鹽 77%）。修法：每個數字沿筆畫掃 **23 個位置 × 6 級縮小**（1→0.42），取第一個完全不撞嘅大小；目標函數由「絕對重疊面積」改為「**覆蓋比例**」（絕對面積會獎勵「兩個細數字完全疊埋」——實測 髏/璽/閣 因此退步，已修正）。
- 結果：警報 **196 → 25**；瀏覽器複核最終 **23 字（0.51%）** 仍有 >20% 墨跡重疊，全部係 15–29 筆嘅密集字（閣 60%、邇 59%、髒 55%、齪 46%、齡 44%、璽 42%…）。

### Tried and reverted
- **放寬「側移離開筆畫」嘅懲罰**：可清掉疊字，但數字會浮喺筆畫隔籬（暗/靜/髏/璽 實測中招）—— 正正係本層要避免嘅缺陷。已撤回並寫入程式註解。

### Verified (live, 部署後)
`孿`=22 筆/22 數字、`你`=7/7、`離`=19/19、`兒`=8/8；**0 個數字偏離自己筆畫**（逐個 `isPointInFill` 檢查）；全庫 54,474 個數字中 0 個錨點落在自己筆畫外。


## [1.2.6] - 2026-09-15

### Changed (refactor, no user-visible change except where noted)
- **`renderWorksheet` 170 → 57 行**：抽出 `charCardHtml` / `sentenceSectionHtml` / `setWsFooter` / `installGlyphLayer`。
- **消滅重複碼**：描紅格（字卡 vs 句格）本來有兩段近乎一樣的 11 行，而且標點規則唔一致 — 句格會將「。」標成有筆順數字嘅格。現在統一由 `traceCellHtml(ch, cellClass, opts)` 產生；**修正**：句格標點唔再被當成筆順格（本版唯一輸出差異）。
- **參數/資料整理**：`glyphFrame(rec)` 統一 {box, C, fs, viewBox}（原本三處各自計）；`placeNumberLabels(medians, frame, insideFn)`、`hkGlyphSvg(rec)` — 全部函數 ≤3 個參數。
- **移除死碼**：`zhVoiceSummary`、`hkGlyphSvg` 的 `opts.numbers`、3 個重複嘅 `const NS`（提升為 module 常數）。
- **資料管線入版控**：所有 parser / build / flip / reframe script 由 `/tmp` 移入 `tools/`（`CW_WORK` 可指定工作目錄），並附 `tools/README.md` 記錄流程與陷阱。此前所有 parser 修正只存在 /tmp，無法重現亦無測試。

### Added
- **Sanity testing（`tools/`）**：三個獨立檢查，每個都對應今日真出過嘅 bug —
  `sanity_data.py`（4,493 glyph：JSON/中線/方向/筆畫數/表一致性）、`sanity_parser.py`（重新解析 EDB 動畫並要求已出貨 glyph 可重現）、`sanity_numbers.js`（54,474 個數字：碰撞 + 錨點是否落喺自己筆畫內）。
- `docs/code-review.md`：12 項 code smell 嘅審查結果（已修 / 接受 / 不存在）＋刻意唔做嘅部分。

### Fixed
- **`導` 15→16 畫、`巍` 20→21 畫**：早前 label 計數 bug（將重複 timeline 嘅號碼 double count，再用「安全網」剪走真筆畫）令呢兩字少了一筆。label 改為取動畫顯示嘅**最大**號碼後，全量重新解析：4,491 字完全不變，只有呢兩字修正。
- `sanity_parser` 因此新增「已出貨 glyph 必須能由 parser 重現」嘅檢查 — 呢個缺口就係由佢捉出嚟。


## [1.2.5] - 2026-09-15

### Fixed
- **描紅數字跌落空白位（用戶報「兒」顯示錯誤）**：數字原本放在筆畫中心線的弧長中點，但短／幼筆畫的中點可能落在墨跡之外（兒的第 1 筆只有約 25 單位闊，數字 1 就飄在空白處），加上避撞用的側移亦可能把數字推到鄰筆之上。
  - 現在每個數字候選位置都要通過 **`path.isPointInFill()`** 驗證（必須落在自己那筆的墨跡內），否則重罰；仍會在多個候選中取重疊最少者。
  - ⚠️ 關鍵陷阱：**`isPointInFill()` 對未插入 DOM 的節點永遠回 `false`**（已實測，detached=false / attached=true）。由於數字本來在 `hkGlyphSvg()` 內、SVG 尚未 append 時計算，這個檢查會靜默失效。已改為 `addGlyphNumbers(svg)` 在 `installHKGlyphs()` **append 之後**才計算數字。
  - 驗證（live，用 `isPointInFill` 逐字檢查）：花/兒/先/個/進/香/鄭/雅/說 **全部 0 個數字偏離自己的筆畫**（修前 兒 #1、進 #7 偏離）。

### Added
- **無筆順字形字（STROKE_SEQ 197 字）的描紅格顯示次序文字**：這批字沒有任何筆畫輪廓，無法畫數字，所以改為在**第一個描紅格內**顯示漢典「笔顺编号」的逐筆類型次序（例：咗 → 豎折橫橫撇橫豎橫），螢幕與列印皆可，並附來源 tooltip；這些格不再標記為 `stroke-num-cell`。

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