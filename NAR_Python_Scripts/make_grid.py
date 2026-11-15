#!/usr/bin/env python3
"""Date grid of NISAR GCOV RGB composites (R=HH, G=HV, B=HH/HV) from nisar_clip.sh output.
Usage: python3 make_grid.py [clip_dir] [tag] [title] [out.png]"""
import sys, glob, os, math
from datetime import datetime
import numpy as np
from osgeo import gdal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

d     = sys.argv[1] if len(sys.argv) > 1 else "nisar_clips"
tag   = sys.argv[2] if len(sys.argv) > 2 else "T084A"
title = sys.argv[3] if len(sys.argv) > 3 else f"NISAR GCOV {tag}"
out   = sys.argv[4] if len(sys.argv) > 4 else f"grid_{tag}.png"
K = 5  # speckle box filter size (pixels); 1 = off

# NISAR false-colour convention (NASA SVS legend) - used everywhere in this project
MIX = [("HH", "#FF0000"), ("HV", "#33FF00"), ("HH/HV ratio", "#0000FF"),
       ("HH + HV", "#FFFF00"), ("HH + ratio", "#FF00FF"),
       ("HV + ratio", "#00FFFF"), ("all high", "#FFFFFF")]

def read(p):
    a = gdal.Open(p).ReadAsArray().astype("float32")
    a[~np.isfinite(a) | (a <= 0)] = np.nan
    return a

def box(a, k=K):
    if k <= 1:
        return a
    r = k // 2
    m = np.isfinite(a).astype("float64")
    z = np.where(m > 0, a, 0).astype("float64")
    def wsum(x):
        c = np.pad(np.pad(x, r).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        return c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    with np.errstate(invalid="ignore", divide="ignore"):
        return (wsum(z) / wsum(m)).astype("float32")

hh_files = sorted(glob.glob(os.path.join(d, f"*_{tag}_*_frequencyA_HHHH.tif")))
if not hh_files:
    sys.exit(f"No *_{tag}_*_HHHH.tif files in {d}")

scenes = []
for f in hh_files:
    hv_f = f.replace("_HHHH.tif", "_HVHV.tif")
    if not os.path.exists(hv_f):
        print("missing HV for", f); continue
    hh, hv = box(read(f)), box(read(hv_f))
    with np.errstate(invalid="ignore", divide="ignore"):
        hh_db, hv_db = 10 * np.log10(hh), 10 * np.log10(hv)
    name = os.path.basename(f)
    date = datetime.strptime(name[:8], "%Y%m%d")
    label = date.strftime("%b %-d") + (" (VALIDATED)" if "_P05036_" in name else "")
    scenes.append((label, hh_db, hv_db, hh_db - hv_db))
    print("read", label)

def limits(i):
    v = np.concatenate([s[i][np.isfinite(s[i])][::50] for s in scenes])
    return np.percentile(v, [2, 98])
lims = [limits(1), limits(2), limits(3)]
print("stretch (dB): HH %.1f..%.1f  HV %.1f..%.1f  HH/HV %.1f..%.1f" % tuple(np.ravel(lims)))

def rgb(s):
    ch = [np.clip((s[i + 1] - lo) / (hi - lo), 0, 1) for i, (lo, hi) in enumerate(lims)]
    img = np.dstack(ch); img[~np.isfinite(img)] = 0
    return img

n = len(scenes); nc = 3; nr = math.ceil(n / nc)
h, w = scenes[0][1].shape
fig, axs = plt.subplots(nr, nc, figsize=(5 * nc, 5 * nr * h / w + 0.9), squeeze=False)
for ax in axs.ravel():
    ax.axis("off")
for ax, s in zip(axs.ravel(), scenes):
    ax.imshow(rgb(s), interpolation="nearest"); ax.set_title(s[0], fontsize=12)
fig.suptitle(f"{title} (R=HH, G=HV, B=HH/HV ratio)", fontsize=12)
fig.legend(handles=[Patch(facecolor=c, edgecolor="0.3", label=l) for l, c in MIX],
           loc="lower center", ncol=len(MIX), frameon=False, fontsize=10)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(out, dpi=120)
print(f"saved {out} with {n} dates")
