import glob, os, re, csv, sys, datetime as dt
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
try:
    from osgeo import gdal; gdal.UseExceptions()
except ImportError:
    gdal = None

SITE = os.path.abspath(os.path.expanduser(sys.argv[1])); NAME = os.path.basename(SITE)
SETS = {"Asc": "Ascending_RGB", "Desc": "Descending_RGB"}
EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp")
ST = {"HH": (-22.0, -2.0), "HV": (-28.0, -8.0)}
to_db = lambda c, k: ST[k][0] + c / 255.0 * (ST[k][1] - ST[k][0])
lin = lambda x: 10 ** (x / 10); dB = lambda x: 10 * np.log10(x)
def mdb(v):
    v = v[np.isfinite(v)]; return round(float(dB(lin(v).mean())), 2) if v.size else ""
def date_of(f):
    m = re.search(r"(20\d{6})", os.path.basename(f)); return m.group(1) if m else None

for tag, sub in SETS.items():
    src = os.path.join(SITE, sub); imgs, tifs = {}, {}
    for f in sorted(glob.glob(f"{src}/**/*", recursive=True)):
        b = f.lower(); d = date_of(f)
        if not d or ":zone" in b: continue
        if b.endswith("_db.tif"): tifs[d] = f
        elif b.endswith(EXT) and "white" not in b: imgs.setdefault(d, f)
    if not imgs: print(f"\n!! {tag}: no RGB images in {src}"); continue
    out = os.path.join(SITE, f"Red_Display_{tag}"); os.makedirs(out, exist_ok=True)
    print(f"\n=== {NAME} {tag}: {len(imgs)} RGB images, {len(tifs)} _db.tif files")
    rows, pan = [], []
    for d in sorted(imgs):
        im = np.array(Image.open(imgs[d]).convert("RGB")).astype(float)
        R, G, B = im[..., 0], im[..., 1], im[..., 2]; valid = im.sum(2) > 0
        red = valid & (R - G >= 9) & (R >= 64); strict = red & (R - B >= 6)
        o = np.full(im.shape, 255, np.uint8); o[red] = im[red].astype(np.uint8)
        Image.fromarray(o).save(f"{out}/{NAME}_{tag}_{d}_HH_white.png"); pan.append((d, o))
        src_db, hh, hv = "none", None, None
        if d in tifs and gdal:
            ds = gdal.Open(tifs[d]); hh = ds.GetRasterBand(1).ReadAsArray().astype(float)
            hv = ds.GetRasterBand(2).ReadAsArray().astype(float); ds = None
            h, w = min(hh.shape[0], R.shape[0]), min(hh.shape[1], R.shape[1]); hh, hv = hh[:h, :w], hv[:h, :w]; src_db = "db.tif"
        else:
            un = valid & (R > 2) & (R < 253) & (G > 2) & (G < 253) & (B > 2) & (B < 253)
            err = float(np.median(np.abs((to_db(R, "HH") - to_db(G, "HV")) / 15 * 255 - B)[un])) if un.any() else 99
            if err < 6:
                hh = np.where(valid & (R > 1), to_db(R, "HH"), np.nan); hv = np.where(valid & (G > 1), to_db(G, "HV"), np.nan)
                h, w = R.shape; src_db = f"from RGB (check {err:.1f} OK)"
            else:
                src_db = f"NOT AVAILABLE (stretch check {err:.1f} failed)"
        hhd = hvd = ""
        if hh is not None:
            m = red[:h, :w] & np.isfinite(hh) & (hh > -18); hhd, hvd = mdb(hh[m]), mdb(hv[m])
        r = R[red]
        rows.append({"date": d, "file": os.path.basename(imgs[d]), "HH_pixels": int(red.sum()),
                     "HH_pct": round(100 * red.sum() / max(valid.sum(), 1), 2),
                     "strict_red_pct": round(100 * strict.sum() / max(valid.sum(), 1), 2),
                     "R_mean_0_255": round(float(r.mean()), 1) if r.size else "",
                     "R_median_0_255": int(np.median(r)) if r.size else "",
                     "HH_dB_HH_px": hhd, "HV_dB_HH_px": hvd, "dB_source": src_db})
        print(f"  {d}: red {rows[-1]['HH_pct']}% | R mean {rows[-1]['R_mean_0_255']} | HH {hhd if hhd != '' else '-'} dB | {src_db}")
    lows = [x for x in rows if x["HH_dB_HH_px"] != ""]
    if lows:
        ref = min(lows, key=lambda x: x["HH_dB_HH_px"])
        for x in rows: x["dHH_dB_vs_lowest"] = round(x["HH_dB_HH_px"] - ref["HH_dB_HH_px"], 2) if x["HH_dB_HH_px"] != "" else ""
    with open(f"{out}/HH_intensity_{tag.lower()}.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=rows[0].keys()); wr.writeheader(); wr.writerows(rows)
    n = len(pan); c = 4 if n > 6 else 3; rr = int(np.ceil(n / c))
    fig, axes = plt.subplots(rr, c, figsize=(4.5 * c, 4.8 * rr)); axes = np.atleast_1d(axes).ravel()
    for ax, (d, o) in zip(axes, pan):
        ax.imshow(o); ax.axis("off"); ax.set_title(dt.datetime.strptime(d, "%Y%m%d").strftime("%d %b %Y"), fontsize=12)
    for ax in axes[n:]: ax.axis("off")
    fig.suptitle(f"{NAME} - HH-dominant (red/pink) pixels, {tag} pass, all others white", fontsize=15)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    for ext in ("png", "tif"): plt.savefig(f"{out}/HH_grid_{tag.lower()}.{ext}", dpi=150)
    plt.close()
    dd = [dt.datetime.strptime(x["date"], "%Y%m%d") for x in rows]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(dd, [x["R_mean_0_255"] for x in rows], "s-", color="red", label="mean red intensity (0-255)")
    ax.set_ylabel("Red intensity (0-255)", color="red"); ax.grid(alpha=.3)
    if lows:
        b = ax.twinx(); b.plot([dt.datetime.strptime(x["date"], "%Y%m%d") for x in lows], [x["HH_dB_HH_px"] for x in lows], "o--", color="darkred")
        b.set_ylabel("HH (dB)", color="darkred")
    ax.set_title(f"{NAME} - HH-dominant pixels, {tag} pass"); plt.tight_layout()
    plt.savefig(f"{out}/HH_timeseries_{tag.lower()}.png", dpi=150); plt.close()
    print(f"  saved {out}/")
