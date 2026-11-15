import glob, os, re, csv
import numpy as np
from PIL import Image
from osgeo import gdal; gdal.UseExceptions()

BASE = os.path.expanduser("~/nisar/rgb_t120/Ampara"); OUT = f"{BASE}/HH_measure"; os.makedirs(OUT, exist_ok=True)
PASSES = {"desc": ("HH_desc", "Images_Dec", "D"), "asc": ("HH_asc", "Images_Asc", "A")}
lin = lambda x: 10 ** (x / 10); dB = lambda x: 10 * np.log10(x)
def date_of(f):
    m = re.search(r"(20\d{6})", os.path.basename(f)); return m.group(1) if m else None

tifs = {}
for t in glob.glob(f"{BASE}/**/*_db.tif", recursive=True):
    m = re.search(r"T\d{3}([AD])_(20\d{6})", os.path.basename(t))
    if m: tifs[(m.group(1), m.group(2))] = t
print(f"found {len(tifs)} _db.tif files")

for tag, (mdir, rgbdir, direc) in PASSES.items():
    mf = {date_of(f): f for f in glob.glob(f"{BASE}/{mdir}/*_HH_white.png") if date_of(f)}
    dates = sorted(mf)
    if not dates:
        print(f"!! {tag}: no *_HH_white.png in {mdir}"); continue
    masks = {d: ~(np.array(Image.open(mf[d]).convert("RGB")) == 255).all(2) for d in dates}
    h = min(m.shape[0] for m in masks.values()); w = min(m.shape[1] for m in masks.values())
    fixed = np.mean([m[:h, :w] for m in masks.values()], axis=0) >= 0.5
    use_db = all((direc, d) in tifs for d in dates)
    unit = "dB" if use_db else "0-255"

    rows = []
    for d in dates:
        if use_db:
            ds = gdal.Open(tifs[(direc, d)])              # keep the dataset open
            img = ds.GetRasterBand(1).ReadAsArray().astype(float)[:h, :w]
            ds = None
            ok = np.isfinite(img) & (img > -18)           # drop water / no-data
        else:
            src = [f for f in glob.glob(f"{BASE}/{rgbdir}/*") if date_of(f) == d and "white" not in f.lower()]
            img = np.array(Image.open(src[0]).convert("RGB")).astype(float)[:h, :w, 0]
            ok = img > 0

        def mean(m):
            v = img[m & ok]
            if v.size == 0: return np.nan
            return float(dB(lin(v).mean())) if use_db else float(v.mean())

        m_d = masks[d][:h, :w]
        rows.append({"date": d,
                     f"HH_daily_mask_{unit}": round(mean(m_d), 2), "daily_mask_px": int((m_d & ok).sum()),
                     f"HH_fixed_mask_{unit}": round(mean(fixed), 2), "fixed_mask_px": int((fixed & ok).sum())})

    ref = np.nanmin([r[f"HH_fixed_mask_{unit}"] for r in rows])
    for r in rows: r["change_vs_lowest"] = round(r[f"HH_fixed_mask_{unit}"] - ref, 2)
    with open(f"{OUT}/HH_intensity_{tag}.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=rows[0].keys()); wr.writeheader(); wr.writerows(rows)

    print(f"\n=== {tag.upper()}  (units: {unit}; fixed mask = {rows[0]['fixed_mask_px']:,} px)")
    print(f"{'date':10s} {'HH daily mask':>14s} {'HH fixed mask':>14s} {'change':>8s} {'daily px':>10s}")
    for r in rows:
        print(f"{r['date']:10s} {r[f'HH_daily_mask_{unit}']:14.2f} {r[f'HH_fixed_mask_{unit}']:14.2f} "
              f"{r['change_vs_lowest']:+8.2f} {r['daily_mask_px']:10,}")
    print(f"saved {OUT}/HH_intensity_{tag}.csv")
