#!/usr/bin/env python3
"""
check_retention.py  -  is the "stays wet longer" map real?

Reads the per-date wetness rasters written by wetness_index.py (<tag>_W_YYYYMMDD.tif)
and runs three checks:

  A. Split-half by date: retention from each drying-test date ALONE, compared pairwise
     (correlation + class agreement; chance class agreement = 33%).
     CONTROL: same correlation for every other pair of dates. If drying-test pairs are
     no more alike than any random pair, the map is a fixed per-pixel pattern
     (e.g. normalisation artefact), not drying behaviour.
     Also on ANOMALIES: W on the test date minus that pixel's mean W on non-test dates.
  B. Land cover: correlation of retention with forest fraction (optional --forest).
  C. Terrain: correlation with slope and aspect (optional --dem, any CRS; warped here).
  (+) optional --other: a second retention raster (e.g. descending pass) for agreement.

Usage (WSL, in ~/nisar; first make 100 m wetness rasters):
  python3 -u wetness_index.py --dir DataSet/Nawalapitiya/Ascending_RGB \
      --rain DataSet/Nawalapitiya/Rainfall.csv --site Nawalapitiya --block 10 \
      --out DataSet/Nawalapitiya/results/wetness_asc_b10
  python3 -u check_retention.py --wdir DataSet/Nawalapitiya/results/wetness_asc_b10 \
      --tests 20260819 20260912 20261030 [--forest forest.tif] [--dem dem.tif] \
      [--other DataSet/Nawalapitiya/results/wetness_desc/Nawalapitiya_T048D_HH_retention.tif]
"""
import argparse, glob, os, re, sys, warnings
import numpy as np

warnings.simplefilter("ignore", RuntimeWarning)


# ---------------- core statistics (no GDAL needed)
def corr(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30:
        return np.nan, int(ok.sum())
    return float(np.corrcoef(a[ok], b[ok])[0, 1]), int(ok.sum())


def tertiles(x):
    out = np.full(x.shape, np.nan)
    ok = np.isfinite(x)
    e1, e2 = np.nanpercentile(x[ok], [33.3, 66.7])
    out[ok] = np.digitize(x[ok], [e1, e2])          # 0 fast, 1 typical, 2 slow
    return out


def class_agreement(a, b):
    ta, tb = tertiles(a), tertiles(b)
    ok = np.isfinite(ta) & np.isfinite(tb)
    po = float(np.mean(ta[ok] == tb[ok]))
    slow_both = float(np.mean(tb[ok][ta[ok] == 2] == 2))
    return po, slow_both, (po - 1 / 3) / (1 - 1 / 3)  # agreement, slow->slow, kappa-like


def split_half(W, dates, tests):
    idx = [dates.index(t) for t in tests]
    others = [i for i in range(len(dates)) if i not in idx]
    # independent baselines (alternate halves of the non-test dates) so the two anomalies
    # do not share a common subtracted term
    baseA = np.nanmean(W[others[0::2]], 0)
    baseB = np.nanmean(W[others[1::2]], 0)
    out = {"test_pairs": [], "control_pairs": [], "anom_pairs": []}
    for i in range(len(idx)):
        for j in range(i + 1, len(idx)):
            a, b = W[idx[i]], W[idx[j]]
            r, n = corr(a, b)
            po, ss, k = class_agreement(a, b)
            ra, _ = corr(a - baseA, b - baseB)
            out["test_pairs"].append((dates[idx[i]], dates[idx[j]], r, po, ss, k, n))
            out["anom_pairs"].append((dates[idx[i]], dates[idx[j]], ra))
    for i in range(len(dates)):
        for j in range(i + 1, len(dates)):
            if i in idx and j in idx:
                continue
            out["control_pairs"].append((dates[i], dates[j], corr(W[i], W[j])[0]))
    return out


def slope_aspect(dem, px):
    gy, gx = np.gradient(dem, px)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    aspect = (np.degrees(np.arctan2(-gx, gy)) + 360) % 360   # 0 = north-facing... approx
    return slope, aspect


def block_mean(x, b):
    if b <= 1:
        return x
    H, W = x.shape
    return np.nanmean(x[:H // b * b, :W // b * b].reshape(H // b, b, W // b, b), (1, 3))


# ---------------- GDAL helpers
def gdal():
    from osgeo import gdal as g
    g.UseExceptions()
    return g


def read(path):
    g = gdal()
    ds = g.Open(path)
    a = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
    nd = ds.GetRasterBand(1).GetNoDataValue()
    if nd is not None and np.isfinite(nd):
        a[a == nd] = np.nan
    return a, ds.GetGeoTransform(), ds.GetProjection(), ds.RasterXSize, ds.RasterYSize


def warp_to(path, gt, proj, nx, ny, resample="average"):
    g = gdal()
    xmin, ymax = gt[0], gt[3]
    xmax, ymin = xmin + gt[1] * nx, ymax + gt[5] * ny
    ds = g.Warp("", path, format="MEM", dstSRS=proj, outputBounds=(xmin, ymin, xmax, ymax),
                width=nx, height=ny, resampleAlg=resample, dstNodata=np.nan)
    return ds.GetRasterBand(1).ReadAsArray().astype(np.float64)


# ---------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wdir", required=True)
    ap.add_argument("--tests", nargs="+", required=True, help="drying-test dates YYYYMMDD")
    ap.add_argument("--forest", default=None, help="forest mask/fraction raster (nonzero = forest)")
    ap.add_argument("--dem", default=None, help="DEM raster (any CRS, metres)")
    ap.add_argument("--other", default=None, help="second retention raster to compare")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(os.path.expanduser(a.wdir), "*_W_*.tif")))
    files = [f for f in files if re.search(r"_W_\d{8}\.tif$", f)]
    if not files:
        sys.exit("No *_W_YYYYMMDD.tif in --wdir (run wetness_index.py first)")
    dates, stack = [], []
    for f in files:
        arr, gt, proj, nx, ny = read(f)
        dates.append(re.search(r"_W_(\d{8})\.tif$", f).group(1))
        stack.append(arr)
    W = np.stack(stack)
    missing = [t for t in a.tests if t not in dates]
    if missing:
        sys.exit(f"test dates not found: {missing}; available {dates}")
    print(f"{len(dates)} wetness rasters, grid {nx} x {ny}, pixel {gt[1]:.0f} m")

    # A. split-half
    s = split_half(W, dates, a.tests)
    print("\nA. Split-half by drying-test date (chance class agreement = 33%, slow->slow chance = 33%)")
    for d1, d2, r, po, ss, k, n in s["test_pairs"]:
        print(f"   {d1} vs {d2}:  r = {r:+.2f}   class agreement {po * 100:.0f}%   "
              f"slow->slow {ss * 100:.0f}%   kappa {k:+.2f}   (n={n})")
    cr = np.array([c[2] for c in s["control_pairs"]])
    print(f"   CONTROL, all other date pairs: median r = {np.nanmedian(cr):+.2f} "
          f"(range {np.nanmin(cr):+.2f} .. {np.nanmax(cr):+.2f}, {len(cr)} pairs)")
    for d1, d2, ra in s["anom_pairs"]:
        print(f"   anomaly (test date minus pixel's usual wetness) {d1} vs {d2}: r = {ra:+.2f}")
    tr = np.array([p[2] for p in s["test_pairs"]])
    verdict_A = np.nanmean(tr) > np.nanmedian(cr) + 0.1 and np.nanmean([p[2] for p in s["anom_pairs"]]) > 0.1
    print(f"   -> {'PASS' if verdict_A else 'FAIL'}: drying-test dates "
          f"{'are' if verdict_A else 'are NOT'} clearly more alike than ordinary date pairs")

    idx = [dates.index(t) for t in a.tests]
    ret = np.nanmean(W[idx], 0)

    # B. land cover
    if a.forest:
        fr = warp_to(os.path.expanduser(a.forest), gt, proj, nx, ny, "average")
        fr = (np.nan_to_num(fr) > 0).astype(float) if np.nanmax(fr) > 1 else fr
        r, n = corr(ret, fr)
        print(f"\nB. Retention vs forest fraction: r = {r:+.2f} (n={n})")
        for lo, hi in [(0, .2), (.2, .5), (.5, .8), (.8, 1.01)]:
            m = (fr >= lo) & (fr < hi)
            if m.sum() > 30:
                print(f"   forest {lo:.0%}-{min(hi, 1):.0%}: median retention {np.nanmedian(ret[m]):.2f}  (n={m.sum()})")
        print("   -> |r| > 0.5 means the map mostly shows land cover, not drainage")

    # C. terrain
    if a.dem:
        dem = warp_to(os.path.expanduser(a.dem), gt, proj, nx, ny, "bilinear")
        slope, aspect = slope_aspect(dem, abs(gt[1]))
        print(f"\nC. Terrain: retention vs slope r = {corr(ret, slope)[0]:+.2f}; "
              f"vs elevation r = {corr(ret, dem)[0]:+.2f}; "
              f"vs east-facing (sin aspect) r = {corr(ret, np.sin(np.radians(aspect)))[0]:+.2f}; "
              f"vs north-facing (cos aspect) r = {corr(ret, np.cos(np.radians(aspect)))[0]:+.2f}")
        print("   -> strong aspect correlation = viewing-geometry artefact; slope/elevation = plausible drainage")

    # (+) other pass
    if a.other:
        o = warp_to(os.path.expanduser(a.other), gt, proj, nx, ny, "average")
        r, n = corr(ret, o)
        po, ss, k = class_agreement(ret, o)
        print(f"\n+. This retention vs --other: r = {r:+.2f}, class agreement {po * 100:.0f}%, "
              f"slow->slow {ss * 100:.0f}% (chance 33%)")


if __name__ == "__main__":
    main()
