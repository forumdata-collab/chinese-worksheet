"""EDB stroke-order extractor v11.

v11 changes vs v10:
  * the "show-all" final-glyph block is located with PLAIN STRING ops, not regex.
    The v10 regex silently failed to match (no backslashes involved in the JS, so
    the pattern was at fault), which meant every character kept using the
    animation's progressive sub-shapes -- those differ from the final glyph on some
    characters.  個 id=189 was the visible victim: its bottom stroke came from an
    intermediate sub-shape that overshoots left under 亻, so 人 and 固 looked joined
    by a baseline that EDB never draws (user: "官方的人與固是分開").
  * number-label count now also understands the state-based p:{text:"N"} format (三).
"""

import re
import os
import json
from createjs_decode import decode_createjs_path
# --- work directory (all scratch data lives here; CW_WORK overrides) ---------
import os as _os
WORK = _os.environ.get('CW_WORK', '/tmp')
def wpath(*parts):
    return _os.path.join(WORK, *parts)




def _load_db_counts():
    """EDB id -> CHAR_DB 筆畫數 (Unihan kTotalStrokes); an independent count source."""
    try:
        dbfile = open('/home/ubuntu/chinese-worksheet/data.js', encoding='utf-8').read()
        db = json.loads(re.search(r'window\.CHAR_DB\s*=\s*(\{.*\});?\s*$', dbfile, re.DOTALL).group(1))
        idmap = json.load(open(wpath('edb_id_map.json')))['mapping']
        return {v: (db.get(k) or {}).get('s', 0) for k, v in idmap.items()}
    except Exception:
        return {}


db_counts = _load_db_counts()

HEAD_SHOWALL = 'addTween(cjs.Tween.get({}).to({state:['
HEAD_CHAIN = 'addTween(cjs.Tween.get({}).to({state:[]})'
HEAD_TEXTTWEEN = 'addTween(cjs.Tween.get(this.'


def is_ink(color):
    try:
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        return r < 0x40 and g < 0x40 and b < 0x40
    except Exception:
        return False


def _name_of(seg):
    """'{t:this.shape_44}' -> 'shape_44'"""
    return seg.split('t:this.')[-1].strip().rstrip('}')


def find_showall(js):
    """Final-glyph shapes, in stroke order.  These carry the completed stroke
    geometry (and are drawn grey in the animation).  Returns [] when absent."""
    out = []
    pos = 0
    while True:
        p = js.find(HEAD_SHOWALL, pos)
        if p < 0:
            break
        start = p + len(HEAD_SHOWALL)
        q = js.find(']', start)
        after = js[q + 1:q + 9]
        # a stroke chain stores its delay inside the .to(...) call, i.e. '},240)';
        # the show-all state is a bare list followed by '}).wait('
        if after.startswith('}).wait('):
            names = [_name_of(s) for s in js[start:q].split(',') if 't:this.' in s]
            if names and all(n and not n.startswith('text') for n in names):
                out.append(names)
        pos = q + 1
    return max(out, key=len) if out else []


def find_chains(js):
    """[{delay, final, names}] for every animated stroke-progress chain.

    `final` = the names in the LAST state — the completed stroke.  A chain's
    final state may hold MULTIPLE shapes that together form ONE stroke
    (又 id=462: state ends [shape_10, shape_9]; 離 id=4428: [shape_33, shape_32])
    — earlier states are partial reveals of the same stroke, only the last
    state's shapes matter for geometry.  `names` keeps the flattened list so
    the same-delay merge below can compare chain lengths.

    NOTE: keep this on the proven regex — a plain-string variant that anchored on
    '.to({state:[]})' silently dropped chains whose first state is non-empty
    (鋸 id=? lost its opening stroke -> 15 instead of 16)."""
    chains = []
    pat_block = re.compile(r'addTween\(cjs\.Tween\.get\(\{\}\)\.to\(\{state:\[[^\]]*\]\}\)(.*?)\);', re.DOTALL)
    pat_step = re.compile(r'\.to\(\{state:\[([^\]]*)\]\},(\d+)\)')
    for m in pat_block.finditer(js):
        steps = pat_step.findall(m.group(1))
        if not steps:
            continue
        names = []
        for chunk, _ in steps:
            names.extend(re.findall(r'this\.(\w+)', chunk))
        final = re.findall(r'this\.(\w+)', steps[-1][0])
        chains.append({'delay': int(steps[0][1]), 'final': final, 'names': names})
    return chains


def find_offset_chains(js):
    """Format B: addTween(cjs.Tween.get(this.shape).wait(N).to({_off:false}..."""
    out = []
    pos = 0
    marker = '.wait('
    needle = 'addTween(cjs.Tween.get(this.'
    while True:
        p = js.find(needle, pos)
        if p < 0:
            break
        end = js.find(');', p)
        body = js[p:end + 2]
        if '_off:false' in body:
            name = body[len(needle):].split(')')[0]
            wp = body.find(marker)
            wq = body.find(')', wp)
            try:
                out.append({'delay': int(body[wp + len(marker):wq]), 'final': [name], 'names': [name]})
            except ValueError:
                pass
        pos = end + 2
    return out


def label_count(js):
    """Highest number the animation's label actually displays.

    Two label encodings exist and BOTH may carry extra props before the text
    (山: to({x:76.2,y:22.1,text:"3"},0) — the old ^to({text:"N"} regex missed it and
    reported 2 for a 3-stroke char).  The label starts at "1" implicitly (it is shown
    with to({_off:false})), so the count is 1 + number of number-setting transitions.
    NOTE: the label can LAG the drawing (先 shows 1..5 for 6 strokes), so it is a hint,
    never the authority."""
    # NOTE: use the MAXIMUM number displayed, not 1+len(transitions): a file whose
    # timeline is duplicated (名 id=501) lists the numbers twice, which made the count
    # 11 for a 6-stroke character.
    trans = re.findall(r'to\(\{[^}]*text:"(\d+)"[^}]*\},0\)', js)
    if trans:
        return max(int(t) for t in trans)
    n = len(re.findall(r'p:\{text:"', js))
    return n


def _shape_origin(shape):
    """Effective path origin after setTransform (CreateJS: translate(x,y) then
    rotate/skew/scale then translate(-regX,-regY)).  EDB uses 2-arg setTransform
    (x,y) or 9-arg (x,y,sx,sy,rot,skx,sky,regX,regY); rotation/skew are always 0
    in the 9-arg forms we have seen, so origin = (x - regX*sx, y - regY*sy)."""
    if 'x' not in shape:
        return 0.0, 0.0
    sx = shape.get('sx', 1.0)
    sy = shape.get('sy', 1.0)
    rx = shape.get('regX', 0.0)
    ry = shape.get('regY', 0.0)
    return shape['x'] - rx * sx, shape['y'] - ry * sy


def bbox(shape):
    if not shape or 'x' not in shape:
        return None
    ox, oy = _shape_origin(shape)
    xs, ys = [], []
    for cmd in decode_createjs_path(shape['path']):
        if cmd[0] == 'Z':
            continue
        for i in range(1, len(cmd), 2):
            xs.append(ox + cmd[i] * shape.get('sx', 1.0))
            ys.append(oy + cmd[i + 1] * shape.get('sy', 1.0))
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def parse_edb_js(path):
    js = open(path, encoding='utf-8', errors='replace').read()

    shapes = {}
    for m in re.finditer(r'this\.(\w+)\.graphics\.f\("#([0-9A-Fa-f]{6})"\)\.s\(\)\.p\("([^"]*)"\)', js):
        shapes[m.group(1)] = {'color': m.group(2), 'path': m.group(3)}
    for m in re.finditer(r'this\.(\w+)\.setTransform\(([^)]+)\)', js):
        vals = [float(x) for x in m.group(2).split(',')]
        if m.group(1) in shapes:
            shapes[m.group(1)]['x'] = vals[0]
            shapes[m.group(1)]['y'] = vals[1]
            if len(vals) >= 9:
                shapes[m.group(1)]['sx'] = vals[2]
                shapes[m.group(1)]['sy'] = vals[3]
                shapes[m.group(1)]['regX'] = vals[7]
                shapes[m.group(1)]['regY'] = vals[8]
            elif len(vals) >= 4:
                shapes[m.group(1)]['sx'] = vals[2]
                shapes[m.group(1)]['sy'] = vals[3]

    label_n = label_count(js)
    # label transition times: the label is shown at wait(24), then every
    # wait(24) advances to the next number.  Chains whose delay falls between
    # two label ticks belong to the SAME stroke (second-segment reveal) and
    # must be merged into it, not dropped (凹 id=320 / 凸 id=322 lost their
    # final right-side stroke to a blind trim).
    label_times = [24]
    for mm in re.finditer(r'wait\((\d+)\)\.to\(\{_off:false\},0\)(.*?)\);', js):
        acc = 24
        for w in re.finditer(r'wait\((\d+)\)\.to\(\{text:', mm.group(2)):
            acc += int(w.group(1))
            label_times.append(acc)
        break
    fin_names = find_showall(js)

    chains = find_chains(js) + find_offset_chains(js)

    # drop chains that carry no ink at all (number-label / text instance tweens)
    chains = [c for c in chains
              if any(n in shapes and is_ink(shapes[n].get('color', '')) for n in c['names'])]

    # The number-label tween is NOT a stroke: it can list more names than the real
    # chain sharing its delay and therefore win the same-delay merge, deleting a
    # stroke (山 id=1088 came out with 2 strokes instead of 3).
    chains = [c for c in chains if not any(n.startswith('text') for n in c['names'])]

    chains.sort(key=lambda c: c['delay'])
    merged = []
    for c in chains:
        if merged and merged[-1]['delay'] == c['delay']:
            if len(c['names']) >= len(merged[-1]['names']):
                merged[-1] = c
        else:
            merged.append(c)

    picked = []      # list of lists: one stroke = all ink shapes in the chain's FINAL state
    seen = set()
    for c in merged:
        finals = []
        for name in c['final']:
            s = shapes.get(name)
            if s and is_ink(s.get('color', '')) and name not in seen:
                finals.append(name)
        if not finals:
            # chain whose final state carries no new ink — duplicated timeline or
            # label tween already consumed; fall back to any ink name not yet used
            for name in reversed(c['names']):
                s = shapes.get(name)
                if s and is_ink(s.get('color', '')) and name not in seen:
                    finals.append(name)
                    break
        if not finals:
            continue
        seen.update(finals)
        picked.append(finals)

    # Trim over-counting only when BOTH independent counts agree on fewer strokes
    # (EDB label + Unihan kTotalStrokes via CHAR_DB).  The label alone is unsafe: it
    # lags on 先/山/京/亭/兌/克/免/光/充/兆/兇/鑰/鑼 … and trimming there deleted real
    # strokes for 25 characters.
    jid_files = re.findall(r'(\d+)\.js$', path)
    jid_num = int(jid_files[0]) if jid_files else 0
    if label_n and db_counts.get(jid_num, 0) == label_n and len(picked) > label_n:
        # Do NOT blind-trim to the first N chains: a chain starting between two
        # label ticks is the SECOND SEGMENT of the previous stroke, not a new
        # stroke (凹 id=320: chains at delay 36 & 105 sit inside label windows;
        # the old picked[:5] dropped 底橫 shape_7 + 右下 shape_4 -> missing
        # lower-right corner).  Group chains by which label window they start
        # in, merging every chain that starts before the next label tick into
        # the current stroke.
        if len(label_times) > 1:
            groups = []
            for c in merged:
                if c['delay'] >= label_times[-1]:
                    g = len(label_times) - 1
                else:
                    g = 0
                    for t in label_times[1:]:
                        if c['delay'] < t:
                            break
                        g += 1
                while len(groups) <= g:
                    groups.append([])
                groups[g].extend(c.get('final', []))
            groups = [list(dict.fromkeys(g)) for g in groups if g]
            if len(groups) == label_n:
                picked = groups
            else:
                picked = picked[:label_n]
        else:
            picked = picked[:label_n]

    # ---- prefer the official final geometry --------------------------------
    # The show-all list is NOT reliably in stroke order (147/296 chars differ — e.g.
    # 什 id=69), so order always comes from the animation chains; only the geometry is
    # taken from the final set, paired by global-greedy bbox matching.  Requiring equal
    # counts also rejects the 14 chars whose "show-all" block is something else
    # (名/印/韋… list 2 shapes for 6+ strokes) — those keep the animation geometry.
    if fin_names and len(fin_names) == len(picked):
        pairs = []
        for i, names in enumerate(picked):
            cb = stroke_bbox(names, shapes)
            if not cb:
                continue
            for j, fname in enumerate(fin_names):
                fb = bbox(shapes.get(fname))
                if fb:
                    pairs.append((sum(abs(a - b) for a, b in zip(cb, fb)), i, j))
        pairs.sort()
        assign, taken = {}, set()
        for _d, i, j in pairs:
            if i in assign or j in taken:
                continue
            assign[i] = j
            taken.add(j)
        picked = [[fin_names[assign[i]]] if i in assign else n for i, n in enumerate(picked)]
    # else: no usable final set — 14 chars (名/印/韋…) have a "show-all"-looking block
    # that lists 2 shapes for 6+ strokes, so keep the animation geometry untouched.

    strokes = []
    for names in picked:
        g = []
        for name in names:
            s = shapes.get(name)
            if not s:
                continue
            g.append({'x': s.get('x', 0), 'y': s.get('y', 0), 'path': s['path'],
                      'sx': s.get('sx', 1.0), 'sy': s.get('sy', 1.0),
                      'regX': s.get('regX', 0.0), 'regY': s.get('regY', 0.0)})
        if g:
            strokes.append(g)
    return strokes, label_n, len(fin_names)


def stroke_bbox(names, shapes):
    """Union bbox over a stroke's shapes (a stroke can be several shapes)."""
    boxes = [bbox(shapes.get(n)) for n in names]
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def to_svg(shape):
    ox, oy = _shape_origin(shape)
    sx, sy = shape.get('sx', 1.0), shape.get('sy', 1.0)
    parts = []
    for cmd in decode_createjs_path(shape['path']):
        if cmd[0] == 'Z':
            parts.append('Z')
            continue
        coords = []
        for ci, v in enumerate(cmd[1:]):
            coords.append(round((ox if ci % 2 == 0 else oy) + v * (sx if ci % 2 == 0 else sy), 1))
        parts.append(cmd[0] + ','.join(str(c) for c in coords))
    return ' '.join(parts)


def group_to_svg(group):
    """Serialize one stroke (one or more shapes) to a single SVG path."""
    return ' '.join(to_svg(s) for s in group)


if __name__ == '__main__':
    mapping = json.load(open(wpath('edb_id_map.json')))['mapping']
    out, errors, swapped_chars = {}, [], []
    for n, (ch, idv) in enumerate(mapping.items()):
        fn = wpath('edb_strokes', '%04d.js') % idv
        if not os.path.exists(fn):
            errors.append((ch, idv, 'no file'))
            continue
        try:
            strokes, label_n, n_fin = parse_edb_js(fn)
            if not strokes:
                errors.append((ch, idv, 'no strokes'))
                continue
            out[ch] = [group_to_svg(s) for s in strokes]
            if n_fin and n_fin != len(strokes):
                swapped_chars.append((ch, idv, n_fin, len(strokes)))
        except Exception as e:
            errors.append((ch, idv, str(e)[:60]))
        if (n + 1) % 1000 == 0:
            print('  %d/%d...' % (n + 1, len(mapping)), flush=True)

    json.dump(out, open(wpath('edb_svg_strokes.json'), 'w'), ensure_ascii=False)
    print('converted:', len(out), 'errors:', len(errors))
    if errors:
        print('errors sample:', errors[:5])
    print('partial-substitutions (n_fin != strokes):', len(swapped_chars), swapped_chars[:5])
    for ch in ['\u4e00', '\u4e8c', '\u4e09', '\u500b', '\u9032', '\u92f8', '\u4e0d', '\u4eba']:
        if ch in out:
            print('%s: %d strokes' % (ch, len(out[ch])))
