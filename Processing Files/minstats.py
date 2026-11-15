import json, csv
import numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter, binary_dilation
gdal.UseExceptions()
meta = {"jun20":("2026-06-20",23),"jul02":("2026-07-02",24),"jul14":("2026-07-14",25),"jul26":("2026-07-26",26),
        "aug19":("2026-08-19",28),"aug31":("2026-08-31",29),"sep12":("2026-09-12",30),"sep24":("2026-09-24",31),
        "oct06":("2026-10-06",32),"oct18":("2026-10-18",33)}
tags = list(meta)
def rd(t, b):
    ds = gdal.Open(f"mn_{t}_{b}.tif"); a = ds.GetRasterBand(1).ReadAsArray().astype("float64")
    ok = np.isfinite(a) & (a > 0)
    m = np.where(ok, a, 0.0); w = uniform_filter(ok.astype("float64"), 5)
    return 10*np.log10(np.where(w > 0, uniform_filter(m, 5)/np.maximum(w, 1e-9), np.nan)), ok
HV, HH, common = {}, {}, None
for t in tags:
    HV[t], o1 = rd(t, "hvhv"); HH[t], o2 = rd(t, "hhhh"); ok = o1 & o2
    common = ok if common is None else common & ok
px = (0.2/800*111.32*np.cos(np.radians(8.03))) * (0.15/600*110.57)
dark = {t: (HV[t] < -22) & common for t in tags}
persist = sum(dark[t].astype(int) for t in tags) >= 9
near = binary_dilation(persist, iterations=20)
stack = np.stack([HV[t] for t in tags]); med = np.nanmedian(stack, axis=0)
stable = common & ~near & (np.nanmax(np.abs(stack - med), axis=0) < 1.0)
print("common valid %.1f%%  persistent tank px %d (%.2f km2)  stable-ref px %d" % (100*common.mean(), persist.sum(), persist.sum()*px, stable.sum()))
rows = []
for t in tags:
    r = {"tag": t, "date": meta[t][0], "cycle": meta[t][1]}
    r["tank_water_km2"] = round(float((dark[t] & near).sum()*px), 2)
    r["field_water_km2"] = round(float((dark[t] & ~near).sum()*px), 2)
    for pol, D in (("hh", HH), ("hv", HV)):
        v = D[t][common & ~near]
        r[f"{pol}_fields_median_db"] = round(float(np.median(v)), 2)
        r[f"{pol}_fields_std_db"] = round(float(v.std()), 2)
    r["stable_ref_hv_median_db"] = round(float(np.median(HV[t][stable])), 2)
    rows.append(r)
out = {"site": "Minneriya", "bbox_wsen": [80.82, 7.95, 81.02, 8.10], "track": 84, "frame": 6, "crid": "P05023 (provisional)",
       "dark_threshold_hv_db": -22, "pixel_km2": round(px, 6), "common_valid_pct": round(100*float(common.mean()), 1),
       "note": "tank = dark (HV<-22) on >=9 of 10 dates plus 20-px margin; field water = dark outside it; stats on common valid area", "dates": rows}
json.dump(out, open("web_minneriya/stats.json", "w"), indent=1)
with open("web_minneriya/timeseries.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("date        tank_km2  field_water_km2  HV_fields_med  HH_fields_med  stable_HV")
for r in rows: print(r["date"], "%8.2f %14.2f %13.2f %13.2f %10.2f" % (r["tank_water_km2"], r["field_water_km2"], r["hv_fields_median_db"], r["hh_fields_median_db"], r["stable_ref_hv_median_db"]))
