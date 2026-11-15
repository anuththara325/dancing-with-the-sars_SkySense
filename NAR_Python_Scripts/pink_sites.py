#!/usr/bin/env python3
"""Turn pink_loss.tif (1 = lost pink) into clustered polygons with coordinates.
Outputs: pink_sites.csv, pink_sites.geojson, pink_sites.kml (Google Earth)
Usage: python3 pink_sites.py [min_ha]"""
import sys, csv
import numpy as np
from osgeo import gdal, ogr, osr
gdal.UseExceptions(); ogr.UseExceptions()

MIN_HA = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
src = gdal.Open("pink_loss.tif")
gt = src.GetGeoTransform(); px_m2 = abs(gt[1] * gt[5])
minpx = int(round(MIN_HA * 1e4 / px_m2))

lost = (src.GetRasterBand(1).ReadAsArray() == 1).astype(np.uint8)
mem = gdal.GetDriverByName("MEM").Create("", src.RasterXSize, src.RasterYSize, 1, gdal.GDT_Byte)
mem.SetGeoTransform(gt); mem.SetProjection(src.GetProjection())
b = mem.GetRasterBand(1); b.WriteArray(lost)
gdal.SieveFilter(b, None, b, minpx, 8)          # drop clusters smaller than MIN_HA

utm = osr.SpatialReference(); utm.ImportFromWkt(src.GetProjection())
wgs = osr.SpatialReference(); wgs.ImportFromEPSG(4326)
for s in (utm, wgs):
    s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
ct = osr.CoordinateTransformation(utm, wgs)

vds = ogr.GetDriverByName("Memory").CreateDataSource("v")
lyr = vds.CreateLayer("p", utm, ogr.wkbPolygon)
lyr.CreateField(ogr.FieldDefn("val", ogr.OFTInteger))
gdal.Polygonize(b, b, lyr, 0, ["8CONNECTED=8"])

sites = []
for f in lyr:
    g = f.GetGeometryRef().Clone()
    ha = g.GetArea() / 1e4
    if ha < MIN_HA:
        continue
    c = g.Centroid(); g.Transform(ct); c.Transform(ct)
    sites.append((ha, c.GetY(), c.GetX(), g))
sites.sort(key=lambda s: -s[0])
print(f"{len(sites)} clusters >= {MIN_HA} ha, total {sum(s[0] for s in sites):.1f} ha")

with open("pink_sites.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["rank", "area_ha", "lat", "lon", "google_maps"])
    for i, (ha, lat, lon, _) in enumerate(sites, 1):
        w.writerow([i, round(ha, 2), round(lat, 6), round(lon, 6),
                    f"https://www.google.com/maps/@{lat:.6f},{lon:.6f},400m/data=!3m1!1e3"])

for drvname, fname in (("GeoJSON", "pink_sites.geojson"), ("KML", "pink_sites.kml")):
    drv = ogr.GetDriverByName(drvname)
    if drv is None:
        print("no", drvname, "driver - skipped"); continue
    ds = drv.CreateDataSource(fname)
    L = ds.CreateLayer("lost_pink", wgs, ogr.wkbPolygon)
    for name, t in (("rank", ogr.OFTInteger), ("area_ha", ogr.OFTReal),
                    ("lat", ogr.OFTReal), ("lon", ogr.OFTReal)):
        L.CreateField(ogr.FieldDefn(name, t))
    for i, (ha, lat, lon, g) in enumerate(sites, 1):
        ft = ogr.Feature(L.GetLayerDefn())
        ft.SetField("rank", i); ft.SetField("area_ha", round(ha, 2))
        ft.SetField("lat", lat); ft.SetField("lon", lon); ft.SetGeometry(g)
        L.CreateFeature(ft)
    ds = None

print("\nrank  area_ha   lat        lon")
for i, (ha, lat, lon, _) in enumerate(sites[:15], 1):
    print(f"{i:>4}  {ha:7.2f}  {lat:.5f}  {lon:.5f}")
print("\nsaved pink_sites.csv, pink_sites.geojson, pink_sites.kml")
