import argparse, glob, os, re, csv, datetime as dt
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

STRETCH = {"HH": (-22.0, -2.0), "HV": (-28.0, -8.0), "RATIO": (0.0, 15.0)}
FOLDERS = {"asc": "RGB_Images_Asc", "desc": "RGB_Images_Dec"}
LAG = {"asc": 1, "desc": 0}
QP = {"20260821", "20260902", "20260914", "20260926"}
EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp")
to_db = lambda c, k: STRETCH[k][0] + c / 255.0 * (STRETCH[k][1] - STRETCH[k][0])
lin = lambda d: 10 ** (d / 10); dB = lambda x: 10 * np.log10(x)

def date_of(f):
    m = re.search(r"(20\d{6})", os.path.basename(f)); return m.group(1) if m else None
def load_giovanni(p):
    d = {}
    if not p or not os.path.exists(p): return d
    for line in open(p):
        q = [s.strip() for s in line.split(",")]
        try:
            v = float(q[1])
            if v > -9000: d[dt.date.fromisoformat(q[0][:10])] = v
        except (ValueError, IndexError): pass
    return d
def mean_db(v):
    v = v[np.isfinite(v)]; return round(float(dB(lin(v).mean())), 2) if v.size else float("nan")
def corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float); ok = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() > 2 else float("nan")

ap = argparse.ArgumentParser(); ap.add_argument("site"); ap.add_argument("--rain"); ap.add_argument("--sm"); a = ap.parse_args()
site = os.path.abspath(os.path.expanduser(a.site)); name = os.path.basename(site)
fix = lambda p: p if (not p or os.path.isabs(p)) else os.path.join(site, p)
rain, sm = load_giovanni(fix(a.rain)), load_giovanni(fix(a.sm))
print(f"{name}: rain days {len(rain)}, soil-moisture days {len(sm)}")

for tag, sub in FOLDERS.items():
    files = {}
    for f in sorted(glob.glob(f"{site}/{sub}/**/*", recursive=True)):
        if f.lower().endswith(EXT) and ":Zone" not in f and "white" not in f.lower() and "_db." not in f.lower() and date_of(f):
            files.setdefault(date_of(f), f)
    if not files: print(f"\n!! {tag}: no RGB images in {sub}"); continue
    out = f"{site}/Results_RGB_dB/{tag}"; os.makedirs(out, exist_ok=True); dates = sorted(files)
    print(f"\n=== {tag}: {len(dates)} images in {sub}")
    HH, HV, gm, hm, vm = {}, {}, {}, {}, {}
    for d in dates:
        im = np.array(Image.open(files[d]).convert("RGB")).astype(float)
        R, G, B = im[..., 0], im[..., 1], im[..., 2]; valid = im.sum(2) > 0
        un = valid & (R > 2) & (R < 253) & (G > 2) & (G < 253) & (B > 2) & (B < 253)
        predB = (to_db(R, "HH") - to_db(G, "HV")) / 15.0 * 255
        err = float(np.median(np.abs(predB[un] - B[un]))) if un.any() else float("nan")
        sat = 100 * float(((R >= 254) | (G >= 254))[valid].mean())
        hh = np.where(valid, to_db(R, "HH"), np.nan); hv = np.where(valid, to_db(G, "HV"), np.nan)
        hh[valid & (R <= 1)] = np.nan; hv[valid & (G <= 1)] = np.nan
        HH[d], HV[d], vm[d] = hh, hv, valid
        gm[d] = valid & (G - R >= 9) & (G - B >= 6) & (G >= 64)
        hm[d] = valid & (R - G >= 9) & (R >= 64)
        for lab, mk in (("green_white", gm[d]), ("HH_white", hm[d])):
            o = np.full(im.shape, 255, np.uint8); o[mk] = im[mk].astype(np.uint8)
            Image.fromarray(o).save(f"{out}/{name}_{tag}_{d}_{lab}.png")
        print(f"  {d}: stretch check |B error| = {err:.1f} ({'OK' if err < 6 else 'CHECK - stretch may differ'}), saturated {sat:.1f}%")
    h = min(x.shape[0] for x in vm.values()); w = min(x.shape[1] for x in vm.values()); c = lambda x: x[:h, :w]
    fg = np.mean([c(gm[d]) for d in dates], 0) >= 0.5; fh = np.mean([c(hm[d]) for d in dates], 0) >= 0.5
    print(f"  fixed masks: green {fg.sum():,} px ({100*fg.mean():.1f}%), red/pink {fh.sum():,} px ({100*fh.mean():.1f}%)")
    rows = []
    for d in dates:
        hh, hv = c(HH[d]), c(HV[d]); land = np.isfinite(hh) & (hh > -18)
        D = dt.datetime.strptime(d, "%Y%m%d").date()
        smv = [sm[D + dt.timedelta(k)] for k in (-1, 0, 1) if D + dt.timedelta(k) in sm]
        rs = lambda n: round(sum(rain.get(D - dt.timedelta(days=LAG[tag] + i), 0) for i in range(n)), 1) if rain else float("nan")
        rows.append({"date": d, "flag": ("quad-pol" if (tag == "desc" and d in QP) else "validated" if (tag == "asc" and d >= "20261021") else ""),
                     "HH_red_fixed_dB": mean_db(hh[fh & land]), "HH_red_daily_dB": mean_db(hh[c(hm[d]) & land]),
                     "HV_green_fixed_dB": mean_db(hv[fg & land]), "HV_green_daily_dB": mean_db(hv[c(gm[d]) & land]),
                     "HH_box_dB": mean_db(hh[land]), "HV_box_dB": mean_db(hv[land]),
                     "red_pct": round(100 * hm[d].sum() / vm[d].sum(), 2), "green_pct": round(100 * gm[d].sum() / vm[d].sum(), 2),
                     "rain_1d_mm": rs(1), "rain_7d_mm": rs(7),
                     "soil_moisture_3day": round(float(np.mean(smv)), 1) if smv else float("nan")})
    ref = min(rows, key=lambda r: r["HH_red_fixed_dB"])
    for r in rows:
        r["dHH_dB"] = round(r["HH_red_fixed_dB"] - ref["HH_red_fixed_dB"], 2)
        r["dHV_dB"] = round(r["HV_green_fixed_dB"] - ref["HV_green_fixed_dB"], 2)
    with open(f"{out}/{name}_{tag}_dB_table.csv", "w", newline="") as f_:
        wr = csv.DictWriter(f_, fieldnames=rows[0].keys()); wr.writeheader(); wr.writerows(rows)
    print(f"  {'date':9s} {'HH fixed':>9s} {'HH daily':>9s} {'dHH':>6s} {'HV fixed':>9s} {'HV daily':>9s} {'dHV':>6s} {'rain7d':>7s} {'SM':>6s}")
    for r in rows:
        print(f"  {r['date']:9s} {r['HH_red_fixed_dB']:9.2f} {r['HH_red_daily_dB']:9.2f} {r['dHH_dB']:+6.2f} {r['HV_green_fixed_dB']:9.2f} "
              f"{r['HV_green_daily_dB']:9.2f} {r['dHV_dB']:+6.2f} {r['rain_7d_mm']:7.1f} {r['soil_moisture_3day']:6.1f}  {r['flag']}")
    if rain or sm:
        for v in ("HH_red_fixed_dB", "HV_green_fixed_dB"):
            print(f"  r({v}): rain 1d {corr([r[v] for r in rows], [r['rain_1d_mm'] for r in rows]):.2f} | "
                  f"rain 7d {corr([r[v] for r in rows], [r['rain_7d_mm'] for r in rows]):.2f} | "
                  f"soil moisture {corr([r[v] for r in rows], [r['soil_moisture_3day'] for r in rows]):.2f}")
    for lab in ("HH_white", "green_white"):
        n = len(dates); cc = 3 if n > 4 else n; rr = int(np.ceil(n / cc))
        fig, axes = plt.subplots(rr, cc, figsize=(5 * cc, 5.3 * rr)); axes = np.atleast_1d(axes).ravel()
        for ax, d in zip(axes, dates):
            ax.imshow(Image.open(f"{out}/{name}_{tag}_{d}_{lab}.png")); ax.axis("off")
            ax.set_title(dt.datetime.strptime(d, "%Y%m%d").strftime("%d %b %Y"), fontsize=13)
        for ax in axes[n:]: ax.axis("off")
        what = "HH-dominant (red/pink)" if lab == "HH_white" else "HV-dominant (green)"
        fig.suptitle(f"{name} - {what} pixels, {tag} pass, all others white", fontsize=16)
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        for ext in ("png", "tif"): plt.savefig(f"{out}/{name}_{tag}_{lab}_grid.{ext}", dpi=150)
        plt.close()
    days = [dt.datetime.strptime(r["date"], "%Y%m%d") for r in rows]
    fig, ax = plt.subplots(figsize=(14, 5.5))
    if rain:
        rd = sorted(rain); ax.bar(rd, [rain[x] for x in rd], width=1, color="steelblue", alpha=.45, label="IMERG rain (mm/day)")
    ax.set_ylabel("Rain (mm/day)"); b = ax.twinx()
    b.plot(days, [r["dHH_dB"] for r in rows], "s-", color="red", lw=2, label="HH, red/pink pixels")
    b.plot(days, [r["dHV_dB"] for r in rows], "o-", color="green", lw=2, label="HV, green pixels")
    for x, r in zip(days, rows):
        if r["flag"]: b.axvspan(x - dt.timedelta(days=1), x + dt.timedelta(days=1), color="grey", alpha=.25)
    b.set_ylabel(f"Change since {ref['date']} (dB)")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = b.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, loc="upper left")
    ax.set_title(f"{name} - {tag} pass: HH and HV change (dB, from RGB) vs rain  [grey = flagged date]")
    plt.tight_layout(); plt.savefig(f"{out}/{name}_{tag}_dB_timeseries.png", dpi=150); plt.close()
    print(f"  saved {out}/")
