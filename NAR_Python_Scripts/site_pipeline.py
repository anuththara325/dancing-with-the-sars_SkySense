#!/usr/bin/env python3
# site_pipeline.py - HV (green) and HH (red/pink) intensities on fixed masks, rain + soil moisture, figures, web-app JSON
import argparse, glob, os, re, csv, json, datetime as dt
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from osgeo import gdal; gdal.UseExceptions()

lin = lambda x: 10 ** (np.asarray(x, float) / 10)
dB = lambda x: 10 * np.log10(x)
WIN = (1, 3, 7, 12)
LAG = {"D": 0, "A": 1}
PASSNAME = {"D": "descending", "A": "ascending"}

def load_giovanni(path):
    d = {}
    if not path or not os.path.exists(path): return d
    for line in open(path):
        p = [s.strip() for s in line.split(",")]
        try:
            v = float(p[1])
            if v > -9000: d[dt.date.fromisoformat(p[0][:10])] = v
        except (ValueError, IndexError): pass
    return d

def corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float); ok = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() > 2 else float("nan")

def read_band(path, i):
    ds = gdal.Open(path); a = ds.GetRasterBand(i).ReadAsArray().astype(float); ds = None
    return a

def lin_mean_db(v):
    v = v[np.isfinite(v)]
    return float(dB(lin(v).mean())) if v.size else float("nan")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True); ap.add_argument("--name", default=None)
    ap.add_argument("--rain", default=None); ap.add_argument("--sm", default=None)
    ap.add_argument("--min-freq", type=float, default=0.5)
    a = ap.parse_args()
    site = os.path.abspath(os.path.expanduser(a.site)); name = a.name or os.path.basename(site)
    res = os.path.join(site, "results"); os.makedirs(res, exist_ok=True)
    fix = lambda p: p if (p is None or os.path.isabs(p)) else os.path.join(site, p)
    rain, sm = load_giovanni(fix(a.rain)), load_giovanni(fix(a.sm))
    print(f"{name}: rain days {len(rain)}, soil-moisture days {len(sm)}")

    rgbs, tifs, qp = {}, {}, set()
    for f in glob.glob(f"{site}/**/*", recursive=True):
        b = os.path.basename(f)
        if ":Zone.Identifier" in b: continue
        m = re.match(r"(T\d{3}([AD]))_(20\d{6})_(rgb\.png|db\.tif)$", b)
        if m: (rgbs if m.group(4) == "rgb.png" else tifs)[(m.group(2), m.group(3))] = f
        if b == "stats.csv":
            for r in csv.DictReader(open(f)):
                try:
                    if float(r["native_px_m"]) > 15: qp.add(r["date"])
                except (KeyError, ValueError): pass

    webapp = {}
    for D in ("D", "A"):
        dates = sorted(d for (k, d) in rgbs if k == D and (k, d) in tifs)
        if not dates: continue
        print(f"\n=== {PASSNAME[D]} pass: {len(dates)} dates")
        green_m, hh_m, valid_m = {}, {}, {}
        for d in dates:
            im = np.array(Image.open(rgbs[(D, d)]).convert("RGB")).astype(np.int16)
            R, G, B = im[..., 0], im[..., 1], im[..., 2]
            valid = im.sum(2) > 0
            green_m[d] = valid & (G - R >= 9) & (G - B >= 6) & (G >= 64)
            hh_m[d] = valid & (R - G >= 9) & (R >= 64)
            valid_m[d] = valid
            for tag, mk in (("green_white", green_m[d]), ("HH_white", hh_m[d])):
                o = np.full_like(im, 255); o[mk] = im[mk]
                Image.fromarray(o.astype(np.uint8)).save(f"{res}/T{D}_{d}_{tag}.png")
        h = min(m.shape[0] for m in valid_m.values()); w = min(m.shape[1] for m in valid_m.values())
        crop = lambda m: m[:h, :w]
        fixed_g = np.mean([crop(green_m[d]) for d in dates], 0) >= a.min_freq
        fixed_h = np.mean([crop(hh_m[d]) for d in dates], 0) >= a.min_freq
        print(f"fixed masks: HV-green {fixed_g.sum():,} px ({100*fixed_g.mean():.1f}%), "
              f"HH-red/pink {fixed_h.sum():,} px ({100*fixed_h.mean():.1f}%)")

        rows = []
        for d in dates:
            hh = read_band(tifs[(D, d)], 1)[:h, :w]; hv = read_band(tifs[(D, d)], 2)[:h, :w]
            land = np.isfinite(hh) & np.isfinite(hv) & (hh > -18)
            day = dt.datetime.strptime(d, "%Y%m%d").date()
            smv = [sm[day + dt.timedelta(k)] for k in (-1, 0, 1) if day + dt.timedelta(k) in sm]
            row = {"date": d, "mode": "quad-pol" if d in qp else "dual-pol",
                   "HV_green_dB": round(lin_mean_db(hv[fixed_g & land]), 3),
                   "HH_red_dB": round(lin_mean_db(hh[fixed_h & land]), 3),
                   "HH_red_daily_dB": round(lin_mean_db(hh[crop(hh_m[d]) & land]), 3),
                   "HV_box_dB": round(lin_mean_db(hv[land]), 3),
                   "HH_box_dB": round(lin_mean_db(hh[land]), 3),
                   "green_pct_of_date": round(100 * green_m[d].sum() / max(valid_m[d].sum(), 1), 2),
                   "HH_pct_of_date": round(100 * hh_m[d].sum() / max(valid_m[d].sum(), 1), 2),
                   "soil_moisture_3day": round(float(np.mean(smv)), 2) if smv else float("nan")}
            for n in WIN:
                row[f"rain_{n}d_mm"] = round(sum(rain.get(day - dt.timedelta(days=LAG[D] + i), 0.0)
                                                 for i in range(n)), 1) if rain else float("nan")
            rows.append(row)

        ref = min(rows, key=lambda r: r["HH_red_dB"])
        for r in rows:
            r["dHH_dB"] = round(r["HH_red_dB"] - ref["HH_red_dB"], 2)
            r["dHV_dB"] = round(r["HV_green_dB"] - ref["HV_green_dB"], 2)
        with open(f"{res}/{name}_{PASSNAME[D]}_table.csv", "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=rows[0].keys()); wr.writeheader(); wr.writerows(rows)

        dual = [r for r in rows if r["mode"] == "dual-pol"]
        print(f"{'date':9s} {'mode':8s} {'HH fixed':>9s} {'HH daily':>9s} {'dHH':>6s} {'HV green':>9s} {'dHV':>6s} {'rain7d':>7s} {'SM':>6s}")
        for r in rows:
            print(f"{r['date']:9s} {r['mode']:8s} {r['HH_red_dB']:9.2f} {r['HH_red_daily_dB']:9.2f} {r['dHH_dB']:+6.2f} "
                  f"{r['HV_green_dB']:9.2f} {r['dHV_dB']:+6.2f} {r['rain_7d_mm']:7.1f} {r['soil_moisture_3day']:6.1f}")
        cors = {}
        for v in ("HV_green_dB", "HH_red_dB"):
            for x in ("rain_1d_mm", "rain_7d_mm", "soil_moisture_3day"):
                cors[f"{v}~{x}"] = (corr([r[v] for r in rows], [r[x] for r in rows]),
                                    corr([r[v] for r in dual], [r[x] for r in dual]))
        if rain or sm:
            print("correlations (all dates | dual-pol only):")
            for k, (c1, c2) in cors.items(): print(f"  r({k:32s}) = {c1:5.2f} | {c2:5.2f}")
        print(f"driest-looking pass: {ref['date']}; max dHH {max(r['dHH_dB'] for r in rows):+.2f} dB, "
              f"max dHV {max(r['dHV_dB'] for r in rows):+.2f} dB")

        days = [dt.datetime.strptime(r["date"], "%Y%m%d") for r in rows]
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(15, 9), sharex=True, gridspec_kw={"height_ratios": [1, 1.4]})
        if rain:
            rd = sorted(rain); a1.bar(rd, [rain[x] for x in rd], width=1, color="steelblue", alpha=.6, label="GPM IMERG rain (mm/day)")
        a1b = a1.twinx()
        if sm:
            sd = sorted(sm); a1b.plot(sd, [sm[x] for x in sd], ".", color="saddlebrown", alpha=.5, ms=4)
            full = [sd[0] + dt.timedelta(i) for i in range((sd[-1] - sd[0]).days + 1)]
            a1b.plot(full, [np.mean([sm[x] for x in sm if abs((x - q).days) <= 3]) for q in full],
                     color="saddlebrown", lw=2, label="soil moisture, 7-day mean")
            a1b.set_ylabel("Soil moisture", color="saddlebrown")
        a1.set_ylabel("Rain (mm/day)", color="steelblue")
        h1, l1 = a1.get_legend_handles_labels(); h2, l2 = a1b.get_legend_handles_labels()
        if h1 + h2: a1.legend(h1 + h2, l1 + l2, loc="upper left")
        a1.set_title(f"{name} 2026 - rain and soil moisture (top) vs NISAR {PASSNAME[D]} change (bottom)")
        a2.axhline(0, color="k", lw=.6)
        a2.plot(days, [r["dHH_dB"] for r in rows], "s-", color="red", lw=2, label="HH, red/pink (surface) pixels")
        a2.plot(days, [r["dHV_dB"] for r in rows], "o-", color="green", lw=2, label="HV, green (vegetation) pixels")
        for x, r in zip(days, rows):
            if r["mode"] == "quad-pol": a2.axvspan(x - dt.timedelta(days=1), x + dt.timedelta(days=1), color="grey", alpha=.25)
        a2.set_ylabel(f"Change since driest pass {ref['date']} (dB)"); a2.legend(loc="upper left"); a2.grid(alpha=.3)
        plt.tight_layout(); plt.savefig(f"{res}/{name}_{PASSNAME[D]}_timeseries.png", dpi=150); plt.close()

        fig, axs = plt.subplots(2, 2, figsize=(13, 10))
        for i, (v, col) in enumerate((("HH_red_dB", "red"), ("HV_green_dB", "green"))):
            for j, x in enumerate(("rain_7d_mm", "soil_moisture_3day")):
                ax = axs[i, j]
                X = np.array([r[x] for r in rows], float); Y = np.array([r[v] for r in rows], float)
                ok = np.isfinite(X) & np.isfinite(Y)
                for r, xv, yv in zip(rows, X, Y):
                    if np.isfinite(xv):
                        ax.scatter(xv, yv, s=70, color="grey" if r["mode"] == "quad-pol" else col, edgecolor="k", zorder=3)
                        ax.annotate(r["date"][4:6] + "/" + r["date"][6:], (xv, yv), textcoords="offset points", xytext=(4, 4), fontsize=8)
                if ok.sum() > 2:
                    k, c = np.polyfit(X[ok], Y[ok], 1); xx = np.linspace(X[ok].min(), X[ok].max(), 20); ax.plot(xx, k * xx + c, "k--", lw=1)
                ax.set_xlabel("rain in the 7 days before the pass (mm)" if x == "rain_7d_mm" else "soil moisture (3-day mean)")
                ax.set_ylabel(v.replace("_", " ")); ax.grid(alpha=.3); ax.set_title(f"r = {corr(X, Y):.2f} (n = {ok.sum()})")
        fig.suptitle(f"{name} - NISAR {PASSNAME[D]} vs rain and soil moisture (grey = quad-pol)")
        plt.tight_layout(); plt.savefig(f"{res}/{name}_{PASSNAME[D]}_scatter.png", dpi=150); plt.close()

        iso = lambda s: f"{s[:4]}-{s[4:6]}-{s[6:]}"
        webapp[PASSNAME[D]] = {
            "yLabel": f"NISAR change since the driest pass ({ref['date'][6:]}/{ref['date'][4:6]}), dB",
            "series": [{"label": "HH, surface (red/pink) pixels", "sensor": "nisar", "color": "#ff5a5a",
                        "pts": [[iso(r["date"]), r["dHH_dB"]] for r in rows]},
                       {"label": "HV, vegetation (green) pixels", "sensor": "nisar", "color": "#46c46b",
                        "pts": [[iso(r["date"]), r["dHV_dB"]] for r in rows]}],
            "rain": [{"d0": d.isoformat(), "d1": d.isoformat(), "mm": round(v, 1)} for d, v in sorted(rain.items())],
            "soil_moisture": [[d.isoformat(), round(v, 1)] for d, v in sorted(sm.items())],
            "correlations": {k: [round(c1, 2), round(c2, 2)] for k, (c1, c2) in cors.items()},
            "table": rows}

    def clean(o):
        if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
        if isinstance(o, list): return [clean(v) for v in o]
        if isinstance(o, float) and not np.isfinite(o): return None
        return o
    with open(f"{res}/{name}_webapp.json", "w") as fh: json.dump(clean(webapp), fh, indent=1)
    print(f"\nsaved to {res}/")

if __name__ == "__main__":
    main()
