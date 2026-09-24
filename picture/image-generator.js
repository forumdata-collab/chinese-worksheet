// ===== 詞語圖解工作紙 — image-generator.js =====
// 圖片生成:淨係單張插圖(永遠唔會生成成張工作紙)。
// Phase 1: placeholder SVG(黑白線稿風格,內建小場景)。Phase 3+: AI image API + R2 cache。
'use strict';

// 風格定義(UI 三選:黑白線稿/彩色兒童插畫/真實照片)
const STYLES = {
  'line':  { label: '黑白線稿',    promptStyle: 'black-and-white educational children line art, simple clean outlines, white background, no shading' },
  'color': { label: '彩色兒童插畫', promptStyle: 'colorful friendly children book illustration, simple shapes, soft pastel palette, white background' },
  'photo': { label: '真實照片',    promptStyle: 'realistic photo, natural lighting, shallow depth of field, white background' },
};
const STYLE_KEYS = ['line', 'color', 'photo'];
const STYLE_LABELS = STYLE_KEYS.map(k => STYLES[k].label);

// Phase 1 placeholder:由 scene 生成一個簡單嘅黑白 SVG 插圖
// (冇文字/冇漢字,符合 spec §13)。用 emoji 作為視覺佔位,將來 AI 版直接換 URL。
function placeholderSvgFor(scene, styleKey) {
  const s = String(scene || '').toLowerCase();
  const emoji = sceneEmoji(s);
  const color = styleKey === 'color' ? '#5b8def' : (styleKey === 'photo' ? '#888' : '#333');
  const svg = `
  <svg viewBox="0 0 200 160" xmlns="http://www.w3.org/2000/svg" role="img">
    <rect width="200" height="160" fill="#ffffff" rx="8"/>
    <circle cx="100" cy="80" r="56" fill="none" stroke="${color}" stroke-width="2.5" stroke-dasharray="6 6" opacity="0.35"/>
    <text x="100" y="96" font-size="58" text-anchor="middle" dominant-baseline="middle">${emoji}</text>
    <text x="100" y="146" font-size="9" fill="#999" text-anchor="middle" opacity="0"></text>
  </svg>`;
  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
}

// scene 字串 → 代表性 emoji(純視覺佔位;AI 版唔會用)
function sceneEmoji(scene) {
  const s = scene || '';
  const table = [
    ['watermelon', '🍉'], ['ice cream', '🍦'], ['dog', '🐶'], ['gift', '🎁'],
    ['present', '🎁'], ['birthday', '🎂'], ['beach', '🏖️'], ['picnic', '🧺'],
    ['book', '📚'], ['read', '📖'], ['study', '📝'], ['desk', '🪑'],
    ['kitchen', '🍳'], ['shelf', '🛋️'], ['room', '🏠'], ['fruit', '🍎'],
    ['food', '🍽️'], ['toy', '🧸'], ['story', '📖'], ['friend', '🧑‍🤝‍🧑'],
    ['family', '👨‍👩‍👧‍👦'], ['outdoor', '🌳'], ['play', '🪁'], ['artwork', '🎨'],
    ['together', '👫'], ['table', '🍽️'], ['decorative', '🏺'], ['stationery', '✏️'],
    ['vegetable', '🥬'], ['stall', '🍉'],
  ];
  for (const [k, e] of table) if (s.includes(k)) return e;
  return '🌟';
}

// 圖片 prompt(Phase 3 AI 版用):scene + style → 完整英文 prompt,規格同 spec §12 一致
function buildImagePrompt(scene, styleKey) {
  const st = STYLES[styleKey] || STYLES.line;
  return `Create a ${st.promptStyle} illustration for Hong Kong primary-school children.

Scene:
${scene}

Requirements:
- clear action
- friendly children's workbook style
- simple clean outlines
- white background
- no text
- no Chinese characters
- no numbers
- no letters
- no logo
- no watermark
- no border
- landscape composition`;
}

// 主入口:scene+style → 圖片 URL。API 後端(picture-api worker)生圖 + R2 cache。
const API_BASE = 'https://picture-api.forumdata.workers.dev';

async function imageFor({ word, scene, caption, style, grade, version }) {
  try {
    const r = await fetch(API_BASE + '/image', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word, scene, style: style || 'line', grade: grade || 'P1', version: version || 'v1' }),
    });
    const d = await r.json();
    if (d && d.url) return { url: API_BASE + d.url, error: null };
    if (d && (d.error || d.detail)) {
      // ⚠️ worker 可能回 {error, detail} — 4006 可能喺 detail,合併檢查
      return { url: null, error: String(d.error || '') + ' ' + String(d.detail || '') };
    }
  } catch (e) { /* fallthrough */ }
  return { url: null, error: 'network' };
}

if (typeof module !== 'undefined') module.exports = { STYLES, STYLE_KEYS, STYLE_LABELS, placeholderSvgFor, buildImagePrompt, imageFor };