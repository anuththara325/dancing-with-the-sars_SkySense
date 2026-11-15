#!/usr/bin/env python3
"""One KML with a separate layer per class, so each can be switched on/off.
Usage: python3 mask_to_kml_split.py input_groups.tif output.kml [opacity]"""
import sys, os
import numpy as np
from osgeo import gdal
gdal.UseExceptions()

src, kml = sys.argv[1], sys.argv[2]
op = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
base = os.path.splitext(kml)[0]
out_dir = os.path.dirname(kml) or "."

ds = gdal.Warp("", src, format="MEM", dstSRS="EPSG:4326",
               resampleAlg="near", dstNodata=0)
a = ds.GetRasterBand(1).ReadAsArray()
gt = ds.GetGeoTransform()
h, w = a.shape
west, north = gt[0], gt[3]
east, south = west + gt[1] * w, north + gt[5] * h

classes = {1: ("bright_HH", "magenta", (255, 0, 255)),
           2: ("forest",    "green",   (0, 200, 0)),
           3: ("steady",    "blue",    (0, 120, 255))}

overlays = ""
for v, (name, cname, (r, g, b)) in classes.items():
    m = a == v
    rgba = np.zeros((4, h, w), np.uint8)
    rgba[0][m], rgba[1][m], rgba[2][m] = r, g, b
    rgba[3][m] = int(255 * op)
    png = f"{base}_{name}.png"
    mem = gdal.GetDriverByName("MEM").Create("", w, h, 4, gdal.GDT_Byte)
    for i in range(4):
        mem.GetRasterBand(i + 1).WriteArray(rgba[i])
    gdal.GetDriverByName("PNG").CreateCopy(png, mem)
    overlays += f"""
 <GroundOverlay><name>{cname}: {name} ({int(m.sum()):,} px)</name>
  <visibility>0</visibility>
  <Icon><href>{os.path.basename(png)}</href></Icon>
  <LatLonBox><north>{north}</north><south>{south}</south><east>{east}</east><west>{west}</west></LatLonBox>
 </GroundOverlay>"""
    print(f"{cname:8s} {name:10s} {int(m.sum()):>9,} px -> {png}")

# box outline + a fixed camera view so every screenshot matches
lon_c, lat_c = (west + east) / 2, (north + south) / 2
with open(kml, "w") as f:
    f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Folder>
<name>{os.path.basename(src)}</name>
<LookAt><longitude>{lon_c}</longitude><latitude>{lat_c}</latitude>
 <altitude>0</altitude><heading>0</heading><tilt>0</tilt><range>30000</range></LookAt>
<Placemark><name>study box</name>
 <Style><LineStyle><color>ff00ffff</color><width>2</width></LineStyle><PolyStyle><fill>0</fill></PolyStyle></Style>
 <Polygon><outerBoundaryIs><LinearRing><coordinates>
 {west},{south},0 {east},{south},0 {east},{north},0 {west},{north},0 {west},{south},0
 </coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>{overlays}
</Folder></kml>
""")
print("Saved:", kml)
