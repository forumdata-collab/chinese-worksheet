"""Zhang-Suen thinning (pure numpy) — replacement for segfaulting skimage.skeletonize."""
import numpy as np
# --- work directory (all scratch data lives here; CW_WORK overrides) ---------
import os as _os
WORK = _os.environ.get('CW_WORK', '/tmp')
def wpath(*parts):
    return _os.path.join(WORK, *parts)




def _neighbours(img):
    """Return p2..p9 arrays (clockwise from north) plus centre."""
    p = np.zeros((8,) + img.shape, dtype=np.uint8)
    # offsets clockwise: N, NE, E, SE, S, SW, W, NW
    offs = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    for i, (dr, dc) in enumerate(offs):
        p[i] = np.roll(np.roll(img, dr, axis=0), dc, axis=1)
    return p


def thin(img, max_iter=200):
    img = (img > 0).astype(np.uint8)
    for _ in range(max_iter):
        changed = False
        for step in (0, 1):
            p = _neighbours(img)
            P2, P3, P4, P5, P6, P7, P8, P9 = p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]
            B = p.sum(axis=0)
            seq = np.stack([P2, P3, P4, P5, P6, P7, P8, P9, P2], axis=0)
            A = ((seq[:-1] == 0) & (seq[1:] == 1)).sum(axis=0)

            cond = (img == 1) & (B >= 2) & (B <= 6) & (A == 1)
            if step == 0:
                cond &= (P2 * P4 * P6 == 0) & (P4 * P6 * P8 == 0)
            else:
                cond &= (P2 * P4 * P8 == 0) & (P2 * P6 * P8 == 0)

            if cond.any():
                img[cond] = 0
                changed = True
        if not changed:
            break
    return img.astype(bool)


if __name__ == '__main__':
    from PIL import Image, ImageDraw
    import time
    img = Image.new('1', (128, 128), 0)
    dr = ImageDraw.Draw(img)
    dr.polygon([(20, 20), (100, 30), (100, 50), (20, 40)], fill=1)
    a = np.array(img, dtype=bool)
    t0 = time.time()
    sk = thin(a)
    print(f'thin: {sk.sum()} px in {time.time()-t0:.3f}s (input {a.sum()} px)')
    # visual
    vis = np.full((128, 128, 3), 255, np.uint8)
    vis[a] = [220, 220, 220]
    vis[sk] = [200, 0, 0]
    Image.fromarray(vis).resize((384, 384), Image.NEAREST).save(wpath('thin_test.png'))
    print('saved /tmp/thin_test.png')
