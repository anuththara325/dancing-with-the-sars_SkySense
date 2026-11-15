#!/usr/bin/env python3
"""Keep only GREEN pixels (HV-dominated) of each composite (R=HH, G=HV, B=HH/HV), rest white; one grid.
Usage: python3 green_grid.py <web_export_dir> <track> "<title>" <out> [hue_min hue_max]"""
import sys, os, glob, json, math
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import rgb_to_hsv

base  = sys.argv[1] if len(sys.argv) > 1 else "web_export"
track = sys.argv[2] if len(sys.argv) > 2 else "T084A"
title = sys.argv[3] if len(sys.argv) > 3 else f"NISAR GCOV {track}"
out   = sys.argv[4] if len(sys.argv) > 4 else "green_grid"
HMIN  = float(sys.argv[5]) if len(sys.argv) > 5 else 75.0
HMAX  = float(sys.argv[6]) if len(sys.argv) > 6 else 165.0
SMIN, VMIN = 0.25, 0.25
idir = os.path.join(base, "images", track)
os.makedirs(out, exist_ok=True)

phase = {}
try:
    for im in json.load(open(os.path.join(base, "data", "manifest.json")))["images"]:
        if im["track"] == track and im["date"]:
            phase[im["date"].replace("-", "")] = im["phase"]
except Exception:
    pass

dates = sorted({os.path.basename(f)[:8] for f in glob.glob(os.path.join(idir, "*_rgb.png"))})
if not dates:
    sys.exit(f"no *_rgb.png in {idir}")

panels = []
print("date        phase    green % of valid pixels")
for d in dates:
    img = plt.imread(os.path.join(idir, f"{d}_rgb.png"))[:, :, :4]
    rgb, alpha = img[:, :, :3], img[:, :, 3] > 0.5
    hsv = rgb_to_hsv(rgb); hue = hsv[:, :, 0] * 360
    green = alpha & (hue >= HMIN) & (hue <= HMAX) & (hsv[:, :, 1] >= SMIN) & (hsv[:, :, 2] >= VMIN)
    outimg = np.ones_like(rgb); outimg[green] = rgb[green]
    plt.imsave(os.path.join(out, f"{d}_green.png"), outimg)
    pct = 100 * green.sum() / max(alpha.sum(), 1)
    lab = datetime.strptime(d, "%Y%m%d").strftime("%d %b %Y") + (f" ({phase[d]})" if d in phase else "")
    panels.append((f"{lab}: {pct:.1f}% green", outimg))
    print(f"{d}  {phase.get(d, ''):8s} {pct:6.1f}")

h, w = panels[0][1].shape[:2]
nc = 3; nr = math.ceil(len(panels) / nc)
fig, axs = plt.subplots(nr, nc, figsize=(5.5 * nc, 5.5 * nr * h / w + 1.0), squeeze=False)
for ax in axs.ravel():
    ax.axis("off")
for ax, (t, im) in zip(axs.ravel(), panels):
    ax.imshow(im); ax.set_title(t, fontsize=12)
    ax.add_patch(plt.Rectangle((0, 0), w - 1, h - 1, fill=False, ec="0.6", lw=0.8))
fig.suptitle(f"{title}: green pixels only (HV-dominated, vegetation volume); everything else white", fontsize=13)
fig.tight_layout(rect=(0, 0, 1, 0.96)); fig.savefig(f"{out}.png", dpi=120)
print(f"saved {out}.png and {len(panels)} images in {out}/")
