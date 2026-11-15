#!/usr/bin/env python3
"""Print georeferencing for a NISAR GCOV grid:
   line 1: SRS (EPSG:xxxx)   line 2: ulx uly lrx lry   (for gdal_translate -a_ullr)"""
import sys
from osgeo import gdal
gdal.UseExceptions()
url, freq = sys.argv[1], sys.argv[2]
ds = gdal.OpenEx(f"/vsicurl/{url}", gdal.OF_MULTIDIM_RASTER)
rg = ds.GetRootGroup()
base = f"/science/LSAR/GCOV/grids/{freq}"
x = rg.OpenMDArrayFromFullname(f"{base}/xCoordinates").ReadAsArray()
y = rg.OpenMDArrayFromFullname(f"{base}/yCoordinates").ReadAsArray()
p = rg.OpenMDArrayFromFullname(f"{base}/projection")
attrs = {a.GetName(): a.Read() for a in p.GetAttributes()}
epsg = attrs.get("epsg_code")
if isinstance(epsg, (list, tuple)): epsg = epsg[0]
if epsg is None:
    epsg = int(p.ReadAsArray())          # NISAR stores the EPSG code as the value too
dx, dy = float(x[1] - x[0]), float(y[1] - y[0])
# CF convention: coordinates are pixel centres -> shift half a pixel to get the outer edges
ulx, uly = float(x[0]) - dx / 2, float(y[0]) - dy / 2
lrx, lry = float(x[-1]) + dx / 2, float(y[-1]) + dy / 2
print(f"EPSG:{int(epsg)}")
print(f"{ulx} {uly} {lrx} {lry}")
print(f"# dx={dx} dy={dy} nx={len(x)} ny={len(y)}", file=sys.stderr)
