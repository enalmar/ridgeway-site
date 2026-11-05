#!/usr/bin/env python3
"""Decode and stitch Terrarium elevation tiles into one float grid.

Standard library only (zlib PNG decoding). Terrarium encoding:
    elevation_m = R * 256 + G + B / 256 - 32768

Usage:
    python3 -I dem.py TILE_DIR Z X0 X1 Y0 Y1 OUT_PREFIX
        reads TILE_DIR/{z}_{x}_{y}.png for x in X0..X1, y in Y0..Y1 (inclusive)
        writes OUT_PREFIX.bin (little-endian float32, row-major) and OUT_PREFIX.json (size + geo bounds)

Fetch tiles first with fetch_dem.sh (same public source the app uses).
"""
import json
import math
import struct
import sys
import zlib
from array import array


def decode_png(path):
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    pos = 8
    idat = []
    width = height = bitdepth = ctype = interlace = None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctag == b"IHDR":
            width, height, bitdepth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif ctag == b"IDAT":
            idat.append(body)
        elif ctag == b"IEND":
            break
    if bitdepth != 8 or ctype not in (2, 6) or interlace != 0:
        raise ValueError("unsupported PNG layout in %s" % path)
    bpp = 3 if ctype == 2 else 4
    raw = zlib.decompress(b"".join(idat))
    stride = width * bpp
    out = bytearray(height * stride)
    prev = bytearray(stride)
    i = 0
    for row in range(height):
        ftype = raw[i]
        i += 1
        line = bytearray(raw[i:i + stride])
        i += stride
        if ftype == 1:
            for k in range(bpp, stride):
                line[k] = (line[k] + line[k - bpp]) & 255
        elif ftype == 2:
            for k in range(stride):
                line[k] = (line[k] + prev[k]) & 255
        elif ftype == 3:
            for k in range(stride):
                left = line[k - bpp] if k >= bpp else 0
                line[k] = (line[k] + ((left + prev[k]) >> 1)) & 255
        elif ftype == 4:
            for k in range(stride):
                a = line[k - bpp] if k >= bpp else 0
                b = prev[k]
                c = prev[k - bpp] if k >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[k] = (line[k] + pr) & 255
        elif ftype != 0:
            raise ValueError("bad filter %d" % ftype)
        out[row * stride:(row + 1) * stride] = line
        prev = line
    return width, height, bpp, out


def tile_to_lonlat(x, y, z):
    n = 2 ** z
    lon = x / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon, lat


def main():
    tile_dir, z, x0, x1, y0, y1, out = sys.argv[1:8]
    z, x0, x1, y0, y1 = int(z), int(x0), int(x1), int(y0), int(y1)
    nx, ny = x1 - x0 + 1, y1 - y0 + 1
    W, H = nx * 256, ny * 256
    grid = array("f", [0.0]) * (W * H)
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            w, h, bpp, px = decode_png("%s/%d_%d_%d.png" % (tile_dir, z, tx, ty))
            ox, oy = (tx - x0) * 256, (ty - y0) * 256
            for r in range(h):
                base = (oy + r) * W + ox
                rb = r * w * bpp
                for c in range(w):
                    k = rb + c * bpp
                    grid[base + c] = px[k] * 256 + px[k + 1] + px[k + 2] / 256.0 - 32768
    grid.tofile(open(out + ".bin", "wb"))
    lon0, lat0 = tile_to_lonlat(x0, y0, z)
    lon1, lat1 = tile_to_lonlat(x1 + 1, y1 + 1, z)
    meta = {"width": W, "height": H, "z": z, "x0": x0, "y0": y0,
            "west": lon0, "north": lat0, "east": lon1, "south": lat1,
            "min": min(grid), "max": max(grid)}
    json.dump(meta, open(out + ".json", "w"), indent=1)
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
