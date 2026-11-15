#!/usr/bin/env python3
"""Forest-only overlay + zoom boxes on the densest forest spots.
Usage: python3 forest_zoom_kml.py groups.tif out.kml [window_km=2] [n_spots=3]"""
import sys, os
import numpy as np
from osgeo import gdal
gdal.UseExceptions()

src, kml = sys.argv[1], sys.argv[2]
win_km = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
n = int(sys.argv[4]) if len(sys.argv) > 4 else 3
png = os.path.splitext(kml)[0] + "_forest.png"

ds = gdal.Warp("", src, format="MEM", dstSRS="EPSG:4326",
               resampleAlg="near", dstNodata=0)
a = ds.GetRasterBand(1).ReadAsArray()
gt = ds.GetGeoTransform()
h, w = a.shape
forest = (a == 2)

# forest-only PNG (green, solid)
rgba = np.zeros((4, h, w), np.uint8)
rgba[1][forest] = 200
rgba[3][forest] = 255
mem = gdal.GetDriverByName("MEM").Create("", w, h, 4, gdal.GDT_Byte)
for i in range(4):
    mem.GetRasterBand(i + 1).WriteArray(rgba[i])
gdal.GetDriverByName("PNG").CreateCopy(png, mem)

# find the n densest forest windows (moving-window count)
k = max(3, int(round(win_km * 1000 / (abs(gt[5]) * 111320))))
I = np.pad(forest.astype(np.float64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
S = I[k:, k:] - I[:-k, k:] - I[k:, :-k] + I[:-k, :-k]
spots = []
for _ in range(n):
    r, c = np.unravel_index(np.argmax(S), S.shape)
    if S[r, c] <= 0:
        break
    spots.append((r, c, 100 * S[r, c] / (k * k)))
    S[max(0, r - k):r + k, max(0, c - k):c + k] = -1   # no overlap

W, N = gt[0], gt[3]
E, Sth = W + gt[1] * w, N + gt[5] * h
rng = win_km * 1000 * 1.6

def box(name, west, south, east, north, colour, rng):
    lon, lat = (west + east) / 2, (south + north) / 2
    return f"""
 <Placemark><name>{name}</name>
  <LookAt><longitude>{lon}</longitude><latitude>{lat}</latitude><altitude>0</altitude>
   <heading>0</heading><tilt>0</tilt><range>{rng}</range></LookAt>
  <Style><LineStyle><color>{colour}</color><width>2</width></LineStyle><PolyStyle><fill>0</fill></PolyStyle></Style>
  <Polygon><outerBoundaryIs><LinearRing><coordinates>
  {west},{south},0 {east},{south},0 {east},{north},0 {west},{north},0 {west},{south},0
  </coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>"""

marks = box("Study box (full view)", W, Sth, E, N, "ff00ffff", 30000)
for i, (r, c, pct) in enumerate(spots, 1):
    west, north = W + c * gt[1], N + r * gt[5]
    east, south = west + k * gt[1], north + k * gt[5]
    marks += box(f"Zoom {i} ({pct:.0f}% forest px)", west, south, east, north, "ff0000ff", rng)
    print(f"Zoom {i}: centre {(south+north)/2:.5f}N, {(west+east)/2:.5f}E  forest px {pct:.0f}%")

with open(kml, "w") as f:
    f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Folder>
<name>{os.path.basename(src)} forest zoom</name>
 <GroundOverlay><name>forest (green)</name>
  <Icon><href>{os.path.basename(png)}</href></Icon>
  <LatLonBox><north>{N}</north><south>{Sth}</south><east>{E}</east><west>{W}</west></LatLonBox>
 </GroundOverlay>{marks}
</Folder></kml>
""")
print("Saved:", kml, "and", png)
