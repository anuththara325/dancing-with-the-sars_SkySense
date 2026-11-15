#!/usr/bin/env python3
"""Turn a mask GeoTIFF into a KML overlay for Google Earth.
Usage: python3 mask_to_kml.py input.tif output.kml [opacity 0-1]"""
import sys, os
import numpy as np
from osgeo import gdal
gdal.UseExceptions()

src, kml = sys.argv[1], sys.argv[2]
op = float(sys.argv[3]) if len(sys.argv) > 3 else 0.7
png = os.path.splitext(kml)[0] + ".png"

# 1. Reproject to lat/lon (what Google Earth uses)
ds = gdal.Warp("", src, format="MEM", dstSRS="EPSG:4326",
               resampleAlg="near", dstNodata=0)
a = ds.GetRasterBand(1).ReadAsArray()
gt = ds.GetGeoTransform()
h, w = a.shape
west, north = gt[0], gt[3]
east, south = west + gt[1] * w, north + gt[5] * h

# 2. Colours: use the file's colour table if it has one
colours = {1: (255, 0, 255), 2: (0, 200, 0), 3: (0, 120, 255)}
src_ds = gdal.Open(src)
ct = src_ds.GetRasterBand(1).GetColorTable()
if ct is not None:
    colours = {int(v): ct.GetColorEntry(int(v))[:3] for v in np.unique(a) if v > 0}

rgba = np.zeros((4, h, w), np.uint8)
for v, (r, g, b) in colours.items():
    m = a == v
    rgba[0][m], rgba[1][m], rgba[2][m] = r, g, b
    rgba[3][m] = int(255 * op)          # transparent everywhere else

# 3. Write the PNG
mem = gdal.GetDriverByName("MEM").Create("", w, h, 4, gdal.GDT_Byte)
for i in range(4):
    mem.GetRasterBand(i + 1).WriteArray(rgba[i])
gdal.GetDriverByName("PNG").CreateCopy(png, mem)

# 4. Write the KML that points to the PNG
name = os.path.basename(src)
with open(kml, "w") as f:
    f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Folder><name>{name}</name>
<GroundOverlay><name>{name}</name>
<description>magenta = bright HH (radar-facing slopes, some buildings); green = forest; blue = steady</description>
<Icon><href>{os.path.basename(png)}</href></Icon>
<LatLonBox><north>{north}</north><south>{south}</south><east>{east}</east><west>{west}</west></LatLonBox>
</GroundOverlay></Folder></kml>
""")

for v, c in colours.items():
    print(f"class {v}: colour {c}, {int((a == v).sum()):,} pixels")
print("Saved:", kml, "and", png)
