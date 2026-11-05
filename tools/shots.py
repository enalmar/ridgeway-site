#!/usr/bin/env python3
"""Turn the raw app captures into the images the site serves.

    python3 tools/shots.py [RAW]        RAW defaults to ~/Dev/ridgeway-site-assets-raw

Reads the full-size iPhone captures (1320 x 2868 PNG, `RAW/all-phone/`) and the Apple Watch
captures (400 x 487 PNG, `RAW/site/watch-*.png`), and writes `assets/shots/` and `assets/watch/`.

iPhone captures are cropped (where a tile shows only part of the screen), scaled to 720 px wide,
or 480 px for the small map-style thumbnails, and saved as progressive JPEG with optimised
Huffman tables. That is about 40% smaller than `sips` at the same quality setting, with no
visible difference on the map text (checked at 2x on the hero capture). JPEG, not AVIF: see
the README. Watch captures stay PNG (white text on black), except the map page, which is JPEG.

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

# (capture in RAW/site, file in assets/watch)
WATCH = [
    ("watch-session-map.png", "map.jpg"),
    ("watch-run-stats.png", "run.png"),
    ("watch-next-aid.png", "next-aid.png"),
    ("watch-route-compass.png", "route-compass.png"),
    ("watch-off-route.png", "off-route.png"),
]


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
        im = Image.open(os.path.join(RAW, "all-phone", src + ".png"))
        if crop:
            im = im.crop(crop)
        height = round(im.height * width / im.width)
        im = im.convert("RGB").resize((width, height), Image.LANCZOS)
        out = os.path.join(shots, name + ".jpg")
        save_jpeg(im, out, quality)
        size = os.path.getsize(out)
        total += size
        print("%-34s %4d x %-4d %4d KB" % ("shots/" + name + ".jpg", width, height, size // 1024))
    for src, name in WATCH:
        im = Image.open(os.path.join(RAW, "site", src)).convert("RGB")
        out = os.path.join(watch, name)
        if name.endswith(".jpg"):
            save_jpeg(im, out, 86)
        else:
            im.save(out, "PNG", optimize=True)
        size = os.path.getsize(out)
        total += size
        print("%-34s %4d x %-4d %4d KB" % ("watch/" + name, im.width, im.height, size // 1024))
    print("total %d KB" % (total // 1024))


if __name__ == "__main__":
    main()
