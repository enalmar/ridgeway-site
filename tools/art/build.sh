#!/bin/sh
# Rebuild every non-capture art asset for the Ridgeway site, in order.
# Needs: python3 (standard library only), swift, curl, Google Chrome (headless, for og.png).
#   APPICON=path/to/AppIcon-1024.png sh art/tools/build.sh
# APPICON is the app's 1024 px icon (App/iOS/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png in the
# app repository). It is required: there is no default, so no local path is published with the site.
set -eu
if [ -z "${APPICON:-}" ] || [ ! -f "$APPICON" ]; then
  echo "usage: APPICON=path/to/AppIcon-1024.png sh $0" >&2
  exit 64
fi
HERE=$(cd "$(dirname "$0")" && pwd)
ART="$HERE/.."
DEM="$ART/../dem-tiles"

sh "$HERE/fetch_dem.sh"
python3 -I "$HERE/dem.py" "$DEM" 13 4025 4029 2608 2611 "$DEM/helvellyn_z13"

# Background: desktop (16:10, 20 m interval, 100 m index) and mobile (portrait, 40 m / 200 m).
python3 -I "$HERE/contours.py" "$DEM/helvellyn_z13" "$ART/contours.svg" \
  --crop 160,140,1024,640 --interval 20 --sigma 3 --chaikin 2 --tol 0.45 --minlen 30
python3 -I "$HERE/contours.py" "$DEM/helvellyn_z13" "$ART/contours-mobile.svg" \
  --crop 367,70,480,860 --interval 40 --sigma 3.5 --chaikin 2 --tol 0.5 --minlen 30 --minor-w 0.7 --index-w 1.2

# Route motif + profile + stats.
python3 -I "$HERE/route.py" "$DEM/helvellyn_z13" "$ART"

# Icons from the app icon.
swift "$HERE/icons.swift" "$APPICON" "$ART"

# Social card.
python3 -I "$HERE/og.py"
