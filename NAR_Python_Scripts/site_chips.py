#!/usr/bin/env python3
"""Same location on every date: zoomed NISAR chips per site (from pink_sites.csv) across all
dates + Copernicus Browser (Sentinel-2) links per site and date.
Outputs: site_chips.png, site_links.csv   Usage: python3 site_chips.py [clip_dir] [tag] [half_width_m]"""
import sys, glob, os, csv
from datetime import datetime, timedelta
import numpy as np
from osgeo import gdal, osr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
gdal.UseExceptions()

d    = sys.argv[1] if len(sys.argv) > 1 else "nisar_clips"
tag  = sys.argv[2] if len(sys.argv) > 2 else "T084A"
HALF = float(sys.argv[3]) if len(sys.argv) > 3 else 300.0
K = 5

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

sites = [(int(r["rank"]), float(r["lat"]), float(r["lon"]), float(r["area_ha"]))
         for r in csv.DictReader(open("pink_sites.csv"))]
files = sorted(f for f in glob.glob(os.path.join(d, f"*_{tag}_*_frequencyA_HHHH.tif"))
               if "_P05023_" in f)
dates, HH, HV = [], [], []
for f in files:
    hv_f = f.replace("_HHHH.tif", "_HVHV.tif")
    if not os.path.exists(hv_f):
        continue
    with np.errstate(invalid="ignore", divide="ignore"):
        HH.append(10 * np.log10(box(read(f)))); HV.append(10 * np.log10(box(read(hv_f))))
    dates.append(datetime.strptime(os.path.basename(f)[:8], "%Y%m%d"))
    print("read", dates[-1].date())
HH, HV = np.stack(HH), np.stack(HV); R = HH - HV

def lim(a):
    v = a[np.isfinite(a)][::50]; return np.percentile(v, [2, 98])
(hl, hh_), (vl, vh), (rl, rh) = lim(HH), lim(HV), lim(R)

src = gdal.Open(files[0]); gt = src.GetGeoTransform()
utm = osr.SpatialReference(); utm.ImportFromWkt(src.GetProjection())
wgs = osr.SpatialReference(); wgs.ImportFromEPSG(4326)
for s in (utm, wgs):
    s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
to_utm = osr.CoordinateTransformation(wgs, utm)
hp = int(round(HALF / abs(gt[1])))

nS, nD = len(sites), len(dates)
fig, axs = plt.subplots(nS, nD, figsize=(1.9 * nD, 2.2 * nS + 0.8), squeeze=False)
for si, (rank, lat, lon, ha) in enumerate(sites):
    x, y, _ = to_utm.TransformPoint(lon, lat)
    col = int((x - gt[0]) / gt[1]); row = int((y - gt[3]) / gt[5])
    r0, r1 = max(row - hp, 0), min(row + hp + 1, HH.shape[1])
    c0, c1 = max(col - hp, 0), min(col + hp + 1, HH.shape[2])
    for di, t in enumerate(dates):
        sl = (di, slice(r0, r1), slice(c0, c1))
        img = np.dstack([np.clip((HH[sl] - hl) / (hh_ - hl), 0, 1),
                         np.clip((HV[sl] - vl) / (vh - vl), 0, 1),
                         np.clip((R[sl] - rl) / (rh - rl), 0, 1)])
        img[~np.isfinite(img)] = 0
        ax = axs[si, di]
        ax.imshow(img, interpolation="nearest")
        ax.plot(col - c0, row - r0, marker="o", mfc="none", mec="white", ms=12, mew=1.2)
        ax.set_xticks([]); ax.set_yticks([])
        if si == 0:
            ax.set_title(f"{t:%b %-d}", fontsize=10)
        if di == 0:
            ax.set_ylabel(f"Site {rank}\n{lat:.5f}, {lon:.5f}\n{ha:.2f} ha", fontsize=8)
fig.suptitle(f"Same location on every date: NISAR {tag} (R=HH, G=HV, B=HH/HV), "
             f"{2*HALF:.0f} m wide chips, white circle = site centre", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig("site_chips.png", dpi=130)

with open("site_links.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["site", "lat", "lon", "nisar_date", "layer", "copernicus_browser"])
    for rank, lat, lon, _ in sites:
        for t in dates:
            t0 = (t - timedelta(days=10)).strftime("%Y-%m-%dT00:00:00.000Z")
            t1 = t.strftime("%Y-%m-%dT23:59:59.999Z")
            for layer in ("1_TRUE_COLOR", "3_NDVI"):
                url = ("https://browser.dataspace.copernicus.eu/?zoom=16"
                       f"&lat={lat:.5f}&lng={lon:.5f}&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS"
                       f"&fromTime={t0}&toTime={t1}&layerId={layer}")
                w.writerow([rank, lat, lon, t.date(), layer, url])
print("saved site_chips.png and site_links.csv")
