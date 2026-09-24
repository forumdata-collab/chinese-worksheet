// ===== 詞語圖解工作紙 — semantic.js =====
// 語義引擎:詞語 → 意思 + 6 個情境 + 標題(短語)。
// Phase 1: 本地 hardcoded 四個詞(快樂/分享/擺滿/度過)。
// Phase 2+: aiSemantic(word, grade) 接 AI API,失敗 fallback 返 hardcoded。
'use strict';

const SEMANTIC_VERSION = 'v1';

// 每個情境都有 scene(英文,俾 image generator 用)+ caption(繁體中文,顯示喺工作紙)。
const SEMANTIC_DB = {
  '快樂': {
    meaning: '心情很好、感到開心',
    examples: [
      { caption: '開心',      scene: 'child happily playing outdoors' },
      { caption: '幸福',      scene: 'child enjoying a happy family moment' },
      { caption: '歡樂',      scene: 'children happily playing together' },
      { caption: '收到禮物',  scene: 'child receiving a present' },
      { caption: '和寵物玩',  scene: 'child playing with a dog' },
      { caption: '吃冰淇淋',  scene: 'child eating ice cream happily' },
    ],
  },
  '分享': {
    meaning: '把自己的東西、食物或成果和別人一起使用或欣賞',
    examples: [
      { caption: '分吃',      scene: 'children sharing watermelon' },
      { caption: '給予',      scene: 'child giving a toy to another child' },
      { caption: '講故事',    scene: 'child telling a story to friends' },
      { caption: '合作',      scene: 'children working together' },
      { caption: '請客',      scene: 'children sharing food at a table' },
      { caption: '分享成果',  scene: 'children showing artwork to friends' },
    ],
  },
  '擺滿': {
    meaning: '東西放得很多，把一個地方放得滿滿的',
    examples: [
      { caption: '擺滿了書桌',    scene: 'desk covered with books and stationery' },
      { caption: '擺滿了廚房用品','scene': 'kitchen counter full of utensils' },
      { caption: '擺滿了飾品',    scene: 'shelf full of decorative objects' },
      { caption: '擺滿了書籍與雜物','scene': 'room filled with books and objects' },
      { caption: '擺滿了水果',    scene: 'fruit stall full of fresh fruit' },
      { caption: '擺滿了派對食物','scene': 'party table filled with food' },
    ],
  },
  '度過': {
    meaning: '經歷一段時間',
    examples: [
      { caption: '度過週末',  scene: 'family enjoying a weekend picnic' },
      { caption: '度過假期',  scene: 'children playing at the beach during holiday' },
      { caption: '度過學期',  scene: 'child studying at a desk' },
      { caption: '度過時光',  scene: 'grandparent and child reading together' },
      { caption: '度過下午',  scene: 'child relaxing and reading in the afternoon' },
      { caption: '度過生日',  scene: 'family celebrating a birthday' },
    ],
  },
};

// 詞語解析:支援 2–4 字詞(亦可用空格分隔多個詞)。淨係提取字面。
function parseWord(raw) {
  if (!raw) return null;
  const word = String(raw).replace(/[　\s]+/g, '').replace(/[，。、！？,.!?；;：:]/g, '');
  if (!word) return null;
  return word;
}

// 主查詢:詞語 → semantic 對象(意思 + 6 個例子)。
// Phase 1 只有 hardcoded;AI 版會喺呢度接駁。
function semanticFor(word) {
  const entry = SEMANTIC_DB[word];
  if (entry) {
    return {
      word,
      grade: null,
      meaning: entry.meaning,
      version: SEMANTIC_VERSION,
      source: 'local',
      examples: entry.examples.map((e, i) => ({ id: String(i + 1).padStart(2, '0'), ...e })),
    };
  }
  return null; // 未收錄 → 交由 AI(Phase 2)/提示
}

// 唔喺 hardcoded 表 → 有冇本地相近詞?冇就回 null。
function hasLocalSemantic(word) {
  return !!SEMANTIC_DB[word];
}

// Phase 2:AI 語義生成(經 picture-api worker,免費 CF 模型)→ JSON。失敗 fallback 本地。
// ⚠️ 一定要 timeout:gpt-oss-120b 有時要 20-30s,用戶會以為「冇反應」。
async function aiSemantic(word, grade) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 20000);
  try {
    const r = await fetch('https://picture-api.forumdata.workers.dev/semantic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word, grade: grade || 'P1' }),
      signal: ctrl.signal,
    });
    const d = await r.json();
    if (d && d.meaning && Array.isArray(d.examples) && d.examples.length >= 4) {
      // 例子少過 6 都照用(唔好因為差一張就成張紙失敗);多過 6 截返 6
      const ex = d.examples.slice(0, 6);
      return {
        word,
        grade,
        meaning: d.meaning,
        version: 'v1',
        source: 'ai',
        examples: ex.map((e, i) => ({
          id: String(i + 1).padStart(2, '0'),
          caption: String(e.caption || '').trim(),
          scene: String(e.scene || '').trim(),
        })),
      };
    }
  } catch (e) { /* timeout / network / parse — fallthrough */ }
  finally { clearTimeout(timer); }
  return null;
}

if (typeof module !== 'undefined') module.exports = { SEMANTIC_DB, semanticFor, parseWord, hasLocalSemantic, SEMANTIC_VERSION };