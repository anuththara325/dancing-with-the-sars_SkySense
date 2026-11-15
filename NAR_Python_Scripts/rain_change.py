#!/usr/bin/env python3
"""Before vs after monsoon rainfall, measured (not just eyeballed).
Colours follow the project rule: R = HH, G = HV, B = HH/HV.
Outputs (folder rain_change/):
  rain_change.png      before mean | after mean | change composite | significant change
  change_dHH.png, change_dHV.png, change_dRatio.png   single change maps (dB)
  dates.csv            per date: scene mean/median HH, HV, ratio + dark-water area
  summary.csv          after minus before, area of significant increase/decrease
Usage: python3 rain_change.py <clip_dir> <tag> <before dates> <after dates>
  e.g. python3 rain_change.py clips_ratnapura T084A 20260912,20261018 20261030,20261111"""
import sys, glob, os, csv
from datetime import datetime
import numpy as np
from osgeo import gdal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
gdal.UseExceptions()

d      = sys.argv[1] if len(sys.argv) > 1 else "clips_ratnapura"
tag    = sys.argv[2] if len(sys.argv) > 2 else "T084A"
BEFORE = (sys.argv[3] if len(sys.argv) > 3 else "20260912,20261018").split(",")
AFTER  = (sys.argv[4] if len(sys.argv) > 4 else "20261030,20261111").split(",")
OUT = "rain_change"; os.makedirs(OUT, exist_ok=True)
K = 5
WATER_HH, WATER_HV = -15.0, -21.0          # dark-water thresholds (dB), L-band open water
C_HH, C_HV, C_R = "#FF0000", "#33FF00", "#0000FF"

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

files = sorted(glob.glob(os.path.join(d, f"*_{tag}_*_frequencyA_HHHH.tif")))
data = {}
for f in files:
    hv_f = f.replace("_HHHH.tif", "_HVHV.tif")
    if not os.path.exists(hv_f):
        continue
    key = os.path.basename(f)[:8]
    data[key] = (box(read(f)), box(read(hv_f)), "_P05036_" in f)   # linear power
    print("read", key, "(validated)" if data[key][2] else "")
src = gdal.Open(files[0]); gt = src.GetGeoTransform(); px_ha = abs(gt[1] * gt[5]) / 1e4
db = lambda x: 10 * np.log10(x)

# ---- per-date statistics ----
rows = []
for k in sorted(data):
    hh, hv, val = data[k]
    ok = np.isfinite(hh) & np.isfinite(hv)
    with np.errstate(invalid="ignore", divide="ignore"):
        Hd, Vd = db(hh), db(hv)
    water = ok & (Hd < WATER_HH) & (Vd < WATER_HV)
    phase = "before" if k in BEFORE else "after" if k in AFTER else "other"
    rows.append({"date": f"{k[:4]}-{k[4:6]}-{k[6:]}", "phase": phase, "validated": val,
                 "HH_mean_dB": round(float(db(np.nanmean(hh[ok]))), 3),
                 "HV_mean_dB": round(float(db(np.nanmean(hv[ok]))), 3),
                 "HHHV_mean_dB": round(float(db(np.nanmean(hh[ok]) / np.nanmean(hv[ok]))), 3),
                 "HH_median_dB": round(float(np.nanmedian(Hd[ok])), 3),
                 "HV_median_dB": round(float(np.nanmedian(Vd[ok])), 3),
                 "dark_water_ha": round(float(water.sum() * px_ha), 1)})
with open(os.path.join(OUT, "dates.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("\ndate        phase   HHmean  HVmean  HH/HV  dark-water(ha)")
for r in rows:
    print(f"{r['date']}  {r['phase']:6s} {r['HH_mean_dB']:7.2f} {r['HV_mean_dB']:7.2f} {r['HHHV_mean_dB']:6.2f} {r['dark_water_ha']:9.1f}"
          + ("  (validated)" if r["validated"] else ""))

# ---- before / after means (linear) and change ----
def mean_of(keys):
    hh = np.nanmean(np.stack([data[k][0] for k in keys]), 0)
    hv = np.nanmean(np.stack([data[k][1] for k in keys]), 0)
    return hh, hv
missing = [k for k in BEFORE + AFTER if k not in data]
if missing:
    sys.exit(f"dates not found: {missing}")
bh, bv = mean_of(BEFORE); ah, av = mean_of(AFTER)
with np.errstate(invalid="ignore", divide="ignore"):
    dHH, dHV = db(ah) - db(bh), db(av) - db(bv)
    dR = dHH - dHV
# natural variability = std of all non-after dates (dB), per pixel
ref = [k for k in data if k not in AFTER]
with np.errstate(invalid="ignore", divide="ignore"):
    sHH = np.nanstd(np.stack([db(data[k][0]) for k in ref]), 0)
    sHV = np.nanstd(np.stack([db(data[k][1]) for k in ref]), 0)
sig_up   = (dHV > np.maximum(2 * sHV, 1.5)) | (dHH > np.maximum(2 * sHH, 1.5))
sig_down = (dHV < -np.maximum(2 * sHV, 1.5)) | (dHH < -np.maximum(2 * sHH, 1.5))
ok = np.isfinite(dHH) & np.isfinite(dHV)
sig_up &= ok; sig_down &= ok

summ = {"before": "+".join(BEFORE), "after": "+".join(AFTER),
        "scene_dHH_dB": round(float(np.nanmedian(dHH)), 3), "scene_dHV_dB": round(float(np.nanmedian(dHV)), 3),
        "scene_dRatio_dB": round(float(np.nanmedian(dR)), 3),
        "sig_increase_ha": round(float(sig_up.sum() * px_ha), 1),
        "sig_decrease_ha": round(float(sig_down.sum() * px_ha), 1),
        "total_ha": round(float(ok.sum() * px_ha), 1)}
with open(os.path.join(OUT, "summary.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(summ)); w.writeheader(); w.writerow(summ)
print("\nafter minus before (scene median):  dHH %+.2f dB   dHV %+.2f dB   dHH/HV %+.2f dB"
      % (summ["scene_dHH_dB"], summ["scene_dHV_dB"], summ["scene_dRatio_dB"]))
print(f"significant increase: {summ['sig_increase_ha']} ha   significant decrease: {summ['sig_decrease_ha']} ha"
      f"   (of {summ['total_ha']} ha)")

# ---- figures ----
def lim(a):
    v = a[np.isfinite(a)][::50]; return np.percentile(v, [2, 98])
with np.errstate(invalid="ignore", divide="ignore"):
    BH, BV, AH, AV = db(bh), db(bv), db(ah), db(av)
L = [lim(np.concatenate([BH.ravel(), AH.ravel()])), lim(np.concatenate([BV.ravel(), AV.ravel()])),
     lim(np.concatenate([(BH - BV).ravel(), (AH - AV).ravel()]))]
def rgb(H, V):
    ch = [np.clip((x - lo) / (hi - lo), 0, 1) for x, (lo, hi) in zip((H, V, H - V), L)]
    img = np.dstack(ch); img[~np.isfinite(img)] = 0; return img
chg = np.dstack([np.clip(x / 6 + 0.5, 0, 1) for x in (dHH, dHV, dR)])   # grey = no change, +/-3 dB = full
chg[~np.isfinite(chg)] = 0
sig = np.zeros(dHH.shape + (3,)); sig[:] = 0.92
sig[sig_up] = (0.0, 0.6, 0.0); sig[sig_down] = (0.75, 0.0, 0.75)

fig, ax = plt.subplots(2, 2, figsize=(14, 14 * dHH.shape[0] / dHH.shape[1] + 1))
for a, img, t in ((ax[0, 0], rgb(BH, BV), f"Before ({', '.join(BEFORE)})"),
                  (ax[0, 1], rgb(AH, AV), f"After ({', '.join(AFTER)})"),
                  (ax[1, 0], chg, "Change composite: R = dHH, G = dHV, B = dHH/HV\n(grey = no change, +/-3 dB)"),
                  (ax[1, 1], sig, "Change beyond normal variation\ngreen = increase, magenta = decrease")):
    a.imshow(img, interpolation="nearest"); a.set_title(t, fontsize=11); a.axis("off")
fig.suptitle(f"{tag}: before vs after rainfall (R = HH, G = HV, B = HH/HV)", fontsize=13)
fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(os.path.join(OUT, "rain_change.png"), dpi=110)
plt.close(fig)

for arr, name, col in ((dHH, "dHH", C_HH), (dHV, "dHV", C_HV), (dR, "dRatio", C_R)):
    cm = LinearSegmentedColormap.from_list(name, ["#202020", "#f2f2f2", col])
    fig, a = plt.subplots(figsize=(9, 9 * arr.shape[0] / arr.shape[1] + 0.6))
    im = a.imshow(arr, cmap=cm, vmin=-4, vmax=4, interpolation="nearest"); a.axis("off")
    a.set_title(f"{name} = after - before (dB): bright colour = increase, dark = decrease")
    fig.colorbar(im, ax=a, fraction=0.035, pad=0.02, label="dB")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"change_{name}.png"), dpi=110); plt.close(fig)
print(f"\nsaved {OUT}/rain_change.png, change_dHH/dHV/dRatio.png, dates.csv, summary.csv")
