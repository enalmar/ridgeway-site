#!/usr/bin/env python3
"""Render a contour SVG the way the site is meant to use it, to a PNG, with headless Chrome.

    python3 -I preview.py IN.svg OUT.png [--w 1600] [--h 1000] [--color rgba(...)] [--glow 38%,42%]

Writes OUT.png.html next to the PNG (the inlined page) and screenshots it.
The page treatment here is the recommended one: Night ground, contours in a pale blue-grey at
very low alpha, a faint Ridgeway Blue glow behind the hero that also lifts the lines locally.
"""
import argparse
import os
import subprocess
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PAGE = """<!doctype html><meta charset="utf-8"><style>
html,body{margin:0;height:100%%;background:#07090E}
.bg{position:fixed;inset:0;overflow:hidden;
  background:radial-gradient(60%% 55%% at %(glow)s, rgba(64,156,255,.13), rgba(26,98,219,.04) 45%%, transparent 70%%), #07090E}
.bg svg{position:absolute;inset:0;width:100%%;height:100%%;color:%(color)s}
.bg .lift{color:#409CFF;opacity:.30;
  -webkit-mask-image:radial-gradient(38%% 40%% at %(glow)s,#000,transparent 75%%);
          mask-image:radial-gradient(38%% 40%% at %(glow)s,#000,transparent 75%%)}
.fade{position:fixed;inset:0;background:linear-gradient(180deg,transparent 55%%,#07090E 100%%)}
%(extra)s
</style><div class="bg">%(svg)s<div class="lift-wrap">%(svg_lift)s</div></div><div class="fade"></div>%(body)s
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("svg")
    ap.add_argument("png")
    ap.add_argument("--w", type=int, default=1600)
    ap.add_argument("--h", type=int, default=1000)
    ap.add_argument("--color", default="rgba(170,190,220,.16)")
    ap.add_argument("--glow", default="50% 42%")
    ap.add_argument("--plain", action="store_true", help="white lines on black, no treatment")
    ap.add_argument("--body", default="")
    a = ap.parse_args()
    svg = open(a.svg).read()
    if a.plain:
        html = ('<!doctype html><style>html,body{margin:0;background:#000;height:100%%}'
                'svg{width:100%%;height:100%%;color:#fff}</style>%s' % svg)
    else:
        lift = svg.replace("<svg ", '<svg class="lift" ', 1)
        html = PAGE % {"glow": a.glow, "color": a.color, "svg": svg, "svg_lift": lift,
                       "extra": "", "body": a.body}
    hp = os.path.abspath(a.png + ".html")
    open(hp, "w").write(html)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--user-data-dir=" + tempfile.mkdtemp(prefix="rw-chrome-"), "--no-first-run", "--window-size=%d,%d" % (a.w, a.h),
                    "--screenshot=%s" % os.path.abspath(a.png), "file://" + hp],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(a.png):
        raise SystemExit("Chrome did not write %s" % a.png)
    print(a.png)


if __name__ == "__main__":
    main()
