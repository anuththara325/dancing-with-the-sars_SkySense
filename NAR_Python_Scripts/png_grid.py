#!/usr/bin/env python3
"""Grids from export_web.py PNGs: <out>_rgb.png (composites) and <out>_matrix.png (dates x bands).
Usage: python3 png_grid.py <web_export_dir> <track> "<title>" <out_prefix>"""
import sys, os, glob, json, math
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

base  = sys.argv[1] if len(sys.argv) > 1 else "web_export"
track = sys.argv[2] if len(sys.argv) > 2 else "T084A"
title = sys.argv[3] if len(sys.argv) > 3 else f"NISAR GCOV {track}"
out   = sys.argv[4] if len(sys.argv) > 4 else "png_grid"
idir = os.path.join(base, "images", track)

phase = {}
try:
    m = json.load(open(os.path.join(base, "data", "manifest.json")))
    for im in m["images"]:
        if im["track"] == track and im["date"]:
            phase[im["date"].replace("-", "")] = im["phase"]
except Exception:
    pass

dates = sorted({os.path.basename(f)[:8] for f in glob.glob(os.path.join(idir, "*_rgb.png"))})
if not dates:
    sys.exit(f"no *_rgb.png in {idir}")

def label(d):
    s = datetime.strptime(d, "%Y%m%d").strftime("%d %b %Y")
    p = phase.get(d)
    return f"{s} ({p})" if p else s

MIX = [("HH", "#FF0000"), ("HV", "#33FF00"), ("HH/HV ratio", "#0000FF"), ("HH + HV", "#FFFF00"),
       ("HH + ratio", "#FF00FF"), ("HV + ratio", "#00FFFF"), ("all high", "#FFFFFF"), ("low / water", "#000000")]

first = plt.imread(os.path.join(idir, f"{dates[0]}_rgb.png"))
h, w = first.shape[:2]
nc = 3; nr = math.ceil(len(dates) / nc)
fig, axs = plt.subplots(nr, nc, figsize=(5.5 * nc, 5.5 * nr * h / w + 1.4), squeeze=False)
for ax in axs.ravel():
    ax.axis("off")
for ax, d in zip(axs.ravel(), dates):
    ax.imshow(plt.imread(os.path.join(idir, f"{d}_rgb.png"))); ax.set_title(label(d), fontsize=12)
fig.suptitle(f"{title}: R = HH, G = HV, B = HH/HV", fontsize=14)
fig.legend(handles=[Patch(facecolor=c, edgecolor="0.3", label=l) for l, c in MIX],
           loc="lower center", ncol=len(MIX), frameon=False, fontsize=10)
fig.tight_layout(rect=(0, 0.05, 1, 0.96)); fig.savefig(f"{out}_rgb.png", dpi=120); plt.close(fig)

kinds = [("rgb", "Composite"), ("hh", "HH (red)"), ("hv", "HV (green)"), ("ratio", "HH/HV (blue)")]
fig, axs = plt.subplots(len(dates), len(kinds), figsize=(4 * len(kinds), 4 * len(dates) * h / w + 1), squeeze=False)
for r, d in enumerate(dates):
    for c, (k, name) in enumerate(kinds):
        ax = axs[r, c]; ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        p = os.path.join(idir, f"{d}_{k}.png")
        if os.path.exists(p):
            ax.imshow(plt.imread(p))
        if r == 0:
            ax.set_title(name, fontsize=12)
        if c == 0:
            ax.set_ylabel(label(d), fontsize=10)
fig.suptitle(f"{title}: composite and each band", fontsize=14)
fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(f"{out}_matrix.png", dpi=110)
print(f"saved {out}_rgb.png ({len(dates)} dates) and {out}_matrix.png")
