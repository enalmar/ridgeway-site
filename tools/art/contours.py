#!/usr/bin/env python3
"""Contour lines from a stitched DEM grid (see dem.py) to a small, tintable SVG.

Standard library only. Steps: crop -> Gaussian smooth -> marching squares (edge-keyed, saddles
resolved by the cell centre) -> chain segments into polylines -> Douglas-Peucker simplify ->
drop tiny fragments -> optional Chaikin rounding -> compact relative-path SVG.

Lines use stroke="currentColor" and vector-effect="non-scaling-stroke", so the page sets colour
(and opacity) with CSS `color`, and line weight stays the same at any size.
Every Nth contour (default 5th) is an index line, in its own <path class="rw-ci">; minor lines are
<path class="rw-cm"> (class names are prefixed so the SVG can be inlined without style collisions).

Usage:
    python3 -I contours.py DEM_PREFIX OUT.svg [--crop x,y,w,h] [--sigma 1.6] [--interval 20]
        [--index 5] [--tol 0.6] [--minlen 18] [--chaikin 1] [--minor-w 0.6] [--index-w 1.1]
        [--min-elev 0]
"""
import argparse
import json
import math
from array import array


def load(prefix):
    meta = json.load(open(prefix + ".json"))
    g = array("f")
    g.frombytes(open(prefix + ".bin", "rb").read())
    return meta, g


def crop(g, W, x, y, w, h):
    out = array("f", [0.0]) * (w * h)
    for r in range(h):
        out[r * w:(r + 1) * w] = g[(y + r) * W + x:(y + r) * W + x + w]
    return out


def gaussian(g, w, h, sigma):
    if sigma <= 0:
        return g
    rad = max(1, int(math.ceil(sigma * 3)))
    k = [math.exp(-(i * i) / (2 * sigma * sigma)) for i in range(-rad, rad + 1)]
    s = sum(k)
    k = [v / s for v in k]
    tmp = array("f", [0.0]) * (w * h)
    for r in range(h):
        row = g[r * w:(r + 1) * w]
        base = r * w
        for c in range(w):
            acc = 0.0
            for t, kv in enumerate(k):
                cc = c + t - rad
                cc = 0 if cc < 0 else (w - 1 if cc >= w else cc)
                acc += row[cc] * kv
            tmp[base + c] = acc
    out = array("f", [0.0]) * (w * h)
    for c in range(w):
        col = tmp[c::w]
        for r in range(h):
            acc = 0.0
            for t, kv in enumerate(k):
                rr = r + t - rad
                rr = 0 if rr < 0 else (h - 1 if rr >= h else rr)
                acc += col[rr] * kv
            out[r * w + c] = acc
    return out


def contour_level(g, w, h, cells, level):
    """Return polylines (lists of (x, y)) for one level. `cells` are candidate cell indices."""
    # edge keys: horizontal edge from (i,j)-(i+1,j): (j*w+i)*2 ; vertical (i,j)-(i,j+1): (j*w+i)*2+1
    def point(key):
        idx, vert = key >> 1, key & 1
        j, i = divmod(idx, w)
        a = g[idx]
        if vert:
            b = g[idx + w]
            t = (level - a) / (b - a)
            return (i, j + t)
        b = g[idx + 1]
        t = (level - a) / (b - a)
        return (i + t, j)

    adj = {}

    def link(e1, e2):
        adj.setdefault(e1, []).append(e2)
        adj.setdefault(e2, []).append(e1)

    for ci in cells:
        j, i = divmod(ci, w - 1)
        p = j * w + i
        a, b, c, d = g[p], g[p + 1], g[p + w + 1], g[p + w]  # TL TR BR BL
        code = (8 if a > level else 0) | (4 if b > level else 0) | (2 if c > level else 0) | (1 if d > level else 0)
        if code == 0 or code == 15:
            continue
        top, right, bottom, left = p * 2, (p + 1) * 2 + 1, (p + w) * 2, p * 2 + 1
        if code in (1, 14):
            link(left, bottom)
        elif code in (2, 13):
            link(bottom, right)
        elif code in (3, 12):
            link(left, right)
        elif code in (4, 11):
            link(top, right)
        elif code in (6, 9):
            link(top, bottom)
        elif code in (7, 8):
            link(left, top)
        elif code in (5, 10):
            centre = (a + b + c + d) / 4
            # 5: TR and BL high. 10: TL and BR high.
            if (code == 10) == (centre > level):
                link(left, bottom)
                link(top, right)
            else:
                link(left, top)
                link(bottom, right)
    lines = []
    seen = set()
    # start at ends (degree 1) first, then loops
    starts = [k for k, v in adj.items() if len(v) == 1] + list(adj.keys())
    for s in starts:
        if s in seen:
            continue
        chain = [s]
        seen.add(s)
        cur = s
        while True:
            nxt = None
            for n in adj[cur]:
                if n not in seen:
                    nxt = n
                    break
            if nxt is None:
                if len(chain) > 2 and chain[0] in adj[cur]:
                    chain.append(chain[0])  # closed
                break
            seen.add(nxt)
            chain.append(nxt)
            cur = nxt
        lines.append([point(k) for k in chain])
    return lines


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    t2 = tol * tol
    while stack:
        s, e = stack.pop()
        ax, ay = pts[s]
        bx, by = pts[e]
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        best, bi = -1.0, -1
        for k in range(s + 1, e):
            px, py = pts[k]
            if L == 0:
                d = (px - ax) ** 2 + (py - ay) ** 2
            else:
                cr = (px - ax) * dy - (py - ay) * dx
                d = cr * cr / L
            if d > best:
                best, bi = d, k
        if best > t2 and bi > 0:
            keep[bi] = True
            stack.append((s, bi))
            stack.append((bi, e))
    return [p for p, k in zip(pts, keep) if k]


def chaikin(pts, n):
    closed = len(pts) > 3 and pts[0] == pts[-1]
    for _ in range(n):
        if len(pts) < 3:
            return pts
        out = [] if closed else [pts[0]]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            out.append((0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1))
            out.append((0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1))
        if closed:
            out.append(out[0])
        else:
            out.append(pts[-1])
        pts = out
    return pts


def length(pts):
    return sum(math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(pts, pts[1:]))


def path_d(lines, q):
    """Compact relative path. Coordinates are multiplied by q and rounded to integers."""
    parts = []
    for pts in lines:
        ip = [(int(round(x * q)), int(round(y * q))) for x, y in pts]
        # drop repeated points after rounding
        dedup = [ip[0]]
        for p in ip[1:]:
            if p != dedup[-1]:
                dedup.append(p)
        if len(dedup) < 2:
            continue
        closed = len(dedup) > 3 and dedup[0] == dedup[-1]
        if closed:
            dedup = dedup[:-1]
        s = ["M%d %d" % dedup[0], "l"]
        prev = dedup[0]
        nums = []
        for p in dedup[1:]:
            nums.append((p[0] - prev[0], p[1] - prev[1]))
            prev = p
        buf = ""
        for dx, dy in nums:
            for v in (dx, dy):
                tok = str(v)
                if buf and not tok.startswith("-") and buf[-1] not in "lMz ":
                    buf += " "
                buf += tok
        s.append(buf)
        if closed:
            s.append("z")
        parts.append("".join(s))
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dem")
    ap.add_argument("out")
    ap.add_argument("--crop", default=None)
    ap.add_argument("--sigma", type=float, default=1.6)
    ap.add_argument("--interval", type=float, default=20)
    ap.add_argument("--index", type=int, default=5)
    ap.add_argument("--tol", type=float, default=0.6)
    ap.add_argument("--minlen", type=float, default=18)
    ap.add_argument("--chaikin", type=int, default=1)
    ap.add_argument("--q", type=float, default=10, help="coordinate quantisation (units per DEM pixel)")
    ap.add_argument("--min-elev", type=float, default=0)
    ap.add_argument("--minor-w", type=float, default=0.6)
    ap.add_argument("--index-w", type=float, default=1.1)
    ap.add_argument("--minor-o", type=float, default=0.5, help="minor line opacity relative to index lines")
    ap.add_argument("--title", default="Contours of Helvellyn and Striding Edge, Lake District")
    a = ap.parse_args()

    meta, g = load(a.dem)
    W, H = meta["width"], meta["height"]
    if a.crop:
        x, y, w, h = [int(v) for v in a.crop.split(",")]
        g = crop(g, W, x, y, w, h)
    else:
        w, h = W, H
    g = gaussian(g, w, h, a.sigma)

    # bucket cells by the levels they cross
    buckets = {}
    iv = a.interval
    for j in range(h - 1):
        r0 = j * w
        r1 = r0 + w
        for i in range(w - 1):
            v0, v1, v2, v3 = g[r0 + i], g[r0 + i + 1], g[r1 + i], g[r1 + i + 1]
            lo = min(v0, v1, v2, v3)
            hi = max(v0, v1, v2, v3)
            k0 = int(math.floor(lo / iv)) + 1
            k1 = int(math.floor(hi / iv))
            ci = j * (w - 1) + i
            for k in range(k0, k1 + 1):
                buckets.setdefault(k, []).append(ci)

    minor, index = [], []
    nverts = 0
    for k in sorted(buckets):
        level = k * iv
        if level < a.min_elev:
            continue
        lines = contour_level(g, w, h, buckets[k], level - 1e-4)
        is_index = (k % a.index == 0)
        for pts in lines:
            if length(pts) < a.minlen:
                continue
            pts = dp(pts, a.tol)
            if a.chaikin:
                pts = chaikin(pts, a.chaikin)
                pts = dp(pts, a.tol * 0.35)
            nverts += len(pts)
            (index if is_index else minor).append(pts)

    q = a.q
    vb = "0 0 %d %d" % (int((w - 1) * q), int((h - 1) * q))
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s" preserveAspectRatio="xMidYMid slice" '
        'fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><!-- %s. Terrain: Terrarium elevation tiles (Mapzen/AWS Open Data). -->'
        '<style>.rw-cm,.rw-ci{vector-effect:non-scaling-stroke}.rw-cm{stroke-width:%gpx;opacity:%g}.rw-ci{stroke-width:%gpx}</style>'
        '<path class="rw-cm" d="%s"/><path class="rw-ci" d="%s"/></svg>\n'
        % (vb, a.title, a.minor_w, a.minor_o, a.index_w, path_d(minor, q), path_d(index, q))
    )
    open(a.out, "w").write(svg)
    print("%s: %dx%d grid, %d minor + %d index lines, %d vertices, %.1f KB"
          % (a.out, w, h, len(minor), len(index), nverts, len(svg) / 1024))


if __name__ == "__main__":
    main()
