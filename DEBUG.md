# DEBUG.md — 字形 / 筆順 / 數字診斷手冊

用於排查 chineseword.we1co.me 嘅三層問題：EDB 字形資料、筆順數字、glyph pipeline。
每個 bug class 都對應一個**真出過**嘅案例；改任何 parser / 資料層前先讀呢篇。

---

## 1. 症狀 → 根因速查

| 症狀 | 最先懷疑 | 案例 |
| --- | --- | --- |
| 字形缺筆／殘缺 | 多-shape final state 被丟 | 又 st1 = `[shape_10, shape_9]`，舊 parser 只取 shape_9（細碎片）→ 主體消失 |
| 筆畫位置整體偏移 | 9-arg `setTransform` 忽略 regX/regY | 你 亻豎 被畫低 273 單位（「第2筆直線過長」） |
| 第一筆唔見／出現小碎片 | stale deployed glyph（舊 parse 產物） | 兒 st1 係 25×40 碎片，正確係 257×211 撇 |
| 數字疊住／飄走 | number-layer bug（見第 5 節） | 噠 11/12 疊 33×33px；兒 #1 飄落空白 |
| 字形上下倒轉 | y-flip 雙重套用 | stored 必須 y-up；前端 `translate(0,C) scale(1,-1)` 還原 |
| 筆畫數多／少 | label 計數陷阱（v12 系列） | 三 得 2 畫；山 2/3；先 5/6 |

---

## 2. 三層架構（改之前先搞清楚）

```
EDB 動畫 JS (edbchinese.hk)
   │  tools/edb_convert.py  (parser, v14)
   ▼
edb_svg_strokes.json        ← 逐字 {strokes: [path…]}，EDB 1080-space y-down
   │  tools/build_glyphs.py + flip_glyphs.py + reframe_glyphs.py
   ▼
glyphs/<hex>.json           ← {s:[stroke path…], m:[[[x,y]…]…]}，y-up + HW reframe
   │  index.html hkGlyphSvg() / addGlyphNumbers()
   ▼
螢幕 / 列印
```

- **EDB 字**：字形 + 數字都用 `glyphs/<hex>.json` 嘅 `s` + `m`（同一 frame）。
- **非 EDB 字**（~1000 字）：font 字形 + HanziWriter 資料 + `applyHKOrder()`，`overlayStrokeNum()` 放數字。
- **完全冇資料**（197 字）：`STROKE_SEQ` 顯示筆順次序文字，筆順／試寫按鈕灰掉。

---

## 3. 診斷流程（字有問題時按序做）

### Step 1 — parser 一致性（最快）
```bash
python3 tools/sanity_parser.py --verbose
```
檢查：fresh parse（raw EDB 動畫）vs deployed glyph 筆畫數。`chain < label` = parser 漏筆。

### Step 2 — 幾何一致性（全庫，重點）
sanity_parser 只比筆畫數、**唔比對幾何** → stale glyph 會漏網（兒 案例）。

```bash
python3 tools/sanity_geom.py      # fresh parse → strip → flip → reframe，同 deployed 逐 path 比對
```
- 每字：`parse_edb_js` → `group_to_svg` → strip spaces → y-flip → HW reframe，
  同 `glyphs/<hex>.json` 嘅 `s` 比對；max delta > 0.3 先算 stale（<0.3 = 亞像素 rounding）。
- **關鍵常數**：flip C = 該字 ink bbox y0+y1；reframe scale = min(HW_w/ow, HW_h/oh) 中心對齊。
- 正常狀態：**4493/4493 0 stale**（756 字 sub-pixel drift 屬正常，係 parser rounding 演進）。

### Step 3 — 數字層（browser 權威驗證）
```bash
node tools/sanity_numbers.js --verbose
```
- 數字必須喺**自己**筆畫墨跡內（`isPointInFill`，stored space：`new DOMPoint(cx, C - cy)`）。
- 碰撞用**真實墨跡**量度（0.48em/位 寬、0.70em 高），唔好用 em box。
- >20% 重疊先算問題；密集字（鬱/鸚/鹽/髏/璽）有 ~23-25 個已知殘餘，屬「短筆無法避開」，唔係 regression。

### Step 4 — 目視
用 headless chromium 渲染實際 glyph + 數字：
```bash
cd ~/chinese-worksheet && python3 -m http.server 8891
# 建一個 eval index.html 真實 placeNumberLabels/addGlyphNumbers 嘅測試頁
~/.cache/ms-playwright/chromium_headless_shell-1234/chrome-linux/headless_shell \
  --headless --no-sandbox --screenshot=/tmp/x.png --window-size=500,400 \
  http://localhost:8891/test.html
```
⚠️ 唔好用 vision 判斷字形（多次誤判：重=里+東、來 7 筆、個/固 底部）。以 isPointInFill + DOM rect 為準。

---

## 4. Parser 已知陷阱（edb_convert.py，v14）

1. **9-arg `setTransform(x,y,sx,sy,rot,skx,sky,regX,regY)`**：最後兩個係 registration point，
   有效位置 = `(x − regX·sx, y − regY·sy)`。只讀頭兩個會令 shape 偏移（你 案例 +273）。
   全庫 37 個 9-arg call（30 檔）；4 檔（仟/卒/協/南）仲要 scale≈10.6。
2. **chain 最後一個 state 可以含多個 shape 合組一筆**：又 st1 `[shape_10, shape_9]`、
   離 st8 `[shape_33, shape_32]`。`find_chains()` 要記錄 `final`（最後 state 全部 name），
   `picked` 係 list-of-lists，`group_to_svg()` 併成單一路徑。
   ⚠️ 但 10 個字（凹/睏/睽/瞠/聿/鑣/鑠/鑲/鑰/鑿）兩個 shape 幾何**完全重疊**（fill+outline），
   揀邊個都一樣 → 唔會觸發 bug。判斷方法：`old==new` diff parser 輸出。
3. **label 計數兩種格式**：`to({text:"N"},0)` 多數 + state-based `p:{text:"N"}`（三）。
4. **label 會落後實際筆畫**（先 5/6、京 7/8）→ 只喺 label == CHAR_DB 兩個獨立來源一致且
   細過 chain 數時先 trim。
5. **同 delay 合併會吞真筆畫**：合併前先剔除含 `text*` name 嘅 chain（數字標籤 tween）。
6. **show-all block 唔係筆順**：順序沿用動畫 chain，只係用 bbox 配對換上最終 shape；
   `len(fin) != len(picked)` 就完全唔替換（名/印/韋 假陽性）。
7. **chain 數 > label 數時 blind trim 砍錯筆（v14）**：凹(320) 7 chain / 5 label，
   舊 `picked[:5]` 砍走 delay 105+120（底橫 shape_7 + 右下 shape_4）→ 缺右下角。
   修法：用 **label timing window** 分組 — chain delay 落入邊個 label 區間就併入邊筆
   （label 1-5 喺 24/48/72/96/120ms；chain 36 同 105 喺區間內 = 同一筆第二段，合併唔好砍）。
   影響：凹/凸 兩字幾何改變，其餘 4491 字不變（diff edb_svg_strokes.json 驗證）。
8. **median 方向錯 → 動畫由下而上（v14）**：build_glyphs orient 邏輯對多段 chain 判斷錯起筆點。
   修法：直接反轉 glyph JSON 嘅 `rec.m[i]`（HanziWriter 沿 median[0]→[-1] 畫）。
   驗證：stored y-up 空間 **start_y > end_y = 由上而下 ✓**；動畫方向錯唔會影響字形/數字，
   只影響筆順動畫起筆位置。

**改完 parser 必做**：
```bash
cd ~/chinese-worksheet/tools
python3 edb_convert.py          # 全庫重 parse（4493 字）
# diff old vs new edb_svg_strokes.json → 受影響字清單
# rebuild-only-changed flow（見第 6 節）
```

---

## 5. 數字層已知陷阱（index.html placeNumberLabels / addGlyphNumbers）

1. **`isPointInFill()` 對未插入 DOM 嘅節點永遠 false** → 數字必須喺 `appendChild()` 之後先放。
2. **中點可能唔喺墨跡內**（兒 #1：短／幼筆弧長中點跌出筆畫）→ 候選點必須 `isPointInFill` 自驗。
3. **中線可以完全唔入自己筆畫**（幼/強彎筆）→ `inkPointFn(i)` 提供保証喺 fill 內嘅點做最後手段。
4. **數字唔可以大過筆畫**：size cap = `min(fs, 1.8×thick, 2.36×thick/位數)`，floor 45%。
5. **碰撞盒模擬真實墨跡**：寬 0.55em×位數、高由基線向上 0.72em，唔係以 cy 居中。
6. **密集字縮小避撞**：23 個弧長位置 × 6 級縮小（1→0.42），取第一個零碰撞。
7. **謎之 `#2 唔喺自己筆畫` 嘅假警報**：polygon 測試係近似；browser `isPointInFill`
   （`hits.includes(n)`）先係權威。交叉筆畫（花 #3、導 #4）一點可以同時喺兩筆內。

---

## 6. Rebuild-only-changed flow（避免 10 分鐘全量重建）

```bash
# 1. 計 changed chars（old vs new edb_svg_strokes.json）
# 2. 從進度檔移除（⚠️ key 格式唔同）：
python3 - <<'EOF'
import json
rebuild = [...]   # 受影響字 list
hexes = ['%x.json' % ord(c) for c in rebuild]
for f, key in [('/tmp/glyph_build_done.json', 'char'),
               ('/tmp/glyph_flip_done.json', 'file'),
               ('/tmp/reframe_done.json', 'file')]:
    d = json.load(open(f))
    d = [x for x in d if x not in (set(rebuild) if key=='char' else set(hexes))]
    json.dump(d, open(f,'w'), ensure_ascii=False)
# 3. HK_ORDER 進度（/tmp/hk_iou_progress.json）都要 pop 走受影響字
EOF
cd ~/chinese-worksheet/tools
python3 build_glyphs.py      # to build: N
python3 flip_glyphs.py       # to flip: N
python3 reframe_glyphs.py    # to reframe: N（唔使刪成個 reframe_done.json，只移走 N 個）
cd /tmp && python3 build_perm_iou.py   # 重生成 hk_order.js
cp /tmp/hk_order_iou.js ~/chinese-worksheet/hk_order.js
# 4. bump index.html hkGlyph() 嘅 ?v=N（glyphs cache-bust）
# 5. sanity 全套 + deploy + git push + CHANGELOG
```

⚠️ `glyph_build_done.json` 存**字元**（`先`），`glyph_flip_done.json` / `reframe_done.json`
存**檔名**（`5148.json`）— 用錯 key 會靜默 `removed 0` 然後跳過該步驟 → 字形上下倒轉。

---

## 7. 部署 + 同步

```bash
cd ~/chinese-worksheet
# bump ?v=N in index.html (hkGlyph)
export $(grep -v '^#' ~/.hermes/.env | grep -E 'CF_ACCOUNT_ID|CF_WORKERS_TOKEN' | xargs)
export CLOUDFLARE_API_TOKEN=$CF_WORKERS_TOKEN
wrangler pages deploy . --project-name=chineseword-we1co --branch=main
git add -A && git commit -m "..." && git push origin main
# CHANGELOG.md 加條目；README 字形覆蓋／筆順次序數字如有變要同步
```

---

## 8. 相關檔案

| 檔案 | 用途 |
| --- | --- |
| `tools/edb_convert.py` | EDB 動畫 parser（v14；regX/regY + multi-shape final + label-window 分組） |
| `tools/sanity_parser.py` | parser vs deployed 筆畫數一致性 |
| `tools/sanity_geom.py` | **幾何**一致性：fresh parse 全鏈路 vs deployed 逐 path（stale glyph 檢測） |
| `tools/sanity_data.py` | glyph JSON 完整性 + medians 對齊 + y-up 方向 |
| `tools/sanity_numbers.js` | 數字碰撞 + 錨點歸屬（node 跑） |
| `tools/build_glyphs.py` / `flip_glyphs.py` / `reframe_glyphs.py` | glyph pipeline |
| `docs/stroke-data-notes.md` | 筆順資料來源調查 |
| `docs/code-review.md` | 2026-09-15 code review 記錄 |
| `hk_order.js` | 671 個筆順次序 override（`window.HK_ORDER`） |
| `stroke_seq.js` | 197 個無字形字嘅筆順次序文字 |
