#!/usr/bin/env python3
"""Turn the raw app captures into the images the site serves.

    python3 tools/shots.py [RAW]        RAW defaults to ~/Dev/ridgeway-site-assets-raw

Reads the full-size iPhone captures (1320 x 2868 PNG, `RAW/all-phone/`) and the Apple Watch
captures (`RAW/site/watch-*.png`, 400 x 487 or 422 x 514), and writes `assets/shots/` and `assets/watch/`.

iPhone captures are cropped (where a tile shows only part of the screen), scaled to 720 px wide,
or 480 px for the small map-style thumbnails, and saved as progressive JPEG with optimised
Huffman tables. That is about 40% smaller than `sips` at the same quality setting, with no
visible difference on the map text (checked at 2x on the hero capture). JPEG, not AVIF: see
the README. Watch captures are JPEG too.

Two captures come from the app's demo mode and carry its "Demo" tag, which says nothing about the
feature shown and reads as a mock-up at the top of a device: the Trail Run dashboard's "Demo"
subtitle and the watch map page's "Demo" capsule. `unmark_dashboard` and `unmark_watch_map` take
the tag out and change nothing else (see the README).

Needs Pillow (`pip3 install pillow`). Run it from anywhere; paths are relative to this file.
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Dev/ridgeway-site-assets-raw")

# (capture in RAW/all-phone, file in assets/shots, width, JPEG quality, crop box in capture pixels or None)
PHONE = [
    ("map-hero-standard-dark", "map-standard-dark", 720, 84, None),
    ("trail-run-dashboard", "trail-run", 720, 84, None),
    ("race-day", "race-day", 720, 84, None),
    ("off-route", "off-route", 720, 84, None),
    ("run-navigation-map", "turn-alert", 720, 84, (0, 0, 1320, 1900)),      # the turn banner and the route
    ("route-detail-profile", "climbs", 720, 84, (0, 1030, 1320, 2240)),  # Elevation and Climbs
    ("offline-grid", "offline-grid", 720, 84, None),
    ("offline-downloading", "offline-card", 720, 86, (60, 1171, 1260, 1442)),  # the In Progress card
    ("planner", "planner", 720, 84, None),
    ("planner-route-profile", "route-profile", 720, 84, None),
    ("you-stats-map", "you", 720, 84, None),
    ("you-world-map", "you-world-map", 720, 84, None),
    ("map-standard-light", "style-standard-light", 480, 80, None),
    ("map-minimal-light", "style-minimal-light", 480, 80, None),
    ("map-hiking-pro", "style-hiking-pro", 480, 80, None),
    ("map-hiking-pro", "style-hiking-pro-detail", 360, 84, (100, 1240, 620, 1760)),  # Helvellyn at full size
    ("map-tactical", "style-tactical", 480, 80, None),
]

# (capture in RAW/site, file in assets/watch, JPEG quality)
WATCH = [
    ("watch-session-map.png", "map.jpg", 86),
    ("watch-run-stats.png", "run.jpg", 82),
    ("watch-next-aid.png", "next-aid.jpg", 82),
    ("watch-route-compass.png", "route-compass.jpg", 82),
    ("watch-off-route.png", "off-route.jpg", 82),
]


def unmark_dashboard(im):
    """The Trail Run dashboard (1320 x 2868): drop the "Demo" subtitle under "Recording" and set the title
    on the toolbar buttons' centre line, where iOS puts an inline title that has no subtitle. The
    background there is pure black."""
    title = im.crop((520, 205, 800, 262))          # "Recording", with its antialiasing
    im.paste((0, 0, 0), (420, 200, 900, 305))      # title and "Demo" subtitle
    im.paste(title, (520, 205 + 19))               # centre 233 -> 252, the buttons' centre
    return im


def unmark_watch_map(im):
    """The watch map page (400 x 487): take out the "Demo" capsule at the top left.

    The capsule is the system tertiary fill, rgb(118, 118, 128) at 24%, over the map, so outside the
    letters the map is recovered exactly by un-blending it. Its soft shadow darkens a pixel or two
    round the edge by about 7%. Under the letters (secondary label grey, opaque) the map is filled
    in from the recovered pixels around them. Only faint contour lines sit behind the word."""
    x0, y0, x1, y1 = 31.3, 47.4, 140.0, 96.5        # the capsule, in pixels (measured on its edges)
    r = (y1 - y0) / 2
    fill, alpha = (118, 118, 128), 0.24

    def dist(x, y):                                 # signed distance to the capsule's edge
        cx = min(max(x, x0 + r), x1 - r)
        return ((x - cx) ** 2 + (y - (y0 + r)) ** 2) ** .5 - r

    def inside(x, y):
        return dist(x, y) <= 0

    px = im.load()
    box = (int(x0) - 3, int(y0) - 3, int(x1) + 4, int(y1) + 4)
    text = (45, 58, 125, 87)                        # the word's box
    unknown = set()
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            cover = sum(inside(x + (i + .5) / 4, y + (j + .5) / 4) for i in range(4) for j in range(4)) / 16
            if not cover:
                d = dist(x + .5, y + .5)
                if d < 2:                           # the shadow just outside
                    px[x, y] = tuple(min(255, round(c / (1 - .07 * (2 - d) / 2))) for c in px[x, y])
                continue
            a = alpha * cover
            p = px[x, y]
            m = tuple(max(0, min(255, round((p[k] - fill[k] * a) / (1 - a)))) for k in range(3))
            px[x, y] = m
            if text[0] <= x < text[2] and text[1] <= y < text[3] and sum(m) / 3 > 52:
                unknown.add((x, y))
    # two pixels round each letter, for its antialiased edge and shadow
    for _ in range(2):
        unknown |= {(x + dx, y + dy) for x, y in unknown for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    while unknown:                                  # fill from the outside in
        done = {}
        for x, y in unknown:
            near = [px[x + dx, y + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if (dx or dy) and (x + dx, y + dy) not in unknown]
            if len(near) >= 3:
                done[(x, y)] = tuple(round(sum(c[k] for c in near) / len(near)) for k in range(3))
        if not done:
            break
        for xy, c in done.items():
            px[xy] = c
        unknown -= done.keys()
    return im


UNMARK = {"trail-run-dashboard": unmark_dashboard, "watch-session-map.png": unmark_watch_map}


def save_jpeg(im, path, quality):
    im.convert("RGB").save(path, "JPEG", quality=quality, optimize=True, progressive=True,
                           subsampling="4:2:0")


def main():
    shots = os.path.join(SITE, "assets", "shots")
    watch = os.path.join(SITE, "assets", "watch")
    os.makedirs(shots, exist_ok=True)
    os.makedirs(watch, exist_ok=True)
    total = 0
    for src, name, width, quality, crop in PHONE:
        im = Image.open(os.path.join(RAW, "all-phone", src + ".png")).convert("RGB")
        if src in UNMARK:
            im = UNMARK[src](im)
        if crop:
            im = im.crop(crop)
        height = round(im.height * width / im.width)
        im = im.convert("RGB").resize((width, height), Image.LANCZOS)
        out = os.path.join(shots, name + ".jpg")
        save_jpeg(im, out, quality)
        size = os.path.getsize(out)
        total += size
        print("%-34s %4d x %-4d %4d KB" % ("shots/" + name + ".jpg", width, height, size // 1024))
    for src, name, quality in WATCH:
        im = Image.open(os.path.join(RAW, "site", src)).convert("RGB")
        if src in UNMARK:
            im = UNMARK[src](im)
        if im.size != (400, 487):                   # Ultra 3 (49 mm) is 422 x 514; same shape
            im = im.resize((400, 487), Image.LANCZOS)
        out = os.path.join(watch, name)
        save_jpeg(im, out, quality)
        size = os.path.getsize(out)
        total += size
        print("%-34s %4d x %-4d %4d KB" % ("watch/" + name, im.width, im.height, size // 1024))
    print("total %d KB" % (total // 1024))


if __name__ == "__main__":
    main()
