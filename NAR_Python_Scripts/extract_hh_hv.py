import glob, os, re, csv, sys, datetime as dt
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from osgeo import gdal; gdal.UseExceptions()

SRC = sys.argv[1]            # folder with T###A_YYYYMMDD_rgb.png + _db.tif
SITE = sys.argv[2]           # site folder for outputs
TAG = sys.argv[3] if len(sys.argv) > 3 else "Asc"
lin = lambda x: 10 ** (x / 10); dB = lambda x: 10 * np.log10(x)
def mdb(v):
    v = v[np.isfinite(v)]; return round(float(dB(lin(v).mean())), 2) if v.size else ""

pairs = {}
for f in glob.glob(f"{SRC}/*_rgb.png"):
    m = re.match(r"(T\d{3}[AD])_(20\d{6})_rgb\.png$", os.path.basename(f))
    t = f.replace("_rgb.png", "_db.tif")
    if m and os.path.exists(t): pairs[m.group(2)] = (m.group(1), f, t)
dates = sorted(pairs)
print(f"{len(dates)} dates in {SRC}")

gdir = f"{SITE}/Green_Display_{TAG}"; rdir = f"{SITE}/Red_Display_{TAG}"
os.makedirs(gdir, exist_ok=True); os.makedirs(rdir, exist_ok=True)
grows, rrows, gpan, rpan = [], [], [], []
for d in dates:
    name, fr, ft = pairs[d]
    im = np.array(Image.open(fr).convert("RGB")).astype(np.int16)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]; valid = im.sum(2) > 0
    green = valid & (G - R >= 9) & (G - B >= 6) & (G >= 64)          # HV-dominant
    red = valid & (R - G >= 9) & (R >= 64)                            # HH-dominant (red + pink)
    strict = red & (R - B >= 6)                                       # strictly red
    ds = gdal.Open(ft); hh = ds.GetRasterBand(1).ReadAsArray().astype(float); hv = ds.GetRasterBand(2).ReadAsArray().astype(float); ds = None
    h, w = min(hh.shape[0], im.shape[0]), min(hh.shape[1], im.shape[1])
    hh, hv, green, red, strict, valid = hh[:h, :w], hv[:h, :w], green[:h, :w], red[:h, :w], strict[:h, :w], valid[:h, :w]
    ok = np.isfinite(hh) & np.isfinite(hv) & (hh > -18)
    for mk, folder, suf, pan in ((green, gdir, "green_white", gpan), (red, rdir, "HH_white", rpan)):
        o = np.full((h, w, 3), 255, np.uint8); o[mk] = im[:h, :w][mk].astype(np.uint8)
        Image.fromarray(o).save(f"{folder}/{name}_{d}_{suf}.png"); pan.append((d, o))
    g = G[:h, :w][green]; r = R[:h, :w][red]
    grows.append({"date": d, "mode": "dual-pol", "green_pixels": int(green.sum()),
                  "G_mean_0_255": round(float(g.mean()), 1) if g.size else "",
                  "G_median": int(np.median(g)) if g.size else "", "G_std": round(float(g.std()), 1) if g.size else "",
                  "HV_dB_green_px": mdb(hv[green & ok]), "HH_dB_green_px": mdb(hh[green & ok])})
    rrows.append({"date": d, "file": name + "_" + d, "HH_pixels": int(red.sum()),
                  "HH_pct": round(100 * red.sum() / max(valid.sum(), 1), 2),
                  "strict_red_pct": round(100 * strict.sum() / max(valid.sum(), 1), 2),
                  "R_mean_0_255": round(float(r.mean()), 1) if r.size else "",
                  "HH_dB_HH_px": mdb(hh[red & ok]), "HV_dB_HH_px": mdb(hv[red & ok])})
    print(f"  {d}: green {grows[-1]['green_pixels']:,} px, HV {grows[-1]['HV_dB_green_px']} dB | "
          f"red {rrows[-1]['HH_pct']}%, HH {rrows[-1]['HH_dB_HH_px']} dB")

for rows, path in ((grows, f"{gdir}/green_intensity_{TAG.lower()}.csv"), (rrows, f"{rdir}/HH_intensity_{TAG.lower()}.csv")):
    with open(path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=rows[0].keys()); wr.writeheader(); wr.writerows(rows)
    print("saved", path)

for pan, folder, what in ((gpan, gdir, "HV-dominant (green)"), (rpan, rdir, "HH-dominant (red/pink)")):
    n = len(pan); c = 5 if n > 6 else 3; r_ = int(np.ceil(n / c))
    fig, axes = plt.subplots(r_, c, figsize=(4.5 * c, 4.8 * r_)); axes = np.atleast_1d(axes).ravel()
    for ax, (d, o) in zip(axes, pan):
        ax.imshow(o); ax.axis("off"); ax.set_title(dt.datetime.strptime(d, "%Y%m%d").strftime("%d %b %Y"), fontsize=12)
    for ax in axes[n:]: ax.axis("off")
    fig.suptitle(f"{os.path.basename(os.path.abspath(SITE))} - {what} pixels, {TAG} pass (track {pairs[dates[0]][0]}), all others white", fontsize=15)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    for ext in ("png", "tif"): plt.savefig(f"{folder}/grid_{TAG.lower()}.{ext}", dpi=150)
    plt.close()
print("done")
