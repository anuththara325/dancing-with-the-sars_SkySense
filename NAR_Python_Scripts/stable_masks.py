#!/usr/bin/env python3
"""Where are the 'stable' pixels, and what land cover are they really?
1. Rebuilds the stable groups as stable_check.py does (provisional dates only).
2. Saves each group as a GeoTIFF mask.
3. Reads ESA WorldCover 10 m (2021) on the same grid and prints each group's land-cover mix.
Usage: python3 stable_masks.py <clip_dir> <track> <out_dir> [worldcover_tif_or_url]"""
import sys, os, glob, csv
import numpy as np
from osgeo import gdal
gdal.UseExceptions()

CLIPS = sys.argv[1] if len(sys.argv) > 1 else "nisar_clips"
TRACK = sys.argv[2] if len(sys.argv) > 2 else "T084A"
OUT   = sys.argv[3] if len(sys.argv) > 3 else "web_nawal/stable_masks"
WC    = sys.argv[4] if len(sys.argv) > 4 else \
    "/vsicurl/https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N06E078_Map.tif"
os.makedirs(OUT, exist_ok=True)
K = 5
CLASSES = {10: "tree cover", 20: "shrubland", 30: "grassland", 40: "cropland", 50: "built-up",
           60: "bare/sparse", 70: "snow/ice", 80: "water", 90: "herbaceous wetland", 95: "mangroves", 100: "moss/lichen"}

def read(p):
    a = gdal.Open(p).ReadAsArray().astype("float32")
    a[~np.isfinite(a) | (a <= 0)] = np.nan
    return a

def box(a, k=K):
    r = k // 2
    m = np.isfinite(a).astype("float64"); z = np.where(m > 0, a, 0).astype("float64")
    def wsum(x):
        c = np.pad(np.pad(x, r).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        return c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    with np.errstate(invalid="ignore", divide="ignore"):
        return (wsum(z) / wsum(m)).astype("float32")

files = sorted(f for f in glob.glob(os.path.join(CLIPS, f"*_{TRACK}_*_frequencyA_HHHH.tif"))
               if "_P05023_" in f and os.path.exists(f.replace("_HHHH.tif", "_HVHV.tif")))
if len(files) < 3:
    sys.exit("need >= 3 provisional dates")
with np.errstate(invalid="ignore", divide="ignore"):
    HH = np.stack([10 * np.log10(box(read(f))) for f in files])
    HV = np.stack([10 * np.log10(box(read(f.replace("_HHHH.tif", "_HVHV.tif")))) for f in files])
    mHH, mHV = np.nanmean(HH, 0), np.nanmean(HV, 0)
    sHH, sHV = np.nanstd(HH, 0), np.nanstd(HV, 0)
del HH, HV
ok = np.isfinite(mHH) & np.isfinite(mHV) & np.isfinite(sHH) & np.isfinite(sHV)
q = lambda a, p: np.nanpercentile(a[ok], p)
ratio = mHH - mHV
groups = {"built":  ok & (mHH > q(mHH, 97)) & (ratio > q(ratio, 75)),
          "forest": ok & (mHV > q(mHV, 85)) & (sHV < q(sHV, 50)),
          "steady": ok & (sHH < q(sHH, 10)) & (sHV < q(sHV, 10)),
          "scene":  ok}

ref = gdal.Open(files[0]); gt, prj = ref.GetGeoTransform(), ref.GetProjection()
ny, nx = ok.shape
code = np.zeros(ok.shape, np.uint8)
for v, g in ((1, "built"), (2, "forest"), (3, "steady")):
    code[groups[g] & (code == 0)] = v
    ds = gdal.GetDriverByName("GTiff").Create(os.path.join(OUT, f"{TRACK}_{g}.tif"), nx, ny, 1, gdal.GDT_Byte, ["COMPRESS=DEFLATE"])
    ds.SetGeoTransform(gt); ds.SetProjection(prj)
    b = ds.GetRasterBand(1); b.SetNoDataValue(0); b.WriteArray(groups[g].astype(np.uint8)); ds = None
ds = gdal.GetDriverByName("GTiff").Create(os.path.join(OUT, f"{TRACK}_groups.tif"), nx, ny, 1, gdal.GDT_Byte, ["COMPRESS=DEFLATE"])
ds.SetGeoTransform(gt); ds.SetProjection(prj)
b = ds.GetRasterBand(1); b.SetNoDataValue(0)
ct = gdal.ColorTable()
ct.SetColorEntry(1, (255, 0, 255, 255)); ct.SetColorEntry(2, (0, 140, 0, 255)); ct.SetColorEntry(3, (30, 110, 255, 255))
b.SetRasterColorTable(ct); b.WriteArray(code); ds = None
print(f"saved masks {TRACK}_built/forest/steady.tif and {TRACK}_groups.tif (1 built magenta, 2 forest green, 3 steady blue) in {OUT}/")

try:
    xmin, ymax = gt[0], gt[3]; xmax, ymin = xmin + gt[1] * nx, ymax + gt[5] * ny
    wc_ds = gdal.Warp("", WC, format="MEM", dstSRS=prj, outputBounds=(xmin, ymin, xmax, ymax),
                      width=nx, height=ny, resampleAlg="mode")
    wc = wc_ds.GetRasterBand(1).ReadAsArray()
except Exception as e:
    print("\nWorldCover could not be read:", e)
    print("Download tile N06E078 (2021 v200 map) from https://esa-worldcover.org and pass its path as the 4th argument.")
    sys.exit(0)

rows = []
print("\nLand cover of each group (ESA WorldCover 2021, % of the group's pixels):")
for g, m in groups.items():
    vals, cnt = np.unique(wc[m], return_counts=True)
    tot = cnt.sum()
    mix = sorted(((CLASSES.get(int(v), str(v)), 100 * c / tot) for v, c in zip(vals, cnt)), key=lambda x: -x[1])
    print(f"  {g:7s} ({int(tot):>7d} px): " + ", ".join(f"{n} {p:.0f}%" for n, p in mix[:4]))
    for n, p in mix:
        rows.append({"track": TRACK, "group": g, "landcover": n, "percent": round(p, 1), "group_px": int(tot)})
with open(os.path.join(OUT, f"{TRACK}_landcover_check.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"saved {OUT}/{TRACK}_landcover_check.csv")
