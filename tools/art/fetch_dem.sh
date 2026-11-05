#!/bin/sh
# Fetch the Terrarium elevation tiles used for the Ridgeway site art (Helvellyn and Striding Edge,
# Lake District). Same public source the app uses. Tiles land in ../../dem-tiles/ (outside art/).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
OUT="$HERE/../../dem-tiles"
mkdir -p "$OUT"
fetch() { # z x y
  f="$OUT/$1_$2_$3.png"
  [ -s "$f" ] || curl -sf -o "$f" "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/$1/$2/$3.png"
}
for x in 4025 4026 4027 4028 4029; do for y in 2608 2609 2610 2611; do fetch 13 $x $y; done; done
echo "tiles in $OUT"
# Then:  python3 -I dem.py "$OUT" 13 4025 4029 2608 2611 "$OUT/helvellyn_z13"
