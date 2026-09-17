// 通用筆順次序（逐筆類型）for characters with no EDB glyph and no HanziWriter data.
// 1=橫 2=豎 3=撇 4=點 5=折 — source: 漢典 zdic.net 「笔顺编号」, length == official
// stroke count (cross-checked against CHAR_DB 筆畫數 for all in-lexicon chars).
// Used only to SHOW the writing order for chars that have no stroke outlines at all.
window.STROKE_SEQ = {
  "撝": ["121344335554444", "橫豎橫撇點點撇撇折折折點點點點"],
};

