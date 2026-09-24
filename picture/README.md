# 中文詞語圖解工作紙生成器

位置: `/picture/`(子目錄,獨立於主站)

輸入中文詞語(如「快樂」)→ 生成 A4 印刷版認字工作紙:
大楷香港標準字形 + 筆順數字 + 詞義 + 6 幅情境插圖(3×2)。

## 架構(spec §34 分離原則)

```
輸入詞語 → 字形引擎(共用) → 語義引擎 → 單張插圖 → HTML/SVG 版面 → A4 預覽/列印
```

- **字形/筆順完全重用主站引擎**:`../glyph-engine.js`(2026-09-24 由主站 index.html 抽離共享)— HK 教育局字形、HK 筆順次序、筆順數字避撞,同主站一模一樣。
- **AI 只負責語義 + 單張插圖**,永遠唔會生成成張工作紙(字形/排版由自家 engine + CSS 出)。
- **插圖冇文字**(spec §13):意思由畫面表達,標題由 renderer 加。

## 檔案

| 檔案 | 職責 |
|---|---|
| `index.html` | UI + 主流程(輸入/年級/風格/產生/列印) |
| `picture.css` | A4 210×297mm 版面 + 列印樣式(`@page size: A4 portrait; margin:0`) |
| `semantic.js` | 詞語 → 意思 + 6 情境(本地 hardcoded 4 詞;Phase 2 接 AI) |
| `image-generator.js` | 單張插圖(Phase 1 placeholder SVG;Phase 3 接 AI image API) |
| `worksheet-renderer.js` | A4 版面:大楷字形 + 筆順數字 + 3×2 圖格 + 標題 |
| `cache.js` | 確定性 cache key(word\|scene\|style\|grade\|version);Phase 1 local,Phase 4 R2 |

## 共享引擎(重要)

`../glyph-engine.js` 係主站 `index.html` 抽離出嚟嘅共享 glyph 引擎(2026-09-24):
`hkGlyph` / `hkGlyphSvg` / `addGlyphNumbers` / `placeNumberLabels` / `appendStrokeArrows` /
`measureInkFrame` / `partialGlyphSvg` / `addStepNumber` / `strokeCountOf` / `applyHKOrder` 等 21 個函數。

⚠️ **改主站字形邏輯時,兩邊一齊用呢個檔** — 唔好再喺 index.html 內嵌一份(會 drift)。
改完 engine 要 bump 兩個引用:主站 index.html 同 picture/index.html 嘅 `glyph-engine.js?v=N`。

## Phase 進度

- [x] Phase 1 — Renderer(四硬編詞、placeholder 圖、A4 列印)
- [x] Phase 2 — AI 語義(經 picture-api worker gpt-oss-120b;失敗 fallback 本地四詞)
- [x] Phase 3 — AI 單張插圖(經 picture-api worker flux-1-schnell 黑白線稿)
- [x] Phase 4 — R2 cache(worker 內建,確定性 SHA-256 key,同價命中 0.1s)
- [ ] Phase 5 — 進階(播放筆順 / 重新生單張 / 改 caption / 下載 PDF 等)

## AI 後端(picture-api worker)

`~/picture-api/`(獨立部署,`picture-api.forumdata.workers.dev`):
- `POST /semantic` — gpt-oss-120b(CF 免費)→ meaning + 6 情境 JSON
- `POST /image` — flux-1-schnell(CF 免費,~57.6 neurons/張)→ 存 R2 `pic-worksheets` → 派 `/image/<sha256>` URL
- `GET /image/<sha256>` — R2 直派圖(Cache-Control immutable)
- ⚠️ CF 免費 tier 限制:**每日 10,000 neurons(~170 張)**、**1 個並行請求**(前端已設串行 + 120ms gap)
- 秘密(Cf key)只存 worker binding,前端零 secret(spec §25)
- 認證後備:cf-manager DB 解密(`X-Auth-Email + X-Auth-Key`,入 skill cloudflare-workers-ai)

## 驗證(Phase 1)

- 四詞:快樂 / 分享 / 擺滿 / 度過 全部生成成功
- 每詞:2 大楷字形(SVG)+ 筆順數字 + 6 圖格 + 6 標題
- A4 列印:210mm 寬、零溢出、無裁剪
- 主站(index.html)不受影響:抽離 engine 後回歸測試通過
- 未收錄字(如「𠮷」)→ 提示「暫時未有香港標準字形資料」,唔會靜默替代
