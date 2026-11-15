import json, csv
import numpy as np
from osgeo import gdal
from scipy.ndimage import uniform_filter, label, binary_dilation
import matplotlib.pyplot as plt
gdal.UseExceptions()
meta = {"jun20":("2026-06-20",23),"jul02":("2026-07-02",24),"jul14":("2026-07-14",25),"jul26":("2026-07-26",26),
        "aug19":("2026-08-19",28),"aug31":("2026-08-31",29),"sep12":("2026-09-12",30),"sep24":("2026-09-24",31),
        "oct06":("2026-10-06",32),"oct18":("2026-10-18",33)}
tags = list(meta)
def band(t, b):
    ds = gdal.Open(f"mt_{t}_{b}.tif"); a = ds.GetRasterBand(1).ReadAsArray().astype("float64")
    return 10*np.log10(uniform_filter(a, 5))
HV = {t: band(t, "hvhv") for t in tags}; HH = {t: band(t, "hhhh") for t in tags}
lab, n = label(HV["sep12"] < -18)
ids = [i for i in np.unique(lab[-1, :]) if i != 0]
land = ~binary_dilation(np.isin(lab, ids), iterations=6)
fp = np.zeros_like(land); fp[160:520, 200:680] = True; fp &= land
stack = np.stack([HV[t] for t in tags]); med = np.median(stack, axis=0)
stable = land & (np.abs(stack-med).max(axis=0) < 1.0)
px = (0.3/1200*111.32*np.cos(np.radians(6.0))) * (0.2/800*110.57)
print("land %.0f%%  floodplain px %d  stable-reference px %d" % (100*land.mean(), fp.sum(), stable.sum()))
rows = []
for t in tags:
    r = {"tag": t, "date": meta[t][0], "cycle": meta[t][1]}
    for nm, m in (("land", land), ("floodplain", fp)):
        for pol, D in (("hh", HH), ("hv", HV)):
            v = D[t][m]
            r[f"{pol}_{nm}_median_db"] = round(float(np.median(v)), 2)
            r[f"{pol}_{nm}_mean_db"] = round(float(v.mean()), 2)
            r[f"{pol}_{nm}_std_db"] = round(float(v.std()), 2)
    r["stable_ref_hh_median_db"] = round(float(np.median(HH[t][stable])), 2)
    r["stable_ref_hv_median_db"] = round(float(np.median(HV[t][stable])), 2)
    r["dark_land_km2"] = round(float(((HV[t] < -22) & land).sum()*px), 2)
    r["dark_floodplain_km2"] = round(float(((HV[t] < -22) & fp).sum()*px), 2)
    rows.append(r)
base = [r["dark_land_km2"] for r in rows if r["date"] <= "2026-09-12"]
out = {"site": "Matara / Thihagoda", "bbox_wsen": [80.45, 5.9, 80.75, 6.1], "track": 84, "frame": 5, "crid": "P05023 (provisional)",
       "dark_threshold_hv_db": -22, "baseline_dark_land_km2_mean": round(float(np.mean(base)), 2),
       "baseline_dark_land_km2_std": round(float(np.std(base)), 2), "pixel_km2": round(px, 6),
       "note": "5x5 smoothed, unaligned dB; land excludes sea; floodplain = box rows 160-520, cols 200-680", "dates": rows}
json.dump(out, open("web_matara/stats.json", "w"), indent=1)
with open("web_matara/timeseries.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
d = HV["oct18"] - HV["sep12"]; m = land & (d < -3)
img = np.zeros(m.shape + (4,), "uint8"); img[m] = (0, 229, 255, 210)
plt.imsave("web_matara/change_sep12_oct18.png", img)
print("HV darkened >3 dB on land: %.2f km2" % (m.sum()*px))
print("baseline dark land %.2f +/- %.2f km2" % (out["baseline_dark_land_km2_mean"], out["baseline_dark_land_km2_std"]))
for r in rows: print(r["date"], "HV_land_med", r["hv_land_median_db"], "HV_fp_med", r["hv_floodplain_median_db"], "stable_HV", r["stable_ref_hv_median_db"], "dark", r["dark_land_km2"])
