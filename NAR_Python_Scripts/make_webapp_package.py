#!/usr/bin/env python3
"""Build ONE folder with everything the web-app teammate needs (Nawalapitiya, NISAR GCOV).

  webapp_package/
    README.md                       how the folder is organised + Leaflet example
    INTERPRETATION.md               what the results mean (auto numbers filled in)
    google_earth/                   your Google Earth Pro screenshots (copied in)
    images/<track>/<date>_rgb.png   NISAR composite R=HH, G=HV, B=HH/HV (web map, transparent edge)
    images/<track>/<date>_green.png green pixels only, transparent elsewhere (web map overlay)
    display/<track>/<date>_green_white.png   green pixels on white (for slides / gallery)
    layers/forest_mask_<track>.png  verified forest mask (web map overlay)
    layers/study_box.geojson        the study polygon
    charts/                         green-vs-rain graphs, forest check, grids, comparison
    data/nisar_by_date.csv          ONE table: every date, both tracks, all numbers
    data/rainfall_daily.csv         GPM IMERG daily rainfall
    data/results_summary.csv        correlations with rain, ranges, responses
    data/manifest.json              bounds, file list, colours, stretch, correction

VALIDATED dates are shifted by the forest-measured offset so they line up with PROVISIONAL.
Usage:
  python3 make_webapp_package.py [clips] [web_dir] [mask_dir] [rain_csv] [google_earth_dir] [out]
  defaults: nisar_clips web_nawal web_nawal/stable_masks rainfall/imerg_nawalapitiya.csv
            web_nawal/google_earth webapp_package
"""
import sys, os, glob, json, csv, math, shutil, datetime as dt
import numpy as np
from osgeo import gdal, osr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as md
from matplotlib.colors import rgb_to_hsv
gdal.UseExceptions()

a = sys.argv[1:] + [None] * 6
CLIPS = a[0] or "nisar_clips"
WEB   = a[1] or "web_nawal"
MASKS = a[2] or os.path.join(WEB, "stable_masks")
RAIN  = a[3] or "rainfall/imerg_nawalapitiya.csv"
GE    = a[4] or os.path.join(WEB, "google_earth")
OUT   = a[5] or "webapp_package"

TRACKS = {"T084A": ("ascending", "05:44"), "T048D": ("descending", "18:34")}
CORR = {"T084A": (0.35, 0.11), "T048D": (0.68, 0.25)}   # dB added to VALIDATED (HH, HV)
BOX = [80.45, 6.90, 80.62, 7.10]                         # W S E N
K = 5
HMIN, HMAX, SMIN, VMIN = 75.0, 165.0, 0.25, 0.25
C_HH, C_HV, C_R, C_RAIN = "#D62828", "#2DB800", "#1F4FFF", "#7F93A8"
GAP = (dt.date(2026, 7, 27), dt.date(2026, 8, 10))

for s in ("images", "display", "layers", "charts", "data", "google_earth"):
    os.makedirs(os.path.join(OUT, s), exist_ok=True)

# ---------------- stretch (same as all earlier images) ----------------
man = json.load(open(os.path.join(WEB, "data", "manifest.json")))
LIM = man["settings"]["stretch_dB_2_98pct_all_dates_all_tracks"]

# ---------------- rainfall ----------------
rain = {}
for line in open(RAIN, encoding="utf-8", errors="ignore"):
    p = [x.strip().strip('"') for x in line.split(",")]
    if len(p) < 2:
        continue
    d = None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            d = dt.datetime.strptime(p[0].replace("T", " ").split(" ")[0], fmt).date(); break
        except ValueError:
            pass
    try:
        v = float(p[1])
    except ValueError:
        continue
    if d and v > -9000:
        rain[d] = max(v, 0.0)
if not rain:
    sys.exit(f"no rainfall rows read from {RAIN}")
print(f"rain days read: {len(rain)} ({min(rain)} .. {max(rain)})")
with open(os.path.join(OUT, "data", "rainfall_daily.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["date", "rain_mm"])
    for d in sorted(rain):
        w.writerow([d.isoformat(), round(rain[d], 2)])

def rain7(d):
    v = [rain.get(d - dt.timedelta(days=i)) for i in range(1, 8)]
    v = [x for x in v if x is not None]
    return round(sum(v), 1) if v else None

# ---------------- helpers ----------------
def read(p):
    x = gdal.Open(p).ReadAsArray().astype("float32")
    x[~np.isfinite(x) | (x <= 0)] = np.nan
    return x

def box(x, k=K):
    r = k // 2
    m = np.isfinite(x).astype("float64"); z = np.where(m > 0, x, 0).astype("float64")
    def ws(y):
        c = np.pad(np.pad(y, r).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        return c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    with np.errstate(invalid="ignore", divide="ignore"):
        return (ws(z) / ws(m)).astype("float32")

def lin_db(x):
    x = x[np.isfinite(x)]
    return round(float(10 * np.log10(np.mean(10 ** (x / 10)))), 3) if x.size else None

def norm(x, k):
    return np.clip((x - LIM[k][0]) / (LIM[k][1] - LIM[k][0]), 0, 1)

BOUNDS = None
def to_web(rgba, gt, prj, path):
    """UTM rgba -> EPSG:3857 PNG; returns the warped array and [[S,W],[N,E]]."""
    global BOUNDS
    ny, nx = rgba.shape[:2]
    mem = gdal.GetDriverByName("MEM").Create("", nx, ny, 4, gdal.GDT_Byte)
    mem.SetGeoTransform(gt); mem.SetProjection(prj)
    for b in range(4):
        mem.GetRasterBand(b + 1).WriteArray(rgba[:, :, b])
    mem.GetRasterBand(4).SetColorInterpretation(gdal.GCI_AlphaBand)
    w = gdal.Warp("", mem, format="MEM", dstSRS="EPSG:3857", resampleAlg="near", dstAlpha=False)
    arr = np.dstack([w.GetRasterBand(b + 1).ReadAsArray() for b in range(4)]).astype(np.uint8)
    plt.imsave(path, arr)
    if BOUNDS is None:
        g = w.GetGeoTransform()
        xs = [g[0], g[0] + g[1] * w.RasterXSize]; ys = [g[3], g[3] + g[5] * w.RasterYSize]
        m = osr.SpatialReference(); m.ImportFromEPSG(3857)
        ll = osr.SpatialReference(); ll.ImportFromEPSG(4326)
        for s in (m, ll):
            s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        ct = osr.CoordinateTransformation(m, ll)
        (w_, s_, _), (e_, n_, _) = ct.TransformPoint(min(xs), min(ys)), ct.TransformPoint(max(xs), max(ys))
        BOUNDS = [[round(s_, 6), round(w_, 6)], [round(n_, 6), round(e_, 6)]]
    return arr

def on_white(arr):
    arr = arr.astype("float64")
    if arr.max() > 1.0:
        arr = arr / 255.0
    al = arr[:, :, 3:4]
    return (arr[:, :, :3] * al + (1 - al)).clip(0, 1)

def load_mask(tag, ref_ds):
    p = os.path.join(MASKS, f"{tag}_groups.tif")
    ds = gdal.Open(p)
    if (ds.RasterXSize, ds.RasterYSize) != (ref_ds.RasterXSize, ref_ds.RasterYSize):
        gt = ref_ds.GetGeoTransform()
        ds = gdal.Warp("", ds, format="MEM", dstSRS=ref_ds.GetProjection(),
                       outputBounds=(gt[0], gt[3] + gt[5] * ref_ds.RasterYSize,
                                     gt[0] + gt[1] * ref_ds.RasterXSize, gt[3]),
                       width=ref_ds.RasterXSize, height=ref_ds.RasterYSize, resampleAlg="near")
    return ds.GetRasterBand(1).ReadAsArray() == 2

# ---------------- main loop ----------------
rows, images = [], []
for tag, (direction, ptime) in TRACKS.items():
    files = sorted(f for f in glob.glob(os.path.join(CLIPS, f"*_{tag}_*_frequencyA_HHHH.tif"))
                   if os.path.exists(f.replace("_HHHH.tif", "_HVHV.tif")))
    if not files:
        print("no clips for", tag); continue
    for s in ("images", "display"):
        os.makedirs(os.path.join(OUT, s, tag), exist_ok=True)
    ref = gdal.Open(files[0]); gt, prj = ref.GetGeoTransform(), ref.GetProjection()
    px_ha = abs(gt[1] * gt[5]) / 1e4
    forest = load_mask(tag, ref)
    fm = np.zeros(forest.shape + (4,), np.uint8)
    fm[forest] = (0, 200, 0, 255)
    to_web(fm, gt, prj, os.path.join(OUT, "layers", f"forest_mask_{tag}.png"))

    for f in files:
        name = os.path.basename(f); ds8 = name[:8]
        d = dt.datetime.strptime(ds8, "%Y%m%d").date()
        val = "_P05036_" in name
        cHH, cHV = CORR[tag] if val else (0.0, 0.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            HH = 10 * np.log10(box(read(f))) + cHH
            HV = 10 * np.log10(box(read(f.replace("_HHHH.tif", "_HVHV.tif")))) + cHV
        R = HH - HV
        ok = np.isfinite(HH) & np.isfinite(HV)
        rgb = np.dstack([norm(HH, "HH"), norm(HV, "HV"), norm(R, "R")])
        rgb = np.round(np.nan_to_num(rgb) * 255) / 255.0
        hsv = rgb_to_hsv(rgb); hue = hsv[:, :, 0] * 360
        green = ok & (hue >= HMIN) & (hue <= HMAX) & (hsv[:, :, 1] >= SMIN) & (hsv[:, :, 2] >= VMIN)

        u8 = (rgb * 255).astype(np.uint8)
        A = np.where(ok, 255, 0).astype(np.uint8)
        rgb_png = f"images/{tag}/{ds8}_rgb.png"
        grn_png = f"images/{tag}/{ds8}_green.png"
        to_web(np.dstack([u8, A]), gt, prj, os.path.join(OUT, rgb_png))
        garr = to_web(np.dstack([u8, np.where(green, 255, 0).astype(np.uint8)]), gt, prj,
                      os.path.join(OUT, grn_png))
        plt.imsave(os.path.join(OUT, "display", tag, f"{ds8}_green_white.png"), on_white(garr))

        G = rgb[:, :, 1][green] * 255
        nf = ~forest & ok
        rows.append({
            "track": tag, "direction": direction, "pass_local_time": ptime,
            "date": d.isoformat(), "product": "VALIDATED" if val else "PROVISIONAL",
            "offset_HH_dB_added": cHH, "offset_HV_dB_added": cHV,
            "rain_day_mm": round(rain.get(d, float("nan")), 1) if d in rain else None,
            "rain7_mm": rain7(d),
            "scene_HH_dB": lin_db(HH[ok]), "scene_HV_dB": lin_db(HV[ok]),
            "scene_HHHV_dB": None,
            "forest_HH_dB": lin_db(HH[forest & ok]), "forest_HV_dB": lin_db(HV[forest & ok]),
            "nonforest_HH_dB": lin_db(HH[nf]), "nonforest_HV_dB": lin_db(HV[nf]),
            "green_px": int(green.sum()), "green_ha": round(float(green.sum() * px_ha), 1),
            "green_pct": round(float(100 * green.sum() / max(ok.sum(), 1)), 2),
            "G_mean": round(float(G.mean()), 2) if G.size else None,
            "G_median": round(float(np.median(G)), 2) if G.size else None,
            "green_HV_dB": lin_db(HV[green]),
            "rgb_png": rgb_png, "green_png": grn_png,
        })
        r = rows[-1]
        r["scene_HHHV_dB"] = round(r["scene_HH_dB"] - r["scene_HV_dB"], 3)
        images += [{"file": rgb_png, "track": tag, "date": r["date"], "kind": "rgb", "product": r["product"]},
                   {"file": grn_png, "track": tag, "date": r["date"], "kind": "green", "product": r["product"]}]
        print(f"{tag} {r['date']} {r['product'][:4]}  rain7 {r['rain7_mm']}  green {r['green_pct']:5.1f}%  "
              f"G_mean {r['G_mean']}  HV {r['scene_HV_dB']}")
        del HH, HV, R, rgb, hsv, hue, green, u8

if not rows:
    sys.exit("nothing processed")

# ---------------- data files ----------------
with open(os.path.join(OUT, "data", "nisar_by_date.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

VARS = ["G_mean", "green_pct", "scene_HH_dB", "scene_HV_dB", "forest_HH_dB", "forest_HV_dB",
        "nonforest_HH_dB", "nonforest_HV_dB"]
summ = []
for tag in TRACKS:
    R_ = [r for r in rows if r["track"] == tag and r["rain7_mm"] is not None]
    if len(R_) < 3:
        continue
    rn = np.array([r["rain7_mm"] for r in R_], float)
    prov = np.array([r["product"] == "PROVISIONAL" for r in R_])
    for v in VARS:
        y = np.array([np.nan if r[v] is None else r[v] for r in R_], float)
        ok = np.isfinite(y)
        rr = np.corrcoef(rn[ok], y[ok])[0, 1]
        rp = np.corrcoef(rn[ok & prov], y[ok & prov])[0, 1] if (ok & prov).sum() > 2 else np.nan
        slope = np.polyfit(rn[ok], y[ok], 1)[0] * 100
        summ.append({"track": tag, "variable": v, "n_dates": int(ok.sum()),
                     "r_with_rain7_all": round(float(rr), 2), "r_with_rain7_provisional": round(float(rp), 2),
                     "change_per_100mm_rain7": round(float(slope), 3),
                     "min": round(float(np.nanmin(y)), 3), "max": round(float(np.nanmax(y)), 3),
                     "range": round(float(np.nanmax(y) - np.nanmin(y)), 3)})
with open(os.path.join(OUT, "data", "results_summary.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(summ[0])); w.writeheader(); w.writerows(summ)

W_, S_, E_, N_ = BOX
json.dump({"type": "FeatureCollection", "features": [{"type": "Feature",
           "properties": {"name": "Nawalapitiya study box"},
           "geometry": {"type": "Polygon", "coordinates": [[[W_, S_], [E_, S_], [E_, N_], [W_, N_], [W_, S_]]]}}]},
          open(os.path.join(OUT, "layers", "study_box.geojson"), "w"))

# ---------------- Google Earth screenshots ----------------
ge = sorted(glob.glob(os.path.join(GE, "*.jpg")) + glob.glob(os.path.join(GE, "*.jpeg")) +
            glob.glob(os.path.join(GE, "*.png")))
for g in ge:
    shutil.copy2(g, os.path.join(OUT, "google_earth", os.path.basename(g)))
print(f"Google Earth images copied: {len(ge)}" + ("" if ge else f"  (put screenshots in {GE}/ and re-run)"))

# ---------------- charts ----------------
def dts(R_):
    return [dt.date.fromisoformat(r["date"]) for r in R_]

rd = sorted(rain)
for tag, (direction, ptime) in TRACKS.items():
    R_ = [r for r in rows if r["track"] == tag]
    if not R_:
        continue
    x = dts(R_); val = np.array([r["product"] == "VALIDATED" for r in R_])
    title = f"Nawalapitiya, {direction} pass ({ptime} local)"

    # 1) green intensity + rainfall (two panels, shared dates)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True,
                                   gridspec_kw={"height_ratios": [2.2, 1]})
    y = np.array([r["G_mean"] for r in R_], float)
    ax1.plot(x, y, color=C_HV, lw=2.2, zorder=3)
    ax1.scatter(np.array(x)[~val], y[~val], s=55, color=C_HV, zorder=4, label="provisional")
    ax1.scatter(np.array(x)[val], y[val], s=55, facecolors="white", edgecolors=C_HV, lw=2, zorder=4,
                label="validated (offset-corrected)")
    ax1.set_ylabel("green pixel intensity\n(mean, 0-255)")
    ax1.legend(frameon=False, loc="upper left"); ax1.grid(axis="y", color="#eee")
    ax2.bar(rd, [rain[d] for d in rd], width=1, color=C_RAIN)
    ax2.set_ylabel("daily rain (mm)"); ax2.grid(axis="y", color="#eee")
    for ax in (ax1, ax2):
        ax.axvspan(*GAP, color="#eeeeee", zorder=0)
    ax1.text(GAP[0], ax1.get_ylim()[1], " NISAR data gap", fontsize=8, color="#777", va="top")
    ax2.xaxis.set_major_locator(md.MonthLocator()); ax2.xaxis.set_major_formatter(md.DateFormatter("%b %Y"))
    ax1.set_title(f"{title}: green pixel intensity (HV) and rainfall", loc="left")
    fig.text(0.01, 0.005, "NISAR GCOV R=HH, G=HV, B=HH/HV, one stretch for all dates. Rain: GPM IMERG Late daily.",
             fontsize=7.5, color="#777")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(os.path.join(OUT, "charts", f"green_rain_{tag}.png"), dpi=150); plt.close(fig)

    # 2) forest vs non-forest, change from own provisional mean
    fig, axs = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True)
    for ax, pol, col in ((axs[0], "HH", C_HH), (axs[1], "HV", C_HV)):
        for grp, ls, lab in (("forest", "-", "forest (WorldCover-verified)"),
                             ("nonforest", "--", "non-forest (tea / grass / town)")):
            v = np.array([r[f"{grp}_{pol}_dB"] for r in R_], float)
            v = v - v[~val].mean()
            ax.plot(x, v, ls, color=col, lw=2, alpha=1 if grp == "forest" else 0.65, label=lab)
            ax.scatter(np.array(x)[~val], v[~val], color=col, s=30, zorder=3)
            ax.scatter(np.array(x)[val], v[val], facecolors="white", edgecolors=col, s=30, zorder=3)
        ax.axhline(0, color="#999", lw=0.8); ax.axvspan(*GAP, color="#eeeeee", zorder=0)
        ax.set_ylabel(f"{pol} change (dB)"); ax.legend(frameon=False, fontsize=8, loc="upper left")
    axs[1].xaxis.set_major_locator(md.MonthLocator()); axs[1].xaxis.set_major_formatter(md.DateFormatter("%b %Y"))
    axs[0].set_title(f"{title}: forest vs non-forest (change from each group's provisional mean; hollow = validated)",
                     loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "charts", f"forest_vs_nonforest_{tag}.png"), dpi=150)
    plt.close(fig)

    # 3) green-only grid on white
    ims = [(r["date"], plt.imread(os.path.join(OUT, "display", tag, f"{r['date'].replace('-', '')}_green_white.png")),
            r) for r in R_]
    nc = 4; nr = math.ceil(len(ims) / nc); h, w = ims[0][1].shape[:2]
    fig, axs = plt.subplots(nr, nc, figsize=(4.2 * nc, 4.2 * nr * h / w + 0.8), squeeze=False)
    for ax in axs.ravel():
        ax.axis("off")
    for ax, (d, im, r) in zip(axs.ravel(), ims):
        ax.imshow(im)
        ax.set_title(f"{d}  {'V' if r['product'] == 'VALIDATED' else 'P'}\n"
                     f"{r['green_pct']:.1f}% green, rain7 {r['rain7_mm']} mm", fontsize=9)
    fig.suptitle(f"{title}: green pixels only (P = provisional, V = validated, offset-corrected)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(os.path.join(OUT, "charts", f"green_grid_{tag}.png"), dpi=110); plt.close(fig)

    # 4) comparison: Google Earth | NISAR dry | NISAR wet | green dry | green wet
    P = [r for r in R_ if r["product"] == "PROVISIONAL" and r["rain7_mm"] is not None]
    if P:
        dry, wet = min(P, key=lambda r: r["rain7_mm"]), max(P, key=lambda r: r["rain7_mm"])
        panels = []
        gef = [g for g in ge if "box" in os.path.basename(g).lower() or "original" in os.path.basename(g).lower()]
        if gef or ge:
            panels.append(("Google Earth Pro (reference)", plt.imread((gef or ge)[0])))
        for r, lab in ((dry, "driest"), (wet, "wettest")):
            panels.append((f"NISAR {r['date']} ({lab})\nrain7 {r['rain7_mm']} mm",
                           on_white(plt.imread(os.path.join(OUT, r["rgb_png"]))[:, :, :4])))
        for r, lab in ((dry, "driest"), (wet, "wettest")):
            panels.append((f"green only {r['date']} ({lab})\n{r['green_pct']:.1f}% green, G {r['G_mean']}",
                           plt.imread(os.path.join(OUT, "display", tag, f"{r['date'].replace('-', '')}_green_white.png"))))
        fig, axs = plt.subplots(1, len(panels), figsize=(4.4 * len(panels), 5.2))
        for ax, (t_, im) in zip(np.atleast_1d(axs), panels):
            ax.imshow(im); ax.set_title(t_, fontsize=9); ax.axis("off")
        fig.suptitle(f"{title}: reference image, NISAR composite (R=HH, G=HV, B=HH/HV) and green-only, dry vs wet",
                     fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        fig.savefig(os.path.join(OUT, "charts", f"comparison_{tag}.png"), dpi=130); plt.close(fig)

# ---------------- manifest ----------------
json.dump({
    "site": "Nawalapitiya, Central Province, Sri Lanka", "study_box_WSEN": BOX,
    "bounds_latlon": BOUNDS, "image_crs": "EPSG:3857 PNG overlays; bounds are [[south, west], [north, east]]",
    "colours": {"HH": "red", "HV": "green", "HH/HV": "blue", "legend": "R = HH, G = HV, B = HH/HV (NASA SVS style)"},
    "stretch_dB": LIM, "speckle_filter": f"{K}x{K} boxcar in linear power",
    "green_rule": f"hue {HMIN}-{HMAX} deg, saturation >= {SMIN}, value >= {VMIN}",
    "validated_offset_dB_added": {t: {"HH": c[0], "HV": c[1]} for t, c in CORR.items()},
    "offset_method": "validated minus last two provisional dates, measured on WorldCover-verified forest",
    "tracks": {t: {"direction": v[0], "pass_local_time": v[1]} for t, v in TRACKS.items()},
    "layers": [f"layers/forest_mask_{t}.png" for t in TRACKS] + ["layers/study_box.geojson"],
    "images": images, "google_earth": [f"google_earth/{os.path.basename(g)}" for g in ge],
    "data": ["data/nisar_by_date.csv", "data/rainfall_daily.csv", "data/results_summary.csv"],
}, open(os.path.join(OUT, "data", "manifest.json"), "w"), indent=1)


# ---------------- INTERPRETATION ----------------
S = {(x["track"], x["variable"]): x for x in summ}
def g(t, v, k):
    x = S.get((t, v)); return "n/a" if x is None else x[k]
def extreme(t, fn):
    P = [r for r in rows if r["track"] == t and r["product"] == "PROVISIONAL" and r["rain7_mm"] is not None]
    return fn(P, key=lambda r: r["rain7_mm"]) if P else None
lines = ["# Nawalapitiya: what the NISAR results mean", "",
 "Site: Nawalapitiya, Central Province, Sri Lanka (hill country, forest + tea + town).",
 "Data: NISAR L2 GCOV, L-band (24 cm), HH + HV, 10 m, June - November 2026; GPM IMERG daily rainfall; ESA WorldCover 2021.",
 "Colours everywhere: R = HH, G = HV, B = HH/HV.", "",
 "## 1. What the green colour is",
 "Green pixels are where HV (cross-polarised) is strong compared with HH. At L-band, HV comes mainly from",
 "volume scattering in vegetation (branches, stems, leaves), and it gets stronger when that vegetation and",
 "the soil under it hold more water (higher dielectric constant). So the green intensity is a proxy for",
 "vegetation + moisture, not 'greenness' in the optical sense.", "",
 "## 2. Main result: backscatter follows rainfall",
 "| Track | Variable | r with 7-day rain | change per 100 mm | range over season |", "|---|---|---|---|---|"]
for t, (direction, ptime) in TRACKS.items():
    for v, lab in (("G_mean", "green intensity (0-255)"), ("scene_HV_dB", "scene HV (dB)"),
                   ("forest_HV_dB", "forest HV (dB)"), ("nonforest_HV_dB", "non-forest HV (dB)"),
                   ("scene_HH_dB", "scene HH (dB)")):
        lines.append(f"| {direction} ({ptime}) | {lab} | {g(t, v, 'r_with_rain7_all')} | "
                     f"{g(t, v, 'change_per_100mm_rain7')} | {g(t, v, 'range')} |")
lines += ["",
 "* Both passes (05:44 morning and 18:34 evening) show the same rise and fall, so the signal is not dew or a",
 "  time-of-day effect; it is water in the soil and vegetation after rain.",
 "* The lowest values are in the dry spell of mid/late July; values rise again after the August rains,",
 "  dip on 12 Sep after a few dry days, peak on 24 Sep after heavy rain, and stay high in the October monsoon."]
for t, (direction, _) in TRACKS.items():
    dry, wet = extreme(t, min), extreme(t, max)
    if dry and wet:
        lines.append(f"* {direction}: driest provisional pass {dry['date']} (rain7 {dry['rain7_mm']} mm, green {dry['green_pct']}%, "
                     f"HV {dry['scene_HV_dB']} dB); wettest {wet['date']} (rain7 {wet['rain7_mm']} mm, green {wet['green_pct']}%, "
                     f"HV {wet['scene_HV_dB']} dB).")
lines += ["",
 "## 3. Forest vs open land",
 "Inside the WorldCover-verified forest mask (98-99 % tree cover) and in the open land around it (tea, grass, town)",
 "HH and HV change on the same dates. Open land responds about twice as strongly to rain as forest in HV,",
 "because L-band reaches the wet soil and low vegetation there, while the dense forest canopy damps the response.",
 "This is what we expect physically, so the change is moisture, not land-cover change (no clearing, no landslide",
 "scars were found at 10 m).", "",
 "## 4. Provisional vs validated",
 "NISAR products changed from PROVISIONAL to VALIDATED on 21 Oct 2026. On verified forest the validated data read",
 "0.35 dB (ascending) and 0.68 dB (descending) lower in HH. That step is processing, not the ground, so we added",
 "the forest-measured offset to the validated dates. After correction they continue the October trend.",
 "Note: the offset was measured on forest, so the forest values line up by design; the provisional-only",
 "correlations in data/results_summary.csv are the independent test.", "",
 "## 5. Limits",
 "* Few dates per track (12 ascending, 7 descending), and a global NISAR gap 27 Jul - 10 Aug 2026.",
 "* IMERG rainfall is about 10 km resolution, so it is an area average, not a rain gauge.",
 "* The response flattens in late Oct / Nov: soils are probably already saturated after more than 500 mm in October.",
 "* WorldCover is from 2021; tea is often classed as grassland or shrubland.",
 "* Green pixel intensity is a display-scale (0-255) value from a fixed stretch; use the dB columns for science.", "",
 "## 6. One-line story",
 "NISAR's L-band radar 'sees' the hill country of Nawalapitiya get wetter and drier with the monsoon: HV (green)",
 "rises after rain and falls in dry spells, on both morning and evening passes, most strongly over tea and",
 "grassland, and the forest acts as a steady reference.", ""]
open(os.path.join(OUT, "INTERPRETATION.md"), "w").write("\n".join(lines))

# ---------------- README ----------------
first = rows[0]
open(os.path.join(OUT, "README.md"), "w").write(f"""# Nawalapitiya NISAR web-app package

Site: Nawalapitiya, Sri Lanka. Box W {BOX[0]}, S {BOX[1]}, E {BOX[2]}, N {BOX[3]}.
NISAR L2 GCOV, L-band frequency A, HH + HV, 10 m. Two tracks:
T084A ascending (05:44 local) and T048D descending (18:34 local). {len(rows)} dates in total.

## Folders
| Folder | What | Use in the app |
|---|---|---|
| images/<track>/<date>_rgb.png | NISAR colour composite R=HH, G=HV, B=HH/HV | map overlay + date slider |
| images/<track>/<date>_green.png | only green (HV-dominated) pixels, transparent elsewhere | toggle layer |
| display/<track>/ | green pixels on white | gallery / slides |
| layers/forest_mask_<track>.png | verified forest | toggle layer |
| layers/study_box.geojson | study polygon | outline |
| google_earth/ | Google Earth Pro screenshots (reference) | "what it looks like" panel; keep the Google attribution visible |
| charts/ | static graphs | explainer / fallback |
| data/nisar_by_date.csv | one row per track and date: rain, HH, HV, ratio, forest / non-forest, green stats, image paths | chart + slider |
| data/rainfall_daily.csv | GPM IMERG daily rain | rain bars |
| data/results_summary.csv | correlation with rain, response per 100 mm | validation panel |
| data/manifest.json | bounds, colours, stretch, file list | config |

All PNG overlays share the same bounds: `{BOUNDS}`  ([[south, west], [north, east]]).

## Leaflet example
```js
const b = {BOUNDS};
const map = L.map('map').fitBounds(b);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
            {{attribution: 'Esri World Imagery'}}).addTo(map);
const nisar = L.imageOverlay('{first["rgb_png"]}', b, {{opacity: 0.85}}).addTo(map);
// date slider: nisar.setUrl(row.rgb_png)   green toggle: L.imageOverlay(row.green_png, b)
```

## Notes
* VALIDATED dates (from 21 Oct 2026) have the forest-measured offset added
  (ascending HH +0.35, HV +0.11 dB; descending HH +0.68, HV +0.25 dB) so they line up with PROVISIONAL.
  Columns offset_HH_dB_added / offset_HV_dB_added show exactly what was added.
* NISAR data gap 27 Jul - 10 Aug 2026 (no acquisitions anywhere).
* Means are averaged in linear power, then converted to dB.
* rain7_mm = rain in the 7 days before the pass.
""")
print(f"\nsaved package -> {OUT}/  ({len(rows)} dates, {len(images)} images)")
