#!/usr/bin/env python3
"""Radar Vegetation Index maps from NISAR HH/HV.  RVI = 4*HV / (HH + HV) in LINEAR power.
usage: python3 rvi_map.py <folder with *_db.tif of ONE track> [--block 10] [--out DIR]
Blocks are averaged in linear power FIRST, then RVI is computed. Open water is masked (mean HH < -15 dB).
Outputs in --out (default <folder>/../results/rvi_<track>):
  <track>_RVI_mean.png / .tif      mean RVI over all dates (how vegetated)
  <track>_RVI_change.png           RVI last third minus first third (where vegetation grows / is cleared)
  <track>_RVI_timeseries.png/.csv  median RVI of forest-like (top quartile) vs changing blocks
  <track>_RVI_dates.png            small multiples, one map per date"""
import argparse, glob, os, re, sys
from datetime import date
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import per_pixel_rain as p
ap = argparse.ArgumentParser(); ap.add_argument("folder"); ap.add_argument("--block", type=int, default=10); ap.add_argument("--out", default=None); a = ap.parse_args()
fs = sorted(glob.glob(os.path.join(a.folder, "*_db.tif"))); R, Hm, ds, track, geo0 = [], [], [], None, None
for f in fs:
    m = re.search(r"(T\d{3}[AD])_(\d{8})_db", f)
    if not m: continue
    tr, s = m.groups(); track = tr; b, geo = p.read_bands(f); geo0 = geo0 or geo
    o = p.OFFSETS.get(tr, {}); on = s in o.get("dates", ())
    hh = 10 ** (p.block_db(p.pick(b, "HH", 0) + (o.get("HH", 0) if on else 0), a.block) / 10)   # linear power
    hv = 10 ** (p.block_db(p.pick(b, "HV", 1) + (o.get("HV", 0) if on else 0), a.block) / 10)
    R.append(4 * hv / (hh + hv)); Hm.append(10 * np.log10(hh)); ds.append(date(int(s[:4]), int(s[4:6]), int(s[6:])))
    print(f"  {tr} {ds[-1]}  RVI median {np.nanmedian(R[-1]):.2f}")
o_ = np.argsort(ds); ds = [ds[i] for i in o_]; RVI = np.stack([R[i] for i in o_]); HHdb = np.stack([Hm[i] for i in o_]); n = len(ds)
water = np.nanmean(HHdb, 0) < -15; RVI[:, water] = np.nan; mean = np.nanmean(RVI, 0)
k = max(1, n // 3); chg = np.nanmean(RVI[-k:], 0) - np.nanmean(RVI[:k], 0)
forest = mean >= np.nanpercentile(mean, 75); chang = np.isfinite(chg) & (np.abs(chg) >= 0.15)
print(f"\nmean RVI: median {np.nanmedian(mean):.2f}, 10th pct {np.nanpercentile(mean,10):.2f}, 90th pct {np.nanpercentile(mean,90):.2f}")
print(f"blocks with |RVI change| >= 0.15: {100*chang.sum()/np.isfinite(chg).sum():.1f}%")
out = a.out or os.path.join(a.folder, "..", "results", f"rvi_{track}"); os.makedirs(out, exist_ok=True)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
def show(arr, name, title, cmap, lo, hi, label):
    fig, ax = plt.subplots(figsize=(7, 6)); im = ax.imshow(arr, cmap=cmap, vmin=lo, vmax=hi); fig.colorbar(im, label=label); ax.set_title(title); ax.axis("off")
    fig.savefig(os.path.join(out, f"{track}_{name}.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
show(mean, "RVI_mean", f"{track}: mean Radar Vegetation Index (100 m blocks)", "YlGn", 0.2, 1.1, "RVI (relative, 0 = bare, ~1 = dense forest)")
show(chg, "RVI_change", f"{track}: RVI change, last third minus first third of the season", "RdYlGn", -0.4, 0.4, "change in RVI")
fig, axs = plt.subplots(2, (n + 1) // 2, figsize=(3 * ((n + 1) // 2), 6.4))
for ax, d, r in zip(axs.ravel(), ds, RVI): ax.imshow(r, cmap="YlGn", vmin=0.2, vmax=1.1); ax.set_title(d.strftime("%d %b"), fontsize=9); ax.axis("off")
for ax in axs.ravel()[n:]: ax.axis("off")
fig.suptitle(f"{track}: RVI per date"); fig.tight_layout(); fig.savefig(os.path.join(out, f"{track}_RVI_dates.png"), dpi=130); plt.close(fig)
ts = {"forest-like (top quartile)": np.nanmedian(RVI[:, forest], 1)}
if chang.sum() >= 20: ts["changing blocks"] = np.nanmedian(RVI[:, chang], 1)
fig, ax = plt.subplots(figsize=(9, 4.5))
for nm, v in ts.items(): ax.plot(ds, v, "o-", label=nm)
ax.set_ylabel("median RVI"); ax.grid(alpha=.3); ax.legend(); ax.set_title(f"{track}: RVI over time"); fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(os.path.join(out, f"{track}_RVI_timeseries.png"), dpi=150); plt.close(fig)
with open(os.path.join(out, f"{track}_RVI_timeseries.csv"), "w") as fh:
    fh.write("date," + ",".join(ts) + "\n")
    for i, d in enumerate(ds): fh.write(f"{d}," + ",".join(f"{v[i]:.3f}" for v in ts.values()) + "\n")
try: p.write_tif(os.path.join(out, f"{track}_RVI_mean.tif"), mean.astype(np.float32), p.block_geo(geo0, a.block))
except (Exception, SystemExit) as e: print("  (GeoTIFF not written:", e, ")")
print("done ->", os.path.abspath(out))
