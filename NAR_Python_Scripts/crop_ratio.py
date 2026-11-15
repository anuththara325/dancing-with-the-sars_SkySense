#!/usr/bin/env python3
"""Crop growth from the cross-ratio HV-HH (dB), with an honest selection test.
usage: python3 crop_ratio.py <folder with *_db.tif of ONE track> [--block 10] [--min-rise 1.5] [--out DIR]
Blocks are CHOSEN from odd-numbered dates (rise of the ratio, last third minus first third) and the curve is
SHOWN on even-numbered dates, so selection cannot create the trend. Needs per_pixel_rain.py alongside."""
import argparse, glob, os, re, sys
from datetime import date
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import per_pixel_rain as p
ap = argparse.ArgumentParser(); ap.add_argument("folder"); ap.add_argument("--block", type=int, default=10)
ap.add_argument("--min-rise", type=float, default=1.5); ap.add_argument("--out", default=None); a = ap.parse_args()
fs = sorted(glob.glob(os.path.join(a.folder, "*_db.tif"))); H, V, ds, track = [], [], [], None
for f in fs:
    m = re.search(r"(T\d{3}[AD])_(\d{8})_db", f)
    if not m: continue
    tr, s = m.groups(); track = tr; b, _ = p.read_bands(f)
    o = p.OFFSETS.get(tr, {}); on = s in o.get("dates", ())
    H.append(p.block_db(p.pick(b, "HH", 0) + (o.get("HH", 0) if on else 0), a.block))
    V.append(p.block_db(p.pick(b, "HV", 1) + (o.get("HV", 0) if on else 0), a.block))
    ds.append(date(int(s[:4]), int(s[4:6]), int(s[6:])))
o_ = np.argsort(ds); ds = [ds[i] for i in o_]; H = np.stack([H[i] for i in o_]); V = np.stack([V[i] for i in o_]); n = len(ds)
CR = V - H                                         # dB cross-ratio, cancels most of the wetness effect
mh, mv = np.nanmean(H, 0), np.nanmean(V, 0)
land = np.isfinite(CR).sum(0) >= n - 1; land &= (mh > -15) & (mh < 2)
ctrl = land & (np.nanstd(CR, 0) < 0.5) & (mv > np.nanpercentile(mv[land], 50))
odd, even = list(range(0, n, 2)), list(range(1, n, 2))
def rise(idx):
    k = max(1, len(idx) // 3); return np.nanmean(CR[idx[-k:]], 0) - np.nanmean(CR[idx[:k]], 0)
sel = land & (rise(odd) >= a.min_rise); chk = rise(even)
rc = np.nanmedian(chk[sel]); rn = np.nanmedian(chk[ctrl])
print(f"{track}: land {land.sum()} blocks; chosen on odd dates {sel.sum()} ({100*sel.sum()/land.sum():.1f}%)")
print(f"rise of ratio on the OTHER (even) dates: chosen blocks {rc:+.2f} dB, stable control {rn:+.2f} dB")
fr = np.nanmean(chk[sel] > 0.5) if sel.sum() else float('nan')
print(f"share of chosen blocks that also rise >0.5 dB on even dates: {100*fr:.0f}%  (chance for noise ~ 15-25%)")
print("CROP-GROWTH SIGNAL SUPPORTED" if (rc > 0.8 and rc - rn > 0.6) else "NOT SUPPORTED (selection effect or noise)")
out = a.out or os.path.join(a.folder, "..", "results", f"cropratio_{track}"); os.makedirs(out, exist_ok=True)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(9, 4.8)); x = np.array(ds)
if sel.sum():
    q = lambda M, k: np.nanpercentile(M[:, sel], k, 1)
    ax.fill_between(x, q(CR, 25), q(CR, 75), alpha=.2, color="tab:green"); ax.plot(x, np.nanmedian(CR[:, sel], 1), "o-", color="tab:green", label="chosen blocks (all dates)")
    ax.plot(x[even], np.nanmedian(CR[:, sel], 1)[even], "D", color="darkgreen", ms=9, mfc="none", label="even dates = not used for choosing")
ax.plot(x, np.nanmedian(CR[:, ctrl], 1), "s--", color="gray", label="stable control")
ax.set_ylabel("HV − HH (dB)"); ax.grid(alpha=.3); ax.legend(); ax.set_title(f"{track}: cross-ratio of blocks chosen on odd dates"); fig.autofmt_xdate()
fig.tight_layout(); fig.savefig(os.path.join(out, f"{track}_ratio_timeseries.png"), dpi=150); plt.close(fig)
tot = np.where(land, rise(list(range(n))), np.nan)
fig, ax = plt.subplots(figsize=(7, 6)); im = ax.imshow(tot, cmap="RdYlGn", vmin=-3, vmax=3); fig.colorbar(im, label="change of HV−HH, last third minus first third (dB)")
ax.set_title(f"{track}: where the canopy ratio rises (green)"); ax.axis("off"); fig.savefig(os.path.join(out, f"{track}_ratio_change_map.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
print("done ->", os.path.abspath(out))
