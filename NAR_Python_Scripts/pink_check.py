#!/usr/bin/env python3
"""Is the fading 'pink' (high HH + high HH/HV, low HV) real or a scene-wide shift?
Outputs: pink_timeseries.png, pink_loss.tif (1 = lost pink, 2 = stayed pink), pink_stats.csv
Usage: python3 pink_check.py [clip_dir] [tag] [event_date YYYYMMDD]"""
import sys, glob, os, csv
from datetime import datetime
import numpy as np
from osgeo import gdal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
gdal.UseExceptions()

d     = sys.argv[1] if len(sys.argv) > 1 else "nisar_clips"
tag   = sys.argv[2] if len(sys.argv) > 2 else "T084A"
event = datetime.strptime(sys.argv[3] if len(sys.argv) > 3 else "20260802", "%Y%m%d")
K = 5
C_HH, C_HV, C_R, C_PINK = "#FF0000", "#33FF00", "#0000FF", "#FF00FF"   # project colours

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
pre = np.array([t < event for t in dates]); post = ~pre
print(f"{pre.sum()} pre-event dates, {post.sum()} post-event dates")

def lim(a):
    v = a[np.isfinite(a)][::50]; return np.percentile(v, [2, 98])
(hl, hh_), (vl, vh), (rl, rh) = lim(HH), lim(HV), lim(R)
nR = np.clip((HH - hl) / (hh_ - hl), 0, 1)
nG = np.clip((HV - vl) / (vh - vl), 0, 1)
nB = np.clip((R - rl) / (rh - rl), 0, 1)
valid = np.isfinite(HH) & np.isfinite(HV)
pink = (nR > 0.55) & (nB > 0.55) & (nG < 0.5) & valid

pink_pre  = pink[pre].sum(0)  >= max(1, int(np.ceil(0.75 * pre.sum())))
pink_post = pink[post].sum(0) >= max(1, int(np.ceil(0.66 * post.sum())))
lost   = pink_pre & ~pink_post & (pink[post].sum(0) <= 1)
stable = pink_pre & pink_post

med = lambda a: np.nanmedian(a.reshape(len(dates), -1), axis=1)
def roi_rel(a, m):
    return np.array([np.nanmedian(a[i][m]) for i in range(len(dates))]) - med(a)

fig, ax = plt.subplots(4, 1, figsize=(10, 13), sharex=True)
ax[0].plot(dates, med(HH), "o-", c=C_HH, label="HH"); ax[0].plot(dates, med(HV), "o-", c=C_HV, label="HV")
ax[0].plot(dates, med(R), "o-", c=C_R, label="HH/HV"); ax[0].set_ylabel("scene median (dB)")
ax[0].set_title("Whole scene"); ax[0].legend()
pinkpct = 100 * pink.reshape(len(dates), -1).sum(1) / valid.reshape(len(dates), -1).sum(1)
ax[1].plot(dates, pinkpct, "o-", c=C_PINK); ax[1].set_ylabel("% pixels pink"); ax[1].set_title("Pink fraction per date")
for a, m, ttl in ((ax[2], lost, f"Pixels that LOST pink ({lost.sum()} px = {lost.sum()*0.01:.1f} ha)"),
                  (ax[3], stable, f"Pixels that STAYED pink - control ({stable.sum()} px)")):
    if m.sum():
        a.plot(dates, roi_rel(HH, m), "o-", c=C_HH, label="HH")
        a.plot(dates, roi_rel(HV, m), "o-", c=C_HV, label="HV")
        a.plot(dates, roi_rel(R, m),  "o-", c=C_R,  label="HH/HV")
    a.axhline(0, c="0.6", lw=0.8); a.set_ylabel("dB, relative to scene"); a.set_title(ttl); a.legend()
for a in ax:
    a.axvline(event, c="k", ls="--", lw=1); a.grid(alpha=0.3)
ax[0].text(event, ax[0].get_ylim()[1], " event", va="top")
fig.tight_layout(); fig.savefig("pink_timeseries.png", dpi=110)

src = gdal.Open(files[0])
out = gdal.GetDriverByName("GTiff").Create("pink_loss.tif", src.RasterXSize, src.RasterYSize, 1,
                                          gdal.GDT_Byte, ["COMPRESS=DEFLATE"])
out.SetGeoTransform(src.GetGeoTransform()); out.SetProjection(src.GetProjection())
cls = np.zeros(lost.shape, np.uint8); cls[stable] = 2; cls[lost] = 1
b = out.GetRasterBand(1)
ct = gdal.ColorTable(); ct.SetColorEntry(1, (255, 0, 255, 255)); ct.SetColorEntry(2, (120, 120, 120, 255))
b.SetRasterColorTable(ct); b.SetNoDataValue(0); b.WriteArray(cls); out = None
print(f"lost pink: {lost.sum()} px ({lost.sum()*0.01:.1f} ha); stayed pink: {stable.sum()} px")

# ---------- numeric summary: mean (linear power -> dB) and median (dB) ----------
def stats(m):
    rows = []
    for i in range(len(dates)):
        hh, hv = HH[i][m], HV[i][m]
        ok = np.isfinite(hh) & np.isfinite(hv); hh, hv = hh[ok], hv[ok]
        if hh.size == 0:
            rows.append([np.nan] * 7); continue
        lh, lv = 10 ** (hh / 10), 10 ** (hv / 10)
        rows.append([10*np.log10(lh.mean()), np.median(hh), 10*np.log10(lv.mean()), np.median(hv),
                     10*np.log10(lh.mean()/lv.mean()), np.median(hh - hv), hh.size])
    return np.array(rows, float)
groups = {"scene": valid.all(0), "lost_pink": lost, "stayed_pink": stable}
hdr = ["date", "group", "HH_mean_dB", "HH_median_dB", "HV_mean_dB", "HV_median_dB",
       "HHHV_mean_dB", "HHHV_median_dB", "n_px", "pink_pct_scene"]
with open("pink_stats.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(hdr)
    for g, m in groups.items():
        s = stats(m)
        print(f"\n== {g} ({int(m.sum())} px) ==")
        print("date        HHmean HHmed  HVmean HVmed  HH/HVmean HH/HVmed  pink%")
        for i, t in enumerate(dates):
            mark = "*" if pre[i] else " "
            print(f"{t.date()}{mark} {s[i,0]:6.2f} {s[i,1]:6.2f} {s[i,2]:7.2f} {s[i,3]:6.2f}"
                  f"  {s[i,4]:8.2f} {s[i,5]:8.2f}  {pinkpct[i]:5.1f}")
            w.writerow([t.date(), g] + [round(x, 3) for x in s[i, :6]] + [int(s[i, 6]), round(pinkpct[i], 2)])
        a, b2 = s[pre, :6], s[post, :6]
        dlt = np.nanmean(b2, 0) - np.nanmean(a, 0)
        print(f"post-pre    {dlt[0]:+6.2f} {dlt[1]:+6.2f} {dlt[2]:+7.2f} {dlt[3]:+6.2f}"
              f"  {dlt[4]:+8.2f} {dlt[5]:+8.2f}")
print("\n(* = pre-event date)  saved pink_timeseries.png, pink_loss.tif, pink_stats.csv")
