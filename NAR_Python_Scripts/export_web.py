#!/usr/bin/env python3
"""Export every NISAR date as separate web-ready images + all statistics.

Colour convention (whole project): R = HH, G = HV, B = HH/HV ratio.
Output folder (default web_export/):
  images/<track>/<date>_rgb.png     composite R=HH, G=HV, B=HH/HV
  images/<track>/<date>_pink.png    only pixels that look pink (high HH + high ratio, low HV)
  images/<track>/<date>_hh.png      HH alone (black -> red)
  images/<track>/<date>_hv.png      HV alone (black -> green)
  images/<track>/<date>_ratio.png   HH/HV alone (black -> blue)
  images/<track>/pink_loss.png      lost pink (magenta) / stayed pink (grey)
  data/stats_by_date.csv            mean, median, std per date, track and pixel group
  data/stats_summary.csv            post-minus-pre per track and group
  data/manifest.json                every image with date, track, bounds, stretch + all stats
  charts/timeline.png               scene HH (red), HV (green), HH/HV (blue), both tracks
  README.md                         methods, settings, results, caveats
All PNGs are reprojected to Web Mercator (EPSG:3857) with a transparent no-data area, so they
drop straight onto a Leaflet / MapLibre map with the lat/lon bounds in manifest.json.

Usage: python3 export_web.py [clip_dir] [out_dir] [event YYYYMMDD] [tracks e.g. T084A,T048D]"""
import sys, glob, os, csv, json
from datetime import datetime
import numpy as np
from osgeo import gdal, osr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
gdal.UseExceptions()

CLIPS  = sys.argv[1] if len(sys.argv) > 1 else "nisar_clips"
OUT    = sys.argv[2] if len(sys.argv) > 2 else "web_export"
EVENT  = datetime.strptime(sys.argv[3] if len(sys.argv) > 3 else "20260802", "%Y%m%d")
TRACKS = (sys.argv[4] if len(sys.argv) > 4 else "T084A,T048D").split(",")
K = 5                                   # speckle box filter (pixels)
C_HH, C_HV, C_R = "#FF0000", "#33FF00", "#0000FF"
TRACK_INFO = {"T084A": "track 084 ascending, ~05:44 local", "T048D": "track 048 descending, ~18:34 local"}

for sub in ("images", "data", "charts"):
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)

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

def db_pair(f):
    with np.errstate(invalid="ignore", divide="ignore"):
        return (10 * np.log10(box(read(f))),
                10 * np.log10(box(read(f.replace("_HHHH.tif", "_HVHV.tif")))))

# ---------- find files (one maturity level, HH + HV present) ----------
sets = {}
for t in TRACKS:
    fs = sorted(f for f in glob.glob(os.path.join(CLIPS, f"*_{t}_*_frequencyA_HHHH.tif"))
                if os.path.exists(f.replace("_HHHH.tif", "_HVHV.tif")))
    if fs:
        sets[t] = fs
if not sets:
    sys.exit("no files found")

# ---------- pass 1: one stretch for ALL dates of ALL tracks ----------
samp = {"HH": [], "HV": [], "R": []}
for t, fs in sets.items():
    for f in fs:
        hh, hv = db_pair(f)
        ok = np.isfinite(hh) & np.isfinite(hv)
        samp["HH"].append(hh[ok][::50]); samp["HV"].append(hv[ok][::50]); samp["R"].append((hh - hv)[ok][::50])
        print("sampled", t, os.path.basename(f)[:8])
lims = {k: [float(x) for x in np.percentile(np.concatenate(v), [2, 98])] for k, v in samp.items()}
print("stretch (dB):", lims)

# ---------- web mercator warp helper ----------
ref = gdal.Open(sets[TRACKS[0] if TRACKS[0] in sets else list(sets)[0]][0])
GT, PRJ, NX, NY = ref.GetGeoTransform(), ref.GetProjection(), ref.RasterXSize, ref.RasterYSize
BOUNDS = None

def save_web(rgba, path):
    """rgba: (ny, nx, 4) uint8 on the UTM grid -> PNG in EPSG:3857; returns [[S,W],[N,E]]."""
    global BOUNDS
    mem = gdal.GetDriverByName("MEM").Create("", NX, NY, 4, gdal.GDT_Byte)
    mem.SetGeoTransform(GT); mem.SetProjection(PRJ)
    for b in range(4):
        mem.GetRasterBand(b + 1).WriteArray(rgba[:, :, b])
    mem.GetRasterBand(4).SetColorInterpretation(gdal.GCI_AlphaBand)
    w = gdal.Warp("", mem, format="MEM", dstSRS="EPSG:3857", resampleAlg="near", dstAlpha=False)
    arr = np.dstack([w.GetRasterBand(b + 1).ReadAsArray() for b in range(4)]).astype(np.uint8)
    plt.imsave(path, arr)
    if BOUNDS is None:
        g = w.GetGeoTransform(); xs = [g[0], g[0] + g[1] * w.RasterXSize]; ys = [g[3], g[3] + g[5] * w.RasterYSize]
        m = osr.SpatialReference(); m.ImportFromEPSG(3857)
        ll = osr.SpatialReference(); ll.ImportFromEPSG(4326)
        for s in (m, ll):
            s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        ct = osr.CoordinateTransformation(m, ll)
        (w_, s_, _), (e_, n_, _) = ct.TransformPoint(min(xs), min(ys)), ct.TransformPoint(max(xs), max(ys))
        BOUNDS = [[round(s_, 6), round(w_, 6)], [round(n_, 6), round(e_, 6)]]
    return BOUNDS

def u8(x):
    return (np.nan_to_num(x, nan=0.0) * 255).round().astype(np.uint8)

# ---------- pass 2: per track ----------
rows, summary, manifest_imgs = [], [], []
px_ha = abs(GT[1] * GT[5]) / 1e4

def gstats(hh, hv, m):
    ok = m & np.isfinite(hh) & np.isfinite(hv)
    a, b = hh[ok], hv[ok]
    if a.size == 0:
        return None
    la, lb = 10 ** (a / 10), 10 ** (b / 10)
    return {"n_px": int(a.size), "area_ha": round(a.size * px_ha, 2),
            "HH_mean_dB": 10 * np.log10(la.mean()), "HH_median_dB": float(np.median(a)), "HH_std_dB": float(a.std()),
            "HV_mean_dB": 10 * np.log10(lb.mean()), "HV_median_dB": float(np.median(b)), "HV_std_dB": float(b.std()),
            "HHHV_mean_dB": 10 * np.log10(la.mean() / lb.mean()), "HHHV_median_dB": float(np.median(a - b)),
            "HHHV_std_dB": float((a - b).std())}

series = {}
for t, fs in sets.items():
    tdir = os.path.join(OUT, "images", t); os.makedirs(tdir, exist_ok=True)
    dates = [datetime.strptime(os.path.basename(f)[:8], "%Y%m%d") for f in fs]
    pre = np.array([d < EVENT for d in dates])
    HH, HV = zip(*[db_pair(f) for f in fs]); HH, HV = np.stack(HH), np.stack(HV)
    nR = np.clip((HH - lims["HH"][0]) / (lims["HH"][1] - lims["HH"][0]), 0, 1)
    nG = np.clip((HV - lims["HV"][0]) / (lims["HV"][1] - lims["HV"][0]), 0, 1)
    nB = np.clip((HH - HV - lims["R"][0]) / (lims["R"][1] - lims["R"][0]), 0, 1)
    valid = np.isfinite(HH) & np.isfinite(HV)
    pink = (nR > 0.55) & (nB > 0.55) & (nG < 0.5) & valid

    for i, d in enumerate(dates):
        a = (valid[i] * 255).astype(np.uint8)
        z = np.zeros_like(a)
        imgs = {
            "rgb":   np.dstack([u8(nR[i]), u8(nG[i]), u8(nB[i]), a]),
            "pink":  np.dstack([u8(nR[i]), u8(nG[i]), u8(nB[i]), (pink[i] * 255).astype(np.uint8)]),
            "hh":    np.dstack([u8(nR[i]), z, z, a]),
            "hv":    np.dstack([z, u8(nG[i]), z, a]),
            "ratio": np.dstack([z, z, u8(nB[i]), a]),
        }
        for kind, rgba in imgs.items():
            fn = f"{d:%Y%m%d}_{kind}.png"
            b = save_web(rgba, os.path.join(tdir, fn))
            manifest_imgs.append({"file": f"images/{t}/{fn}", "track": t, "date": f"{d:%Y-%m-%d}",
                                  "phase": "before" if pre[i] else "after", "kind": kind, "bounds_latlon": b})
        print("images", t, d.date())

    n_pre, n_post = int(pre.sum()), int((~pre).sum())
    pink_pre = pink[pre].sum(0) >= max(1, int(np.ceil(0.75 * n_pre)))
    pink_post = pink[~pre].sum(0) >= max(1, int(np.ceil(0.66 * n_post)))
    lost = pink_pre & ~pink_post & (pink[~pre].sum(0) <= 1)
    stable = pink_pre & pink_post
    cls = np.zeros(lost.shape + (4,), np.uint8)
    cls[lost] = (255, 0, 255, 255); cls[stable] = (136, 136, 136, 255)
    b = save_web(cls, os.path.join(tdir, "pink_loss.png"))
    manifest_imgs.append({"file": f"images/{t}/pink_loss.png", "track": t, "date": None, "phase": None,
                          "kind": "pink_loss", "bounds_latlon": b})

    groups = {"scene": valid.all(0), "lost_pink": lost, "stayed_pink": stable}
    per = {g: [] for g in groups}
    for i, d in enumerate(dates):
        pct = float(100 * pink[i].sum() / max(valid[i].sum(), 1))
        for g, m in groups.items():
            s = gstats(HH[i], HV[i], m)
            if s is None:
                continue
            row = {"track": t, "track_info": TRACK_INFO.get(t, ""), "date": f"{d:%Y-%m-%d}",
                   "phase": "before" if pre[i] else "after", "group": g, **s, "pink_pct_scene": pct}
            rows.append(row); per[g].append(row)
    for g, rs in per.items():
        if not rs:
            continue
        out = {"track": t, "group": g, "n_pre_dates": n_pre, "n_post_dates": n_post,
               "n_px": rs[0]["n_px"], "area_ha": rs[0]["area_ha"]}
        for k in ("HH_mean_dB", "HH_median_dB", "HV_mean_dB", "HV_median_dB", "HHHV_mean_dB", "HHHV_median_dB"):
            a = np.mean([r[k] for r in rs if r["phase"] == "before"])
            b_ = np.mean([r[k] for r in rs if r["phase"] == "after"])
            out[f"pre_{k}"], out[f"post_{k}"], out[f"delta_{k}"] = a, b_, b_ - a
        summary.append(out)
    series[t] = per["scene"]
    del HH, HV, nR, nG, nB

# ---------- write data ----------
def rnd(d):
    return {k: (round(float(v), 3) if isinstance(v, (float, np.floating)) else v) for k, v in d.items()}
with open(os.path.join(OUT, "data", "stats_by_date.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(rnd(r)) for r in rows]
with open(os.path.join(OUT, "data", "stats_summary.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(summary[0].keys())); w.writeheader(); [w.writerow(rnd(r)) for r in summary]
settings = {"event_date": f"{EVENT:%Y-%m-%d}", "speckle_filter": f"{K}x{K} boxcar, linear power",
            "stretch_dB_2_98pct_all_dates_all_tracks": lims, "pixel_m": abs(GT[1]),
            "pink_rule": "norm(HH)>0.55 and norm(HH/HV)>0.55 and norm(HV)<0.5",
            "lost_pink_rule": "pink on >=75% of pre dates, not pink on >=66% of post dates, pink on <=1 post date",
            "mean_rule": "means averaged in linear power then converted to dB",
            "product": "NISAR L2 GCOV PROVISIONAL (CRID P05023), frequency A, HHHH + HVHV",
            "image_crs": "EPSG:3857 (Web Mercator), bounds given in lat/lon",
            "colours": {"HH": C_HH, "HV": C_HV, "HH/HV": C_R}}
json.dump({"settings": json.loads(json.dumps(settings, default=float)), "bounds_latlon": BOUNDS, "images": manifest_imgs,
           "stats_by_date": [rnd(r) for r in rows], "stats_summary": [rnd(r) for r in summary]},
          open(os.path.join(OUT, "data", "manifest.json"), "w"), indent=1)

# ---------- timeline chart (scene medians, both tracks) ----------
fig, ax = plt.subplots(figsize=(10, 5))
styles = {"T084A": ("o", "-"), "T048D": ("s", "--")}
for t, rs in series.items():
    mk, ls = styles.get(t, ("o", "-"))
    x = [datetime.strptime(r["date"], "%Y-%m-%d") for r in rs]
    ax.plot(x, [r["HH_median_dB"] for r in rs], marker=mk, ls=ls, c=C_HH, label=f"HH {t}")
    ax.plot(x, [r["HV_median_dB"] for r in rs], marker=mk, ls=ls, c=C_HV, label=f"HV {t}")
ax.axvspan(datetime(2026, 7, 27), datetime(2026, 8, 10), color="0.85", label="NISAR data gap")
ax.axvline(EVENT, c="k", lw=1, ls=":", label="event")
ax.set_ylabel("scene median backscatter (dB)"); ax.grid(alpha=0.3)
ax2 = ax.twinx()
for t, rs in series.items():
    mk, ls = styles.get(t, ("o", "-"))
    x = [datetime.strptime(r["date"], "%Y-%m-%d") for r in rs]
    ax2.plot(x, [r["HHHV_median_dB"] for r in rs], marker=mk, ls=ls, c=C_R, alpha=0.7, label=f"HH/HV {t}")
ax2.set_ylabel("HH/HV (dB)", color=C_R)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="lower left", ncol=3)
ax.set_title("Nawalapitiya, NISAR GCOV: scene median HH, HV and HH/HV, both tracks")
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(os.path.join(OUT, "charts", "timeline.png"), dpi=140)

# ---------- README ----------
lines = ["# NISAR GCOV export: Nawalapitiya, Sri Lanka", "",
         f"Event date used for before/after: {EVENT:%d %b %Y}. Tracks: " +
         ", ".join(f"{t} ({TRACK_INFO.get(t,'')}, {len(sets[t])} dates)" for t in sets) + ".", "",
         "## Settings", ""] + [f"- **{k}**: {v}" for k, v in settings.items()] + [
         "", f"- **map bounds (lat/lon, [[S,W],[N,E]])**: {BOUNDS}", "",
         "## Post minus pre (dB)", "",
         "| Track | Group | Area (ha) | ΔHH mean | ΔHV mean | ΔHH/HV mean |", "|---|---|---|---|---|---|"] + [
         f"| {s['track']} | {s['group']} | {s['area_ha']} | {s['delta_HH_mean_dB']:+.2f} | "
         f"{s['delta_HV_mean_dB']:+.2f} | {s['delta_HHHV_mean_dB']:+.2f} |" for s in summary] + [
         "", "## Caveats", "",
         "- PROVISIONAL products: small date-to-date calibration differences are possible.",
         "- 'Lost pink' pixels are selected using post-event dates, so their change is inflated (selection bias).",
         "- Scene-wide changes where HH and HV move together with a stable ratio indicate moisture, not land-cover change.",
         "- Steep terrain: radar shadow/layover differs between ascending and descending tracks.",
         "- Images are display products (2-98 % stretch); use the CSV/JSON values for science.",
         "", "## Leaflet example", "", "```js",
         f"L.imageOverlay('images/T084A/20260726_rgb.png', {BOUNDS}, {{opacity: 0.85}}).addTo(map);", "```"]
open(os.path.join(OUT, "README.md"), "w").write("\n".join(lines) + "\n")
print(f"\nsaved {len(manifest_imgs)} images, {len(rows)} stat rows -> {OUT}/")
