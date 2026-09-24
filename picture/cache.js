// ===== 詞語圖解工作紙 — cache.js =====
// 確定性 cache key:SHA-256(word|scene|style|grade|semanticVersion)。
// Phase 1: 本地 localStorage cache(唔使 server);Phase 4+: R2 接駁。
'use strict';

// 由場景字典嘅 key 組成 cache key 嘅 input(與 R2 路徑格式一致)
function cacheKeyFor({ word, scene, style, grade, version }) {
  const raw = [word, scene, style, grade, version || SEMANTIC_VERSION].join('|');
  return sha256Hex(raw);
}

// 純 JS SHA-256(Web Crypto,async;localStorage 版用同步 fallback 就唔掂,所以都 async)
async function cacheKeyForAsync({ word, scene, style, grade, version }) {
  const raw = [word, scene, style, grade, version || 'v1'].join('|');
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

// ── Phase 1:localStorage 圖片 cache ──
// key: 'picimg:<sha256>' → dataURL / URL。localStorage 有 ~5MB 上限,
// 所以用 try/catch 包住,寫爆就靜默放棄(唔會整死工作紙)。
const LS_PREFIX = 'picimg:';

function lsGet(key) {
  try { return localStorage.getItem(LS_PREFIX + key); } catch (e) { return null; }
}
function lsSet(key, value) {
  try {
    localStorage.setItem(LS_PREFIX + key, value);
    return true;
  } catch (e) { return false; }
}

// 查 cache:word+scene+style+grade → 有就回 URL/dataURL,冇就 null
async function cacheLookup(params) {
  const key = await cacheKeyForAsync(params);
  const hit = lsGet(key);
  return hit ? { key, value: hit } : { key, value: null };
}

// 寫 cache(Phase 1 local;Phase 4 加 R2 upload)
async function cacheStore(params, value) {
  const key = await cacheKeyForAsync(params);
  lsSet(key, value);
  return key;
}

// R2 路徑(Phase 4):R2/worksheets/<word>/<hash>-NN.webp
function r2PathFor(params, idx) {
  return `worksheets/${encodeURIComponent(params.word)}/${params.key}-${idx}.webp`;
}

if (typeof module !== 'undefined') module.exports = { cacheKeyFor, cacheKeyForAsync, cacheLookup, cacheStore, r2PathFor };