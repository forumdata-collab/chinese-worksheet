"""EDB stroke outline -> median polyline (Zhang-Suen based)."""
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw
from svgpathtools import parse_path
sys.path.insert(0, '/tmp')
from zs_thin import thin
# --- work directory (all scratch data lives here; CW_WORK overrides) ---------
import os as _os
WORK = _os.environ.get('CW_WORK', '/tmp')
def wpath(*parts):
    return _os.path.join(WORK, *parts)



N = 160  # raster size for skeleton work


def rasterise(strokes, n=N):
    paths = [parse_path(s) for s in strokes]
    bbs = [p.bbox() for p in paths]
    x0 = min(b[0] for b in bbs); x1 = max(b[1] for b in bbs)
    y0 = min(b[2] for b in bbs); y1 = max(b[3] for b in bbs)
    pad = 0.04 * max(x1 - x0, y1 - y0)
    x0 -= pad; x1 += pad; y0 -= pad; y1 += pad
    sc = (n - 1) / max(x1 - x0, y1 - y0)
    ox = (n - (x1 - x0) * sc) / 2 - x0 * sc
    oy = (n - (y1 - y0) * sc) / 2 - y0 * sc
    masks = []
    for p in paths:
        img = Image.new('1', (n, n), 0)
        dr = ImageDraw.Draw(img)
        pts = [(pt.real * sc + ox, pt.imag * sc + oy) for pt in (p.point(t / 400) for t in range(401))]
        dr.polygon([(float(a), float(b)) for a, b in pts], fill=1)
        masks.append(np.array(img, dtype=bool))
    return masks, (sc, ox, oy)


def longest_path(skel):
    pts = np.argwhere(skel)
    if len(pts) == 0:
        return []
    idx = {(int(r), int(c)): i for i, (r, c) in enumerate(pts)}
    adj = [[] for _ in range(len(pts))]
    for i, (r, c) in enumerate(pts):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                j = idx.get((int(r) + dr, int(c) + dc))
                if j is not None:
                    adj[i].append(j)

    def bfs(start):
        dist = {start: 0}
        prev = {start: None}
        cur = [start]
        far = start
        while cur:
            nxt = []
            for u in cur:
                for v in adj[u]:
                    if v not in dist:
                        dist[v] = dist[u] + 1
                        prev[v] = u
                        nxt.append(v)
                        if dist[v] > dist[far]:
                            far = v
            cur = nxt
        return far, dist, prev

    deg1 = [i for i in range(len(pts)) if len(adj[i]) == 1]
    start = deg1[0] if deg1 else 0
    a, _, _ = bfs(start)
    b, dist, prev = bfs(a)
    path, cur = [], b
    while cur is not None:
        path.append((int(pts[cur][1]), int(pts[cur][0])))   # (x, y)
        cur = prev[cur]
    path.reverse()
    return path


def rdp(points, eps):
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dmax, index = 0.0, 0
    for i in range(1, len(points) - 1):
        x0, y0 = points[i]
        num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        den = math.hypot(y2 - y1, x2 - x1) or 1
        d = num / den
        if d > dmax:
            index, dmax = i, d
    if dmax > eps:
        return rdp(points[:index + 1], eps)[:-1] + rdp(points[index:], eps)
    return [points[0], points[-1]]


def medians_for(strokes, simplify=1.2):
    masks, (sc, ox, oy) = rasterise(strokes)
    out = []
    for m in masks:
        if m.sum() < 4:
            rr, cc = np.argwhere(m)[0] if m.sum() else (0, 0)
            out.append([((cc - ox) / sc, (rr - oy) / sc)])
            continue
        sk = thin(m)
        path = longest_path(sk)
        if not path:
            rr, cc = np.argwhere(m)[0]
            out.append([((cc - ox) / sc, (rr - oy) / sc)])
            continue
        simp = rdp(path, simplify)
        out.append([(round((px - ox) / sc, 1), round((py - oy) / sc, 1)) for px, py in simp])
    return out


if __name__ == '__main__':
    EDB = json.load(open(wpath('edb_svg_strokes.json')))
    ch = '\u8239'
    med = medians_for(EDB[ch])
    print(f'{ch}: {len(med)} strokes')
    for i, m in enumerate(med):
        print(f'  #{i+1}: {len(m)} pts  start={m[0]} end={m[-1]}')

    # render check: grey ink + red medians with index labels
    strokes = EDB[ch]
    masks, (sc, ox, oy) = rasterise(strokes)
    S = 480
    k = S / N
    vis = np.full((N, N, 3), 255, np.uint8)
    for m in masks:
        vis[m] = [205, 205, 205]
    img = Image.fromarray(vis).resize((S, S), Image.NEAREST)
    dr = ImageDraw.Draw(img)
    for i, m in enumerate(med):
        pts = [((x * sc + ox) * k, (y * sc + oy) * k) for x, y in m]
        if len(pts) > 1:
            dr.line(pts, fill=(200, 0, 0), width=3, joint='curve')
        # arc-length midpoint marker
        if len(pts) > 1:
            total = sum(math.dist(pts[j], pts[j+1]) for j in range(len(pts)-1))
            acc = 0
            mid = pts[0]
            for j in range(len(pts)-1):
                seg = math.dist(pts[j], pts[j+1])
                if acc + seg >= total/2:
                    t = (total/2 - acc)/seg if seg else 0
                    mid = (pts[j][0] + (pts[j+1][0]-pts[j][0])*t, pts[j][1] + (pts[j+1][1]-pts[j][1])*t)
                    break
                acc += seg
            dr.ellipse([mid[0]-6, mid[1]-6, mid[0]+6, mid[1]+6], outline=(0, 90, 220), width=3)
            dr.text((mid[0]+9, mid[1]-9), str(i+1), fill=(0, 60, 200))
        dr.ellipse([pts[0][0]-5, pts[0][1]-5, pts[0][0]+5, pts[0][1]+5], fill=(0, 150, 0))
    img.save(wpath('edb_median_beta.png'))
    print('saved /tmp/edb_median_beta.png')
