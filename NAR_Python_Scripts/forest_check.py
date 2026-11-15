#!/usr/bin/env python3
"""Forest-mask cross-check over all NISAR dates.
Usage: python3 forest_check.py clip_dir mask_dir rain_csv out_dir"""
import sys, os, glob, csv, datetime as dt
import numpy as np
from osgeo import gdal
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
gdal.UseExceptions()

clip_dir, mask_dir, rain_csv, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
# provisional->validated offsets measured on verified forest (added to VALIDATED dates)
CORR = {"T084A": (0.35, 0.11), "T048D": (0.68, 0.25)}
NAMES = {"T084A": "Ascending (05:44 local)", "T048D": "Descending (18:34 local)"}

# ---------- rainfall (Giovanni CSV) ----------
rain = {}
for line in open(rain_csv, encoding="utf-8", errors="ignore"):
    p = [x.strip() for x in line.split(",")]
    if len(p) < 2:
        continue
    p = [x.strip().strip('"') for x in p]
    d = None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y%m%d"):
        try:
            d = dt.datetime.strptime(p[0][:10].replace("T", " ").split(" ")[0], fmt).date(); break
        except ValueError:
            pass
    try:
        if d: rain[d] = max(float(p[1]), 0.0)
    except ValueError:
        continue
print(f"rain days read: {len(rain)}", (min(rain), max(rain)) if rain else "")

def rain7(d):   # rain in the 7 days before the pass
    v = [rain.get(d - dt.timedelta(days=i)) for i in range(1, 8)]
    v = [x for x in v if x is not None]
    return sum(v) if v else np.nan

def load(path, ref):
    ds = gdal.Open(path)
    if (ds.RasterXSize, ds.RasterYSize) != (ref.RasterXSize, ref.RasterYSize):
        gt = ref.GetGeoTransform()
        ds = gdal.Warp("", ds, format="MEM", dstSRS=ref.GetProjection(),
                       outputBounds=(gt[0], gt[3] + gt[5] * ref.RasterYSize,
                                     gt[0] + gt[1] * ref.RasterXSize, gt[3]),
                       width=ref.RasterXSize, height=ref.RasterYSize, resampleAlg="near")
    a = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    a[~np.isfinite(a) | (a <= 0)] = np.nan
    return a

def db(x):   # mean in linear power, then dB
    return float(10 * np.log10(np.nanmean(x)))

rows = []
for tag in ["T084A", "T048D"]:
    ref = gdal.Open(os.path.join(mask_dir, f"{tag}_groups.tif"))
    forest = ref.GetRasterBand(1).ReadAsArray() == 2
    for hh_path in sorted(glob.glob(os.path.join(clip_dir, f"*_{tag}_F*_HHHH.tif"))):
        hv_path = hh_path.replace("_HHHH.tif", "_HVHV.tif")
        if not os.path.exists(hv_path):
            continue
        name = os.path.basename(hh_path)
        d = dt.datetime.strptime(name[:8], "%Y%m%d").date()
        val = "P05036" in name
        hh, hv = load(hh_path, ref), load(hv_path, ref)
        ok = np.isfinite(hh) & np.isfinite(hv)
        f, nf = forest & ok, ~forest & ok
        cHH, cHV = CORR[tag] if val else (0.0, 0.0)
        r = {"track": tag, "date": d.isoformat(),
             "product": "VALIDATED" if val else "PROVISIONAL",
             "forest_px": int(f.sum()), "nonforest_px": int(nf.sum()),
             "forest_HH_dB": db(hh[f]), "forest_HV_dB": db(hv[f]),
             "nonforest_HH_dB": db(hh[nf]), "nonforest_HV_dB": db(hv[nf]),
             "rain7_mm": rain7(d)}
        r["forest_HH_corr"] = r["forest_HH_dB"] + cHH
        r["forest_HV_corr"] = r["forest_HV_dB"] + cHV
        r["nonforest_HH_corr"] = r["nonforest_HH_dB"] + cHH
        r["nonforest_HV_corr"] = r["nonforest_HV_dB"] + cHV
        rows.append(r)

# ---------- CSV ----------
csv_path = os.path.join(out, "forest_check.csv")
with open(csv_path, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})

# ---------- summary + plots ----------
for tag in ["T084A", "T048D"]:
    R = [r for r in rows if r["track"] == tag]
    if not R:
        continue
    dates = [dt.date.fromisoformat(r["date"]) for r in R]
    isval = np.array([r["product"] == "VALIDATED" for r in R])
    rn = np.array([r["rain7_mm"] for r in R])
    print(f"\n=== {tag} {NAMES[tag]}  forest px {R[0]['forest_px']:,} ===")
    print(f"{'date':10s} {'prod':5s} {'rain7':>6s} | {'F_HH':>6s} {'F_HV':>7s} | {'NF_HH':>6s} {'NF_HV':>7s}  (corrected dB)")
    for r in R:
        print(f"{r['date']} {r['product'][:4]:5s} {r['rain7_mm']:6.0f} | "
              f"{r['forest_HH_corr']:6.2f} {r['forest_HV_corr']:7.2f} | "
              f"{r['nonforest_HH_corr']:6.2f} {r['nonforest_HV_corr']:7.2f}")

    fig, ax = plt.subplots(3, 1, figsize=(10, 8), sharex=True,
                           gridspec_kw={"height_ratios": [2, 2, 1]})
    for k, (pol, col) in enumerate([("HH", "#D62828"), ("HV", "#2DB800")]):
        for grp, ls, mk, lab in [("forest", "-", "o", "forest"),
                                 ("nonforest", "--", "s", "non-forest (tea/grass/town)")]:
            y = np.array([r[f"{grp}_{pol}_corr"] for r in R])
            prov = ~isval
            a = y - y[prov].mean()          # change from its own provisional average
            ax[k].plot(dates, a, ls, color=col, alpha=0.9 if grp == "forest" else 0.6,
                       lw=2, label=lab)
            ax[k].scatter(np.array(dates)[prov], a[prov], marker=mk, color=col, zorder=3)
            ax[k].scatter(np.array(dates)[isval], a[isval], marker=mk, facecolors="white",
                          edgecolors=col, zorder=3, label=f"{lab} – validated (corrected)")
            r_ = np.corrcoef(a[np.isfinite(rn)], rn[np.isfinite(rn)])[0, 1]
            print(f"  {pol} {grp:9s}: range {np.ptp(a):.2f} dB, std {a.std():.2f} dB, r(rain7) = {r_:.2f}")
        ax[k].axhline(0, color="#999", lw=0.8)
        ax[k].set_ylabel(f"{pol} change (dB)")
        ax[k].legend(fontsize=7, loc="upper left", ncol=2)
    ax[2].bar(dates, rn, width=4, color="#7F93A8")
    ax[2].set_ylabel("rain 7 d\nbefore (mm)")
    for a_ in ax:
        a_.axvspan(dt.date(2026, 7, 27), dt.date(2026, 8, 10), color="#eee", zorder=0)
    ax[0].set_title(f"Nawalapitiya {tag} {NAMES[tag]}: forest vs non-forest backscatter vs rainfall\n"
                    "(lines = change from each group's provisional mean; grey band = NISAR data gap)",
                    fontsize=10)
    fig.tight_layout()
    png = os.path.join(out, f"forest_check_{tag}.png")
    fig.savefig(png, dpi=150)
    print("  saved", png)
print("\nSaved", csv_path)
