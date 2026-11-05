#!/usr/bin/env python3
"""A real-looking route motif from the DEM: the Helvellyn round from Glenridding.

Glenridding -> Birkhouse Moor -> Hole-in-the-Wall -> Striding Edge -> Helvellyn -> Swirral Edge ->
Red Tarn -> Red Tarn Beck -> Greenside -> Glenridding (the classic horseshoe round Red Tarn).

The waypoints are hand-placed (approximate, from OS grid references); ridge segments are then
snapped to the crest (and beck-side paths to the valley floor) of the real terrain (local maximum across the line of travel, with the offset
smoothed along the path) so Striding Edge and the main ridge follow the DEM.

Writes (into the art/ folder):
    route.svg          the map line (Ridgeway Blue), magenta start dot, faint local contours (class "rw-c")
    route-profile.svg  the elevation profile (line + soft fill), same draw-on timing
    route.json         distance, ascent, highest point, and the sampled profile

Both SVGs have pathLength="1" on the drawn lines and a built-in draw-on animation that respects
prefers-reduced-motion. Inline them to restyle with CSS custom properties (see the <style> blocks).

    python3 -I route.py DEM_PREFIX OUT_DIR
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contours as C  # noqa: E402

# (lat, lon, snap): "r" snaps to the crest (local maximum across the line of travel),
# "v" to the valley floor (beck-side paths), None leaves the line as drawn.
WAYPOINTS = [
    (54.5433, -2.9499, None),  # Glenridding
    (54.5422, -2.9580, "v"),   # Gillside
    (54.5400, -2.9655, "v"),   # Mires Beck
    (54.5378, -2.9740, "v"),   # Mires Beck, upper
    (54.5362, -2.9810, "r"),   # onto the ridge
    (54.5350, -2.9853, "r"),   # Birkhouse Moor (DEM peak)
    (54.5305, -2.9915, "r"),   # Hole-in-the-Wall
    (54.5280, -2.9985, "r"),   # Striding Edge
    (54.5255, -3.0047, "r"),   # High Spying How (DEM peak)
    (54.5265, -3.0120, "r"),   # head of Striding Edge
    (54.5278, -3.0188, "r"),   # Helvellyn summit plateau (DEM high point)
    (54.5293, -3.0155, "r"),   # top of Swirral Edge
    (54.5318, -3.0112, "r"),   # foot of Swirral Edge, below Catstye Cam
    (54.5306, -3.0072, None),  # down to Red Tarn
    (54.5296, -3.0035, None),  # Red Tarn outflow
    (54.5335, -2.9995, "v"),   # Red Tarn Beck
    (54.5385, -2.9935, "v"),   # Red Tarn Beck, lower
    (54.5440, -2.9860, "v"),   # meets Glenridding Beck
    (54.5468, -2.9800, "v"),   # Greenside
    (54.5458, -2.9700, "v"),   # Glenridding Beck
    (54.5433, -2.9499, None),  # Glenridding
]

BLUE = "#409CFF"
MAGENTA = "#FF4FB2"  # the app's planned-route magenta on dark themes (TrailRender Overlays)


def lonlat_to_px(meta, lat, lon):
    n = 2 ** meta["z"] * 256
    x = (lon + 180) / 360 * n - meta["x0"] * 256
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n - meta["y0"] * 256
    return x, y


def px_to_lonlat(meta, x, y):
    n = 2 ** meta["z"] * 256
    lon = (x + meta["x0"] * 256) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + meta["y0"] * 256) / n))))
    return lat, lon


def bilinear(g, w, h, x, y):
    x = min(max(x, 0), w - 1.001)
    y = min(max(y, 0), h - 1.001)
    i, j = int(x), int(y)
    fx, fy = x - i, y - j
    p = j * w + i
    return (g[p] * (1 - fx) * (1 - fy) + g[p + 1] * fx * (1 - fy)
            + g[p + w] * (1 - fx) * fy + g[p + w + 1] * fx * fy)


def haversine(a, b):
    R = 6371008.8
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(d))


def densify(pts, flags, step=1.0):
    out, of = [], []
    for (a, fa), (b, fb) in zip(zip(pts, flags), zip(pts[1:], flags[1:])):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / step))
        for k in range(n):
            t = k / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            of.append(fa if fa == fb else None)
    out.append(pts[-1])
    of.append(flags[-1])
    return out, of


def smooth_series(v, win):
    h = win // 2
    out = []
    for i in range(len(v)):
        s = v[max(0, i - h):i + h + 1]
        out.append(sum(s) / len(s))
    return out


def main():
    dem, out_dir = sys.argv[1], sys.argv[2]
    meta, g = C.load(dem)
    W, H = meta["width"], meta["height"]
    gs = C.gaussian(g, W, H, 1.2)

    pts = [lonlat_to_px(meta, la, lo) for la, lo, _ in WAYPOINTS]
    flags = [f for _, _, f in WAYPOINTS]
    dense, df = densify(pts, flags, 1.0)

    # snap ridge samples to the crest: search across the line of travel
    offs = []
    R = 5.0
    for i, (x, y) in enumerate(dense):
        if not df[i]:
            offs.append(0.0)
            continue
        a = dense[max(0, i - 3)]
        b = dense[min(len(dense) - 1, i + 3)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1
        nx, ny = -ty / L, tx / L
        sign = 1 if df[i] == "r" else -1
        best, bo = -1e9, 0.0
        o = -R
        while o <= R:
            e = sign * bilinear(gs, W, H, x + nx * o, y + ny * o) - 0.6 * abs(o)  # mild pull to the guide
            if e > best:
                best, bo = e, o
            o += 0.25
        offs.append(bo)
    offs = smooth_series(offs, 15)
    snapped = []
    for i, (x, y) in enumerate(dense):
        a = dense[max(0, i - 3)]
        b = dense[min(len(dense) - 1, i + 3)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1
        snapped.append((x - ty / L * offs[i], y + tx / L * offs[i]))
    xs = smooth_series([p[0] for p in snapped], 11)
    ys = smooth_series([p[1] for p in snapped], 11)
    snapped = list(zip(xs, ys))
    snapped[0] = snapped[-1] = dense[0]

    # profile
    lls = [px_to_lonlat(meta, x, y) for x, y in snapped]
    dist = [0.0]
    for a, b in zip(lls, lls[1:]):
        dist.append(dist[-1] + haversine(a, b))
    elev = [bilinear(g, W, H, x, y) for x, y in snapped]
    elev = smooth_series(elev, 5)
    ascent, ref = 0.0, elev[0]
    for e in elev[1:]:
        if e > ref + 3:
            ascent += e - ref
            ref = e
        elif e < ref - 3:
            ref = e
    total = dist[-1]
    hi = max(range(len(elev)), key=lambda i: elev[i])

    # ---- route.svg ----
    route = C.dp(snapped, 0.25)
    minx = min(p[0] for p in route)
    maxx = max(p[0] for p in route)
    miny = min(p[1] for p in route)
    maxy = max(p[1] for p in route)
    pad = 56  # room for the local contours to fade out around the line
    cx0, cy0 = int(minx - pad), int(miny - pad)
    cw, ch = int(maxx - minx + 2 * pad), int(maxy - miny + 2 * pad)
    S = 4  # output units per DEM pixel
    def tr(p):
        return ((p[0] - cx0) * S, (p[1] - cy0) * S)

    d_route = "M" + " ".join("%.1f %.1f" % tr(p) for p in route[:1]) + "L" + " ".join(
        "%.1f %.1f" % tr(p) for p in route[1:])

    # faint local contours under the line, from the same DEM
    sub = C.crop(g, W, cx0, cy0, cw + 1, ch + 1)
    sub = C.gaussian(sub, cw + 1, ch + 1, 2.2)
    clines_minor, clines_index = [], []
    lo_e, hi_e = min(sub), max(sub)
    for k in range(int(lo_e // 20) + 1, int(hi_e // 20) + 1):
        level = k * 20
        cells = [j * cw + i for j in range(ch) for i in range(cw)]
        for pl in C.contour_level(sub, cw + 1, ch + 1, cells, level - 1e-4):
            if C.length(pl) < 12:
                continue
            pl = C.chaikin(C.dp(pl, 0.4), 2)
            pl = C.dp(pl, 0.15)
            (clines_index if k % 5 == 0 else clines_minor).append(pl)
    d_minor = C.path_d(clines_minor, S)
    d_index = C.path_d(clines_index, S)

    sx, sy = tr(route[0])
    hx, hy = tr(snapped[hi])
    vbw, vbh = cw * S, ch * S
    glow_sd = 6.0 * S / 2  # ~6 px of blur at the motif's usual display size
    route_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vbw} {vbh}" fill="none" role="img" aria-label="A round of Helvellyn from Glenridding by Striding Edge and Swirral Edge, {total/1000:.1f} km with {ascent:.0f} m of ascent">
<defs><filter id="rw-route-blur" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="{glow_sd:.0f}"/></filter></defs>
<style>
.rw-c{{stroke:var(--rw-contour,#AABEDC);stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}}
.rw-cm{{stroke-width:.6px;opacity:var(--rw-contour-minor,.10)}}
.rw-ci{{stroke-width:1px;opacity:var(--rw-contour-index,.20)}}
.rw-glow{{stroke:var(--rw-route,{BLUE});stroke-width:16;stroke-linecap:round;stroke-linejoin:round;opacity:var(--rw-glow,.35)}}
.rw-line{{stroke:var(--rw-route,{BLUE});stroke-width:6;stroke-linecap:round;stroke-linejoin:round}}
.rw-draw{{stroke-dasharray:1;stroke-dashoffset:0}}
.rw-start{{fill:var(--rw-start,{MAGENTA});stroke:var(--rw-ground,#07090E);stroke-width:4}}
.rw-top{{fill:var(--rw-ink,#F2F2EE)}}
@media (prefers-reduced-motion:no-preference){{
.rw-draw{{stroke-dashoffset:1;animation:rw-draw var(--rw-dur,3.2s) cubic-bezier(.45,.05,.2,1) var(--rw-delay,.5s) forwards}}
.rw-start{{opacity:0;animation:rw-in .5s ease-out forwards}}
.rw-top{{opacity:0;animation:rw-in .6s ease-out calc(var(--rw-delay,.5s) + 1.4s) forwards}}
}}
@keyframes rw-draw{{to{{stroke-dashoffset:0}}}}
@keyframes rw-in{{to{{opacity:1}}}}
</style>
<path class="rw-c rw-cm" d="{d_minor}"/><path class="rw-c rw-ci" d="{d_index}"/>
<path class="rw-glow rw-draw" filter="url(#rw-route-blur)" pathLength="1" d="{d_route}"/>
<path class="rw-line rw-draw" pathLength="1" d="{d_route}"/>
<circle class="rw-top" cx="{hx:.1f}" cy="{hy:.1f}" r="6"/>
<circle class="rw-start" cx="{sx:.1f}" cy="{sy:.1f}" r="11"/>
</svg>
'''
    open(os.path.join(out_dir, "route.svg"), "w").write(route_svg)

    # ---- route-profile.svg ----
    PW, PH, top_pad, bot = 1200, 240, 24, 8
    emin = math.floor(min(elev) / 100) * 100 - 40
    emax = max(elev) + 30
    def pp(i):
        return (dist[i] / total * PW, top_pad + (1 - (elev[i] - emin) / (emax - emin)) * (PH - top_pad - bot))
    prof = C.dp([pp(i) for i in range(len(elev))], 0.35)
    d_prof = "M" + " ".join("%.1f %.1f" % p for p in prof[:1]) + "L" + " ".join("%.1f %.1f" % p for p in prof[1:])
    d_fill = d_prof + "L%d %dL0 %dZ" % (PW, PH, PH)
    hpx, hpy = pp(hi)
    prof_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PW} {PH}" preserveAspectRatio="none" fill="none" role="img" aria-label="Elevation profile: from {elev[0]:.0f} m to {elev[hi]:.0f} m on Helvellyn and back, {ascent:.0f} m of ascent over {total/1000:.1f} km">
<defs><linearGradient id="rw-pf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--rw-route,{BLUE})" stop-opacity=".22"/><stop offset="1" stop-color="var(--rw-route,{BLUE})" stop-opacity="0"/></linearGradient>
<clipPath id="rw-pc"><rect class="rw-preveal" width="{PW}" height="{PH}"/></clipPath></defs>
<style>
.rw-pfill{{fill:url(#rw-pf)}}
.rw-pbase{{stroke:var(--rw-contour,#AABEDC);stroke-opacity:.18;stroke-width:1px;vector-effect:non-scaling-stroke}}
.rw-pline{{stroke:var(--rw-route,{BLUE});stroke-width:2px;stroke-linejoin:round;stroke-linecap:round;vector-effect:non-scaling-stroke}}
.rw-pdraw{{stroke-dasharray:1;stroke-dashoffset:0}}
@media (prefers-reduced-motion:no-preference){{
.rw-pdraw{{stroke-dashoffset:1;animation:rw-draw var(--rw-dur,3.2s) cubic-bezier(.45,.05,.2,1) var(--rw-delay,.5s) forwards}}
.rw-preveal{{transform:scaleX(0);animation:rw-reveal var(--rw-dur,3.2s) cubic-bezier(.45,.05,.2,1) var(--rw-delay,.5s) forwards}}
}}
@keyframes rw-draw{{to{{stroke-dashoffset:0}}}}
@keyframes rw-reveal{{to{{transform:scaleX(1)}}}}
</style>
<path class="rw-pbase" d="M0 {PH-0.5}H{PW}"/>
<path class="rw-pfill" clip-path="url(#rw-pc)" d="{d_fill}"/>
<path class="rw-pline rw-pdraw" pathLength="1" d="{d_prof}"/>
</svg>
'''
    open(os.path.join(out_dir, "route-profile.svg"), "w").write(prof_svg)

    step = max(1, len(elev) // 200)
    info = {
        "name": "Helvellyn by Striding Edge and Swirral Edge, from Glenridding",
        "distance_km": round(total / 1000, 2),
        "ascent_m": round(ascent),
        "highest_m": round(elev[hi]),
        "highest_at_km": round(dist[hi] / 1000, 2),
        "start": {"lat": round(lls[0][0], 5), "lon": round(lls[0][1], 5), "elev_m": round(elev[0])},
        "note": "Waypoints approximate; ridge sections snapped to the DEM crest. Illustrative, not a navigational route.",
        "profile": [[round(dist[i] / 1000, 3), round(elev[i], 1)] for i in range(0, len(elev), step)],
    }
    json.dump(info, open(os.path.join(out_dir, "route.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in info.items() if k != "profile"}))
    for f in ("route.svg", "route-profile.svg"):
        print(f, "%.1f KB" % (os.path.getsize(os.path.join(out_dir, f)) / 1024))


if __name__ == "__main__":
    main()
