#!/usr/bin/env python3
"""Composite vs pink-only for every date + summary row. Same filter, stretch and pink rule
as pink_check.py. Usage: python3 compare_grid.py [clip_dir] [tag] [title] [event YYYYMMDD]"""
import sys, glob, os, math
from datetime import datetime
import numpy as np
from osgeo import gdal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
gdal.UseExceptions()

d     = sys.argv[1] if len(sys.argv) > 1 else "nisar_clips"
tag   = sys.argv[2] if len(sys.argv) > 2 else "T084A"
title = sys.argv[3] if len(sys.argv) > 3 else f"NISAR GCOV {tag}"
event = datetime.strptime(sys.argv[4] if len(sys.argv) > 4 else "20260802", "%Y%m%d")
K, S = 5, 2          # speckle box size; show every S-th pixel (panels are small)
PINK = "#FF00FF"

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
nR = np.clip((HH - hl) / (hh_ - hl), 0, 1)
nG = np.clip((HV - vl) / (vh - vl), 0, 1)
nB = np.clip((R - rl) / (rh - rl), 0, 1)
valid = np.isfinite(HH) & np.isfinite(HV)
pink = (nR > 0.55) & (nB > 0.55) & (nG < 0.5) & valid
del HH, HV, R
pct = 100 * pink.reshape(len(dates), -1).sum(1) / valid.reshape(len(dates), -1).sum(1)
pre = np.array([t < event for t in dates])

n = len(dates); rows = math.ceil(n / 2) + 1
h, w = nR.shape[1] // S, nR.shape[2] // S
fig, axs = plt.subplots(rows, 4, figsize=(16, 4 * rows * h / w + 1.2), squeeze=False)
for ax in axs.ravel():
    ax.axis("off")

for i, t in enumerate(dates):
    r, c = divmod(i, 2); c *= 2
    img = np.dstack([nR[i, ::S, ::S], nG[i, ::S, ::S], nB[i, ::S, ::S]])
    img[~np.isfinite(img)] = 0
    pimg = img.copy(); pimg[~pink[i, ::S, ::S]] = 0
    axs[r, c].imshow(img, interpolation="nearest")
    axs[r, c].set_title(f"{t:%b %-d} ({'before' if pre[i] else 'after'}): composite", fontsize=10)
    axs[r, c + 1].imshow(pimg, interpolation="nearest")
    axs[r, c + 1].set_title(f"{t:%b %-d}: pink only, {pct[i]:.1f}%", fontsize=10, color="#B000B0")

sr = rows - 1
ax = axs[sr, 0]; ax.axis("on")
ax.plot(dates, pct, "o-", c=PINK); ax.axvline(event, c="k", ls="--", lw=1)
ax.set_title("Pink pixels per date (%)", fontsize=10); ax.grid(alpha=0.3)
ax.tick_params(axis="x", labelrotation=45, labelsize=8)

share = pink[pre].sum(0)[::S, ::S] / max(pre.sum(), 1) - pink[~pre].sum(0)[::S, ::S] / max((~pre).sum(), 1)
im = axs[sr, 2].imshow(share, cmap="PiYG_r", vmin=-1, vmax=1, interpolation="nearest")
axs[sr, 2].set_title("Pink share before minus after\n(pink = lost, green = gained)", fontsize=10)
fig.colorbar(im, ax=axs[sr, 2], fraction=0.046, pad=0.02)

if os.path.exists("pink_loss.tif"):
    cls = gdal.Open("pink_loss.tif").ReadAsArray()[::S, ::S]
    axs[sr, 3].imshow(cls, cmap=ListedColormap(["black", PINK, "#888888"]), vmin=0, vmax=2,
                      interpolation="nearest")
    axs[sr, 3].set_title("pink_loss.tif", fontsize=10)
    axs[sr, 3].legend(handles=[Patch(color=PINK, label="lost pink"),
                               Patch(color="#888888", label="stayed pink")],
                      loc="lower right", fontsize=8)

fig.suptitle(f"{title}: composite (R=HH, G=HV, B=HH/HV) vs pink only, event {event:%d %b %Y}",
             fontsize=13)
fig.tight_layout(rect=(0, 0, 1, 0.98))
fig.savefig("compare_grid.png", dpi=110)
print("saved compare_grid.png")
