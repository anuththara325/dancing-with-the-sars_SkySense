#!/usr/bin/env python3
"""Seasonal crop cycle from NISAR HH/HV time series (paddy check).

usage: python3 crop_cycle.py <folder with *_db.tif of ONE track> [--block 10] [--min-range 3.0] [--out DIR]

Needs per_pixel_rain.py in the same folder. Run ascending and descending separately.
Outputs (in --out, default <folder>/../results/crop_<track>):
  *_timeseries.png  median HH, HV, HH/HV of 'changing' pixels vs a stable (forest-like) control
  *_range_map.png   HV range (max-min, 2nd-ranked) per block
  *_datemin_map.png date of the lowest HV per changing block (planting / flooding)
  *_datemax_map.png date of the highest HV per changing block (peak growth)
  *_series.csv      the numbers behind the time series
"""
import argparse, csv, glob, os, re, sys
from datetime import date
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import per_pixel_rain as p

ap = argparse.ArgumentParser()
ap.add_argument("folder"); ap.add_argument("--block", type=int, default=10)
ap.add_argument("--min-range", type=float, default=3.0, help="HV range (dB) to count as changing crop pixel")
ap.add_argument("--out", default=None)
a = ap.parse_args()

fs = sorted(glob.glob(os.path.join(a.folder, "*_db.tif")))
if not fs: sys.exit("no *_db.tif found in " + a.folder)
HH, HV, ds, track = [], [], [], None
for f in fs:
    m = re.search(r"(T\d{3}[AD])_(\d{8})_db", f)
    if not m: continue
    tr, s = m.groups(); track = tr
    bands, geo = p.read_bands(f)
    o = p.OFFSETS.get(tr, {}); on = s in o.get("dates", ())
    hh = p.pick(bands, "HH", 0) + (o.get("HH", 0) if on else 0)
    hv = p.pick(bands, "HV", 1) + (o.get("HV", 0) if on else 0)
    HH.append(p.block_db(hh, a.block)); HV.append(p.block_db(hv, a.block))
    ds.append(date(int(s[:4]), int(s[4:6]), int(s[6:])))
    print(f"  {tr} {ds[-1]}  offset {'yes' if on else 'no'}")
order = np.argsort(ds); ds = [ds[i] for i in order]
HH = np.stack([HH[i] for i in order]); HV = np.stack([HV[i] for i in order])
n = len(ds)
if n < 5: sys.exit("fewer than 5 dates - too few for a crop cycle")
out = a.out or os.path.join(a.folder, "..", "results", f"crop_{track}")
os.makedirs(out, exist_ok=True)

def rng2(x):  # 2nd highest - 2nd lowest (robust to one bad pass)
    s = np.sort(x, axis=0); return s[-2] - s[1]
mhh, mhv = np.nanmean(HH, 0), np.nanmean(HV, 0)
valid = np.isfinite(HV).sum(0) >= n - 1
land = valid & (mhh > -15.0) & (mhh < 2.0)          # drop open water + layover
R = np.where(valid, rng2(np.nan_to_num(HV, nan=np.nanmean(HV))), np.nan)
crop = land & (R >= a.min_range)
ctrl = land & (R < 1.0) & (mhv > np.nanpercentile(mhv[land], 50))   # stable, vegetated
print(f"blocks: land {land.sum()}, changing (HV range >= {a.min_range} dB) {crop.sum()} "
      f"({100*crop.sum()/max(land.sum(),1):.0f}%), stable control {ctrl.sum()}")
if crop.sum() < 50: print("  ! few changing blocks - try --min-range 2")

def stat(st, mask):
    v = st[:, mask]; return np.nanmedian(v, 1), np.nanpercentile(v, 25, 1), np.nanpercentile(v, 75, 1)
ser = {}
for nm, st in (("HH", HH), ("HV", HV)):
    for k, mk in (("crop", crop), ("ctrl", ctrl)):
        if mk.sum(): ser[(nm, k)] = stat(st, mk)
with open(os.path.join(out, f"{track}_series.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["date"] + [f"{nm}_{k}_{q}" for (nm, k) in ser for q in ("med", "p25", "p75")])
    for i, d in enumerate(ds): w.writerow([d] + [f"{ser[key][j][i]:.2f}" for key in ser for j in range(3)])

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
for axi, nm in zip(ax, ("HV", "HH")):
    if (nm, "crop") in ser:
        m_, lo, hi = ser[(nm, "crop")]
        axi.fill_between(ds, lo, hi, alpha=.2, color="tab:green"); axi.plot(ds, m_, "o-", color="tab:green", label="changing blocks (crop?)")
    if (nm, "ctrl") in ser:
        axi.plot(ds, ser[(nm, "ctrl")][0], "s--", color="gray", label="stable control (forest-like)")
    axi.set_ylabel(f"{nm} backscatter (dB)"); axi.grid(alpha=.3); axi.legend()
ax[0].set_title(f"{track}: seasonal HV/HH of changing pixels vs stable control  ({a.block*10} m blocks)")
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(os.path.join(out, f"{track}_timeseries.png"), dpi=150); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 6)); im = ax.imshow(np.where(land, R, np.nan), cmap="magma", vmin=0, vmax=8)
fig.colorbar(im, label="HV range over the season (dB)"); ax.set_title(f"{track}: how much HV changes"); ax.axis("off")
fig.savefig(os.path.join(out, f"{track}_range_map.png"), dpi=150, bbox_inches="tight"); plt.close(fig)

ordn = np.array([d.toordinal() for d in ds])
for nm, fn in (("datemin", np.nanargmin), ("datemax", np.nanargmax)):
    idx = np.full(HV.shape[1:], np.nan)
    idx[crop] = [fn(HV[:, i, j]) for i, j in zip(*np.where(crop))]
    fig, ax = plt.subplots(figsize=(7, 6)); im = ax.imshow(idx, cmap="turbo", vmin=0, vmax=n - 1)
    cb = fig.colorbar(im, ticks=range(n)); cb.ax.set_yticklabels([d.strftime("%d %b") for d in ds])
    ax.set_title(f"{track}: date of {'lowest' if nm=='datemin' else 'highest'} HV (changing blocks)"); ax.axis("off")
    fig.savefig(os.path.join(out, f"{track}_{nm}_map.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
print("done ->", os.path.abspath(out))
