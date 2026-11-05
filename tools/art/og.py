#!/usr/bin/env python3
"""Render ../og.png (1200 x 630) from og.template.html with headless Chrome.

    python3 -I og.py ["tagline"]

Inlines ../contours.svg and ../route.svg (so CSS can tint them), points the icon at ../icon-256.png,
renders with prefers-reduced-motion forced (the route shows fully drawn), and writes ../og.png
plus og.build.html (the rendered page, for inspection; safe to delete).
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TAGLINE = "Offline maps and navigation for hikes and trail runs."


def main():
    tagline = sys.argv[1] if len(sys.argv) > 1 else TAGLINE
    html = open(os.path.join(HERE, "og.template.html")).read()
    contours = open(os.path.join(ART, "contours.svg")).read()
    route = open(os.path.join(ART, "route.svg")).read()
    # the route's built-in local contours are hidden in the OG (CSS vars); drop its accessible name
    route = route.replace('role="img"', 'aria-hidden="true"', 1)
    html = (html.replace("{{CONTOURS}}", contours)
                .replace("{{ROUTE}}", route)
                .replace("{{ICON}}", "file://" + os.path.join(ART, "icon-256.png"))
                .replace("{{TAGLINE}}", tagline))
    build = os.path.join(HERE, "og.build.html")
    open(build, "w").write(html)
    out = os.path.join(ART, "og.png")
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    "--user-data-dir=" + tempfile.mkdtemp(prefix="rw-chrome-"),
                    "--force-prefers-reduced-motion", "--force-device-scale-factor=1",
                    "--window-size=1200,630", "--screenshot=" + out, "file://" + build],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(out):
        raise SystemExit("Chrome did not write og.png")
    print(out)


if __name__ == "__main__":
    main()
