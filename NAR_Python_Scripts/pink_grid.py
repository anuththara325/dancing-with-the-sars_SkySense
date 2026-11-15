#!/usr/bin/env python3
"""Pink-only view of every date (R=HH, G=HV, B=HH/HV composite; same stretch + pink rule
as pink_check.py), black elsewhere. Outputs pink_only/<date>_pink.png + .tif, pink_grid.png"""
import sys, glob, os, math
from datetime import datetime
import numpy as np
from osgeo import gdal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
gdal.UseExceptions()

d     = sys.argv[1] if len(sys.argv) > 1 else "nisar_clips"
tag   = sys.argv[2] if len(sys.argv) > 2 else "T084A"
title = sys.argv[3] if len(sys.argv) > 3 else f"NISAR GCOV {tag}"
K = 5
OUT = "pink_only"; os.makedirs(OUT, exist_ok=True)

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

files = sorted(f for f in glob.glob(os.path.join(d, f"*_{tag}_*_frequencyA_HHHH.tif"))
               if "_P05023_" in f)
if not files:
    sys.exit("no files")
dates, HH, HV, used = [], [], [], []
for f in files:
    hv_f = f.replace("_HHHH.tif", "_HVHV.tif")
    if not os.path.exists(hv_f):
        continue
    with np.errstate(invalid="ignore", divide="ignore"):
        HH.append(10 * np.log10(box(read(f)))); HV.append(10 * np.log10(box(read(hv_f))))
    dates.append(datetime.strptime(os.path.basename(f)[:8], "%Y%m%d")); used.append(f)
    print("read", dates[-1].date())
HH, HV = np.stack(HH), np.stack(HV); R = HH - HV

def lim(a):
    v = a[np.isfinite(a)][::50]; return np.percentile(v, [2, 98])
(hl, hh_), (vl, vh), (rl, rh) = lim(HH), lim(HV), lim(R)
nR = np.clip((HH - hl) / (hh_ - hl), 0, 1)
nG = np.clip((HV - vl) / (vh - vl), 0, 1)
nB = np.clip((R - rl) / (rh - rl), 0, 1)
valid = np.isfinite(HH) & np.isfinite(HV)
pink = (nR > 0.55) & (nB > 0.55) & (nG < 0.5) & valid
print("stretch (dB): HH %.1f..%.1f  HV %.1f..%.1f  HH/HV %.1f..%.1f" % (hl, hh_, vl, vh, rl, rh))

src = gdal.Open(used[0]); gt = src.GetGeoTransform(); px_ha = abs(gt[1] * gt[5]) / 1e4
panels = []
for i, t in enumerate(dates):
    img = np.dstack([nR[i], nG[i], nB[i]]); img[~np.isfinite(img)] = 0
    img[~pink[i]] = 0
    pct = 100 * pink[i].sum() / max(valid[i].sum(), 1); ha = pink[i].sum() * px_ha
    panels.append((f"{t:%b %-d}  ({pct:.1f}%, {ha:.0f} ha)", img))
    stem = os.path.join(OUT, f"{t:%Y%m%d}_pink")
    plt.imsave(stem + ".png", img)
    ds = gdal.GetDriverByName("GTiff").Create(stem + ".tif", src.RasterXSize, src.RasterYSize, 1,
                                              gdal.GDT_Byte, ["COMPRESS=DEFLATE"])
    ds.SetGeoTransform(gt); ds.SetProjection(src.GetProjection())
    ds.GetRasterBand(1).WriteArray(pink[i].astype(np.uint8)); ds = None
    print(f"{t.date()}  pink {pct:5.2f}%  {ha:7.1f} ha  -> {stem}.png/.tif")

n = len(panels); nc = 3; nr = math.ceil(n / nc)
h, w = panels[0][1].shape[:2]
fig, axs = plt.subplots(nr, nc, figsize=(5 * nc, 5 * nr * h / w + 0.8), squeeze=False)
for ax in axs.ravel():
    ax.axis("off")
for ax, (label, img) in zip(axs.ravel(), panels):
    ax.imshow(img, interpolation="nearest"); ax.set_title(label, fontsize=11)
fig.suptitle(f"{title}: pink pixels only (high HH + high HH/HV, low HV); black = not pink", fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.97))
fig.savefig("pink_grid.png", dpi=120)
print("saved pink_grid.png")
