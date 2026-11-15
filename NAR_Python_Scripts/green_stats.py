#!/usr/bin/env python3
"""Measure GREEN pixels (hue 75-165, sat/val >= 0.25) of every date, both tracks, into one CSV.
Same stretch as web_nawal (manifest.json); computed on the 10 m clips so real dB values are reported.
Usage: python3 green_stats.py <clip_dir> <web_dir> [event YYYYMMDD]"""
import sys, os, glob, json, csv
import numpy as np
from osgeo import gdal
from matplotlib.colors import rgb_to_hsv
gdal.UseExceptions()

CLIPS = sys.argv[1] if len(sys.argv) > 1 else "nisar_clips"
WEB   = sys.argv[2] if len(sys.argv) > 2 else "web_nawal"
EVENT = sys.argv[3] if len(sys.argv) > 3 else "20260802"
K = 5
HMIN, HMAX, SMIN, VMIN = 75.0, 165.0, 0.25, 0.25

man = json.load(open(os.path.join(WEB, "data", "manifest.json")))
lims = man["settings"]["stretch_dB_2_98pct_all_dates_all_tracks"]
tracks = sorted({im["track"] for im in man["images"]})

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

u8 = lambda x: np.round(np.nan_to_num(x, nan=0.0) * 255)
def lin_mean_db(x_db):
    return float(10 * np.log10(np.mean(10 ** (x_db / 10)))) if x_db.size else float("nan")

rows = []
for t in tracks:
    for f in sorted(glob.glob(os.path.join(CLIPS, f"*_{t}_*_frequencyA_HHHH.tif"))):
        hv_f = f.replace("_HHHH.tif", "_HVHV.tif")
        if not os.path.exists(hv_f):
            continue
        d = os.path.basename(f)[:8]
        gt = gdal.Open(f).GetGeoTransform(); px_ha = abs(gt[1] * gt[5]) / 1e4
        with np.errstate(invalid="ignore", divide="ignore"):
            HH = 10 * np.log10(box(read(f))); HV = 10 * np.log10(box(read(hv_f)))
        R = HH - HV
        ok = np.isfinite(HH) & np.isfinite(HV)
        nR = np.clip((HH - lims["HH"][0]) / (lims["HH"][1] - lims["HH"][0]), 0, 1)
        nG = np.clip((HV - lims["HV"][0]) / (lims["HV"][1] - lims["HV"][0]), 0, 1)
        nB = np.clip((R - lims["R"][0]) / (lims["R"][1] - lims["R"][0]), 0, 1)
        rgb = np.dstack([u8(nR), u8(nG), u8(nB)]) / 255.0
        hsv = rgb_to_hsv(rgb); hue = hsv[:, :, 0] * 360
        green = ok & (hue >= HMIN) & (hue <= HMAX) & (hsv[:, :, 1] >= SMIN) & (hsv[:, :, 2] >= VMIN)
        G = rgb[:, :, 1][green] * 255
        has = G.size > 0
        rows.append({
            "track": t, "direction": "ascending" if t.endswith("A") else "descending",
            "date": f"{d[:4]}-{d[4:6]}-{d[6:]}", "phase": "before" if d < EVENT else "after",
            "product": "VALIDATED" if "_P05036_" in f else "PROVISIONAL",
            "green_px": int(green.sum()), "green_ha": round(float(green.sum() * px_ha), 1),
            "green_pct": round(float(100 * green.sum() / max(ok.sum(), 1)), 2),
            "G_mean": round(float(G.mean()), 2) if has else None,
            "G_median": round(float(np.median(G)), 2) if has else None,
            "G_std": round(float(G.std()), 2) if has else None,
            "G_p10": round(float(np.percentile(G, 10)), 2) if has else None,
            "G_p90": round(float(np.percentile(G, 90)), 2) if has else None,
            "HV_mean_dB": round(lin_mean_db(HV[green]), 3),
            "HV_median_dB": round(float(np.median(HV[green])), 3) if has else None,
            "HH_mean_dB": round(lin_mean_db(HH[green]), 3),
            "HHHV_mean_dB": round(lin_mean_db(HH[green]) - lin_mean_db(HV[green]), 3),
            "scene_HV_mean_dB": round(lin_mean_db(HV[ok]), 3)})
        r = rows[-1]
        print(f"{t} {r['date']} {r['phase']:6s} green {r['green_pct']:5.1f}%  G_mean {r['G_mean']}  "
              f"HV(green) {r['HV_mean_dB']:.2f} dB  HV(scene) {r['scene_HV_mean_dB']:.2f} dB"
              + ("  VALIDATED" if r["product"] == "VALIDATED" else ""))

out = os.path.join(WEB, "data", "green_stats.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("\nmean green % before vs after the event, per track")
for t in tracks:
    b = [r["green_pct"] for r in rows if r["track"] == t and r["phase"] == "before"]
    a = [r["green_pct"] for r in rows if r["track"] == t and r["phase"] == "after"]
    if b and a:
        print(f"  {t}: before {np.mean(b):.1f}%  after {np.mean(a):.1f}%  change {np.mean(a) - np.mean(b):+.1f} points")
print(f"saved {out} ({len(rows)} rows)")
