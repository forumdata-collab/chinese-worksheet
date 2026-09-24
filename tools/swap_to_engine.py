# -*- coding: utf-8 -*-
"""Swap the inlined glyph engine in index.html for the shared glyph-engine.js script tag.

Verification: concatenating the removed spans + a marker line for the script tag must
reproduce the original file exactly (proves no lines were lost/moved).
"""
SRC = "/home/ubuntu/chinese-worksheet/index.html"
ENGINE = "/home/ubuntu/chinese-worksheet/glyph-engine.js"
lines = open(SRC, encoding="utf-8").read().split("\n")  # 0-idx

# 1-indexed inclusive spans to remove (must match the extractor)
SPANS = [(1599, 1649), (1651, 1890), (1892, 2197), (2392, 2514)]

# ── 1. proof of exactness: engine body == removed spans joined by exact separators ──
removed_parts = [lines[a - 1:b] for a, b in SPANS]
body = "\n\n".join("\n".join(p) for p in removed_parts)
engine_src = open(ENGINE, encoding="utf-8").read()
# body starts at the first "function applyHKOrder" line (line 20 today).
bi = engine_src.index("function applyHKOrder")
reconstructed = engine_src[bi:]
if reconstructed.endswith("\n"):
    reconstructed = reconstructed[:-1]
if reconstructed != body:
    print("!! ENGINE MISMATCH — extracted body differs from engine file")
    # diff first diff point
    for i, (a, b_) in enumerate(zip(reconstructed.split("\n"), body.split("\n"))):
        if a != b_:
            print(f"first diff at line {i}:")
            print("  engine:", a[:120])
            print("  file  :", b_[:120])
            break
    raise SystemExit(1)
print("extraction matches engine file ✓")

# ── 2. build the new file ──
out = []
skip = set()
for a, b in SPANS:
    skip.update(range(a - 1, b))
# collapse each removed span to ONE blank line (keep structure readable)
prev_removed = False
for i, ln in enumerate(lines):
    removed = (i in skip)
    if removed:
        if not prev_removed:
            out.append("")  # single blank line marker where code was
        prev_removed = True
    else:
        out.append(ln)
        prev_removed = False
new_src = "\n".join(out)

# ── 3. insert engine script tag after stroke_seq.js ──
tag = '<script src="glyph-engine.js?v=1"></script>'
anchor = '<script src="stroke_seq.js?v=3"></script>'
assert new_src.count(anchor) == 1
new_src = new_src.replace(anchor, anchor + "\n" + tag, 1)
open(SRC, "w", encoding="utf-8").write(new_src)
print(f"index.html rewritten: {len(lines)} → {len(new_src.splitlines())} lines")