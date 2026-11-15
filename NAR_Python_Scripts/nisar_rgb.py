#!/usr/bin/env python3
# Stream NISAR GCOV, clip to lon/lat box, save RGB (R=HH, G=HV, B=HH/HV) + dB GeoTIFF + stats.csv
import argparse, os, re, csv
import numpy as np
from osgeo import gdal, osr
gdal.UseExceptions()
GRID = "//science/LSAR/GCOV/grids/frequencyA/"
STRETCH = {"HH": (-22.0, -2.0), "HV": (-28.0, -8.0), "RATIO": (0.0, 15.0)}

def sub(url, name):
    path = url if (url.startswith("/vsicurl/") or not url.startswith("http")) else "/vsicurl/" + url
    return f'HDF5:"{path}":{GRID}{name}'

def read_1d(url, name):
    ds = gdal.Open(sub(url, name))
    return ds.ReadAsArray().astype(np.float64).ravel(), ds

def find_epsg(ds, lon):
    for k, v in (ds.GetMetadata() or {}).items():
        if "epsg" in k.lower():
            try: return int(float(v))
            except ValueError: pass
    return 32600 + int((lon + 180) // 6) + 1

def window(c, lo, hi):
    i = np.where((c >= lo) & (c <= hi))[0]
    return None if i.size == 0 else (int(i.min()), int(i.max()) + 1)

def block_mean(a, f):
    if f <= 1: return a
    h, w = (a.shape[0]//f)*f, (a.shape[1]//f)*f
    with np.errstate(invalid="ignore"):
        return np.nanmean(a[:h, :w].reshape(h//f, f, w//f, f), axis=(1, 3))

def boxcar(a, k=5):
    v = np.isfinite(a); x = np.where(v, a, 0.0); p = k//2
    def cs(z):
        z = np.pad(z, p); c = z.cumsum(0).cumsum(1); return np.pad(c, ((1, 0), (1, 0)))
    cx, cv = cs(x), cs(v.astype(float)); h, w = a.shape
    S = lambda c: c[k:k+h, k:k+w] - c[:h, k:k+w] - c[k:k+h, :w] + c[:h, :w]
    s, n = S(cx), S(cv)
    with np.errstate(invalid="ignore", divide="ignore"): out = s / n
    out[n == 0] = np.nan
    return out

def db(a):
    with np.errstate(invalid="ignore", divide="ignore"): return 10*np.log10(a)

def to_byte(d, lo, hi):
    s = np.clip((d - lo)/(hi - lo), 0, 1); return (np.where(np.isfinite(s), s, 0)*255).astype(np.uint8)

def label(url):
    n = os.path.basename(url).replace(".h5", "")
    m = re.search(r"GCOV_\d+_(\d{3})_([AD])_(\d{3})_.*?_(\d{8})T", n)
    return (n, n) if not m else (f"T{m.group(1)}{m.group(2)}_{m.group(4)}", m.group(4))

def process(url, bbox, res, outdir, rows):
    name, date = label(url); lon0, lat0, lon1, lat1 = bbox
    x, xds = read_1d(url, "xCoordinates"); y, _ = read_1d(url, "yCoordinates")
    epsg = find_epsg(xds, (lon0 + lon1)/2)
    src = osr.SpatialReference(); src.ImportFromEPSG(4326)
    dst = osr.SpatialReference(); dst.ImportFromEPSG(epsg)
    for s in (src, dst): s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    tr = osr.CoordinateTransformation(src, dst)
    pts = [tr.TransformPoint(lo, la)[:2] for lo in (lon0, lon1) for la in (lat0, lat1)]
    wx = window(x, min(p[0] for p in pts), max(p[0] for p in pts))
    wy = window(y, min(p[1] for p in pts), max(p[1] for p in pts))
    if wx is None or wy is None:
        print(f"  !! {name}: box is outside this granule's footprint - skipped"); return
    px = abs(x[1] - x[0]); f = max(1, int(round(res/px)))
    d = {}
    for pol in ("HHHH", "HVHV"):
        a = gdal.Open(sub(url, pol)).ReadAsArray(wx[0], wy[0], wx[1]-wx[0], wy[1]-wy[0]).astype(np.float64)
        a[(a <= 0) | ~np.isfinite(a)] = np.nan
        d[pol] = boxcar(block_mean(a, f), 5)
    hh, hv = d["HHHH"], d["HVHV"]
    with np.errstate(invalid="ignore", divide="ignore"): r = hh/hv
    hh_db, hv_db, r_db = db(hh), db(hv), db(r)
    rgb = [to_byte(hh_db, *STRETCH["HH"]), to_byte(hv_db, *STRETCH["HV"]), to_byte(r_db, *STRETCH["RATIO"])]
    gt = (x[wx[0]] - (x[1]-x[0])/2, (x[1]-x[0])*f, 0.0, y[wy[0]] - (y[1]-y[0])/2, 0.0, (y[1]-y[0])*f)
    h, w = hh.shape
    mem = gdal.GetDriverByName("MEM").Create("", w, h, 3, gdal.GDT_Byte)
    mem.SetGeoTransform(gt); mem.SetProjection(dst.ExportToWkt())
    for i in range(3): mem.GetRasterBand(i+1).WriteArray(rgb[i])
    png = os.path.join(outdir, f"{name}_rgb.png"); gdal.GetDriverByName("PNG").CreateCopy(png, mem)
    t = gdal.GetDriverByName("GTiff").Create(os.path.join(outdir, f"{name}_db.tif"), w, h, 3, gdal.GDT_Float32, ["COMPRESS=DEFLATE"])
    t.SetGeoTransform(gt); t.SetProjection(dst.ExportToWkt())
    for i, (arr, ds_) in enumerate(((hh_db, "HH_dB"), (hv_db, "HV_dB"), (r_db, "HHHV_ratio_dB"))):
        b = t.GetRasterBand(i+1); b.WriteArray(arr.astype(np.float32)); b.SetNoDataValue(np.nan); b.SetDescription(ds_)
    t = None
    mh, mv = np.nanmean(hh), np.nanmean(hv)
    rows.append([date, name, round(px, 1), res, round(float(db(mh)), 2), round(float(db(mv)), 2), round(float(db(mh/mv)), 2)])
    print(f"  ok {name}: {w}x{h} px, HH {rows[-1][4]} dB, HV {rows[-1][5]} dB, ratio {rows[-1][6]} dB -> {png}")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("urls")
    ap.add_argument("--bbox", nargs=4, type=float, default=[81.45, 7.10, 81.70, 7.35])
    ap.add_argument("--res", type=float, default=20.0); ap.add_argument("--out", default="rgb_out")
    a = ap.parse_args()
    urls = [l.strip() for l in open(a.urls) if l.strip() and not l.startswith("#")]
    os.makedirs(a.out, exist_ok=True); rows = []
    for u in urls:
        print(label(u)[0])
        try: process(u, a.bbox, a.res, a.out, rows)
        except Exception as e: print(f"  !! failed: {e}")
    rows.sort()
    with open(os.path.join(a.out, "stats.csv"), "w", newline="") as fh:
        wr = csv.writer(fh); wr.writerow(["date", "name", "native_px_m", "out_px_m", "HH_dB", "HV_dB", "HHHV_ratio_dB"]); wr.writerows(rows)
    print(f"done: {len(rows)}/{len(urls)} granules, stats in {a.out}/stats.csv")

if __name__ == "__main__": main()
