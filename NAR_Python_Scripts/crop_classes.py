#!/usr/bin/env python3
"""HV/HH stability classes + optional WorldCover check.
usage: python3 crop_classes.py <folder *_db.tif of ONE track> [--block 10] [--hv-thr 2.0] [--hh-thr 2.0] [--worldcover WC.tif] [--out DIR]
Classes (range = 2nd-highest minus 2nd-lowest over the season, 100 m blocks):
 1 stable            HV < thr and HH < thr   (forest / built-up)
 2 HH only changes   surface wetness only
 3 HV only changes   (rare; noise / slope)
 4 both change       canopy + surface change together = seasonal-agriculture candidate
WorldCover (ESA, 10 m, code 40 = cropland, 10 trees, 30 grass, 80 water ...) is resampled to the blocks by majority."""
import argparse, glob, os, re, sys
from datetime import date
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import per_pixel_rain as p
ap = argparse.ArgumentParser(); ap.add_argument("folder"); ap.add_argument("--block", type=int, default=10)
ap.add_argument("--hv-thr", type=float, default=2.0); ap.add_argument("--hh-thr", type=float, default=2.0)
ap.add_argument("--worldcover", default=None); ap.add_argument("--out", default=None); a = ap.parse_args()
fs = sorted(glob.glob(os.path.join(a.folder, "*_db.tif"))); Hs, Vs, ds, track, geo0 = [], [], [], None, None
for f in fs:
    m = re.search(r"(T\d{3}[AD])_(\d{8})_db", f)
    if not m: continue
    tr, s = m.groups(); track = tr; b, geo = p.read_bands(f); geo0 = geo0 or geo
    o = p.OFFSETS.get(tr, {}); on = s in o.get("dates", ())
    Hs.append(p.block_db(p.pick(b, "HH", 0) + (o.get("HH", 0) if on else 0), a.block))
    Vs.append(p.block_db(p.pick(b, "HV", 1) + (o.get("HV", 0) if on else 0), a.block))
    ds.append(date(int(s[:4]), int(s[4:6]), int(s[6:])))
o_ = np.argsort(ds); ds = [ds[i] for i in o_]; HH = np.stack([Hs[i] for i in o_]); HV = np.stack([Vs[i] for i in o_]); n = len(ds)
def rg(x):
    s = np.sort(np.where(np.isfinite(x), x, np.nanmean(x)), 0); return s[-2] - s[1]
mh = np.nanmean(HH, 0); land = (np.isfinite(HV).sum(0) >= n - 1) & (mh > -15) & (mh < 2)
rh, rv = rg(HH), rg(HV); ch, cv = rh >= a.hh_thr, rv >= a.hv_thr
cls = np.where(~ch & ~cv, 1, np.where(ch & ~cv, 2, np.where(~ch & cv, 3, 4))).astype(float); cls[~land] = np.nan
names = {1: "stable", 2: "HH only changes", 3: "HV only changes", 4: "both change"}
print(f"{track}: {land.sum()} land blocks")
for k in (1, 2, 3, 4): print(f"  class {k} {names[k]:16s} {np.nansum(cls==k):7.0f}  ({100*np.nansum(cls==k)/land.sum():.1f}%)")
out = a.out or os.path.join(a.folder, "..", "results", f"cropclass_{track}"); os.makedirs(out, exist_ok=True)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
fig, ax = plt.subplots(figsize=(7, 6)); ax.imshow(cls, cmap=ListedColormap(["#bbbbbb", "#4c9be8", "#f0c040", "#d62728"]), vmin=1, vmax=4, interpolation="nearest")
ax.axis("off"); ax.set_title(f"{track}: grey stable | blue HH only | yellow HV only | red both change")
fig.savefig(os.path.join(out, f"{track}_classes_map.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True); col = {1: "gray", 2: "tab:blue", 4: "tab:red"}
for k in (1, 2, 4):
    mk = cls == k
    if mk.sum() < 20: continue
    for axi, S, nm in ((ax[0], HV, "HV"), (ax[1], HH, "HH")):
        axi.plot(ds, np.nanmedian(S[:, mk], 1), "o-", color=col[k], label=names[k]); axi.set_ylabel(f"{nm} (dB)"); axi.grid(alpha=.3)
ax[0].legend(); ax[0].set_title(f"{track}: median HV and HH per class"); fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(os.path.join(out, f"{track}_classes_timeseries.png"), dpi=150); plt.close(fig)
if a.worldcover:                                    # not testable in my sandbox (no GDAL): check the printout
    g = p.gdal(); gt, proj, nx, ny = geo0; bs = a.block
    w, h = nx // bs, ny // bs; bounds = (gt[0], gt[3] + gt[5] * h * bs, gt[0] + gt[1] * w * bs, gt[3])
    wc = g.Warp("", a.worldcover, format="MEM", dstSRS=proj, outputBounds=bounds, width=w, height=h, resampleAlg="mode").ReadAsArray()
    lab = {10: "trees", 20: "shrub", 30: "grass", 40: "cropland", 50: "built", 60: "bare", 80: "water", 90: "wetland", 95: "mangrove"}
    print("\nWorldCover share (rows = share of each class that is that land cover; 'all land' = base rate):")
    codes = [c for c in lab if np.sum(wc[land] == c) > 0]
    print("class".ljust(18) + "".join(f"{lab[c]:>10s}" for c in codes))
    for k, label in ((0, "all land"), (1, "stable"), (2, "HH only"), (4, "both change")):
        mk = land if k == 0 else (cls == k)
        print(label.ljust(18) + "".join(f"{100*np.mean(wc[mk] == c):9.0f}%" for c in codes))
    print("If 'both change' is much richer in cropland than 'all land' -> supports seasonal agriculture.")
print("done ->", os.path.abspath(out))
