import glob, os, re, csv, sys, datetime as dt
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
try:
    from osgeo import gdal; gdal.UseExceptions()
except ImportError:
    gdal = None

SRC = sys.argv[1]; OUT = sys.argv[2]
EXT = (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")
lin = lambda x: 10 ** (x / 10); dB = lambda x: 10 * np.log10(x)

def date_of(b):
    m = re.search(r"(20\d{6})", b); return m.group(1) if m else None
def direction(path):
    s = path.lower()
    if re.search(r"t[o0]?84a|_084_a|asc|ace", s): return "asc"
    if re.search(r"t048d|t120d|_048_d|desc|dec", s): return "desc"
    m = re.search(r"t[o0]?\d{2,3}([ad])_", s)
    return {"a": "asc", "d": "desc"}.get(m.group(1)) if m else None

files = [f for f in glob.glob(f"{SRC}/**/*", recursive=True)
         if f.lower().endswith(EXT) and ":Zone" not in f and not f.lower().endswith("_db.tif") and date_of(os.path.basename(f))]
tifs = {(direction(t), date_of(os.path.basename(t))): t for t in glob.glob(f"{SRC}/**/*_db.tif", recursive=True)}
groups = {}
for f in files:
    d = direction(f)
    if d: groups.setdefault(d, []).append(f)
    else: print(f"  ? can't tell asc/desc from name, skipped: {f}")

for direc, fl in groups.items():
    out = os.path.join(OUT, direc); os.makedirs(out, exist_ok=True)
    rows, panels, seen = [], [], set()
    for f in sorted(fl, key=lambda x: date_of(os.path.basename(x))):
        d = date_of(os.path.basename(f))
        if d in seen: continue
        im = np.array(Image.open(f).convert("RGB")).astype(np.int16)
        if (im == 255).all(2).mean() > 0.2 or (im.sum(2) == 0).mean() > 0.9:
            print(f"  skip {os.path.basename(f)}: already filtered / empty"); continue
        seen.add(d)
        R, G, B = im[..., 0], im[..., 1], im[..., 2]
        valid = im.sum(2) > 0
        hh = valid & (R - G >= 9) & (R >= 64)                 # red + pink/magenta = HH-dominant
        o = np.full_like(im, 255); o[hh] = im[hh]
        Image.fromarray(o.astype(np.uint8)).save(f"{out}/Nawalapitiya_{direc}_{d}_HH_white.png")
        row = {"date": d, "source": os.path.basename(f), "HH_pct": round(100 * hh.sum() / max(valid.sum(), 1), 2),
               "R_mean_0_255": round(float(R[hh].mean()), 1) if hh.any() else "", "HH_dB_HH_px": ""}
        t = tifs.get((direc, d))
        if t and gdal:
            ds = gdal.Open(t); a = ds.GetRasterBand(1).ReadAsArray().astype(float); ds = None
            hgt, wid = min(a.shape[0], hh.shape[0]), min(a.shape[1], hh.shape[1])
            v = a[:hgt, :wid][hh[:hgt, :wid]]; v = v[np.isfinite(v) & (v > -18)]
            if v.size: row["HH_dB_HH_px"] = round(float(dB(lin(v).mean())), 2)
        rows.append(row); panels.append((d, o))
        print(f"  {direc} {d}: HH-dominant {row['HH_pct']}% | R mean {row['R_mean_0_255']} | HH {row['HH_dB_HH_px'] or '-'} dB")
    if not rows: continue
    with open(f"{out}/Nawalapitiya_HH_{direc}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    n = len(panels); c = 3 if n > 4 else n; r = int(np.ceil(n / c))
    fig, axes = plt.subplots(r, c, figsize=(5 * c, 5.5 * r)); axes = np.atleast_1d(axes).ravel()
    for ax, (d, o) in zip(axes, panels):
        ax.imshow(o.astype(np.uint8)); ax.axis("off")
        ax.set_title(dt.datetime.strptime(d, "%Y%m%d").strftime("%d %b %Y"), fontsize=13)
    for ax in axes[n:]: ax.axis("off")
    fig.suptitle(f"Nawalapitiya - HH-dominant (red/pink) pixels, {direc}ending pass, all others white\n"
                 "R=HH  G=HV  B=HH/HV", fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    for ext in ("png", "tif"): plt.savefig(f"{out}/Nawalapitiya_HH_grid_{direc}.{ext}", dpi=150)
    plt.close(); print(f"saved {out}/ ({len(rows)} images, grid, CSV)")
