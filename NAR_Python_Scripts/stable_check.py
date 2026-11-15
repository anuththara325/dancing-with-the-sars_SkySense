#!/usr/bin/env python3
"""Calibration check: do STABLE surfaces shift between PROVISIONAL and VALIDATED dates?
Stable pixels chosen from provisional dates only: built (bright HH + high HH/HV), forest (high HV, low
variation), steady (10 % least-varying in HH and HV). Usage: python3 stable_check.py <clip_dir> <out_dir>"""
import sys, os, glob, csv
import numpy as np
from osgeo import gdal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime
gdal.UseExceptions()

CLIPS = sys.argv[1] if len(sys.argv) > 1 else "nisar_clips"
OUT = sys.argv[2] if len(sys.argv) > 2 else "web_nawal/data"
os.makedirs(OUT, exist_ok=True)
K = 5
C_HH, C_HV = "#FF0000", "#2DB800"

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

rows, fig_data = [], {}
for t in ("T084A", "T048D"):
    files = sorted(glob.glob(os.path.join(CLIPS, f"*_{t}_*_frequencyA_HHHH.tif")))
    files = [f for f in files if os.path.exists(f.replace("_HHHH.tif", "_HVHV.tif"))]
    if not files:
        continue
    dates = [os.path.basename(f)[:8] for f in files]
    val = np.array(["_P05036_" in f for f in files])
    if val.sum() == 0 or (~val).sum() < 3:
        print(t, ": need >= 3 provisional and >= 1 validated date"); continue
    with np.errstate(invalid="ignore", divide="ignore"):
        HH = np.stack([10 * np.log10(box(read(f))) for f in files])
        HV = np.stack([10 * np.log10(box(read(f.replace("_HHHH.tif", "_HVHV.tif")))) for f in files])
    P = ~val
    with np.errstate(invalid="ignore"):
        mHH, mHV = np.nanmean(HH[P], 0), np.nanmean(HV[P], 0)
        sHH, sHV = np.nanstd(HH[P], 0), np.nanstd(HV[P], 0)
    ok = np.isfinite(mHH) & np.isfinite(mHV) & np.isfinite(sHH) & np.isfinite(sHV)
    q = lambda a, p: np.nanpercentile(a[ok], p)
    ratio = mHH - mHV
    groups = {"built":  ok & (mHH > q(mHH, 97)) & (ratio > q(ratio, 75)),
              "forest": ok & (mHV > q(mHV, 85)) & (sHV < q(sHV, 50)),
              "steady": ok & (sHH < q(sHH, 10)) & (sHV < q(sHV, 10)),
              "scene":  ok}
    print(f"\n=== {t}  (provisional {int(P.sum())} dates, validated {int(val.sum())})")
    print("pixels per group:", {g: int(m.sum()) for g, m in groups.items()})
    last_prov = [i for i in range(len(files)) if P[i]][-2:]
    fig_data[t] = (dates, val, {})
    for g, m in groups.items():
        med_hh = np.array([np.nanmedian(HH[i][m]) for i in range(len(files))])
        med_hv = np.array([np.nanmedian(HV[i][m]) for i in range(len(files))])
        fig_data[t][2][g] = (med_hh, med_hv)
        ref_hh, ref_hv = med_hh[last_prov].mean(), med_hv[last_prov].mean()
        for i, d in enumerate(dates):
            rows.append({"track": t, "group": g, "date": f"{d[:4]}-{d[4:6]}-{d[6:]}",
                         "product": "VALIDATED" if val[i] else "PROVISIONAL",
                         "HH_median_dB": round(float(med_hh[i]), 3), "HV_median_dB": round(float(med_hv[i]), 3),
                         "n_px": int(m.sum())})
        off_hh, off_hv = med_hh[val].mean() - ref_hh, med_hv[val].mean() - ref_hv
        print(f"  {g:7s} validated minus last 2 provisional:  HH {off_hh:+.2f} dB   HV {off_hv:+.2f} dB")

with open(os.path.join(OUT, "stable_check.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

n = len(fig_data)
fig, axs = plt.subplots(2, n, figsize=(6.5 * n, 7.5), squeeze=False, sharex="col")
styles = {"built": "-", "forest": "--", "steady": ":", "scene": "-."}
for c, (t, (dates, val, gd)) in enumerate(fig_data.items()):
    x = [datetime.strptime(d, "%Y%m%d") for d in dates]
    for r, (k, col, lab) in enumerate(((0, C_HH, "HH"), (1, C_HV, "HV"))):
        ax = axs[r, c]
        for g, (a, b) in gd.items():
            y = (a, b)[k]
            ax.plot(x, y, ls=styles[g], color=col, lw=1.6, label=g)
            ax.scatter([xi for xi, v in zip(x, val) if not v], [yi for yi, v in zip(y, val) if not v], color=col, s=22, zorder=3)
            ax.scatter([xi for xi, v in zip(x, val) if v], [yi for yi, v in zip(y, val) if v], facecolor="white", edgecolor=col, s=40, zorder=4)
        ax.axvline(datetime(2026, 10, 21), color="#999999", ls=":", lw=1)
        ax.set_title(f"{t} {lab}: stable surfaces (hollow = validated)", loc="left", fontsize=10)
        ax.set_ylabel(f"median {lab} (dB)"); ax.grid(color="#eeeeee")
        if r == 0 and c == 0:
            ax.legend(frameon=False, fontsize=8, ncol=4)
fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(os.path.join(OUT, "stable_check.png"), dpi=130)
print(f"\nsaved {OUT}/stable_check.csv and {OUT}/stable_check.png")
