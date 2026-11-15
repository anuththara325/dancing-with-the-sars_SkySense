#!/usr/bin/env python3
"""
per_pixel_rain.py  -  Dancing with the SARs / SkySense

Per-pixel NISAR rain response maps from a stack of *_db.tif files
(band "HH_dB" and "HV_dB", same grid, written by nisar_rgb.py).

Makes, for HH and HV:
  1. Rain-sensitivity map  : dB change per 100 mm of rain in the previous N days
                             ("where the ground listens to rain"), plus r per pixel.
  2. Soil-memory map       : which rain "memory" (antecedent rain index decay k)
                             fits each pixel best -> fast / medium / slow drying.
  + summary CSV, per-date box medians, GeoTIFFs and PNG/WebP for the web app.

Usage (WSL, inside ~/nisar):
  python3 -u per_pixel_rain.py \
      --dir  ~/nisar/DataSet/Nawalapitiya/Ascending_RGB \
      --rain ~/nisar/DataSet/Nawalapitiya/Rainfall.csv \
      --site Nawalapitiya --out ~/nisar/DataSet/Nawalapitiya/results/per_pixel_asc

Optional:
  --forest-mask forest.tif   (same grid, nonzero = forest) -> forest vs other stats
  --smooth 5                 boxcar size in pixels (in linear power). 0 = off.
  --window 7                 rain window in days (pass day excluded)
  --no-offset                do not add provisional->validated offsets

Needs: python3-gdal, numpy, matplotlib (Pillow optional for .webp).
"""
import argparse, csv, glob, math, os, re, sys
from datetime import date, timedelta

import numpy as np

# ---------------------------------------------------------------- settings
# Provisional -> validated offsets (dB) measured on verified forest.
# Added to VALIDATED (P05036) dates so they line up with the provisional ones.
OFFSETS = {
    "T084A": {"dates": {"20261030", "20261111"}, "HH": 0.35, "HV": 0.11},
    "T048D": {"dates": {"20261027"},             "HH": 0.68, "HV": 0.25},
    # Ampara T156A 23 Oct is validated, but no offset was measured -> warning only.
}
VALIDATED_NO_OFFSET = {"T156A": {"20261023"}}

K_GRID = np.array([0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95])
# e-folding days = -1/ln(k): 1.4, 2.0, 2.8, 4.5, 6.2, 9.5, 19.5
CLASS_EDGES = (3.0, 8.0)          # < 3 d fast, 3-8 d medium, > 8 d slow
R_MIN = 0.5                        # below this: "no clear rain response"
LAYOVER_DB = 2.0                   # mean HH above this -> layover / very steep slope
SHADOW_DB = -24.0                  # mean HV below this -> shadow / water


# ---------------------------------------------------------------- rain
def read_giovanni_csv(path):
    """Giovanni area-averaged time series CSV -> {date: value} (fill -> nan)."""
    out, started, fill = {}, False, None
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if not row:
                continue
            if row[0].strip().lower().startswith("fill value"):
                try:
                    fill = float(row[1])
                except (IndexError, ValueError):
                    pass
            if row[0].strip().lower() == "time":
                started = True
                continue
            if started and len(row) >= 2:
                try:
                    d = date.fromisoformat(row[0].strip()[:10])
                    v = float(row[1])
                except ValueError:
                    continue
                if (fill is not None and abs(v - fill) < 1e-3) or v < -999:
                    v = float("nan")
                out[d] = v
    if not out:
        sys.exit(f"Could not read any rows from {path}")
    return out


def rain_window(rain, d, n):
    """Sum of the n days before d (pass day excluded). nan days count as 0."""
    days = [d - timedelta(days=i) for i in range(1, n + 1)]
    missing = [x for x in days if x not in rain]
    if missing:
        sys.exit(f"Rain file does not cover {min(missing)}..{max(missing)} needed for {d}")
    return float(np.nansum([rain[x] for x in days]))


def rain_api(rain, d, k, max_days=60):
    """Antecedent rain index: sum rain(d-i) * k**(i-1), i = 1..max_days (pass day excluded)."""
    s = 0.0
    for i in range(1, max_days + 1):
        v = rain.get(d - timedelta(days=i), float("nan"))
        if not math.isnan(v):
            s += v * k ** (i - 1)
    return s


# ---------------------------------------------------------------- raster maths
def boxcar_db(db, size):
    """size x size mean in linear power, returned in dB. nan-aware."""
    if size <= 1:
        return db
    lin = np.where(np.isfinite(db), 10.0 ** (db / 10.0), 0.0).astype(np.float64)
    ok = np.isfinite(db).astype(np.float64)
    pad = size // 2

    def box(a):
        a = np.pad(a, pad, mode="edge")
        c = a.cumsum(0).cumsum(1)
        c = np.pad(c, ((1, 0), (1, 0)))
        return c[size:, size:] - c[:-size, size:] - c[size:, :-size] + c[:-size, :-size]

    s, n = box(lin), box(ok)
    with np.errstate(divide="ignore", invalid="ignore"):
        m = s / n
        out = 10.0 * np.log10(m)
    out[(n < size * size / 2) | ~np.isfinite(out)] = np.nan
    out[~np.isfinite(db)] = np.nan
    return out.astype(np.float32)


def pixel_regression(stack, x):
    """stack (n, H, W) dB, x (n,). Returns slope per unit x, r, valid count."""
    ok = np.isfinite(stack)
    n = ok.sum(0).astype(np.float32)
    xs = np.broadcast_to(x[:, None, None], stack.shape)
    y = np.where(ok, stack, 0.0)
    xv = np.where(ok, xs, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        mx = xv.sum(0) / n
        my = y.sum(0) / n
        dx = np.where(ok, xs - mx, 0.0)
        dy = np.where(ok, stack - my, 0.0)
        sxy = (dx * dy).sum(0)
        sxx = (dx * dx).sum(0)
        syy = (dy * dy).sum(0)
        slope = sxy / sxx
        r = sxy / np.sqrt(sxx * syy)
    return slope.astype(np.float32), r.astype(np.float32), n


def memory_fit(stack, api_matrix):
    """api_matrix (nk, n). Returns best k index, best r, r for every k (nk, H, W)."""
    rs = []
    for row in api_matrix:
        _, r, _ = pixel_regression(stack, row)
        rs.append(r)
    rs = np.stack(rs)
    filled = np.where(np.isfinite(rs), rs, -9.0)
    best = filled.argmax(0)
    best_r = np.take_along_axis(filled, best[None], 0)[0]
    best_r[best_r <= -9.0] = np.nan
    return best, best_r, rs


# ---------------------------------------------------------------- IO (GDAL)
def gdal():
    try:
        from osgeo import gdal as g
        g.UseExceptions()
        return g
    except ImportError:
        sys.exit("python3-gdal not found. In WSL: sudo apt install python3-gdal")


def read_bands(path):
    g = gdal()
    ds = g.Open(path)
    bands = {}
    for i in range(1, ds.RasterCount + 1):
        b = ds.GetRasterBand(i)
        name = (b.GetDescription() or f"band{i}").upper()
        a = b.ReadAsArray().astype(np.float32)
        nd = b.GetNoDataValue()
        if nd is not None and not math.isnan(nd):
            a[a == nd] = np.nan
        bands[name] = a
    geo = (ds.GetGeoTransform(), ds.GetProjection(), ds.RasterXSize, ds.RasterYSize)
    return bands, geo


def pick(bands, key, fallback_index):
    for name, a in bands.items():
        if name.startswith(key):
            return a
    names = list(bands)
    if fallback_index < len(names):
        print(f"  ! no band named {key}_dB, using band {fallback_index + 1} ({names[fallback_index]})")
        return bands[names[fallback_index]]
    sys.exit(f"No {key} band found (bands: {names})")


def write_tif(path, arr, geo, nodata=np.nan, dtype=None):
    g = gdal()
    gt, proj, nx, ny = geo
    dt = dtype or g.GDT_Float32
    ds = g.GetDriverByName("GTiff").Create(path, nx, ny, 1, dt, options=["COMPRESS=DEFLATE"])
    ds.SetGeoTransform(gt)
    ds.SetProjection(proj)
    b = ds.GetRasterBand(1)
    b.WriteArray(arr)
    if nodata is not None:
        b.SetNoDataValue(float(nodata))
    ds.FlushCache()
    ds = None


# ---------------------------------------------------------------- figures
def save_png(path, arr, title, cmap, vmin, vmax, cbar_label, ticks=None, ticklabels=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    h, w = arr.shape
    fig, ax = plt.subplots(figsize=(7, 7 * h / w + 0.6), dpi=150)
    im = ax.imshow(np.ma.masked_invalid(arr), cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_title(title, fontsize=10)
    ax.set_axis_off()
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label(cbar_label, fontsize=8)
    if ticks is not None:
        cb.set_ticks(ticks)
        if ticklabels is not None:
            cb.set_ticklabels(ticklabels)
    cb.ax.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    try:
        from PIL import Image
        Image.open(path).convert("RGB").save(path[:-4] + ".webp", quality=85)
    except Exception:
        pass


def save_timeseries(path, dates, x, med, label, window):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=150)
    ax.bar(dates, x, width=4, color="#9ecae1", label=f"rain, previous {window} days (mm)")
    ax.set_ylabel("rain (mm)")
    ax2 = ax.twinx()
    for k, v in med.items():
        ax2.plot(dates, v, marker="o", label=f"{k} box median (dB)")
    ax2.set_ylabel("backscatter (dB)")
    ax.set_title(label, fontsize=10)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True, help="folder with T###X_YYYYMMDD_db.tif")
    ap.add_argument("--rain", required=True, help="Giovanni IMERG daily CSV for the same box")
    ap.add_argument("--site", default="site")
    ap.add_argument("--out", default=None)
    ap.add_argument("--window", type=int, default=7)
    ap.add_argument("--smooth", type=int, default=5)
    ap.add_argument("--forest-mask", default=None)
    ap.add_argument("--no-offset", action="store_true")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(os.path.expanduser(a.dir), "*_db.tif")))
    if len(files) < 5:
        sys.exit(f"Need at least 5 *_db.tif files in {a.dir}, found {len(files)}")
    out = os.path.expanduser(a.out or os.path.join(a.dir, "per_pixel"))
    os.makedirs(out, exist_ok=True)
    rain = read_giovanni_csv(os.path.expanduser(a.rain))

    meta, dates, tracks = [], [], set()
    for f in files:
        m = re.search(r"(T\d{3}[AD])_(\d{8})_db\.tif$", os.path.basename(f))
        if not m:
            print(f"  skip {f} (name not T###X_YYYYMMDD_db.tif)")
            continue
        tracks.add(m.group(1))
        meta.append((f, m.group(1), m.group(2)))
        dates.append(date(int(m.group(2)[:4]), int(m.group(2)[4:6]), int(m.group(2)[6:])))
    if len(tracks) != 1:
        sys.exit(f"Mix of tracks in one folder: {tracks}. Run once per track.")
    track = tracks.pop()
    n = len(meta)
    print(f"{a.site} {track}: {n} dates {dates[0]} .. {dates[-1]}")

    x = np.array([rain_window(rain, d, a.window) for d in dates], dtype=np.float64)
    api = np.array([[rain_api(rain, d, k) for d in dates] for k in K_GRID])

    # ---- load stack
    stacks = {"HH": [], "HV": []}
    geo0 = None
    for (f, tr, ds), d in zip(meta, dates):
        bands, geo = read_bands(f)
        if geo0 is None:
            geo0 = geo
        elif geo[0] != geo0[0] or geo[2:] != geo0[2:]:
            sys.exit(f"{f} is not on the same grid as the first file")
        for key, idx in (("HH", 0), ("HV", 1)):
            arr = pick(bands, key, idx)
            off = 0.0
            if not a.no_offset and tr in OFFSETS and ds in OFFSETS[tr]["dates"]:
                off = OFFSETS[tr][key]
            stacks[key].append(boxcar_db(arr, a.smooth) + off)
        flag = ""
        if tr in OFFSETS and ds in OFFSETS[tr]["dates"]:
            flag = "validated, offset added" if not a.no_offset else "validated, NO offset"
        if tr in VALIDATED_NO_OFFSET and ds in VALIDATED_NO_OFFSET[tr]:
            flag = "validated, no offset measured - treat with care"
        print(f"  {d}  rain{a.window}={x[len(stacks['HH']) - 1]:6.1f} mm  {flag}")
    for key in stacks:
        stacks[key] = np.stack(stacks[key]).astype(np.float32)

    # ---- quality mask: layover/shadow/water/no data
    mean_hh = np.nanmean(stacks["HH"], 0)
    mean_hv = np.nanmean(stacks["HV"], 0)
    good = np.isfinite(mean_hh) & np.isfinite(mean_hv) & (mean_hh < LAYOVER_DB) & (mean_hv > SHADOW_DB)
    good &= np.isfinite(stacks["HH"]).sum(0) >= max(5, int(0.8 * n))
    print(f"  usable pixels: {good.mean() * 100:.1f}% "
          f"(dropped: layover/steep {np.mean(mean_hh >= LAYOVER_DB) * 100:.1f}%, "
          f"shadow/water {np.mean(mean_hv <= SHADOW_DB) * 100:.1f}%)")

    forest = None
    if a.forest_mask:
        fb, fgeo = read_bands(os.path.expanduser(a.forest_mask))
        if fgeo[0] != geo0[0] or fgeo[2:] != geo0[2:]:
            sys.exit("forest mask is not on the same grid")
        forest = np.nan_to_num(list(fb.values())[0]) != 0

    efold = -1.0 / np.log(K_GRID)
    summary, medians = [], {}
    tag = f"{a.site}_{track}"
    for key in ("HH", "HV"):
        st = stacks[key]
        medians[key] = [float(np.nanmedian(np.where(good, s, np.nan))) for s in st]

        slope, r, _ = pixel_regression(st, x)
        slope100 = slope * 100.0
        slope100[~good] = np.nan
        r[~good] = np.nan

        best, best_r, _ = memory_fit(st, api)
        days = efold[best].astype(np.float32)
        days[~good | ~(best_r >= R_MIN)] = np.nan
        cls = np.full(days.shape, np.nan, np.float32)        # 1 fast, 2 medium, 3 slow, 0 no clear response
        cls[good] = 0
        ok = np.isfinite(days)
        cls[ok & (days < CLASS_EDGES[0])] = 1
        cls[ok & (days >= CLASS_EDGES[0]) & (days <= CLASS_EDGES[1])] = 2
        cls[ok & (days > CLASS_EDGES[1])] = 3

        write_tif(f"{out}/{tag}_{key}_dB_per100mm.tif", slope100, geo0)
        write_tif(f"{out}/{tag}_{key}_r_rain{a.window}.tif", r, geo0)
        write_tif(f"{out}/{tag}_{key}_memory_days.tif", days, geo0)
        write_tif(f"{out}/{tag}_{key}_memory_class.tif", cls, geo0)

        save_png(f"{out}/{tag}_{key}_sensitivity.png", slope100,
                 f"{a.site} {track} {key}: change per 100 mm rain (previous {a.window} days)",
                 "RdBu_r", -2.0, 2.0, "dB per 100 mm")
        save_png(f"{out}/{tag}_{key}_r.png", r,
                 f"{a.site} {track} {key}: correlation with {a.window}-day rain (n={n})",
                 "RdBu_r", -1.0, 1.0, "r")
        from matplotlib.colors import ListedColormap
        cmap = ListedColormap(["#d9d9d9", "#fdae61", "#66bd63", "#2166ac"])
        save_png(f"{out}/{tag}_{key}_memory.png", cls,
                 f"{a.site} {track} {key}: how long the ground 'remembers' rain",
                 cmap, -0.5, 3.5, "",
                 ticks=[0, 1, 2, 3],
                 ticklabels=[f"no clear response (r<{R_MIN})", "fast (<3 d)", "medium (3-8 d)", "slow (>8 d)"])

        def stats(sel, name):
            if sel.sum() == 0:
                return
            c = cls[sel]
            summary.append({
                "site": a.site, "track": track, "channel": key, "area": name,
                "n_dates": n, "pixels": int(sel.sum()),
                "median_dB_per100mm": round(float(np.nanmedian(slope100[sel])), 3),
                "median_r": round(float(np.nanmedian(r[sel])), 3),
                "pct_r_gt_0.5": round(float(np.nanmean(r[sel] > 0.5) * 100), 1),
                "pct_fast": round(float(np.mean(c == 1) * 100), 1),
                "pct_medium": round(float(np.mean(c == 2) * 100), 1),
                "pct_slow": round(float(np.mean(c == 3) * 100), 1),
                "pct_no_clear": round(float(np.mean(c == 0) * 100), 1),
                "median_memory_days": round(float(np.nanmedian(days[sel])), 1) if np.isfinite(days[sel]).any() else "",
            })

        stats(good, "all usable")
        if forest is not None:
            stats(good & forest, "forest")
            stats(good & ~forest, "not forest")

        # box-median check: which k fits the whole box
        boxr = [float(np.corrcoef(medians[key], row)[0, 1]) for row in api]
        kb = int(np.argmax(boxr))
        print(f"  {key}: box median r(rain{a.window}) = {np.corrcoef(medians[key], x)[0, 1]:+.2f}; "
              f"best memory k={K_GRID[kb]:.2f} (~{efold[kb]:.1f} d) r={boxr[kb]:+.2f}; "
              f"median {np.nanmedian(slope100[good]):+.2f} dB/100 mm")

    with open(f"{out}/{tag}_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    with open(f"{out}/{tag}_dates.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", f"rain{a.window}_mm"] + [f"{k}_box_median_dB" for k in medians] +
                   [f"api_k{k:.2f}" for k in K_GRID])
        for i, d in enumerate(dates):
            w.writerow([d.isoformat(), round(x[i], 1)] + [round(medians[k][i], 3) for k in medians] +
                       [round(v, 1) for v in api[:, i]])
    save_timeseries(f"{out}/{tag}_timeseries.png", dates, x, medians,
                    f"{a.site} {track}: box median backscatter vs rain", a.window)

    print(f"\nDone -> {out}")
    for s in summary:
        print("  ", s)


if __name__ == "__main__":
    main()


# ---- added 15 Nov: block averaging (needed by wetness_index.py)
def block_db(db, b):
    """b x b block mean in linear power (nan-aware) -> dB on a coarser grid (edges cropped)."""
    if b <= 1:
        return db
    H, W = db.shape
    h, w = H // b, W // b
    a = db[:h * b, :w * b]
    lin = np.where(np.isfinite(a), 10.0 ** (a / 10.0), 0.0).reshape(h, b, w, b)
    ok = np.isfinite(a).reshape(h, b, w, b)
    s, n = lin.sum((1, 3)), ok.sum((1, 3))
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 10.0 * np.log10(s / n)
    out[n < 0.5 * b * b] = np.nan
    return out.astype(np.float32)


def block_geo(geo, b):
    if b <= 1:
        return geo
    gt, proj, nx, ny = geo
    return ((gt[0], gt[1] * b, gt[2], gt[3], gt[4], gt[5] * b), proj, nx // b, ny // b)
